from __future__ import annotations

import asyncio
import json
import threading
from concurrent.futures import TimeoutError
from importlib.resources import files
from pathlib import Path
from typing import Any

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import GLib, Gtk, WebKit2  # noqa: E402

from .bluetooth_config import apply_with_pkexec, controller_status
from .ble import BleLampClient
from .config import ConfigStore, LampState


GROUP_TARGET = "__all__"


class AsyncWorker:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, name="vc-ble-light-controller-asyncio", daemon=True)
        self.thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def submit(self, coro: Any, callback: Any) -> None:
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)

        def done(task: Any) -> None:
            try:
                result = task.result()
            except Exception as exc:
                GLib.idle_add(callback, None, str(exc))
            else:
                GLib.idle_add(callback, result, None)

        future.add_done_callback(done)

    def run_blocking(self, coro: Any, timeout: float = 5.0) -> None:
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()

    def stop(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)


class RaingelWindow(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(title="VC BLE Light Controller")
        self.set_default_size(920, 660)
        self.set_size_request(920, 660)
        self.set_resizable(True)
        self.set_decorated(False)
        self.set_border_width(0)
        self.set_icon_from_file(str(files("raingel").joinpath("assets/vc-ble-light-controller.svg")))

        self.store = ConfigStore()
        self.lamps = self.store.load()
        self.ble = BleLampClient()
        self.worker = AsyncWorker()

        self.manager = WebKit2.UserContentManager()
        self.manager.register_script_message_handler("raingel")
        self.manager.connect("script-message-received::raingel", self._on_script_message)

        self.webview = WebKit2.WebView.new_with_user_content_manager(self.manager)
        self.add(self.webview)
        self.webview.load_uri(Path(str(files("raingel").joinpath("ui/index.html"))).as_uri())
        self.connect("destroy", self._on_destroy)

    def _on_destroy(self, *_args: Any) -> None:
        self.worker.run_blocking(self.ble.disconnect_all(), timeout=4.0)
        self.worker.stop()
        Gtk.main_quit()

    def _on_script_message(self, _manager: Any, message: Any) -> None:
        try:
            raw = message.get_js_value().to_string()
            payload = json.loads(raw)
            request_id = payload["id"]
            method = payload["method"]
            params = payload.get("params", {})
        except Exception as exc:
            self._emit_response(None, None, f"Invalid message: {exc}")
            return

        try:
            result = self._handle_sync(method, params)
        except NotImplementedError:
            self.worker.submit(self._handle_async(method, params), lambda result, error: self._emit_response(request_id, result, error))
        except Exception as exc:
            self._emit_response(request_id, None, str(exc))
        else:
            self._emit_response(request_id, result, None)

    def _handle_sync(self, method: str, params: dict[str, Any]) -> Any:
        if method == "state":
            return self._state_payload()
        if method == "rename":
            address = str(params["address"])
            name = str(params["name"]).strip() or address
            lamp = self._lamp_by_address(address)
            lamp.name = name
            self._save()
            return self._state_payload()
        if method == "bluetooth_config":
            return controller_status()
        if method == "window_minimize":
            self.iconify()
            return self._window_state()
        if method == "window_toggle_maximize":
            if self.is_maximized():
                self.unmaximize()
            else:
                self.maximize()
            return self._window_state()
        if method == "window_close":
            GLib.idle_add(self.destroy)
            return self._window_state()
        if method == "window_drag_start":
            self.begin_move_drag(
                int(params.get("button", 1)),
                int(params.get("rootX", 0)),
                int(params.get("rootY", 0)),
                int(params.get("time", 0)),
            )
            return self._window_state()
        if method == "window_state":
            return self._window_state()
        raise NotImplementedError

    async def _handle_async(self, method: str, params: dict[str, Any]) -> Any:
        if method == "apply_bluetooth_config":
            return await asyncio.to_thread(apply_with_pkexec)

        if method == "scan":
            discovered = await self.ble.scan(float(params.get("timeout", 8)))
            known = {lamp.address: lamp for lamp in self.lamps}
            for index, item in enumerate(discovered, start=1):
                if item.address not in known:
                    known[item.address] = LampState(address=item.address, name=f"Lámpara {index}")
                known[item.address].connected = False
                known[item.address].last_error = None
            self.lamps = sorted(known.values(), key=lambda lamp: lamp.address)
            self._save()
            return self._state_payload()

        if method == "power":
            addresses = self._target_addresses(params["target"])
            powered = bool(params["powered"])
            errors = await self.ble.set_power(addresses, powered)
            for lamp in self._lamps_for(addresses):
                lamp.powered = powered if errors.get(lamp.address) is None else lamp.powered
                lamp.connected = errors.get(lamp.address) is None
                lamp.last_error = errors.get(lamp.address)
            self._save()
            return self._state_payload()

        if method == "brightness":
            addresses = self._target_addresses(params["target"])
            level = max(0, min(100, int(params["brightness"])))
            errors = await self.ble.set_brightness(addresses, level)
            for lamp in self._lamps_for(addresses):
                if errors.get(lamp.address) is None:
                    lamp.brightness = level
                    lamp.connected = True
                lamp.last_error = errors.get(lamp.address)
            self._save()
            return self._state_payload()

        if method == "color":
            addresses = self._target_addresses(params["target"])
            color = tuple(max(0, min(255, int(value))) for value in params["color"])
            if len(color) != 3:
                raise ValueError("color must contain three RGB values")
            errors = await self.ble.set_color(addresses, color[0], color[1], color[2])
            for lamp in self._lamps_for(addresses):
                if errors.get(lamp.address) is None:
                    lamp.color = color
                    lamp.powered = True
                    lamp.connected = True
                lamp.last_error = errors.get(lamp.address)
            self._save()
            return self._state_payload()

        if method == "scene":
            scene = str(params["scene"])
            target = params["target"]
            scenes = {
                "cine": [(80, 0, 120), (60, 0, 90), (40, 0, 60), (0, 0, 0)],
                "leer": [(255, 240, 200), (255, 245, 210), (255, 235, 190), (255, 240, 200)],
                "fiesta": [(255, 0, 100), (0, 200, 255), (255, 100, 0), (100, 0, 255)],
            }
            if scene not in scenes:
                raise ValueError(f"Unknown scene: {scene}")
            selected = self._lamps_for(self._target_addresses(target))
            for index, lamp in enumerate(selected):
                color = scenes[scene][index % len(scenes[scene])]
                if color == (0, 0, 0):
                    errors = await self.ble.set_power([lamp.address], False)
                    error = errors.get(lamp.address)
                    if error is None:
                        lamp.powered = False
                        lamp.brightness = 0
                        lamp.color = color
                        lamp.connected = True
                    else:
                        lamp.connected = False
                    lamp.last_error = error
                else:
                    color_errors = await self.ble.set_color([lamp.address], *color)
                    brightness_errors = await self.ble.set_brightness([lamp.address], 100)
                    power_errors = await self.ble.set_power([lamp.address], True)
                    error = color_errors.get(lamp.address) or brightness_errors.get(lamp.address) or power_errors.get(lamp.address)
                    if error is None:
                        lamp.powered = True
                        lamp.brightness = 100
                        lamp.color = color
                        lamp.connected = True
                    else:
                        lamp.connected = False
                    lamp.last_error = error
            self._save()
            return self._state_payload()

        raise ValueError(f"Unknown method: {method}")

    def _state_payload(self) -> dict[str, Any]:
        return {"lamps": [lamp.to_dict() for lamp in self.lamps], "groupTarget": GROUP_TARGET}

    def _window_state(self) -> dict[str, Any]:
        return {
            "decorated": self.get_decorated(),
            "resizable": self.get_resizable(),
            "maximized": self.is_maximized(),
            "defaultSize": list(self.get_default_size()),
        }

    def _emit_response(self, request_id: Any, result: Any, error: str | None) -> None:
        payload = json.dumps({"id": request_id, "result": result, "error": error}, ensure_ascii=False)
        self.webview.run_javascript(f"window.Raingel.receive({payload});", None, None, None)

    def _lamp_by_address(self, address: str) -> LampState:
        for lamp in self.lamps:
            if lamp.address == address:
                return lamp
        raise ValueError(f"Unknown lamp: {address}")

    def _target_addresses(self, target: str) -> list[str]:
        if target == GROUP_TARGET:
            return [lamp.address for lamp in self.lamps]
        return [self._lamp_by_address(str(target)).address]

    def _lamps_for(self, addresses: list[str]) -> list[LampState]:
        wanted = set(addresses)
        return [lamp for lamp in self.lamps if lamp.address in wanted]

    def _save(self) -> None:
        self.store.save(self.lamps)


def main() -> int:
    Gtk.init([])
    window = RaingelWindow()
    window.show_all()
    Gtk.main()
    return 0
