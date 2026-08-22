# Libre Kambio

[![CI](https://github.com/h2o7y/Libre-Kambio/actions/workflows/ci.yml/badge.svg)](https://github.com/h2o7y/Libre-Kambio/actions/workflows/ci.yml)
[![License: GPL-3.0-only](https://img.shields.io/badge/license-GPL--3.0--only-blue.svg)](LICENSE)

**Open-source currency converter for Linux**

Instant, simultaneous multi-currency conversion using official exchange-rate data from the **European Central Bank (ECB)**, the **Bank of Russia (CBR)** and, optionally, selected central banks in Spanish-speaking Latin America.

**Current release: 1.9.31**

[Español](README.es.md)

## Why Libre Kambio

Libre Kambio is a privacy-friendly Linux desktop currency converter built around official central-bank reference data rather than commercial exchange-rate aggregators.

- **Instant multi-currency conversion:** enter an amount once and see the conversion across all visible currencies at the same time.
- **ECB primary source:** supported euro reference rates come primarily from the European Central Bank.
- **Bank of Russia data:** official Bank of Russia rates provide additional currencies and independent cross-checking where appropriate.
- **Official USD pegs:** selected currencies use their official fixed USD relationships when applicable.
- **Optional Latin American sources:** ARS, CLP, COP, PYG, PEN and UYU can be enabled individually and use their respective official monetary authorities.
- **Independent cross-checking:** the app keeps primary sources and verification sources separate and exposes publication dates/statuses.
- **Flexible organization:** custom groups, manual ordering, regional organization and visibility controls.
- **Bilingual interface:** Spanish and English, with persistent manual language selection.
- **Privacy-friendly:** no accounts, analytics or telemetry; the Flatpak requests only network and Wayland access.

**Official central-bank data · Instant multi-currency conversion · ECB + Bank of Russia · USD pegs · Independent cross-checking · Optional Latin American central-bank sources · Custom organization · Privacy-friendly · Open source · Linux desktop**

## Important disclaimer

> **Reference information only.** Exchange rates and conversions may be delayed, incomplete or inaccurate and are not guaranteed transaction rates. Libre Kambio does not provide financial, investment, accounting, tax or legal advice. Verify important values with the original official source and, where appropriate, your bank or professional adviser. **Use of the software and its output is at your own risk.**

The full warranty disclaimer and limitation of liability are in [`DISCLAIMER.md`](DISCLAIMER.md). They apply in addition to the warranty and liability provisions of the GNU GPLv3 and only to the maximum extent permitted by applicable law.

## Data-source safety

Libre Kambio is deliberately conservative about stale or missing data:

- If a network/source request fails, the app may use the last successfully stored value and clearly mark it as a local copy.
- If an official publication is successfully reached but the expected rate is missing, the app does **not** silently reuse an older rate for that currency.
- Cross-checks never masquerade as primary sources.
- Source dates and status information remain visible so differences between publication days are not hidden.

The parser implementations and regression fixtures live in [`rates.py`](rates.py), [`latam_rates.py`](latam_rates.py) and [`tests/`](tests/).

## Official data sources

| Purpose | Authority |
|---|---|
| Primary EUR reference rates | European Central Bank (ECB) |
| RUB, UAH, additional currencies and cross-checking | Bank of Russia (CBR) |
| AED peg | Central Bank of the UAE |
| SAR peg | Saudi Central Bank (SAMA) |
| QAR peg | Qatar Central Bank |
| BHD parity | Central Bank of Bahrain |
| OMR parity | Central Bank of Oman |
| ARS | Banco Central de la República Argentina (BCRA) |
| CLP | Banco Central de Chile (BCCh) |
| COP | Banco de la República (Colombia) |
| PYG | Banco Central del Paraguay (BCP) |
| PEN | Banco Central de Reserva del Perú (BCRP) |
| UYU | Banco Central del Uruguay (BCU) |
| Optional indicative secondary cross-check | Banco Central de Bolivia (BCB) |

The source URLs are kept in the code so they can be audited. These institutions do **not** sponsor, endorse, maintain or guarantee Libre Kambio. See [`NOTICE.md`](NOTICE.md).

The ECB itself describes its euro foreign exchange reference rates as being published for information purposes and strongly discourages their use for transaction purposes. Libre Kambio therefore treats all displayed rates as reference information, not executable market prices.

## Privacy and Flatpak permissions

The Flatpak manifest grants only:

- `--share=network` — required to download official exchange-rate publications.
- `--socket=wayland` — required to display the application.

It does **not** request access to `$HOME`, Documents, Downloads, devices, audio, camera, microphone, X11 or the system bus.

Local preferences and the last successful source data are stored inside the application's Flatpak data/config area. Flatpak's network permission is general rather than domain-scoped; the application code itself requests the official endpoints defined in [`rates.py`](rates.py) and [`latam_rates.py`](latam_rates.py).

## Install on Fedora KDE

The included helper script installs the required Flatpak build tools/runtimes when needed, runs the automated tests, builds the application, installs it for the current user and performs an off-screen GUI smoke test inside the installed sandbox.

```bash
./build-and-install-flatpak.sh
```

Launch it with:

```bash
flatpak run io.github.h2o7y.LibreKambioCurrency
```

Inspect the effective sandbox permissions with:

```bash
flatpak info --show-permissions io.github.h2o7y.LibreKambioCurrency
```

The visible product name is **Libre Kambio**. The existing Flatpak application ID remains `io.github.h2o7y.LibreKambioCurrency` to preserve application identity and compatibility across upgrades.

## Build a reusable `.flatpak` bundle

```bash
./build-bundle-flatpak.sh
```

For version 1.9.31 this creates:

```text
Libre-Kambio-1.9.31.flatpak
```

## Development checks

The logic and parser tests do not require PySide6:

```bash
./scripts/check-release.sh
```

Equivalent core commands:

```bash
python3 -m py_compile main.py app_logic.py rates.py latam_rates.py
python3 -m json.tool io.github.h2o7y.LibreKambioCurrency.json >/dev/null
python3 -m unittest discover -s tests -v
```

GitHub Actions runs the source checks on pushes and pull requests. A separate workflow can build a Flatpak bundle on demand or for version tags.

## AI-assisted development disclosure

Libre Kambio has been developed with **generative-AI assistance**, including assistance with source code, tests and documentation. The project maintainer selects, reviews, integrates, tests and maintains the published project.

This disclosure is intentional. It does not transfer responsibility or provide any warranty regarding AI-assisted output; the software remains subject to the project licence and disclaimer.

### Distribution note

As checked for this release on **22 August 2026**, Flathub's generative-AI policy states that applications containing AI-generated or AI-assisted code or documentation are not accepted except where Flathub grants an exception for a mature, well-maintained project. For that reason, **GitHub and GitHub Releases are the intended public distribution channel for Libre Kambio at present**, and this repository should not be represented as Flathub-approved or Flathub-ready.

See [`NOTICE.md`](NOTICE.md) for the development disclosure and [`docs/GITHUB_SETUP.md`](docs/GITHUB_SETUP.md) for repository/release setup.

## Contributing

Contributions are welcome. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request, especially the bilingual-UI and official-source rules.

For release steps, see [`docs/RELEASING.md`](docs/RELEASING.md).

## Security

See [`SECURITY.md`](SECURITY.md) for reporting guidance.

## License

Libre Kambio is licensed under **GNU GPL v3 only (`GPL-3.0-only`)**. See [`LICENSE`](LICENSE).

The software is provided **without warranty**, subject to the GPLv3 and applicable law. See [`DISCLAIMER.md`](DISCLAIMER.md).

## Project note

Libre Kambio is an independent Python/Qt implementation. It was inspired in part by interaction/customization ideas from Converter NOW, but does not include copied Converter NOW source code. See [`NOTICE.md`](NOTICE.md).
