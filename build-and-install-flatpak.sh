#!/usr/bin/env bash
set -euo pipefail

APP_ID="io.github.h2o7y.LibreKambioCurrency"
RUNTIME="6.11"
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

echo "Ejecutando pruebas de lógica antes de construir..."
python3 -m py_compile main.py app_logic.py rates.py latam_rates.py
python3 -m json.tool io.github.h2o7y.LibreKambioCurrency.json >/dev/null
python3 -m unittest discover -s tests -q
echo "Pruebas de lógica: OK"

if ! command -v flatpak >/dev/null 2>&1; then
  echo "Error: Flatpak no está instalado. En Fedora: sudo dnf install flatpak" >&2
  exit 1
fi

if ! command -v flatpak-builder >/dev/null 2>&1; then
  echo "Falta flatpak-builder. Instalándolo con DNF..."
  sudo dnf install -y flatpak-builder
fi

if ! flatpak remotes --columns=name | grep -qx flathub; then
  echo "Añadiendo Flathub para tu usuario..."
  flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
fi

echo "Instalando runtime/SDK necesarios para construir..."
flatpak install --user -y flathub \
  "org.kde.Platform//$RUNTIME" \
  "org.kde.Sdk//$RUNTIME" \
  "io.qt.PySide.BaseApp//$RUNTIME"


# Elimina únicamente iconos exportados anteriores de esta aplicación para evitar
# que Plasma siga resolviendo una versión cacheada del mismo nombre.
EXPORT_BASE="$HOME/.local/share/flatpak/exports/share/icons/hicolor"
for size in 16x16 22x22 32x32 48x48 64x64 128x128 256x256 512x512 scalable; do
  for name in io.github.h2o7y.LibreKambioCurrency; do
    rm -f "$EXPORT_BASE/$size/apps/$name.png" "$EXPORT_BASE/$size/apps/$name.svg" 2>/dev/null || true
  done
done


# Limpia restos de la antigua instalación local (pre-Flatpak) y variantes de icono
# usadas por versiones anteriores. Estos archivos pertenecen únicamente a esta app.
rm -f "$HOME/.local/share/applications/libre-kambio-currency.desktop" 2>/dev/null || true
rm -f "$HOME/.local/bin/libre-kambio-currency" 2>/dev/null || true
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/io.github.h2o7y.LibreKambioCurrency.svg" 2>/dev/null || true

echo "Construyendo e instalando $APP_ID en el sandbox Flatpak..."
rm -rf .flatpak-build
flatpak-builder --user --install --force-clean .flatpak-build io.github.h2o7y.LibreKambioCurrency.json


# Si el usuario tenía un acceso directo de esta app copiado al Escritorio, actualiza
# solo su línea Icon= para que no conserve el icono antiguo incrustado por Plasma.
DESKTOP_DIR=""
if command -v xdg-user-dir >/dev/null 2>&1; then
  DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
fi
if [[ -n "$DESKTOP_DIR" && -d "$DESKTOP_DIR" ]]; then
  while IFS= read -r -d '' shortcut; do
    if grep -Eq '(^X-Flatpak=io\.github\.h2o7y\.LibreKambioCurrency$|Libre Kambio( Currency)?)' "$shortcut" 2>/dev/null; then
      sed -i 's/^Icon=.*/Icon=io.github.h2o7y.LibreKambioCurrency/' "$shortcut" 2>/dev/null || true
    fi
  done < <(find "$DESKTOP_DIR" -maxdepth 1 -type f -name '*.desktop' -print0 2>/dev/null)
fi

echo
echo "Comprobando que la aplicación arranca dentro del Flatpak..."
if ! flatpak run --env=QT_QPA_PLATFORM=offscreen "$APP_ID" --smoke-test; then
  echo >&2
  echo "ERROR: la prueba real de arranque ha fallado. La instalación se ha construido, pero la app no ha pasado la comprobación de GUI." >&2
  echo "Ejecuta: flatpak run $APP_ID" >&2
  exit 1
fi
echo "Prueba de arranque: OK"

echo
echo "Instalado correctamente."
echo "Abrir: flatpak run $APP_ID"
echo "Permisos efectivos:"
flatpak info --show-permissions "$APP_ID" || true

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$HOME/.local/share/flatpak/exports/share/applications" >/dev/null 2>&1 || true
fi
if command -v kbuildsycoca6 >/dev/null 2>&1; then
  kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
fi
