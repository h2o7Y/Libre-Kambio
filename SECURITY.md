# Security policy

## Supported version

Security fixes are applied to the latest released version of Libre Kambio.

## Reporting a vulnerability

Please avoid publishing a security issue with exploitation details before the maintainer has had a reasonable opportunity to review it.

If GitHub private vulnerability reporting is enabled for the repository, use **Security → Advisories → Report a vulnerability**. Otherwise open a minimal public issue asking for a private contact channel without including exploit details, credentials, personal data or sensitive logs.

When reporting, include the Libre Kambio version, Flatpak/runtime information, reproducible steps and the smallest safe diagnostic information needed to understand the issue.

## Security model

Libre Kambio does not request filesystem access to the user's home directory in its Flatpak manifest. It requires network access to retrieve official exchange-rate publications and Wayland access for the interface. Flatpak does not provide a built-in per-domain allow-list for the general network permission.

The application has no account system and no analytics/telemetry code. No software can be guaranteed free of vulnerabilities; see [`DISCLAIMER.md`](DISCLAIMER.md).
