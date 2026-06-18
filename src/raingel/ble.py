from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Iterable

from bleak import BleakClient, BleakScanner


DEVICE_NAME_PREFIX = "VC-BLELIGHT"
WRITE_CHARACTERISTIC_UUID = "0000AE01-0000-1000-8000-00805f9b34fb"


@dataclass(frozen=True)
class DiscoveredLamp:
    address: str
    name: str
    rssi: int | None = None


def _byte(value: int, name: str) -> int:
    if not isinstance(value, int) or value < 0 or value > 255:
        raise ValueError(f"{name} must be an integer between 0 and 255")
    return value


def power_command(powered: bool) -> bytes:
    return bytes([0x01, 0x01 if powered else 0x00])


def brightness_command(level: int) -> bytes:
    return bytes([0x02, _byte(level, "brightness")])


def color_command(r: int, g: int, b: int) -> bytes:
    return bytes([0x03, _byte(r, "red"), _byte(g, "green"), _byte(b, "blue")])


def is_supported_name(name: str | None) -> bool:
    return bool(name and name.startswith(DEVICE_NAME_PREFIX))


class BleLampClient:
    def __init__(self) -> None:
        self._clients: dict[str, BleakClient] = {}
        self._devices: dict[str, Any] = {}

    async def scan(self, timeout: float = 8.0) -> list[DiscoveredLamp]:
        devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
        lamps: list[DiscoveredLamp] = []
        for device, advertisement in devices.values():
            name = advertisement.local_name or device.name or ""
            if is_supported_name(name):
                self._devices[device.address] = device
                lamps.append(
                    DiscoveredLamp(
                        address=device.address,
                        name=name,
                        rssi=getattr(advertisement, "rssi", None),
                    )
                )
        return sorted(lamps, key=lambda item: item.address)

    async def connect(self, address: str) -> None:
        client = self._clients.get(address)
        if client and client.is_connected:
            return
        device = await self._device_for(address)
        client = BleakClient(device, timeout=15.0)
        await asyncio.wait_for(client.connect(), timeout=18.0)
        self._clients[address] = client

    async def disconnect_all(self) -> None:
        clients = list(self._clients.values())
        self._clients.clear()
        for client in clients:
            if client.is_connected:
                try:
                    await client.disconnect()
                except Exception:
                    pass

    async def write(self, address: str, payload: bytes) -> None:
        await self.connect(address)
        client = self._clients[address]
        await asyncio.wait_for(
            client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, payload, response=False),
            timeout=10.0,
        )

    async def set_power(self, addresses: Iterable[str], powered: bool) -> dict[str, str | None]:
        return await self._write_many(addresses, power_command(powered))

    async def set_brightness(self, addresses: Iterable[str], level: int) -> dict[str, str | None]:
        return await self._write_many(addresses, brightness_command(level))

    async def set_color(self, addresses: Iterable[str], r: int, g: int, b: int) -> dict[str, str | None]:
        return await self._write_many(addresses, color_command(r, g, b))

    async def _write_many(self, addresses: Iterable[str], payload: bytes) -> dict[str, str | None]:
        results: dict[str, str | None] = {}
        for address in addresses:
            try:
                await self.write(address, payload)
            except Exception as exc:  # BLE failures should be visible but not crash the app.
                results[address] = str(exc)
            else:
                results[address] = None
        return results

    async def _device_for(self, address: str) -> Any:
        device = self._devices.get(address)
        if device is not None:
            return device
        devices = await BleakScanner.discover(timeout=4.0, return_adv=True)
        for found, advertisement in devices.values():
            name = advertisement.local_name or found.name or ""
            if found.address == address or (found.address.upper() == address.upper() and is_supported_name(name)):
                self._devices[address] = found
                return found
        return address
