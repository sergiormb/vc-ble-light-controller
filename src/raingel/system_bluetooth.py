from __future__ import annotations

import json
import sys

from .bluetooth_config import set_controller_mode_le


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if argv != ["apply"]:
        print("usage: python -m raingel.system_bluetooth apply", file=sys.stderr)
        return 2
    print(json.dumps(set_controller_mode_le(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
