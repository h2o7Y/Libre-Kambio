#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
import csv
import io
import json
import re
import urllib.request
import unicodedata
import xml.etree.ElementTree as ET

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Libre-Kambio/1.9.33"

# BCRA v4: discover the A 3500 variable by description instead of trusting a
# hard-coded metadata shape.  The detailed /5 endpoint is retained as an
# official fallback because A 3500 is currently variable 5.
BCRA_API_URL = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias?categoria=Principales%20Variables&limit=250"
BCRA_API_ID_URL = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias?idVariable=5&limit=20"
BCRA_SERIES_URL = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/5?limit=20"
BCRA_URL = "https://www.bcra.gob.ar/principales-variables/"

# BCCh exposes the Observed Dollar in several official views.  The full BDE
# table (without ``?idSerie=``) is deliberately first: unlike the compact
# single-series card and the daily-indicators landing page, it currently
# contains the complete server-rendered year table, including the latest
# business-day publication.  This matters on weekends, when the generic
# daily page can legitimately show ND.
BCCH_TABLE_URL = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_TIPO_CAMBIO/MN_TIPO_CAMBIO4/DOLAR_OBS_ADO"
BCCH_TABLE_ALT_URL = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_EI/MN_TIPO_CAMBIO4/DOLAR_OBS_ADO?id5=SI&idSerie=F073.TCO.PRE.Z.D"
BCCH_HOME_URL = "https://www.bcentral.cl/es/web/banco-central/inicio"
BCCH_HOME_ALT_URL = "https://www.bcentral.cl/inicio"
BCCH_URL = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_TIPO_CAMBIO/MN_TIPO_CAMBIO4/DOLAR_OBS_ADO?idSerie=F073.TCO.PRE.Z.D"
BCCH_DAILY_URL = "https://si3.bcentral.cl/Indicadoressiete/secure/IndicadoresDiarios.aspx"
BCCH_OLD_DAILY_URL = "https://si3.bcentral.cl/Bdemovil/BDE/IndicadoresDiarios"

BANREP_URL = "https://www.banrep.gov.co/es/glosario/tasa-cambio-trm"
BANREP_FALLBACK_URL = "https://www.banrep.gov.co/es"
BCP_URL = "https://www.bcp.gov.py/webapps/web/cotizacion/referencial-fluctuante-interbancario"
BCRP_URL = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04637PD-PD04638PD/csv/"

# BCU has a documented public SOAP Web Service specifically for currency
# quotations. Use it before the SharePoint pages, which intermittently return
# 502/timeouts to automated clients. The web pages remain official fallbacks.
BCU_SOAP_URL = "https://cotizaciones.bcu.gub.uy/wscotizaciones/servlet/awsbcucotizaciones"
BCU_URL = "https://www.bcu.gub.uy/Paginas/Default.aspx?from=amp&onepage_org="
BCU_ALT_URL = "https://www.bcu.gub.uy/Paginas/Default.aspx?ID=1&RootFolder=%2A"
BCU_RATES_URL = "https://www.bcu.gub.uy/Estadisticas-e-Indicadores/Paginas/Cotizaciones.aspx"
BCU_FALLBACK_URL = "https://www.bcu.gub.uy/Estadisticas-e-Indicadores/Paginas/Cotizaciones.aspx?Mobile=1"
BCB_URL = "https://www.bcb.gob.bo/librerias/indicadores/otras/otras_imprimir.php"
BCB_FALLBACK_URL = "https://www.bcb.gob.bo/librerias/indicadores/otras/otras_imprimir2.php"

LATAM_EXTRA_CODES = ("ARS", "CLP", "COP", "PYG", "PEN", "UYU")
LATAM_SOURCE_NAMES = {
    "ARS": "BCRA",
    "CLP": "BCCh",
    "COP": "BanRep",
    "PYG": "BCP",
    "PEN": "BCRP",
    "UYU": "BCU",
}
LATAM_SOURCE_URLS = {
    "ARS": BCRA_URL,
    "CLP": BCCH_TABLE_URL,
    "COP": BANREP_URL,
    "PYG": BCP_URL,
    "PEN": BCRP_URL,
    "UYU": BCU_RATES_URL,
}


class LatamPublicationError(ValueError):
    """The official source was reached but the expected published rate was absent/unreadable.

    Callers should treat this as a safety stop rather than silently reusing an
    older rate, because a fresh publication no longer matched the expected
    currency data.
    """


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data and data.strip():
            self.parts.append(data.strip())


def _decode_html_bytes(data: bytes) -> str:
    """Decode central-bank HTML without destroying accented labels.

    Several legacy statistical pages still answer as Windows-1252/Latin-1.
    Decoding them as UTF-8 with ``errors=ignore`` silently turned "Dólar" into
    "Dlar", which made a perfectly valid BCCh publication look missing.
    """
    head = data[:4096].decode("ascii", errors="ignore")
    declared = re.search(r"charset\s*=\s*[\"']?([A-Za-z0-9._-]+)", head, re.IGNORECASE)
    encodings = []
    if declared:
        encodings.append(declared.group(1))
    encodings.extend(("utf-8", "cp1252", "latin-1"))
    seen = set()
    for encoding in encodings:
        key = encoding.lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("utf-8", errors="replace")


def html_text(data: bytes) -> str:
    parser = _TextExtractor()
    parser.feed(_decode_html_bytes(data))
    text = unescape(" ".join(parser.parts))
    # Some portal pages embed labels inside JavaScript/JSON as \uXXXX.
    text = re.sub(
        r"\\u([0-9a-fA-F]{4})",
        lambda m: chr(int(m.group(1), 16)),
        text,
    )
    return re.sub(r"\s+", " ", text).strip()


def _fetch(url: str, timeout: int = 12) -> bytes:
    # Keep the request deliberately browser-like but ask for identity encoding:
    # Python's stdlib can then read the response without depending on brotli.
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/html,application/xhtml+xml,application/xml,text/csv,text/plain;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-AR,es;q=0.9,en;q=0.7",
            "Accept-Encoding": "identity",
            "Connection": "close",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def _fetch_first(specs: tuple[tuple[str, object], ...]):
    """Try official endpoints/pages in order, preserving the useful distinction.

    Each item is ``(url, parser)``.  A number of central-bank sites expose the
    same data through an API plus a human page, or through two official views.
    We only fail over inside the same official institution; third-party rates
    are never substituted for the primary source.
    """
    failures: list[str] = []
    publication_error: Exception | None = None
    for url, parser in specs:
        try:
            return parser(_fetch(url))
        except LatamPublicationError as exc:
            publication_error = exc
            failures.append(f"{url}: publicación: {exc}")
        except Exception as exc:
            failures.append(f"{url}: {type(exc).__name__}: {exc}")
    if publication_error is not None:
        # At least one official endpoint answered, but its expected publication
        # could not be read.  The caller must not silently treat this as a
        # network failure and reuse an old rate as though it were current.
        raise LatamPublicationError(str(publication_error))
    raise OSError("; ".join(failures) if failures else "No se pudo consultar la fuente oficial")


def _parse_spanish_number(value: str) -> float:
    value = value.strip().replace(" ", "")
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    return float(value)


def _parse_english_number(value: str) -> float:
    return float(value.strip().replace(" ", "").replace(",", ""))


def _parse_number_auto(value: str) -> float:
    """Parse either 923,23 or 923.23, plus grouped variants."""
    value = value.strip().replace(" ", "")
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            return float(value.replace(".", "").replace(",", "."))
        return float(value.replace(",", ""))
    if "," in value:
        return _parse_spanish_number(value)
    return float(value)


def _date_dmy(value: str) -> str:
    return datetime.strptime(value, "%d/%m/%Y").date().isoformat()


_MONTHS_ES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12,
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
    # English fallbacks: the BCCh statistical portal can occasionally answer
    # an English rendering even when the Spanish route was requested.
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}


def _date_spanish_month(day: str, month: str, year: str) -> str:
    month_num = _MONTHS_ES[month.strip().lower().rstrip(".")]
    return datetime(int(year), month_num, int(day)).date().isoformat()


def _normalize_label(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value).strip().lower()


@dataclass(frozen=True)
class LatamRate:
    code: str
    units_per_usd: float
    date: str | None
    source: str


def parse_bcra_api(data: bytes) -> LatamRate:
    """Parse BCRA v4 monetary-variable metadata and discover A 3500 safely.

    Do not depend on the exact wording or on a fixed variable ID.  The BCRA
    documentation defines this endpoint as the catalogue of monetary
    variables; we select the entry whose description identifies A 3500.
    """
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LatamPublicationError("Respuesta JSON no válida del BCRA") from exc

    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        raise LatamPublicationError("El BCRA no devolvió el catálogo monetario esperado")

    candidates: list[dict] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_label(item.get("descripcion", ""))
        if "3500" in normalized and "cambio" in normalized:
            candidates.append(item)

    if not candidates:
        raise LatamPublicationError("No se encontró la variable A 3500 del BCRA")

    # Prefer the traditional Principales Variables / daily entry if more than
    # one result ever mentions A 3500.
    candidates.sort(
        key=lambda item: (
            "principales" not in _normalize_label(item.get("categoria", "")),
            str(item.get("periodicidad", "")).upper() != "D",
            int(item.get("idVariable", 10**9) or 10**9),
        )
    )
    item = candidates[0]
    raw_date = str(item.get("ultFechaInformada", "") or "").strip()
    raw_value = item.get("ultValorInformado")
    if not raw_date or raw_value in (None, ""):
        raise LatamPublicationError("El BCRA no publicó fecha/valor actual para el tipo A 3500")
    try:
        date = datetime.fromisoformat(raw_date[:10]).date().isoformat()
        value = float(raw_value) if isinstance(raw_value, (int, float)) else _parse_spanish_number(str(raw_value))
    except (TypeError, ValueError) as exc:
        raise LatamPublicationError("Fecha/valor A 3500 no legible en la API del BCRA") from exc
    if value <= 0:
        raise LatamPublicationError("Valor A 3500 no válido en la API del BCRA")
    return LatamRate("ARS", value, date, "BCRA")


def parse_bcra_series(data: bytes) -> LatamRate:
    """Parse the documented v4 detailed-series endpoint for variable 5."""
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LatamPublicationError("Respuesta JSON de serie no válida del BCRA") from exc
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        raise LatamPublicationError("El BCRA no devolvió la serie A 3500 esperada")
    observations: list[tuple[str, float]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        # The current A 3500 entry is variable 5.  This is only a fallback
        # after the description-based catalogue lookup above.
        if item.get("idVariable") not in (5, "5", None):
            continue
        detail = item.get("detalle")
        if not isinstance(detail, list):
            continue
        for row in detail:
            if not isinstance(row, dict):
                continue
            raw_date = str(row.get("fecha", "") or "").strip()
            raw_value = row.get("valor")
            if not raw_date or raw_value in (None, ""):
                continue
            try:
                date = datetime.fromisoformat(raw_date[:10]).date().isoformat()
                value = float(raw_value) if isinstance(raw_value, (int, float)) else _parse_spanish_number(str(raw_value))
            except (TypeError, ValueError):
                continue
            if value > 0:
                observations.append((date, value))
    if not observations:
        raise LatamPublicationError("La serie A 3500 del BCRA no contiene observaciones legibles")
    date, value = max(observations, key=lambda item: item[0])
    return LatamRate("ARS", value, date, "BCRA")

def parse_bcra(data: bytes) -> LatamRate:
    """Fallback parser for the official human page, deliberately tightly scoped.

    The BCRA page contains another indicator whose *base date* is 03/06/1993.
    A broad regex used in 1.9.27 could cross unrelated DOM blocks and mistake
    that date/value for the A 3500 quote.  Limit the match to the immediate
    A-3500 card so that a layout change fails safely instead of producing a
    plausible-looking but false rate.
    """
    text = html_text(data)
    anchor = re.search(r"Tipo de Cambio Mayorista.{0,180}?A\s*3500.{0,120}?Referencia", text, re.IGNORECASE)
    if not anchor:
        raise LatamPublicationError("No se encontró el tipo A 3500 del BCRA")
    section = text[anchor.start():anchor.end() + 260]
    m = re.search(r"(\d{2}/\d{2}/\d{4})\s+([\d.]+,\d+)", section, re.IGNORECASE)
    if not m:
        raise LatamPublicationError("El BCRA no mostró fecha/valor A 3500 junto al indicador")
    value = _parse_spanish_number(m.group(2))
    if value <= 0:
        raise LatamPublicationError("Valor A 3500 no válido en la página del BCRA")
    return LatamRate("ARS", value, _date_dmy(m.group(1)), "BCRA")


def parse_bcch(data: bytes) -> LatamRate:
    """Parse the BCCh public Observed Dollar publication defensively.

    The BCCh exposes the same official figure through its homepage and BDE
    views.  Those pages are not fully uniform: Spanish/English rendering,
    UTF-8/Windows-1252 encoding and portal markup can vary.  Work from the
    human-visible publication rather than one brittle DOM shape.
    """
    text = html_text(data)
    normalized = _normalize_label(text)

    # 1) Public BCCh homepage.  This is especially useful on weekends because
    # it keeps showing the latest published business-day quote while the daily
    # indicator form may show ND for the selected non-business day.
    dollar_labels = list(re.finditer(r"\b(?:dolar observado|observed dollar)\b", normalized, re.IGNORECASE))
    for label in dollar_labels:
        # Normalization preserves string length for ordinary accented letters,
        # so use the same positions against the original flattened text.
        pos = label.start()
        before = text[max(0, pos - 1800):pos]
        after = text[pos:pos + 800]

        # When the homepage announces the next official value explicitly,
        # e.g. "$920,26 /$923,23 (21 de agosto)", prefer the dated value.
        slash = re.search(
            r"(?:D[oó]lar\s+Observado|Observed\s+Dollar)\s+\$?([\d.,]+)\s*/\s*\$?([\d.,]+)\s*\((\d{1,2})\s+(?:de\s+)?([A-Za-zÁÉÍÓÚáéíóú]+)\)",
            after, re.IGNORECASE,
        )
        if slash:
            years = re.findall(r"(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóú]+)\s+de\s+(\d{4})", before, re.IGNORECASE)
            year = years[-1][2] if years else str(datetime.now().year)
            return LatamRate(
                "CLP", _parse_number_auto(slash.group(2)),
                _date_spanish_month(slash.group(3), slash.group(4), year), "BCCh",
            )

        single = re.search(
            r"(?:D[oó]lar\s+Observado|Observed\s+Dollar)\s+\$?([0-9][\d.,]*)",
            after, re.IGNORECASE,
        )
        if single and single.group(1).upper() != "ND":
            # Prefer the nearest Spanish long-form date before the quote.
            spanish_dates = re.findall(
                r"(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóú]+)\s+de\s+(\d{4})",
                before, re.IGNORECASE,
            )
            if spanish_dates:
                day, month, year = spanish_dates[-1]
                return LatamRate("CLP", _parse_number_auto(single.group(1)), _date_spanish_month(day, month, year), "BCCh")
            # English homepage rendering: "August 21, 2026".
            english_dates = re.findall(
                r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s*(\d{4})",
                before, re.IGNORECASE,
            )
            if english_dates:
                month, day, year = english_dates[-1]
                return LatamRate("CLP", _parse_number_auto(single.group(1)), _date_spanish_month(day, month, year), "BCCh")

    # 2) BDE single-series page.  Search the whole page, not only a fixed
    # 1800-character window: portal navigation can move the observation block.
    obs_candidates: list[tuple[str, float]] = []
    for m in re.finditer(
        r"(\d{1,2})[.](Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Set|Oct|Nov|Dic|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[.](\d{4})\s*:?\s*([0-9][\d.,]*)",
        text, re.IGNORECASE,
    ):
        try:
            date = _date_spanish_month(m.group(1), m.group(2), m.group(3))
            value = _parse_number_auto(m.group(4))
        except (KeyError, ValueError):
            continue
        if 100.0 <= value <= 5000.0:
            obs_candidates.append((date, value))
    if obs_candidates:
        date, value = max(obs_candidates, key=lambda item: item[0])
        return LatamRate("CLP", value, date, "BCCh")

    # Compact daily-indicators rendering used by some BCCh routes:
    # "Indicadores diarios (18-ago-2026) ... Dólar observado 914,19".
    compact_daily = re.search(
        r"Indicadores\s+diarios\s*\((\d{1,2})-(ene|feb|mar|abr|may|jun|jul|ago|sep|set|oct|nov|dic|jan|apr|aug|dec)-(\d{4})\).{0,1800}?(?:D[oó]lar\s+observado|Observed\s+dollar)\s+([0-9][\d.,]*)",
        text, re.IGNORECASE,
    )
    if compact_daily:
        value = _parse_number_auto(compact_daily.group(4))
        if 100.0 <= value <= 5000.0:
            return LatamRate(
                "CLP", value,
                _date_spanish_month(compact_daily.group(1), compact_daily.group(2), compact_daily.group(3)),
                "BCCh",
            )

    # Horizontal BDE basket/table rendering: all date headers first, then the
    # Dólar observado row.  Keep this fallback because the portal switches
    # between compact and horizontal layouts depending on route/session.
    table = re.search(
        r"\bSerie\s+(.*?)\s+(?:D[oó]lar\s+observado|Observed\s+dollar)\s+(.*?)(?:Eliminar\s+canasta|Remove\s+basket|Base\s+de\s+Datos\s+Estad[ií]sticos|Statistics\s+Database|$)",
        text, re.IGNORECASE,
    )
    if table:
        dates = re.findall(
            r"(\d{1,2})[.](Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Set|Oct|Nov|Dic|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[.](\d{4})",
            table.group(1), re.IGNORECASE,
        )
        # Preserve positional ND cells.  Removing them before zipping shifts all
        # later rates one column to the left and can make a valid BCCh table
        # look unreadable.  Select the newest dated numeric observation.
        value_cells = re.findall(
            r"(?<![A-Za-z0-9.,])(?:ND|[0-9]{2,4}(?:[.,][0-9]{1,4}))(?![A-Za-z0-9.,])",
            table.group(2), re.IGNORECASE,
        )
        if dates and len(value_cells) >= len(dates):
            table_candidates: list[tuple[str, float]] = []
            for (day, month, year), raw_value in zip(dates, value_cells):
                if raw_value.upper() == "ND":
                    continue
                try:
                    date = _date_spanish_month(day, month, year)
                    value = _parse_number_auto(raw_value)
                except (KeyError, ValueError):
                    continue
                if 100.0 <= value <= 5000.0:
                    table_candidates.append((date, value))
            if table_candidates:
                date, value = max(table_candidates, key=lambda item: item[0])
                return LatamRate("CLP", value, date, "BCCh")

    # 3) Older BDE mobile representation: "18-ago-2026 914,19".
    m = re.search(
        r"(\d{1,2})-(ene|feb|mar|abr|may|jun|jul|ago|sep|set|oct|nov|dic|jan|apr|aug|dec)-(\d{4})\s+([\d.,]+)",
        text, re.IGNORECASE,
    )
    if m:
        value = _parse_number_auto(m.group(4))
        if 100.0 <= value <= 5000.0:
            return LatamRate("CLP", value, _date_spanish_month(m.group(1), m.group(2), m.group(3)), "BCCh")

    # 4) Daily-indicators landing page.  It can legitimately show ND on a
    # weekend/holiday, therefore a numeric quote is accepted only when a date
    # can also be recovered from the page markup/text.
    daily_value = re.search(
        r"(?:D[oó]lar\s+observado|Observed\s+dollar)\s+([0-9][\d.,]*)",
        text, re.IGNORECASE,
    )
    if daily_value:
        date_match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if date_match:
            date = datetime(int(date_match.group(3)), int(date_match.group(2)), int(date_match.group(1))).date().isoformat()
            value = _parse_number_auto(daily_value.group(1))
            if 100.0 <= value <= 5000.0:
                return LatamRate("CLP", value, date, "BCCh")

    raise LatamPublicationError("No se encontró el Dólar Observado del Banco Central de Chile")

def parse_banrep(data: bytes) -> LatamRate:
    text = html_text(data)
    # The corporate page has changed its surrounding markup several times.
    # Anchor on the TRM heading, then accept the official value/date immediately
    # before the "Pesos por dólar" label.
    start = text.lower().find("tasa de cambio representativa del mercado")
    section = text[start:start + 2500] if start >= 0 else text
    m = re.search(
        r"([0-9][0-9.]*,[0-9]+)\s+(\d{2}/\d{2}/\d{4})\s+Pesos\s+por\s+d[oó]lar",
        section, re.IGNORECASE,
    )
    if not m:
        # Fallback for a compact card where the unit label is separated from the
        # value/date by harmless accessibility text.
        m = re.search(r"([0-9][0-9.]*,[0-9]+)\s+(\d{2}/\d{2}/\d{4})", section, re.IGNORECASE)
    if not m:
        raise LatamPublicationError("No se encontró la TRM del Banco de la República")
    return LatamRate("COP", _parse_spanish_number(m.group(1)), _date_dmy(m.group(2)), "BanRep")


def parse_bcp(data: bytes) -> LatamRate:
    text = html_text(data)
    header = re.search(r"COTIZACIONES DEL\s+(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚÑ]+)\s+DE\s+(\d{4})", text, re.IGNORECASE)
    close = re.search(r"Cierre\s+\d{1,2}/\d{1,2}\s+([\d.]+,\d+)", text, re.IGNORECASE)
    if not header or not close:
        raise LatamPublicationError("No se encontró el cierre referencial del BCP")
    date = _date_spanish_month(header.group(1), header.group(2), header.group(3))
    return LatamRate("PYG", _parse_spanish_number(close.group(1)), date, "BCP")


def _parse_bcrp_date(value: str) -> str | None:
    cleaned = value.strip().strip('"').replace("\xa0", " ")
    m = re.fullmatch(r"(\d{1,2})[.\s/-]*([A-Za-zÁÉÍÓÚáéíóú]{3,10})[.\s/-]*(\d{2,4})", cleaned)
    if not m:
        return None
    day, month, year = m.groups()
    month_key = month.lower().rstrip(".")
    month_num = _MONTHS_ES.get(month_key) or _MONTHS_ES.get(month_key[:3])
    if not month_num:
        return None
    year_i = int(year)
    if year_i < 100:
        year_i += 2000
    return datetime(year_i, month_num, int(day)).date().isoformat()


def parse_bcrp_csv(data: bytes) -> LatamRate:
    raw = unescape(data.decode("latin-1", errors="ignore"))
    raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    observations: list[tuple[str, float, float]] = []
    for row in csv.reader(io.StringIO(raw)):
        if len(row) < 3:
            continue
        date = _parse_bcrp_date(row[0])
        if not date:
            continue
        try:
            buy = float(row[1].strip().strip('"'))
            sell = float(row[2].strip().strip('"'))
        except ValueError:
            continue
        observations.append((date, buy, sell))

    # Backward-compatible fallback for the older unquoted representation used
    # by BCRPData and by saved test fixtures.
    if not observations:
        matches = re.findall(
            r"(\d{1,2})[.]?(Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Oct|Nov|Dic)[.]?(\d{2,4})\s*,\s*([\d.]+)\s*,\s*([\d.]+)",
            raw, re.IGNORECASE,
        )
        for day, month, year, buy, sell in matches:
            year_i = int(year) + (2000 if int(year) < 100 else 0)
            observations.append((_date_spanish_month(day, month, str(year_i)), float(buy), float(sell)))

    if not observations:
        raise LatamPublicationError("No se encontraron datos diarios del BCRP")
    date, buy, sell = observations[-1]
    return LatamRate("PEN", (buy + sell) / 2.0, date, "BCRP")


def _xml_local_name(tag: str) -> str:
    return str(tag).rsplit("}", 1)[-1]


def parse_bcu_soap(data: bytes) -> LatamRate:
    """Parse the official BCU ``awsbcucotizaciones`` SOAP response.

    Currency code 2222 is DÓLAR USA in the BCU service. The service returns
    TCC/TCV in UYU per USD. Pick the newest successful observation from the
    requested range.
    """
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise LatamPublicationError("Respuesta XML no válida del Web Service del BCU") from exc

    observations: list[tuple[str, float]] = []
    status = None
    error_message = ""
    for elem in root.iter():
        name = _xml_local_name(elem.tag)
        if name == "status" and status is None:
            status = (elem.text or "").strip()
        elif name == "mensaje" and not error_message:
            error_message = (elem.text or "").strip()
        if name != "datoscotizaciones.dato":
            continue
        row = {_xml_local_name(child.tag): (child.text or "").strip() for child in list(elem)}
        if row.get("Moneda") not in {"2222", ""} and row.get("CodigoISO", "").upper() != "USD":
            continue
        raw_date = row.get("Fecha", "")
        try:
            date = datetime.fromisoformat(raw_date[:10]).date().isoformat()
        except ValueError:
            continue
        values = []
        for key in ("TCC", "TCV"):
            try:
                value = float(row.get(key, ""))
            except (TypeError, ValueError):
                continue
            if value > 0:
                values.append(value)
        if not values:
            continue
        observations.append((date, sum(values) / len(values)))

    if observations:
        date, value = max(observations, key=lambda item: item[0])
        return LatamRate("UYU", value, date, "BCU")

    detail = f": {error_message}" if error_message else ""
    if status not in (None, "", "1"):
        raise LatamPublicationError(f"El Web Service del BCU devolvió estado {status}{detail}")
    raise LatamPublicationError("El Web Service del BCU no devolvió cotizaciones USD/UYU utilizables" + detail)


def fetch_bcu_soap(timeout: int = 15) -> LatamRate:
    # A 14-day range covers weekends/holidays and stays well inside the
    # official service's documented maximum period.
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=14)
    body = f'''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cot="Cotiza">
  <soapenv:Header/>
  <soapenv:Body>
    <cot:wsbcucotizaciones.Execute>
      <cot:Entrada>
        <cot:Moneda><cot:item>2222</cot:item></cot:Moneda>
        <cot:FechaDesde>{start.isoformat()}</cot:FechaDesde>
        <cot:FechaHasta>{end.isoformat()}</cot:FechaHasta>
        <cot:Grupo>0</cot:Grupo>
      </cot:Entrada>
    </cot:wsbcucotizaciones.Execute>
  </soapenv:Body>
</soapenv:Envelope>'''.encode("utf-8")
    req = urllib.request.Request(
        BCU_SOAP_URL,
        data=body,
        method="POST",
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "text/xml; charset=utf-8",
            "Accept": "text/xml,application/xml;q=0.9,*/*;q=0.5",
            "SOAPAction": "Cotizaaction/AWSBCUCOTIZACIONES.Execute",
            "Accept-Encoding": "identity",
            "Connection": "close",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return parse_bcu_soap(response.read())


def parse_bcu(data: bytes) -> LatamRate:
    text = html_text(data)

    # Detailed official cotizaciones table.
    m = re.search(r"DLS\.PROMED\.FONDO\s+(\d{2}/\d{2}/\d{4})\s+([\d.,]+)\s+([\d.,]+)", text, re.IGNORECASE)
    if m:
        return LatamRate("UYU", _parse_spanish_number(m.group(2)), _date_dmy(m.group(1)), "BCU")

    # The official table normally reports the same daily UYU/USD value under
    # DLS. USA BILLETE as well.  This gives us a second field on the same BCU
    # publication if the Promedio Fondo row changes or disappears.
    bill = re.search(r"DLS\.\s*USA\s+BILLETE\s+(\d{2}/\d{2}/\d{4})\s+([\d.,]+)\s+([\d.,]+)", text, re.IGNORECASE)
    if bill:
        return LatamRate("UYU", _parse_spanish_number(bill.group(2)), _date_dmy(bill.group(1)), "BCU")

    # Compact summary on the detailed page.
    value_m = re.search(r"U\$S\s+Prom\.?\s*Fdo\.?\s+([\d.,]+)", text, re.IGNORECASE)
    date_m = re.search(r"cierre\s+(?:del|:)\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    if value_m and date_m:
        return LatamRate("UYU", _parse_spanish_number(value_m.group(1)), _date_dmy(date_m.group(1)), "BCU")

    # Official BCU homepage.  This route is substantially more reliable than
    # the SharePoint detail page for non-browser clients and publishes the
    # daily "US$ Billete" quote directly.
    home = re.search(
        r"Cotizaciones\s+cierre\s*:\s*(\d{2}/\d{2}/\d{4}).{0,500}?US\$\s*Billete\s+([\d.,]+)",
        text, re.IGNORECASE,
    )
    if home:
        return LatamRate("UYU", _parse_spanish_number(home.group(2)), _date_dmy(home.group(1)), "BCU")

    raise LatamPublicationError("No se encontró una cotización USD/UYU utilizable del BCU")

def parse_bcb(data: bytes, wanted: set[str] | None = None) -> tuple[dict[str, float], str | None]:
    text = html_text(data)
    date = None
    dm = re.search(r"TABLA DE COTIZACIONES DEL\s+(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚÑ]+)\s+DE\s+(\d{4})", text, re.IGNORECASE)
    if dm:
        date = _date_spanish_month(dm.group(1), dm.group(2), dm.group(3))
    wanted = set(LATAM_EXTRA_CODES) if wanted is None else {c.upper() for c in wanted}
    result: dict[str, float] = {}
    for code in wanted:
        # BCB's last numeric column is "TIPO CAMBIO EN M.E." = units of that currency per USD.
        m = re.search(rf"\b{re.escape(code)}\b\s+([\d.,]+)\s+([\d.,]+)", text)
        if m:
            result[code] = _parse_english_number(m.group(2))
    if not result:
        raise LatamPublicationError("No se encontraron cotizaciones HISPAM en la tabla del BCB")
    return result, date


PARSERS = {
    "ARS": (
        (BCRA_API_URL, parse_bcra_api),
        (BCRA_API_ID_URL, parse_bcra_api),
        (BCRA_SERIES_URL, parse_bcra_series),
        (BCRA_URL, parse_bcra),
    ),
    "CLP": (
        (BCCH_TABLE_URL, parse_bcch),
        (BCCH_TABLE_ALT_URL, parse_bcch),
        (BCCH_HOME_URL, parse_bcch),
        (BCCH_HOME_ALT_URL, parse_bcch),
        (BCCH_URL, parse_bcch),
        (BCCH_DAILY_URL, parse_bcch),
        (BCCH_OLD_DAILY_URL, parse_bcch),
    ),
    "COP": ((BANREP_URL, parse_banrep), (BANREP_FALLBACK_URL, parse_banrep)),
    "PYG": ((BCP_URL, parse_bcp),),
    "PEN": ((BCRP_URL, parse_bcrp_csv),),
    "UYU": (
        (BCU_URL, parse_bcu),
        (BCU_ALT_URL, parse_bcu),
        (BCU_RATES_URL, parse_bcu),
        (BCU_FALLBACK_URL, parse_bcu),
    ),
}


def fetch_latam_rate(code: str) -> LatamRate:
    code = code.upper()
    if code not in PARSERS:
        raise ValueError(f"Divisa HISPAM no soportada: {code}")
    if code == "UYU":
        soap_publication_error: Exception | None = None
        soap_failure: Exception | None = None
        try:
            return fetch_bcu_soap()
        except LatamPublicationError as exc:
            soap_publication_error = exc
        except Exception as exc:
            soap_failure = exc
        try:
            return _fetch_first(PARSERS[code])
        except LatamPublicationError as page_exc:
            raise LatamPublicationError(str(page_exc)) from page_exc
        except Exception as page_exc:
            if soap_publication_error is not None:
                raise LatamPublicationError(str(soap_publication_error)) from soap_publication_error
            prefix = f"Web Service BCU: {soap_failure}; " if soap_failure else ""
            raise OSError(prefix + f"páginas BCU: {page_exc}") from page_exc
    return _fetch_first(PARSERS[code])


def fetch_bcb_rates(codes: set[str]) -> tuple[dict[str, float], str | None]:
    return _fetch_first((
        (BCB_URL, lambda data: parse_bcb(data, codes)),
        (BCB_FALLBACK_URL, lambda data: parse_bcb(data, codes)),
    ))
