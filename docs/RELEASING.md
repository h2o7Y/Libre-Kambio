# Releasing Libre Kambio

## 1. Prepare the version

For a new release `X.Y.Z`, update all version-bearing locations:

- `APP_VERSION` in `main.py`
- `USER_AGENT` strings in `rates.py` and `latam_rates.py`
- bundle filename/version in `build-bundle-flatpak.sh`
- newest `<release>` entry in `io.github.h2o7y.LibreKambioCurrency.metainfo.xml`
- `CHANGELOG.md`
- current-release text in `README.md` and `README.es.md`

Do not change the Flatpak ID (`io.github.h2o7y.LibreKambioCurrency`) for ordinary releases.

## 2. Run checks

```bash
./scripts/check-release.sh
```

On Fedora KDE, also run the real Flatpak build/install/smoke test:

```bash
./build-and-install-flatpak.sh
```

Optionally build the distributable bundle locally:

```bash
./build-bundle-flatpak.sh
```

## 3. Commit and tag

```bash
git add .
git commit -m "Release X.Y.Z"
git tag -a vX.Y.Z -m "Libre Kambio X.Y.Z"
git push origin main
git push origin vX.Y.Z
```

Pushing a `v*` tag starts `.github/workflows/flatpak.yml`, which builds a `Libre-Kambio-X.Y.Z.flatpak` bundle and stores it as a workflow artifact.

## 4. Create the GitHub Release

Create a GitHub Release from the `vX.Y.Z` tag, summarize the relevant `CHANGELOG.md` entries and attach the built `.flatpak` artifact if you want to distribute a ready-to-install bundle in addition to GitHub's automatic source archives.

Before publishing the release, confirm that the README links to the current [`DISCLAIMER.md`](../DISCLAIMER.md) and that any material change to data-source behavior is documented.

## 5. Source/parser release discipline

If a release changes exchange-rate parsing or source endpoints:

- verify the endpoint belongs to the official monetary authority;
- add/update regression fixtures;
- preserve the missing-publication safety behavior;
- update both Spanish and English user-facing text if the visible status changes.

## 6. Distribution-policy discipline

Libre Kambio contains AI-assisted code/documentation. Do not submit a release to a software catalogue whose current rules prohibit such content. In particular, review Flathub's current generative-AI requirements before considering any future submission and do not claim Flathub approval without an actual accepted submission/exception.
