# GitHub repository setup

Recommended upstream repository:

- **Owner:** `h2o7y`
- **Repository:** `Libre-Kambio`
- **Default branch:** `main`
- **Visibility:** public
- **License:** GPL-3.0-only (already included in `LICENSE`)

The visible project name is **Libre Kambio**. Keep the existing Flatpak ID `io.github.h2o7y.LibreKambioCurrency`; changing the App ID would create a different Flatpak application identity.

## Suggested repository description

> Open-source Linux currency converter with instant multi-currency conversion using official ECB, Bank of Russia and optional Latin American central-bank data.

## Suggested topics

`currency-converter`, `exchange-rates`, `flatpak`, `linux`, `kde`, `pyside6`, `python`, `ecb`, `central-bank`, `privacy`, `open-source`

## First publication

From the `Libre-Kambio` repository folder:

```bash
git init
git branch -M main
git add .
git commit -m "Initial public release 1.9.31"
git remote add origin https://github.com/h2o7y/Libre-Kambio.git
git push -u origin main
```

Then create the first version tag:

```bash
git tag -a v1.9.31 -m "Libre Kambio 1.9.31"
git push origin v1.9.31
```

The tag starts the `Build Flatpak` GitHub Actions workflow. The resulting `.flatpak` is uploaded as a workflow artifact.

## Suggested first GitHub Release title

```text
Libre Kambio 1.9.31
```

Suggested short release summary:

> First public GitHub release of Libre Kambio: an open-source Linux currency converter with instant multi-currency conversion, official ECB and Bank of Russia data, official USD pegs, optional Spanish-speaking Latin American central-bank sources, independent cross-checking and customizable currency organization.

Attach `Libre-Kambio-1.9.31.flatpak` if you want users to install the prebuilt bundle directly.

## Recommended GitHub settings

- Enable **Issues**.
- Keep **Actions** enabled.
- Enable **Dependabot alerts** and allow the included Dependabot configuration to update GitHub Actions.
- Enable **Private vulnerability reporting** under Security if available.
- Protect `main` once CI has run successfully at least once; require CI checks before merging pull requests.
- Add the repository description and topics above.

## AI/distribution note

This repository intentionally discloses that the project contains AI-assisted code and documentation. As checked on 22 August 2026, Flathub's generative-AI requirements state that applications containing AI-generated or AI-assisted code/documentation are not accepted unless an exception is granted for a mature, well-maintained project.

Therefore, do **not** submit this repository to Flathub or describe it as Flathub-approved/Flathub-ready while that policy applies and no exception has been granted. Using Flathub to obtain the KDE/PySide runtime for local Flatpak builds is separate from submitting the application to the Flathub store.

Current policy reference: https://docs.flathub.org/docs/for-app-authors/requirements

## Before publishing

Run:

```bash
./scripts/check-release.sh
```

For an end-to-end Fedora/Flatpak smoke test:

```bash
./build-and-install-flatpak.sh
```

Also read [`DISCLAIMER.md`](../DISCLAIMER.md), [`NOTICE.md`](../NOTICE.md) and [`SECURITY.md`](../SECURITY.md) before the first public release.
