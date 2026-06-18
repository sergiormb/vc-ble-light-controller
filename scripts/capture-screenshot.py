#!/usr/bin/env python3
from __future__ import annotations

import sys
import os
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("WEBKIT_DISABLE_COMPOSITING_MODE", "1")

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from raingel.app import RaingelWindow


def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/screenshot.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_config = tempfile.TemporaryDirectory(prefix="vc-ble-light-controller-shot-")
    os.environ["XDG_CONFIG_HOME"] = temp_config.name
    config_dir = Path(temp_config.name) / "vc-ble-light-controller"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "lights.json").write_text(
        json.dumps(
            {
                "lamps": [
                    {
                        "address": "1C:D5:EA:C9:C9:9A",
                        "name": "Lámpara 1",
                        "powered": True,
                        "color": [255, 150, 100],
                        "brightness": 100,
                        "connected": True,
                        "last_error": None,
                    },
                    {
                        "address": "F5:09:7C:A8:DA:7A",
                        "name": "Lámpara 2",
                        "powered": True,
                        "color": [60, 200, 100],
                        "brightness": 100,
                        "connected": True,
                        "last_error": None,
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    Gtk.init([])
    window = RaingelWindow()
    window.show_all()

    def capture() -> bool:
        gdk_window = window.get_window()
        if gdk_window is None:
            return True
        width = window.get_allocated_width()
        height = window.get_allocated_height()
        pixbuf = Gdk.pixbuf_get_from_window(gdk_window, 0, 0, width, height)
        if pixbuf is None:
            return True
        pixbuf.savev(str(output), "png", [], [])
        window.destroy()
        Gtk.main_quit()
        return False

    GLib.timeout_add(1800, capture)
    GLib.timeout_add(6000, Gtk.main_quit)
    Gtk.main()
    return 0 if output.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
