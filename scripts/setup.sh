#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
if ! python3 -m venv --system-site-packages .venv; then
  cat <<'EOF'

No se pudo crear .venv porque falta el modulo venv/ensurepip del sistema.
En Ubuntu instala el paquete correspondiente y vuelve a ejecutar este script:

  sudo apt install python3.14-venv
  ./scripts/setup.sh

Si no puedes instalar paquetes del sistema, usa el fallback de usuario:

  ./scripts/setup-user.sh

EOF
  exit 1
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
