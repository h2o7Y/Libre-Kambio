#!/usr/bin/env bash
set -euo pipefail

APP_ID="io.github.h2o7y.LibreKambioCurrency"
RUNTIME="6.11"
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

if ! command -v flatpak >/dev/null 2>&1 || ! command -v flatpak-builder >/dev/null 2>&1; then
  echo "Necesitas flatpak y flatpak-builder." >&2
  echo "Fedora: sudo dnf install flatpak flatpak-builder" >&2
  exit 1
fi
if ! flatpak remotes --columns=name | grep -qx flathub; then
  flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
fi
flatpak install --user -y flathub \
  "org.kde.Platform//$RUNTIME" \
  "org.kde.Sdk//$RUNTIME" \
  "io.qt.PySide.BaseApp//$RUNTIME"
rm -rf .flatpak-build .flatpak-repo
flatpak-builder --repo=.flatpak-repo --force-clean .flatpak-build io.github.h2o7y.LibreKambioCurrency.json
flatpak build-bundle .flatpak-repo Libre-Kambio-1.9.33.flatpak "$APP_ID"
echo "Creado: $HERE/Libre-Kambio-1.9.33.flatpak"
