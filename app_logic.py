#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import math
import os
from collections.abc import Mapping, Sequence


def parse_amount_text(text: str) -> float | None:
    """Parse user-entered amounts in common Spanish/international formats.

    Accepted examples: ``12,5``, ``12.5``, ``1.234,56`` and ``1,234.56``.
    Empty, malformed and non-finite inputs (NaN/Infinity) return ``None``.
    """
    raw = str(text or "").strip().replace(" ", "")
    if not raw:
        return None

    if "," in raw and "." in raw:
        # The last separator is treated as the decimal separator. The other
        # one is grouping. This matches the formats users are most likely to
        # paste from Spanish and English-language documents.
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    else:
        raw = raw.replace(",", ".")

    try:
        value = float(raw)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _normalise_locale_token(value: str | None) -> str:
    if not value:
        return ""
    token = str(value).strip().split(":", 1)[0]
    token = token.split(".", 1)[0]
    token = token.split("@", 1)[0]
    return token.replace("-", "_").lower()


def detect_system_language(env: Mapping[str, str] | None = None) -> str:
    """Return ``es`` for a Spanish OS locale and ``en`` for everything else.

    Locale precedence follows the useful desktop subset of POSIX/gettext:
    LC_ALL, LC_MESSAGES, LANGUAGE, then LANG.  Unknown/C/POSIX locales fall
    back to English, matching the application's supported language policy.
    """
    values = os.environ if env is None else env
    for key in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        raw = values.get(key)
        if not raw:
            continue
        token = _normalise_locale_token(raw)
        if token in {"c", "posix"}:
            return "en"
        return "es" if token == "es" or token.startswith("es_") else "en"
    return "en"


def resolve_language(saved_language: object, manually_selected: bool, env: Mapping[str, str] | None = None) -> str:
    """Resolve startup language while preserving an explicit user choice.

    Old settings files did not record whether ``language`` was chosen by the
    user.  They are treated as automatic so existing installations migrate to
    OS detection once.  After the user changes language, ``language_manual``
    is saved and their choice wins on later starts.
    """
    language = str(saved_language or "").lower()
    if manually_selected and language in {"es", "en"}:
        return language
    return detect_system_language(env)


def unique_codes(codes: Sequence[object]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for code in codes:
        value = str(code).strip().upper()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def sanitize_currency_state(
    order: Sequence[object],
    visible: Sequence[object] | set[object],
    supported: Sequence[object],
    default_visible: Sequence[object],
) -> tuple[list[str], set[str]]:
    """Return a stable order/visibility state without dropping supported codes.

    This is deliberately independent of the latest network response: a partial
    ECB/CBR refresh must never silently uncheck or move a currency to the end.
    """
    supported_codes = unique_codes(supported)
    supported_set = set(supported_codes)
    clean_order = [code for code in unique_codes(order) if code in supported_set]
    for code in supported_codes:
        if code not in clean_order:
            clean_order.append(code)

    clean_visible = {code for code in unique_codes(list(visible)) if code in supported_set}
    if not clean_visible:
        clean_visible = {code for code in unique_codes(default_visible) if code in supported_set}
    return clean_order, clean_visible


REGION_BY_CODE = {
    # Europe
    "EUR": "europe", "GBP": "europe", "PLN": "europe", "SEK": "europe",
    "CZK": "europe", "CHF": "europe", "DKK": "europe", "HUF": "europe",
    "ISK": "europe", "NOK": "europe", "RON": "europe", "RSD": "europe",
    # Eastern Europe
    "RUB": "eastern_europe", "UAH": "eastern_europe", "BYN": "eastern_europe",
    "MDL": "eastern_europe",
    # Middle East / Gulf
    "AED": "middle_east", "SAR": "middle_east", "TRY": "middle_east",
    "BHD": "middle_east", "IRR": "middle_east", "QAR": "middle_east",
    "OMR": "middle_east", "ILS": "middle_east",
    # Central Asia / Caucasus
    "AMD": "central_asia", "AZN": "central_asia", "GEL": "central_asia",
    "KZT": "central_asia", "KGS": "central_asia", "TJS": "central_asia",
    "TMT": "central_asia", "UZS": "central_asia",
    # East Asia
    "JPY": "east_asia", "CNY": "east_asia", "HKD": "east_asia",
    "KRW": "east_asia", "MNT": "east_asia",
    # South Asia
    "INR": "south_asia", "BDT": "south_asia",
    # Southeast Asia
    "IDR": "southeast_asia", "MYR": "southeast_asia", "PHP": "southeast_asia",
    "SGD": "southeast_asia", "THB": "southeast_asia", "VND": "southeast_asia",
    "MMK": "southeast_asia",
    # North America (continent-level family; Caribbean is included here)
    "USD": "north_america", "CAD": "north_america", "MXN": "north_america",
    "CUP": "north_america",
    # Central & South America
    "BRL": "latin_america", "BOB": "latin_america", "ARS": "latin_america",
    "CLP": "latin_america", "COP": "latin_america", "PYG": "latin_america",
    "PEN": "latin_america", "UYU": "latin_america",
    # Africa
    "DZD": "africa", "EGP": "africa", "NGN": "africa", "ZAR": "africa",
    "ETB": "africa",
    # Oceania
    "AUD": "oceania", "NZD": "oceania",
}


REGION_SORT_ORDER = [
    "europe",
    "eastern_europe",
    "middle_east",
    "central_asia",
    "east_asia",
    "south_asia",
    "southeast_asia",
    "north_america",
    "latin_america",
    "africa",
    "oceania",
    "international",
]

REGION_NAMES = {
    "europe": {"es": "Europa Occidental", "en": "Western Europe"},
    "eastern_europe": {"es": "Europa oriental", "en": "Eastern Europe"},
    "middle_east": {"es": "Oriente Medio y Golfo", "en": "Middle East & Gulf"},
    "central_asia": {"es": "Asia Central y Cáucaso", "en": "Central Asia & Caucasus"},
    "east_asia": {"es": "Asia oriental", "en": "East Asia"},
    "south_asia": {"es": "Asia meridional", "en": "South Asia"},
    "southeast_asia": {"es": "Sudeste asiático", "en": "Southeast Asia"},
    "north_america": {"es": "América del Norte", "en": "North America"},
    "latin_america": {"es": "América Centro y Sur", "en": "Central & South America"},
    "africa": {"es": "África", "en": "Africa"},
    "oceania": {"es": "Oceanía", "en": "Oceania"},
    "international": {"es": "Internacional", "en": "International"},
}

# Higher-contrast regional colours for management views.
# Different continents are intentionally easy to distinguish at a glance,
# while related regions inside the same broader area still share a family.
REGION_COLORS = {
    # Europe = green family
    "europe": "#275d3d",
    "eastern_europe": "#2f7a50",
    # Asian regions share a warm amber / yellow / orange family.
    # Central Asia & Caucasus is intentionally neutral grey to stand apart.
    "middle_east": "#6e675d",
    "central_asia": "#59616d",
    "east_asia": "#b58116",
    "south_asia": "#d17912",
    "southeast_asia": "#9f8b1f",
    # Americas = related pink / rose family
    "north_america": "#a34e82",
    "latin_america": "#8d3f5f",
    # Distinct continents
    "africa": "#6b4423",
    "oceania": "#355e9a",
    "international": "#545b66",
}


def currency_region_key(code: object) -> str:
    return REGION_BY_CODE.get(str(code or "").upper(), "international")


def currency_region_name(code: object, language: str = "es") -> str:
    key = currency_region_key(code)
    lang = language if language in {"es", "en"} else "es"
    return REGION_NAMES[key][lang]


def currency_region_color(code: object) -> str:
    return REGION_COLORS[currency_region_key(code)]


def alphabetical_codes(codes: Sequence[object]) -> list[str]:
    return sorted(unique_codes(codes))


def region_sorted_codes(codes: Sequence[object]) -> list[str]:
    order = {name: index for index, name in enumerate(REGION_SORT_ORDER)}
    return sorted(
        unique_codes(codes),
        key=lambda code: (order.get(currency_region_key(code), len(order)), code),
    )


# ISO 4217 minor-unit precision used by the converter display.
# Only exceptions to the common 2-decimal case need to be listed here.
# JPY, KRW, VND and ISK have no decimal minor unit; BHD and OMR use 3.
ZERO_MINOR_UNIT_CODES = frozenset({"JPY", "KRW", "VND", "ISK", "CLP", "PYG"})
THREE_MINOR_UNIT_CODES = frozenset({"BHD", "OMR"})
ROUNDING_MODES = frozenset({"auto", "0", "1", "2"})


VERIFICATION_DISPLAY_MODES = frozenset({"always", "issues"})

def normalize_verification_display_mode(value: object) -> str:
    mode = str(value or "").lower()
    return mode if mode in VERIFICATION_DISPLAY_MODES else "always"

def strip_zero_fraction(text: str, decimal_separator: str) -> str:
    """Remove only an all-zero fractional part from an already-formatted number.

    ``1.234,00`` -> ``1.234`` and ``1,234.00`` -> ``1,234`` while values
    such as ``1.234,50`` / ``1,234.50`` keep their requested precision.
    """
    value = str(text)
    separator = "," if decimal_separator == "," else "."
    if separator not in value:
        return value
    integer, fraction = value.rsplit(separator, 1)
    if fraction and set(fraction) == {"0"}:
        return integer
    return value

# Decimal separator preference. ``currency`` uses a representative/common
# convention for the currency's primary market. It is intentionally a display
# convention, not a claim that every locale using that currency formats numbers
# identically (EUR is used in countries with both comma and point conventions).
DECIMAL_SEPARATOR_MODES = frozenset({"currency", "comma", "dot"})

# Currencies whose usual local presentation is commonly comma-decimal.
# Codes not listed here default to point-decimal in ``currency`` mode.
COMMA_DECIMAL_CODES = frozenset({
    "EUR", "PLN", "SEK", "TRY", "CZK", "RUB", "UAH", "CHF", "DKK",
    "HUF", "ISK", "NOK", "RON", "RSD", "BYN", "MDL", "AMD", "AZN",
    "GEL", "KZT", "KGS", "TJS", "TMT", "UZS", "IDR", "VND", "BRL",
    "BOB", "ARS", "CLP", "COP", "PYG", "PEN", "UYU", "DZD", "ZAR", "MNT",
})


def normalize_decimal_separator_mode(value: object) -> str:
    mode = str(value or "").lower()
    return mode if mode in DECIMAL_SEPARATOR_MODES else "currency"


def currency_decimal_separator(code: object, mode: object = "currency") -> str:
    normalized = normalize_decimal_separator_mode(mode)
    if normalized == "comma":
        return ","
    if normalized == "dot":
        return "."
    return "," if str(code or "").upper() in COMMA_DECIMAL_CODES else "."



def currency_minor_units(code: object) -> int:
    value = str(code or "").upper()
    if value in ZERO_MINOR_UNIT_CODES:
        return 0
    if value in THREE_MINOR_UNIT_CODES:
        return 3
    return 2


def normalize_rounding_mode(value: object, legacy_two_decimals: object = False) -> str:
    mode = str(value or "").lower()
    if mode in ROUNDING_MODES:
        return mode
    return "2" if bool(legacy_two_decimals) else "auto"


def effective_rounding_decimals(code: object, mode: object) -> int | None:
    """Return display decimals for a fixed mode, respecting currency minor units.

    ``None`` means the application's automatic smart formatting.  Zero-minor-unit
    currencies always return 0, including automatic mode, so JPY/KRW/VND/ISK are
    never displayed with artificial fractional amounts.
    """
    minor_units = currency_minor_units(code)
    if minor_units == 0:
        return 0
    normalized = normalize_rounding_mode(mode)
    if normalized == "auto":
        return None
    return min(int(normalized), minor_units)
