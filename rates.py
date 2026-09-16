#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET

from latam_rates import (
    LATAM_EXTRA_CODES, LATAM_SOURCE_NAMES, LATAM_SOURCE_URLS, BCB_URL,
    fetch_latam_rate, fetch_bcb_rates, LatamPublicationError,
)

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp"
CBUAE_URL = "https://www.centralbank.ae/en/forex-eibor/exchange-rates/"
SAMA_URL = "https://sama.gov.sa/en-US/Currency/FinExc/Pages/Currency.aspx"
QCB_URL = "https://www.qcb.gov.qa/en/Pages/MonetaryPolicyTools.aspx"
CBO_URL = "https://cbo.gov.om/Pages/FixedPeg.aspx"
CBB_URL = "https://www.cbb.gov.bh/wp-content/uploads/2019/01/annual_report_2001eng.pdf"
ECB_INFO_URL = "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html"
CBR_INFO_URL = "https://www.cbr.ru/eng/currency_base/daily/"

AED_USD_PEG = 3.6725
SAR_USD_PEG = 3.75
QAR_USD_PEG = 3.64
# Bahrain and Oman publish the inverse quotation (USD per local currency).
# Store every peg consistently as local-currency units per 1 USD.
BHD_USD_PEG = 1.0 / 2.659
OMR_USD_PEG = 1.0 / 2.6008
USD_PEGS = {
    "AED": AED_USD_PEG,
    "SAR": SAR_USD_PEG,
    "QAR": QAR_USD_PEG,
    "BHD": BHD_USD_PEG,
    "OMR": OMR_USD_PEG,
}

USER_AGENT = "Libre-Kambio/1.9.33 (+local desktop app)"

# Primary-source policy. If a fresh response from the configured primary source
# no longer contains one of these currencies, the app deliberately stops
# calculating that currency instead of silently falling back to another bank.
ECB_PRIMARY_CODES = frozenset({
    "USD", "JPY", "CZK", "DKK", "GBP", "HUF", "PLN", "RON", "SEK", "CHF",
    "ISK", "NOK", "TRY", "AUD", "BRL", "CAD", "CNY", "HKD", "IDR", "ILS",
    "INR", "KRW", "MXN", "MYR", "NZD", "PHP", "SGD", "THB", "ZAR",
})

CBR_PRIMARY_CODES = frozenset({
    "RUB", "UAH", "AZN", "DZD", "AMD", "BYN", "BOB", "VND", "EGP",
    "IRR", "CUP", "MMK", "GEL", "MDL", "NGN", "TMT", "RSD",
    "KGS", "TJS", "BDT", "KZT", "MNT", "UZS", "ETB",
})


def primary_source_for(code: str) -> str:
    code = str(code).upper()
    if code in USD_PEGS or code in ECB_PRIMARY_CODES or code == "EUR":
        return "ECB"
    if code in CBR_PRIMARY_CODES:
        return "CBR"
    if code in LATAM_SOURCE_NAMES:
        return LATAM_SOURCE_NAMES[code]
    return ""



@dataclass
class RatesSnapshot:
    rates_per_eur: dict[str, float]
    ecb_rates_per_eur: dict[str, float]
    cbr_rub_per_unit: dict[str, float]
    ecb_date: str | None
    cbr_date: str | None
    cbr_published_date: str | None
    fetched_at: str
    errors: list[str]
    # Currency codes omitted by a freshly reached primary source. Values are
    # "ECB" or "CBR". These codes are intentionally excluded from
    # rates_per_eur so a discontinued/omitted publication cannot be used.
    source_missing: dict[str, str] = field(default_factory=dict)
    # Optional Latin-American rates are local-currency units per USD from the
    # official monetary authority selected for each currency. BCB values are
    # kept separately because they are an indicative independent cross-check.
    latam_units_per_usd: dict[str, float] = field(default_factory=dict)
    latam_dates: dict[str, str] = field(default_factory=dict)
    latam_sources: dict[str, str] = field(default_factory=dict)
    latam_cached_codes: list[str] = field(default_factory=list)
    # Per-source diagnostics for optional Latin-American currencies.  Values:
    # fresh = downloaded and parsed now; cached = current download failed and a
    # previous successful value is being shown; missing = official publication
    # was reached but the expected rate was absent; error = source could not be
    # downloaded/parsed and there is no safe cached value.
    latam_fetch_status: dict[str, str] = field(default_factory=dict)
    latam_fetch_errors: dict[str, str] = field(default_factory=dict)
    bcb_units_per_usd: dict[str, float] = field(default_factory=dict)
    bcb_date: str | None = None
    bcb_cached: bool = False
    bcb_fetch_status: str = "disabled"
    bcb_fetch_error: str = ""
    # These flags describe the data currently displayed, not merely what was
    # stored in rates.json. They prevent cached values from looking freshly
    # downloaded when a source is unavailable.
    ecb_cached: bool = False
    cbr_cached: bool = False
    cbr_published_cached: bool = False

    def to_json(self) -> str:
        payload = asdict(self)
        # A file loaded from disk is, by definition, cached on the next run.
        # Keep the stored flags false so they do not become historical facts.
        payload["ecb_cached"] = False
        payload["cbr_cached"] = False
        payload["cbr_published_cached"] = False
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> "RatesSnapshot":
        data = json.loads(raw)
        ecb_rates = {k: float(v) for k, v in data.get("ecb_rates_per_eur", {}).items()}
        cbr_rates = {k: float(v) for k, v in data.get("cbr_rub_per_unit", {}).items()}
        return cls(
            rates_per_eur={k: float(v) for k, v in data["rates_per_eur"].items()},
            ecb_rates_per_eur=ecb_rates,
            cbr_rub_per_unit=cbr_rates,
            ecb_date=data.get("ecb_date"),
            cbr_date=data.get("cbr_date"),
            cbr_published_date=data.get("cbr_published_date"),
            fetched_at=data.get("fetched_at", ""),
            errors=list(data.get("errors", [])),
            source_missing={str(k).upper(): str(v) for k, v in data.get("source_missing", {}).items()},
            latam_units_per_usd={str(k).upper(): float(v) for k, v in data.get("latam_units_per_usd", {}).items()},
            latam_dates={str(k).upper(): str(v) for k, v in data.get("latam_dates", {}).items()},
            latam_sources={str(k).upper(): str(v) for k, v in data.get("latam_sources", {}).items()},
            latam_cached_codes=list({str(k).upper() for k in data.get("latam_units_per_usd", {}).keys()}),
            latam_fetch_status={
                **{str(k).upper(): "cached" for k in data.get("latam_units_per_usd", {}).keys()},
                **{str(k).upper(): "missing" for k in data.get("source_missing", {}).keys() if str(k).upper() in LATAM_EXTRA_CODES},
            },
            latam_fetch_errors={str(k).upper(): str(v) for k, v in data.get("latam_fetch_errors", {}).items()},
            bcb_units_per_usd={str(k).upper(): float(v) for k, v in data.get("bcb_units_per_usd", {}).items()},
            bcb_date=data.get("bcb_date"),
            bcb_cached=bool(data.get("bcb_units_per_usd")),
            bcb_fetch_status="cached" if data.get("bcb_units_per_usd") else str(data.get("bcb_fetch_status", "disabled")),
            bcb_fetch_error=str(data.get("bcb_fetch_error", "")),
            ecb_cached=bool(ecb_rates),
            cbr_cached=bool(cbr_rates),
            cbr_published_cached=bool(data.get("cbr_published_date")),
        )


def cache_path() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    path = base / "libre-kambio-currency" / "rates.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _fetch(url: str, timeout: int = 12) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def parse_ecb_xml(data: bytes) -> tuple[dict[str, float], str | None]:
    root = ET.fromstring(data)
    date = None
    rates: dict[str, float] = {"EUR": 1.0}

    for elem in root.iter():
        time_value = elem.attrib.get("time")
        if time_value:
            date = time_value
        currency = elem.attrib.get("currency")
        rate = elem.attrib.get("rate")
        if currency and rate:
            rates[currency.upper()] = float(rate)

    if len(rates) <= 1:
        raise ValueError("La respuesta del BCE no contiene tipos de cambio")
    return rates, date


def _parse_decimal(text: str) -> float:
    return float(text.strip().replace(" ", "").replace(",", "."))


def parse_cbr_xml(data: bytes) -> tuple[dict[str, float], str | None]:
    root = ET.fromstring(data)
    raw_date = root.attrib.get("Date")
    date = None
    if raw_date:
        for fmt in ("%d.%m.%Y", "%m/%d/%Y", "%Y-%m-%d"):
            try:
                date = datetime.strptime(raw_date, fmt).date().isoformat()
                break
            except ValueError:
                pass
        if date is None:
            date = raw_date

    rub_per_unit: dict[str, float] = {"RUB": 1.0}
    for valute in root.findall("Valute"):
        code = (valute.findtext("CharCode") or "").strip().upper()
        nominal_text = valute.findtext("Nominal")
        value_text = valute.findtext("Value")
        if not code or nominal_text is None or value_text is None:
            continue
        nominal = _parse_decimal(nominal_text)
        value = _parse_decimal(value_text)
        if nominal:
            rub_per_unit[code] = value / nominal

    if len(rub_per_unit) <= 1:
        raise ValueError("La respuesta del Banco de Rusia no contiene tipos de cambio")
    return rub_per_unit, date


def parse_cbr_last_updated_html(data: bytes) -> str | None:
    """Extract CBR page's own “Last updated on” date as ISO YYYY-MM-DD.

    This is deliberately separate from the XML ``Date`` attribute: the XML
    date is the date *from which the official rates are valid*, while the
    web page also exposes when that set was published/last updated.
    """
    text = data.decode("utf-8", errors="ignore")
    match = re.search(r"Last\s+updated\s+on\s*:\s*(\d{2}\.\d{2}\.\d{4})", text, re.IGNORECASE)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%d.%m.%Y").date().isoformat()
    except ValueError:
        return None


def load_cache() -> RatesSnapshot | None:
    path = cache_path()
    try:
        return RatesSnapshot.from_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def save_cache(snapshot: RatesSnapshot) -> None:
    path = cache_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(snapshot.to_json(), encoding="utf-8")
    tmp.replace(path)


def _merge_snapshot(
    ecb_rates: dict[str, float] | None,
    ecb_date: str | None,
    cbr_rates: dict[str, float] | None,
    cbr_date: str | None,
    cbr_published_date: str | None,
    errors: list[str],
    previous: RatesSnapshot | None,
    *,
    ecb_fetch_ok: bool,
    cbr_fetch_ok: bool,
    cbr_publication_fetch_ok: bool,
) -> RatesSnapshot:
    ecb_cached = False
    cbr_cached = False
    cbr_published_cached = False

    if ecb_rates is None:
        if previous and previous.ecb_rates_per_eur:
            ecb_rates = dict(previous.ecb_rates_per_eur)
            ecb_date = previous.ecb_date
            ecb_cached = True
        else:
            raise RuntimeError("No hay datos del BCE disponibles ni en caché")
    elif not ecb_fetch_ok:
        ecb_cached = True

    if cbr_rates is None:
        if previous and previous.cbr_rub_per_unit:
            cbr_rates = dict(previous.cbr_rub_per_unit)
            cbr_date = previous.cbr_date
            cbr_cached = True
        else:
            cbr_rates = {}
    elif not cbr_fetch_ok:
        cbr_cached = True

    # Never pair a newly fetched publication date with an older cached CBR
    # rate table. If the rate download fell back to cache, its publication
    # date must come from the same cached snapshot.
    if cbr_cached and previous:
        cbr_published_date = previous.cbr_published_date
        cbr_published_cached = bool(cbr_published_date)
    elif cbr_published_date is None and previous and previous.cbr_published_date:
        cbr_published_date = previous.cbr_published_date
        cbr_published_cached = True
    elif cbr_published_date and not cbr_publication_fetch_ok:
        cbr_published_cached = True

    # Preserve source-missing knowledge only while that source could not be
    # checked again. A successful fresh fetch replaces the previous judgement.
    source_missing = dict(previous.source_missing) if previous else {}
    if ecb_fetch_ok:
        source_missing = {code: src for code, src in source_missing.items() if src != "ECB"}
        for code in ECB_PRIMARY_CODES:
            if code not in ecb_rates:
                source_missing[code] = "ECB"
    if cbr_fetch_ok:
        source_missing = {code: src for code, src in source_missing.items() if src != "CBR"}
        if "EUR" not in cbr_rates:
            for code in CBR_PRIMARY_CODES:
                source_missing[code] = "CBR"
        else:
            for code in CBR_PRIMARY_CODES:
                if code != "RUB" and code not in cbr_rates:
                    source_missing[code] = "CBR"

    rates = dict(ecb_rates)

    # USD-pegged currencies depend on the ECB's USD publication plus their
    # official fixed pegs. If a fresh ECB table omits USD, only these dependent
    # calculations are disabled; the rest of the application remains usable.
    usd_per_eur = rates.get("USD")
    if usd_per_eur is not None and "USD" not in source_missing:
        for code, units_per_usd in USD_PEGS.items():
            rates[code] = usd_per_eur * units_per_usd
            source_missing.pop(code, None)
    else:
        for code in USD_PEGS:
            rates.pop(code, None)
            if ecb_fetch_ok:
                source_missing[code] = "ECB"

    # CBR-primary currencies are calculated only from the currently selected
    # CBR table (fresh, or cached only when the whole source could not be
    # reached). A successful CBR response that omits a currency never falls
    # back to an older value and never silently switches to another source.
    rub_per_eur = cbr_rates.get("EUR")
    if rub_per_eur is not None and rub_per_eur != 0:
        if "RUB" not in source_missing:
            rates["RUB"] = rub_per_eur
        for code in CBR_PRIMARY_CODES:
            if code == "RUB" or code in source_missing:
                continue
            rub_per_unit = cbr_rates.get(code)
            if rub_per_unit is not None and rub_per_unit != 0:
                rates[code] = rub_per_eur / rub_per_unit

    # Enforce the primary-source policy after all merging. This is what blocks
    # a CBR value from replacing a currency omitted by a fresh ECB publication,
    # and vice versa.
    for code in source_missing:
        rates.pop(code, None)

    return RatesSnapshot(
        rates_per_eur=rates,
        ecb_rates_per_eur=ecb_rates,
        cbr_rub_per_unit=cbr_rates,
        ecb_date=ecb_date,
        cbr_date=cbr_date,
        cbr_published_date=cbr_published_date,
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        errors=errors,
        source_missing=source_missing,
        ecb_cached=ecb_cached,
        cbr_cached=cbr_cached,
        cbr_published_cached=cbr_published_cached,
    )



def _apply_latam_extras(
    snapshot: RatesSnapshot,
    enabled_codes: set[str],
    previous: RatesSnapshot | None,
    errors: list[str],
) -> None:
    enabled = {str(code).upper() for code in enabled_codes if str(code).upper() in LATAM_EXTRA_CODES}

    # Optional currencies are independent of the mandatory ECB/CBR set. Remove
    # stale diagnostics for disabled currencies before building this check.
    for code in LATAM_EXTRA_CODES:
        if code not in enabled:
            snapshot.source_missing.pop(code, None)

    if not enabled:
        snapshot.latam_units_per_usd = {}
        snapshot.latam_dates = {}
        snapshot.latam_sources = {}
        snapshot.latam_cached_codes = []
        snapshot.latam_fetch_status = {}
        snapshot.latam_fetch_errors = {}
        snapshot.bcb_units_per_usd = {}
        snapshot.bcb_date = None
        snapshot.bcb_cached = False
        snapshot.bcb_fetch_status = "disabled"
        snapshot.bcb_fetch_error = ""
        return

    local_rates: dict[str, float] = {}
    local_dates: dict[str, str] = {}
    local_sources: dict[str, str] = {}
    cached_codes: list[str] = []
    fetch_status: dict[str, str] = {}
    fetch_errors: dict[str, str] = {}

    for code in sorted(enabled):
        source_name = LATAM_SOURCE_NAMES.get(code, code)
        snapshot.source_missing.pop(code, None)
        try:
            rate = fetch_latam_rate(code)
            local_rates[code] = rate.units_per_usd
            if rate.date:
                local_dates[code] = rate.date
            local_sources[code] = rate.source
            fetch_status[code] = "fresh"
        except LatamPublicationError as exc:
            # The official endpoint answered, but the expected current rate was
            # absent/unreadable. Do not silently reuse an old value.
            message = str(exc)
            errors.append(f"{source_name} ({code}): {message}")
            fetch_status[code] = "missing"
            fetch_errors[code] = message
            snapshot.source_missing[code] = source_name
        except Exception as exc:
            # A download/transport/parser failure is different from an official
            # publication omitting the rate.  Use a prior successful value only
            # when one exists, and expose the distinction to the GUI.
            message = str(exc) or type(exc).__name__
            errors.append(f"{source_name} ({code}): {message}")
            fetch_errors[code] = message
            if previous and code in previous.latam_units_per_usd:
                local_rates[code] = previous.latam_units_per_usd[code]
                if code in previous.latam_dates:
                    local_dates[code] = previous.latam_dates[code]
                local_sources[code] = previous.latam_sources.get(code, source_name)
                cached_codes.append(code)
                fetch_status[code] = "cached"
            else:
                fetch_status[code] = "error"
                snapshot.source_missing[code] = source_name

    bcb_rates: dict[str, float] = {}
    bcb_date = None
    bcb_cached = False
    bcb_status = "fresh"
    bcb_error = ""
    try:
        bcb_rates, bcb_date = fetch_bcb_rates(enabled)
        missing_bcb = sorted(enabled.difference(bcb_rates))
        if missing_bcb:
            bcb_status = "partial"
            bcb_error = "Sin cotización para " + ", ".join(missing_bcb)
            errors.append(f"BCB (comprobación HISPAM): {bcb_error}")
    except LatamPublicationError as exc:
        bcb_status = "missing"
        bcb_error = str(exc)
        errors.append(f"BCB (comprobación HISPAM): {bcb_error}")
    except Exception as exc:
        bcb_error = str(exc) or type(exc).__name__
        errors.append(f"BCB (comprobación HISPAM): {bcb_error}")
        if previous and previous.bcb_units_per_usd:
            bcb_rates = {code: value for code, value in previous.bcb_units_per_usd.items() if code in enabled}
            bcb_date = previous.bcb_date
            bcb_cached = bool(bcb_rates)
            bcb_status = "cached" if bcb_cached else "error"
        else:
            bcb_status = "error"

    usd_per_eur = snapshot.ecb_rates_per_eur.get("USD")
    if usd_per_eur is None or "USD" in snapshot.source_missing:
        for code in enabled:
            snapshot.rates_per_eur.pop(code, None)
            snapshot.source_missing[code] = "ECB"
    else:
        for code in enabled:
            units_per_usd = local_rates.get(code)
            if units_per_usd is None:
                snapshot.rates_per_eur.pop(code, None)
                continue
            snapshot.rates_per_eur[code] = usd_per_eur * units_per_usd
            snapshot.source_missing.pop(code, None)

    snapshot.latam_units_per_usd = local_rates
    snapshot.latam_dates = local_dates
    snapshot.latam_sources = local_sources
    snapshot.latam_cached_codes = cached_codes
    snapshot.latam_fetch_status = fetch_status
    snapshot.latam_fetch_errors = fetch_errors
    snapshot.bcb_units_per_usd = bcb_rates
    snapshot.bcb_date = bcb_date
    snapshot.bcb_cached = bcb_cached
    snapshot.bcb_fetch_status = bcb_status
    snapshot.bcb_fetch_error = bcb_error


def update_rates(enabled_latam_codes: set[str] | None = None) -> RatesSnapshot:
    previous = load_cache()
    errors: list[str] = []

    ecb_rates = None
    ecb_date = None
    ecb_fetch_ok = False
    try:
        ecb_rates, ecb_date = parse_ecb_xml(_fetch(ECB_URL))
        ecb_fetch_ok = True
    except Exception as exc:  # Network/parser errors are deliberately isolated.
        errors.append(f"BCE: {exc}")

    cbr_rates = None
    cbr_date = None
    cbr_fetch_ok = False
    try:
        cbr_rates, cbr_date = parse_cbr_xml(_fetch(CBR_URL))
        cbr_fetch_ok = True
    except Exception as exc:
        errors.append(f"Banco de Rusia: {exc}")

    cbr_published_date = None
    cbr_publication_fetch_ok = False
    try:
        cbr_published_date = parse_cbr_last_updated_html(_fetch(CBR_INFO_URL))
        if cbr_published_date is None:
            errors.append("Banco de Rusia: no se pudo leer la fecha de publicación")
        else:
            cbr_publication_fetch_ok = True
    except Exception as exc:
        errors.append(f"Banco de Rusia (fecha de publicación): {exc}")

    snapshot = _merge_snapshot(
        ecb_rates,
        ecb_date,
        cbr_rates,
        cbr_date,
        cbr_published_date,
        errors,
        previous,
        ecb_fetch_ok=ecb_fetch_ok,
        cbr_fetch_ok=cbr_fetch_ok,
        cbr_publication_fetch_ok=cbr_publication_fetch_ok,
    )
    _apply_latam_extras(snapshot, set(enabled_latam_codes or ()), previous, errors)
    save_cache(snapshot)
    return snapshot


def convert(amount: float, source: str, target: str, snapshot: RatesSnapshot) -> float:
    source = source.upper()
    target = target.upper()
    source_rate = snapshot.rates_per_eur[source]
    target_rate = snapshot.rates_per_eur[target]
    return amount / source_rate * target_rate


def cbr_cross_units_per_eur(code: str, snapshot: RatesSnapshot) -> float | None:
    code = code.upper()
    cbr = snapshot.cbr_rub_per_unit
    rub_per_eur = cbr.get("EUR")
    rub_per_unit = cbr.get(code)
    # CBR-only currencies are derived from this same CBR table, so comparing
    # them back to the CBR would be circular rather than an independent check.
    if code in {"EUR", "RUB"}:
        return None
    if code not in snapshot.ecb_rates_per_eur and code not in USD_PEGS:
        return None
    if rub_per_eur is None or rub_per_unit is None or rub_per_unit == 0:
        return None
    return rub_per_eur / rub_per_unit


def bcb_cross_units_per_eur(code: str, snapshot: RatesSnapshot) -> float | None:
    code = code.upper()
    usd_per_eur = snapshot.ecb_rates_per_eur.get("USD")
    units_per_usd = snapshot.bcb_units_per_usd.get(code)
    if usd_per_eur is None or units_per_usd is None:
        return None
    return usd_per_eur * units_per_usd


def cbr_peg_value(code: str, snapshot: RatesSnapshot) -> float | None:
    code = code.upper()
    if code not in USD_PEGS:
        return None
    cbr = snapshot.cbr_rub_per_unit
    rub_per_usd = cbr.get("USD")
    rub_per_currency = cbr.get(code)
    if rub_per_usd is None or rub_per_currency is None or rub_per_currency == 0:
        return None
    return rub_per_usd / rub_per_currency


def percent_difference(a: float, b: float) -> float:
    if a == 0 and b == 0:
        return 0.0
    denominator = (abs(a) + abs(b)) / 2.0
    if denominator == 0:
        return math.inf
    return abs(a - b) / denominator * 100.0


def _date_gap_days(first: str | None, second: str | None) -> int | None:
    if not first or not second:
        return None
    try:
        a = datetime.strptime(first, "%Y-%m-%d").date()
        b = datetime.strptime(second, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (b - a).days


def verification(code: str, snapshot: RatesSnapshot) -> dict[str, object]:
    code = code.upper()
    main = snapshot.rates_per_eur.get(code)
    is_latam_extra = code in LATAM_SOURCE_NAMES and (code in snapshot.latam_units_per_usd or code in snapshot.latam_fetch_status)
    if is_latam_extra:
        cross = bcb_cross_units_per_eur(code, snapshot)
        gap = _date_gap_days(snapshot.latam_dates.get(code), snapshot.bcb_date)
        check_source = "BCB"
        primary_label = snapshot.latam_sources.get(code, LATAM_SOURCE_NAMES.get(code, code))
    else:
        cross = cbr_cross_units_per_eur(code, snapshot)
        gap = _date_gap_days(snapshot.ecb_date, snapshot.cbr_date)
        check_source = "CBR"
        primary_label = "ECB"
    result: dict[str, object] = {
        "code": code,
        "main": main,
        "cross": cross,
        "difference_pct": None,
        "status": "Sin segunda fuente",
        "level": "neutral",
        "peg": None,
        "peg_expected": None,
        "peg_difference_pct": None,
        "date_gap_days": gap,
        "date_note": "—",
        "source_missing": snapshot.source_missing.get(code),
        "check_source": check_source,
        "primary_label": primary_label,
        "latam_extra": is_latam_extra,
    }

    if result["source_missing"]:
        if is_latam_extra and snapshot.latam_fetch_status.get(code) == "error":
            result["status"] = "Fuente no disponible"
        else:
            result["status"] = "Fuente no publica"
        result["level"] = "warn"
        return result

    if gap is not None:
        if gap == 0:
            result["date_note"] = "Misma fecha"
        else:
            prefix = "BCB" if is_latam_extra else "CBR"
            if gap == 1:
                result["date_note"] = f"{prefix} +1 día"
            elif gap == -1:
                result["date_note"] = f"{prefix} −1 día"
            elif gap > 0:
                result["date_note"] = f"{prefix} +{gap} días"
            else:
                result["date_note"] = f"{prefix} {gap} días"

    if main is not None and cross is not None:
        diff = percent_difference(main, cross)
        result["difference_pct"] = diff
        if diff <= 1.5:
            result["status"] = "Coherente"
            result["level"] = "good"
        elif diff <= 3.0:
            result["status"] = "Revisar"
            result["level"] = "warn"
        else:
            result["status"] = "Diferencia alta"
            result["level"] = "bad"

    if code in USD_PEGS:
        expected = USD_PEGS[code]
        peg = cbr_peg_value(code, snapshot)
        result["peg"] = peg
        result["peg_expected"] = expected
        if peg is not None:
            peg_diff = abs(peg - expected) / expected * 100.0
            result["peg_difference_pct"] = peg_diff
            if peg_diff <= 0.10:
                result["status"] = "Peg confirmado"
                result["level"] = "good"
            elif peg_diff <= 0.50:
                result["status"] = "Peg: revisar"
                result["level"] = "warn"
            else:
                result["status"] = "Peg no coincide"
                result["level"] = "bad"

    return result
