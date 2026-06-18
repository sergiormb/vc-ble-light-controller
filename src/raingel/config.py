from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


APP_ID = "vc-ble-light-controller"
LEGACY_APP_ID = "raingel"


@dataclass
class LampState:
    address: str
    name: str
    powered: bool = False
    color: tuple[int, int, int] = (167, 139, 250)
    brightness: int = 100
    connected: bool = False
    last_error: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LampState":
        color = payload.get("color", (167, 139, 250))
        if not isinstance(color, (list, tuple)) or len(color) != 3:
            color = (167, 139, 250)
        return cls(
            address=str(payload["address"]),
            name=str(payload.get("name") or payload["address"]),
            powered=bool(payload.get("powered", False)),
            color=tuple(max(0, min(255, int(value))) for value in color),
            brightness=max(0, min(100, int(payload.get("brightness", 100)))),
            connected=bool(payload.get("connected", False)),
            last_error=payload.get("last_error"),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["color"] = list(self.color)
        return payload


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / APP_ID
    return Path.home() / ".config" / APP_ID


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or config_dir() / "lights.json"
        self.legacy_path = Path.home() / ".config" / LEGACY_APP_ID / "lights.json"

    def load(self) -> list[LampState]:
        path = self.path
        if not path.exists() and self.legacy_path.exists():
            path = self.legacy_path
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        lamps = data.get("lamps", []) if isinstance(data, dict) else []
        result: list[LampState] = []
        for lamp in lamps:
            if isinstance(lamp, dict) and lamp.get("address"):
                result.append(LampState.from_dict(lamp))
        if path == self.legacy_path and result:
            self.save(result)
        return result

    def save(self, lamps: list[LampState]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"lamps": [lamp.to_dict() for lamp in lamps]}
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
