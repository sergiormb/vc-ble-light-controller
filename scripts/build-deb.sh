#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

version="$(PYTHONPATH=src python3 - <<'PY'
from raingel import __version__
print(__version__)
PY
)"
package="vc-ble-light-controller_${version}_all"
root="build/${package}"
deb="dist/${package}.deb"

rm -rf "$root"
mkdir -p \
  "$root/DEBIAN" \
  "$root/opt/vc-ble-light-controller" \
  "$root/usr/bin" \
  "$root/usr/share/applications" \
  "$root/usr/share/icons/hicolor/scalable/apps"

cp -a src pyproject.toml README.md "$root/opt/vc-ble-light-controller/"
if [ -d docs ]; then
  cp -a docs "$root/opt/vc-ble-light-controller/"
fi
find "$root/opt/vc-ble-light-controller" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$root/opt/vc-ble-light-controller" -type d -name "*.egg-info" -prune -exec rm -rf {} +

cat > "$root/usr/bin/vc-ble-light-controller" <<'EOF'
#!/usr/bin/env bash
export PYTHONPATH="/opt/vc-ble-light-controller/src${PYTHONPATH:+:$PYTHONPATH}"
exec /usr/bin/python3 -s -m raingel "$@"
EOF
chmod 0755 "$root/usr/bin/vc-ble-light-controller"

install -m 0644 packaging/vc-ble-light-controller.desktop "$root/usr/share/applications/vc-ble-light-controller.desktop"
install -m 0644 src/raingel/assets/vc-ble-light-controller.svg "$root/usr/share/icons/hicolor/scalable/apps/vc-ble-light-controller.svg"

installed_size="$(du -sk "$root" | awk '{print $1}')"
cat > "$root/DEBIAN/control" <<EOF
Package: vc-ble-light-controller
Version: ${version}
Section: utils
Priority: optional
Architecture: all
Maintainer: Sergiormb <sergiormb@localhost>
Installed-Size: ${installed_size}
Depends: python3, python3-gi, python3-bleak, gir1.2-gtk-3.0, gir1.2-webkit2-4.1, bluez, pkexec | policykit-1
Conflicts: raingel
Replaces: raingel
Description: Unofficial desktop BLE controller for VC-BLELIGHT lamps
 VC BLE Light Controller controls compatible BLE LED lamps from an Ubuntu desktop.
EOF

desktop-file-validate "$root/usr/share/applications/vc-ble-light-controller.desktop"
mkdir -p dist
dpkg-deb --build --root-owner-group "$root" "$deb"
echo "$deb"
