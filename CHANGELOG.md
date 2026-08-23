# Changelog

All notable changes to Libre Kambio are documented here.

## 1.9.32 — 2026-08-23

- Fixed group reordering so groups can only be moved above or below one another.
- Disabled native Qt drag/drop in the Groups list and replaced it with safe manual between-row reordering.
- Dropping a group over another group can no longer nest, overwrite or make a group disappear.

## 1.9.31 — 2026-08-22

- Shortened the public product name to **Libre Kambio** while keeping the existing Flatpak App ID for upgrade compatibility.
- Added bilingual legal disclaimers, an in-app reference-rate warning and explicit no-affiliation wording for official data sources.
- Added transparent AI-assisted-development disclosure and GitHub-first distribution guidance reflecting current Flathub policy.
- Renamed the recommended public repository and release artifact to `Libre-Kambio` / `Libre-Kambio-X.Y.Z.flatpak`.

- Fixed CLP/BCCh by preferring the official full BDE `DOLAR_OBS_ADO` table.
- Added a second official BDE route before homepage/daily-indicator fallbacks.
- Preserved `ND` cells while parsing horizontal BCCh tables to keep date/value columns aligned.
- Selects the newest numeric BCCh observation by date.
- CLP's visible source link now opens the official BDE table used by the app.
- Spanish uses the compact label `HISPAM`; English uses `LATAM` and `Latin American currencies`.
- Added public GitHub repository documentation, CI/Flatpak workflows, issue templates and release checks.
- Expanded the automated suite to 164 tests.

## 1.9.30 — 2026-08-22

- Hardened the BCCh parser for Spanish/English portal output, UTF-8/Windows-1252, Unicode escapes and decimal separators.
- Added homepage and BDE fallbacks for weekends/holidays where the daily indicator view can return `ND`.

## 1.9.29 — 2026-08-22

- Fixed ARS/BCRA, CLP/BCCh and UYU/BCU optional-source handling.
- BCRA now prefers Monetary Statistics API v4 and identifies Comunicación A 3500 by description.
- BCU now prefers its documented public SOAP quotation service, with official-page fallbacks.
- Added regression fixtures for current BCRA, BCCh and BCU response formats.

## 1.9.28 — 2026-08-22

- Fixed the installed-Flatpak smoke test so Spanish option-label checks no longer depend on the build environment locale.
- Hardened ARS, CLP, COP, PYG, PEN and UYU source readers.
- Added compact source-download status in the header and separated download failures from missing publications.
- Preserved the safety rule: a reached official publication that omits an expected rate does not silently reuse an older value.
- New installations default to two decimal places, while zero-minor-unit currencies remain integer-only.
- Added configurable decimal separators, flag position and currency-symbol position.

## 1.9.27 — 2026-08-22

- Standardized option wording to `Mostrar… / Show…` and removed obsolete `(actual)/(current)` suffixes.
- Added individually opt-in ARS, CLP, COP, PYG, PEN and UYU.
- Added Banco Central de Bolivia as an indicative secondary cross-check for supported optional currencies.

## 1.9.26 — 2026-08-22

- Exact `.00` / `,00` result fractions can be hidden.
- Added verification display mode: always show checks or only warnings/problems.
- Verification dates now distinguish ECB reference date, CBR official-rate date and CBR publication date.

## 1.9.14 — 2026-08-21

- Fixed region-order smoke-test coverage.
- Improved multi-selection group assignment and persistent group colours.
- Refined verification/base-currency visual emphasis.

## 1.9.12 — 2026-08-21

- New installations default to two decimal places.
- Added decimal-separator modes and copy-without-thousands-grouping behavior.
- Standardized the application/Flatpak ID as `io.github.h2o7y.LibreKambioCurrency`.
- Expanded automated coverage.

## 1.9.6 — 2026-08-21

- Added fixed two-decimal display mode.
- Refined region palettes and geographic grouping labels.

## 1.9.5 — 2026-08-21

- Renamed the visible application to Libre Kambio Currency.
- Split Currency and Region into separate management columns.
- Made region colours deterministic across management views.

## 1.9.4 — 2026-08-21

- Added geographic region labels and sorting.
- Added primary-source omission protection with visible safety warnings.
- Removed XDR/SDR from selectable currencies.

## 1.9.2 — 2026-08-21

- Added session undo for currency/group organization (up to 10 steps).
- Added optional currencies already available in the CBR daily feed.
- Corrected handling of CBR-only currencies so they are not falsely cross-checked against themselves.

## 1.9.1 — 2026-08-21

- Compact update-status wording.
- Expanded verification tooltips with formulas, thresholds and date context.
- Added packaging regression tests to ensure personal settings/custom groups are not shipped.

## 1.9.0 — 2026-08-21

- Fixed card rendering after refresh and currency persistence across partial source updates.
- Added finite-number validation for the amount field.
- Added OS language detection with persistent manual override.
- Removed BGN after Bulgaria's euro adoption and the ECB feed change.
- Strengthened the installed-Flatpak GUI smoke test.
- Added the initial open-source/GitHub project metadata and CI structure.
