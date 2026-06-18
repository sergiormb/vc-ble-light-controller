from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


MAIN_CONF = Path("/etc/bluetooth/main.conf")
BACKUP_CONF = Path("/etc/bluetooth/main.conf.vc-ble-light-controller.bak")

_MODE_RE = re.compile(r"^\s*#?\s*ControllerMode\s*=\s*(?P<mode>\S+)\s*$")


def read_controller_mode(path: Path = MAIN_CONF) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        match = _MODE_RE.match(line)
        if match and not line.lstrip().startswith("#"):
            return match.group("mode").strip()
    return None


def controller_status(path: Path = MAIN_CONF) -> dict[str, Any]:
    mode = read_controller_mode(path)
    return {
        "path": str(path),
        "mode": mode,
        "isLe": mode == "le",
        "exists": path.exists(),
    }


def set_controller_mode_le(
    path: Path = MAIN_CONF,
    backup_path: Path = BACKUP_CONF,
    restart_bluetooth: bool = True,
) -> dict[str, Any]:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    changed = False
    found = False

    for index, line in enumerate(lines):
        if _MODE_RE.match(line):
            newline = "\n" if line.endswith("\n") else ""
            lines[index] = f"ControllerMode = le{newline}"
            found = True
            changed = lines[index] != line
            break

    if not found:
        inserted = False
        for index, line in enumerate(lines):
            if line.strip() == "[General]":
                lines.insert(index + 1, "ControllerMode = le\n")
                inserted = True
                changed = True
                break
        if not inserted:
            lines.insert(0, "[General]\nControllerMode = le\n")
            changed = True

    if changed:
        if not backup_path.exists():
            shutil.copy2(path, backup_path)
        path.write_text("".join(lines), encoding="utf-8")

    if restart_bluetooth:
        subprocess.run(["systemctl", "restart", "bluetooth"], check=True)

    status = controller_status(path)
    status["changed"] = changed
    status["backupPath"] = str(backup_path)
    return status


def apply_with_pkexec() -> dict[str, Any]:
    package_parent = str(Path(__file__).resolve().parents[1])
    code = (
        "import sys; "
        f"sys.path.insert(0, {package_parent!r}); "
        "from raingel.system_bluetooth import main; "
        "raise SystemExit(main(['apply']))"
    )
    completed = subprocess.run(
        ["pkexec", sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(detail or f"pkexec failed with exit code {completed.returncode}")
    return controller_status()
