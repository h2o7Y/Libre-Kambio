# Contributing to Libre Kambio

Thank you for considering a contribution.

## Before opening a pull request

1. Keep changes focused and explain the user-visible behavior they change.
2. Run `./scripts/check-release.sh`.
3. Add or update regression tests for parser/source changes.
4. Do not commit user settings, caches, logs, personal group names, local paths, credentials or downloaded private data.
5. Confirm that code, text, fixtures and assets you contribute are legally redistributable under the project's licence.

## Bilingual UI rule

User-facing interface changes must be updated in **Spanish and English in the same pull request**. The two versions should convey the same meaning rather than being literal-but-inconsistent translations.

## Exchange-rate source rule

For currency-rate changes:

- Prefer the currency's official central bank/monetary authority or another first-party official source.
- Do not silently replace a primary official source with an aggregator.
- If an official publication is reached but the expected value is absent, preserve the app's fail-safe behavior rather than reusing stale data invisibly.
- A transport/read failure may use a previously validated local copy only when the UI clearly marks that state.
- Keep cross-check sources separate from primary sources.
- Include parser fixtures for the response format being supported, including failure/edge cases when practical.

## AI-assisted contributions

AI-assisted contributions are allowed in this GitHub project, but the contributor remains responsible for the contribution. Review generated output carefully, test it, and do not submit code or text whose licence/provenance you cannot reasonably assess.

For substantial AI-assisted contributions, disclose that assistance in the pull-request description. The disclosure does not replace review, testing or the contributor's responsibility for what is submitted.

## Code and packaging checks

Run:

```bash
./scripts/check-release.sh
```

For a full local Flatpak installation/smoke test on Fedora KDE:

```bash
./build-and-install-flatpak.sh
```

## Pull requests

A useful pull request description includes:

- what was wrong or missing;
- what changed;
- which official source/format is involved, if applicable;
- tests added or updated;
- whether the change affects Spanish/English UI text, Flatpak permissions or source endpoints;
- whether substantial AI assistance was used.
