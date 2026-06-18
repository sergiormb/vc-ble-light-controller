#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
if [ -x .venv/bin/vc-ble-light-controller ]; then
  exec .venv/bin/vc-ble-light-controller "$@"
fi

export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -s -m raingel "$@"
