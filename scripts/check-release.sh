#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

echo "Checking Python syntax..."
python3 -m py_compile main.py app_logic.py rates.py latam_rates.py

echo "Checking Flatpak manifest JSON..."
python3 -m json.tool io.github.h2o7y.LibreKambioCurrency.json >/dev/null

echo "Checking XML syntax..."
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET
ET.parse(Path("io.github.h2o7y.LibreKambioCurrency.metainfo.xml"))
PY

echo "Checking shell syntax..."
bash -n build-and-install-flatpak.sh
bash -n build-bundle-flatpak.sh
bash -n uninstall-flatpak.sh
bash -n scripts/check-release.sh

echo "Checking version consistency..."
python3 - <<'PY'
from pathlib import Path
import re
import xml.etree.ElementTree as ET

main = Path("main.py").read_text(encoding="utf-8")
match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', main, re.MULTILINE)
if not match:
    raise SystemExit("APP_VERSION not found in main.py")
version = match.group(1)

for path in ("rates.py", "latam_rates.py", "build-bundle-flatpak.sh"):
    text = Path(path).read_text(encoding="utf-8")
    if version not in text:
        raise SystemExit(f"{path} does not contain current version {version}")

root = ET.parse("io.github.h2o7y.LibreKambioCurrency.metainfo.xml").getroot()
release = root.find("./releases/release")
if release is None or release.attrib.get("version") != version:
    raise SystemExit("Newest MetaInfo release does not match APP_VERSION")

print(f"Version {version}: consistent")
PY

echo "Running unit/regression/packaging tests..."
python3 -m unittest discover -s tests -q

echo "All release checks passed."
