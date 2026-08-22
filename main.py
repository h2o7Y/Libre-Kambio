#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from datetime import datetime
import fcntl
import traceback
import tempfile

try:
    from PySide6.QtCore import Qt, QObject, Signal, QRunnable, QThreadPool, QUrl, QSize, QItemSelectionModel
    from PySide6.QtGui import QDesktopServices, QIcon, QPixmap, QColor
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QComboBox,
        QCheckBox,
        QColorDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QTableWidget,
        QTableWidgetItem,
        QTabBar,
        QTabWidget,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    print("Falta PySide6. En Fedora: sudo dnf install python3-pyside6", file=sys.stderr)
    raise


from app_logic import (
    detect_system_language,
    parse_amount_text,
    resolve_language,
    sanitize_currency_state,
    alphabetical_codes,
    region_sorted_codes,
    currency_region_color,
    currency_region_name,
    effective_rounding_decimals,
    normalize_rounding_mode,
    normalize_decimal_separator_mode,
    currency_decimal_separator,
    normalize_verification_display_mode,
    strip_zero_fraction,
)

from latam_rates import (
    LATAM_EXTRA_CODES, LATAM_SOURCE_NAMES, LATAM_SOURCE_URLS, BCB_URL,
)

from rates import (
    AED_USD_PEG,
    SAR_USD_PEG,
    QAR_USD_PEG,
    BHD_USD_PEG,
    OMR_USD_PEG,
    USD_PEGS,
    CBUAE_URL,
    SAMA_URL,
    QCB_URL,
    CBO_URL,
    CBB_URL,
    ECB_INFO_URL,
    CBR_INFO_URL,
    RatesSnapshot,
    convert,
    load_cache,
    update_rates,
    verification,
    primary_source_for,
)

APP_NAME = "Libre Kambio"
APP_VERSION = "1.9.31"

PRIMARY = ["EUR", "JPY", "GBP", "PLN", "SEK", "TRY", "USD", "CZK", "AED", "SAR", "RUB", "UAH"]
META = {
    "EUR": {"es": "Euro", "en": "Euro", "symbol": "€", "flag": "🇪🇺"},
    "JPY": {"es": "Yen japonés", "en": "Japanese yen", "symbol": "¥", "flag": "🇯🇵"},
    "GBP": {"es": "Libra esterlina", "en": "British pound", "symbol": "£", "flag": "🇬🇧"},
    "PLN": {"es": "Złoty polaco", "en": "Polish zloty", "symbol": "zł", "flag": "🇵🇱"},
    "SEK": {"es": "Corona sueca", "en": "Swedish krona", "symbol": "kr", "flag": "🇸🇪"},
    "TRY": {"es": "Lira turca", "en": "Turkish lira", "symbol": "₺", "flag": "🇹🇷"},
    "USD": {"es": "Dólar estadounidense", "en": "US dollar", "symbol": "$", "flag": "🇺🇸"},
    "CZK": {"es": "Corona checa", "en": "Czech koruna", "symbol": "Kč", "flag": "🇨🇿"},
    "AED": {"es": "Dírham de EAU", "en": "UAE dirham", "symbol": "AED", "flag": "🇦🇪"},
    "SAR": {"es": "Riyal saudí", "en": "Saudi riyal", "symbol": "SAR", "flag": "🇸🇦"},
    "RUB": {"es": "Rublo ruso", "en": "Russian ruble", "symbol": "₽", "flag": "🇷🇺"},
    "UAH": {"es": "Grivna ucraniana", "en": "Ukrainian hryvnia", "symbol": "₴", "flag": "🇺🇦"},
    "AUD": {"es": "Dólar australiano", "en": "Australian dollar", "symbol": "A$", "flag": "🇦🇺"},
    "BRL": {"es": "Real brasileño", "en": "Brazilian real", "symbol": "R$", "flag": "🇧🇷"},
    "CAD": {"es": "Dólar canadiense", "en": "Canadian dollar", "symbol": "C$", "flag": "🇨🇦"},
    "CHF": {"es": "Franco suizo", "en": "Swiss franc", "symbol": "Fr", "flag": "🇨🇭"},
    "CNY": {"es": "Yuan chino", "en": "Chinese yuan", "symbol": "¥", "flag": "🇨🇳"},
    "DKK": {"es": "Corona danesa", "en": "Danish krone", "symbol": "kr", "flag": "🇩🇰"},
    "HKD": {"es": "Dólar de Hong Kong", "en": "Hong Kong dollar", "symbol": "HK$", "flag": "🇭🇰"},
    "HUF": {"es": "Forinto húngaro", "en": "Hungarian forint", "symbol": "Ft", "flag": "🇭🇺"},
    "IDR": {"es": "Rupia indonesia", "en": "Indonesian rupiah", "symbol": "Rp", "flag": "🇮🇩"},
    "ILS": {"es": "Nuevo séquel israelí", "en": "Israeli new shekel", "symbol": "₪", "flag": "🇮🇱"},
    "INR": {"es": "Rupia india", "en": "Indian rupee", "symbol": "₹", "flag": "🇮🇳"},
    "ISK": {"es": "Corona islandesa", "en": "Icelandic krona", "symbol": "kr", "flag": "🇮🇸"},
    "KRW": {"es": "Won surcoreano", "en": "South Korean won", "symbol": "₩", "flag": "🇰🇷"},
    "MXN": {"es": "Peso mexicano", "en": "Mexican peso", "symbol": "$", "flag": "🇲🇽"},
    "MYR": {"es": "Ringgit malasio", "en": "Malaysian ringgit", "symbol": "RM", "flag": "🇲🇾"},
    "NOK": {"es": "Corona noruega", "en": "Norwegian krone", "symbol": "kr", "flag": "🇳🇴"},
    "NZD": {"es": "Dólar neozelandés", "en": "New Zealand dollar", "symbol": "NZ$", "flag": "🇳🇿"},
    "PHP": {"es": "Peso filipino", "en": "Philippine peso", "symbol": "₱", "flag": "🇵🇭"},
    "RON": {"es": "Leu rumano", "en": "Romanian leu", "symbol": "lei", "flag": "🇷🇴"},
    "SGD": {"es": "Dólar de Singapur", "en": "Singapore dollar", "symbol": "S$", "flag": "🇸🇬"},
    "THB": {"es": "Baht tailandés", "en": "Thai baht", "symbol": "฿", "flag": "🇹🇭"},
    "ZAR": {"es": "Rand sudafricano", "en": "South African rand", "symbol": "R", "flag": "🇿🇦"},
    "AZN": {"es": "Manat azerbaiyano", "en": "Azerbaijani manat", "symbol": "₼", "flag": "🇦🇿"},
    "DZD": {"es": "Dinar argelino", "en": "Algerian dinar", "symbol": "DZD", "flag": "🇩🇿"},
    "AMD": {"es": "Dram armenio", "en": "Armenian dram", "symbol": "֏", "flag": "🇦🇲"},
    "BHD": {"es": "Dinar bareiní", "en": "Bahraini dinar", "symbol": "BHD", "flag": "🇧🇭"},
    "BYN": {"es": "Rublo bielorruso", "en": "Belarusian ruble", "symbol": "Br", "flag": "🇧🇾"},
    "BOB": {"es": "Boliviano", "en": "Bolivian boliviano", "symbol": "Bs", "flag": "🇧🇴"},
    "VND": {"es": "Dong vietnamita", "en": "Vietnamese dong", "symbol": "₫", "flag": "🇻🇳"},
    "EGP": {"es": "Libra egipcia", "en": "Egyptian pound", "symbol": "E£", "flag": "🇪🇬"},
    "IRR": {"es": "Rial iraní", "en": "Iranian rial", "symbol": "﷼", "flag": "🇮🇷"},
    "QAR": {"es": "Riyal catarí", "en": "Qatari riyal", "symbol": "QAR", "flag": "🇶🇦"},
    "CUP": {"es": "Peso cubano", "en": "Cuban peso", "symbol": "$", "flag": "🇨🇺"},
    "MMK": {"es": "Kyat birmano", "en": "Myanmar kyat", "symbol": "K", "flag": "🇲🇲"},
    "GEL": {"es": "Lari georgiano", "en": "Georgian lari", "symbol": "₾", "flag": "🇬🇪"},
    "MDL": {"es": "Leu moldavo", "en": "Moldovan leu", "symbol": "L", "flag": "🇲🇩"},
    "NGN": {"es": "Naira nigeriana", "en": "Nigerian naira", "symbol": "₦", "flag": "🇳🇬"},
    "TMT": {"es": "Manat turcomano", "en": "Turkmenistan manat", "symbol": "m", "flag": "🇹🇲"},
    "OMR": {"es": "Rial omaní", "en": "Omani rial", "symbol": "OMR", "flag": "🇴🇲"},
    "RSD": {"es": "Dinar serbio", "en": "Serbian dinar", "symbol": "RSD", "flag": "🇷🇸"},
    "KGS": {"es": "Som kirguís", "en": "Kyrgyzstani som", "symbol": "KGS", "flag": "🇰🇬"},
    "TJS": {"es": "Somoni tayiko", "en": "Tajikistani somoni", "symbol": "TJS", "flag": "🇹🇯"},
    "BDT": {"es": "Taka bangladesí", "en": "Bangladeshi taka", "symbol": "৳", "flag": "🇧🇩"},
    "KZT": {"es": "Tenge kazajo", "en": "Kazakhstani tenge", "symbol": "₸", "flag": "🇰🇿"},
    "MNT": {"es": "Tugrik mongol", "en": "Mongolian tugrik", "symbol": "₮", "flag": "🇲🇳"},
    "UZS": {"es": "Som uzbeko", "en": "Uzbekistani som", "symbol": "UZS", "flag": "🇺🇿"},
    "ETB": {"es": "Birr etíope", "en": "Ethiopian birr", "symbol": "Br", "flag": "🇪🇹"},
    "ARS": {"es": "Peso argentino", "en": "Argentine peso", "symbol": "$", "flag": "🇦🇷"},
    "CLP": {"es": "Peso chileno", "en": "Chilean peso", "symbol": "$", "flag": "🇨🇱"},
    "COP": {"es": "Peso colombiano", "en": "Colombian peso", "symbol": "$", "flag": "🇨🇴"},
    "PYG": {"es": "Guaraní paraguayo", "en": "Paraguayan guarani", "symbol": "₲", "flag": "🇵🇾"},
    "PEN": {"es": "Sol peruano", "en": "Peruvian sol", "symbol": "S/", "flag": "🇵🇪"},
    "UYU": {"es": "Peso uruguayo", "en": "Uruguayan peso", "symbol": "$U", "flag": "🇺🇾"},
}

UI_TEXTS = {
    "es": {
        "page_title": "Divisas",
        "subtitle": "BCE (fuente principal) · Algunas peg USD · Banco de Rusia (+ divisas y comprobación cruzada para BCE y peg)",
        "refresh": "↻  Actualizar",
        "amount": "Cantidad",
        "clear_amount": "Borrar cantidad",
        "base_currency": "Moneda base",
        "organize_currencies": "Organizar monedas",
        "tab_converter": "Conversor",
        "tab_verification": "Verificación",
        "tab_sources": "Fuentes",
        "tab_currencies": "Monedas",
        "tab_groups": "Grupos",
        "tab_options": "Opciones",
        "verify_intro": "El CBR se usa como segunda lectura, no para sustituir al BCE. En las divisas hispanoamericanas opcionales, el BCB puede aportar una comprobación indicativa independiente. La columna Fechas deja visible si las referencias corresponden a días distintos.",
        "currencies_help": "Marca las monedas que quieres ver y arrástralas para cambiar el orden. La etiqueta muestra la región y el indicador mantiene una referencia visual discreta. Los cambios se guardan automáticamente.",
        "groups_help": "Crea grupos de divisas, ordénalos y asigna cada moneda a un grupo. En el conversor, las tarjetas se muestran por bloques compactos.",
        "group_assignment_help": "Asigna cada moneda al grupo que prefieras. Puedes seleccionar varias filas y aplicarles el mismo grupo de una vez.",
        "bulk_group_label": "Asignación múltiple",
        "bulk_group_apply": "Aplicar grupo a seleccionadas",
        "bulk_group_apply_count": "Aplicar a {count} seleccionadas",
        "bulk_group_no_selection": "Selecciona una o varias divisas en la tabla.",
        "bulk_group_done": "Grupo aplicado a {count} divisas.",
        "sort_by": "Ordenar por",
        "sort_code": "Código A–Z",
        "sort_region": "Región",
        "currency_column": "Divisa",
        "region_column": "Región",
        "source_missing_short": "No publicado",
        "source_download_failed_short": "Descarga fallida",
        "source_missing_banner": "Cálculo detenido por seguridad",
        "new_group": "Nuevo grupo",
        "add_group": "Añadir grupo",
        "remove_group": "Eliminar grupo",
        "reset_groups": "Restaurar grupos",
        "group_color": "Color del grupo…",
        "group_color_tip": "Cambia el color del grupo seleccionado. En el Conversor se muestra en una versión apagada.",
        "group_color_no_selection": "Selecciona primero un grupo para cambiar su color.",
        "show_all": "Mostrar todas",
        "primary_only": "Solo principales",
        "reset_order": "Restaurar orden",
        "undo": "↶ Deshacer",
        "undo_none": "Nada que deshacer",
        "undo_done": "Cambio deshecho",
        "undo_tip": "Deshace los últimos cambios de monedas y grupos realizados durante esta sesión. Se conservan hasta 10 pasos.",
        "source_none": "Sin datos",
        "update_tooltip": "Al día: ambas fuentes se han podido consultar en esta comprobación y la app está usando la publicación más reciente encontrada en cada una.\nBCE/CBR · última publicación: fecha de la publicación más reciente encontrada.\nCopia local: no se pudo volver a consultar esa fuente y se usa la última descarga correcta guardada; puede existir una publicación posterior que aún no se haya podido confirmar.",
        "options_help": "Elige el idioma de la interfaz y cómo quieres ver las monedas.",
        "language": "Idioma",
        "currency_labels": "Etiquetas de divisa",
        "flag_position": "Posición de la bandera en Conversor",
        "flag_before": "Antes del código / nombre",
        "flag_after_code": "Después del código (EUR 🇪🇺)",
        "flag_after": "Después del símbolo",
        "flag_hint": "Solo afecta a las tarjetas del Conversor. Puedes colocar la bandera antes del código, justo después del código/nombre o después del símbolo.",
        "symbol_position": "Posición del símbolo en Conversor",
        "symbol_before_all": "Antes de bandera/código (€ 🇪🇺 EUR)",
        "symbol_before_code": "Antes del código (🇪🇺 € EUR)",
        "symbol_after_code": "Después del código (🇪🇺 EUR €)",
        "symbol_after": "Al final",
        "symbol_hint": "El símbolo y la bandera se colocan de forma independiente. Las posiciones de la izquierda se adaptan al lugar elegido para la bandera.",
        "rounding": "Redondeo de resultados",
        "round_auto": "Automático",
        "round_zero": "Sin decimales",
        "round_one": "1 decimal",
        "round_two": "2 decimales",
        "rounding_hint": "Las divisas sin unidad fraccionaria (por ejemplo, JPY) se muestran siempre sin decimales.",
        "zero_fraction": "Mostrar ceros decimales exactos",
        "zero_fraction_hide": "Ocultar ,00 / .00 (predeterminado)",
        "zero_fraction_keep": "Mostrar y copiar ,00 / .00",
        "zero_fraction_hint": "Si el resultado redondeado es exacto, puedes ocultar los ceros finales o conservarlos tanto en pantalla como al copiar.",
        "decimal_separator": "Mostrar separador decimal",
        "decimal_currency": "Según divisa/país",
        "decimal_comma": "Coma (1.234,56)",
        "decimal_dot": "Punto (1,234.56)",
        "decimal_hint": "Según divisa/país usa una convención habitual asociada a cada divisa (por ejemplo, EUR con coma y GBP/USD con punto).",
        "verification_display": "Mostrar comprobación en Conversor",
        "verification_always": "Mostrar siempre",
        "verification_issues": "Solo avisos o problemas",
        "verification_display_hint": "En «Solo avisos o problemas» se ocultan las comprobaciones coherentes y los pegs confirmados; si aparece una advertencia o una diferencia alta, el recuadro vuelve a mostrarse en amarillo o rojo.",
        "latam_status_label": "HISPAM",
        "latam_optional_title": "Divisas hispanoamericanas opcionales",
        "latam_optional_hint": "Activa solo las que quieras utilizar. Cada divisa usa una referencia oficial de su autoridad monetaria y, cuando el Banco Central de Bolivia publica esa moneda, se añade una comprobación cruzada indicativa del BCB. Al activar o desactivar una divisa se actualizan las fuentes.",
        "latam_bcb_note": "La tabla del BCB indica que sus cotizaciones de monedas son indicativas (excepto USD); se usan únicamente como comprobación secundaria.",
        "label_code": "Código (JPY)",
        "label_name": "Nombre (Yen japonés)",
        "label_both": "Código + nombre",
        "english": "Inglés",
        "spanish": "Español",
        "base_badge": "BASE",
        "copy_value": "Copiar valor",
        "card_click": "Haz clic en la tarjeta para usar esta moneda como base.",
        "group_currencies": "monedas",
        "group_currency": "moneda",
        "group_default_primary": "Principales",
        "group_default_gulf": "Golfo",
        "group_default_east": "Europa Este",
        "group_default_other": "Otras",
        "status_ready": "Listo",
        "amount_placeholder": "Escribe una cantidad…",
        "source_row_none": "Fuente única en esta app",
        "reference_disclaimer": "Tipos de referencia únicamente · No son tipos transaccionales ni asesoramiento financiero, contable, fiscal o jurídico · Verifica los valores importantes con la fuente oficial",
        "not_available": "No disponible",
        "same_date_note": "Misma fecha",
        "settings_saved": "Guardado",
        "already_open_title": "Aplicación ya abierta",
        "already_open_text": "Libre Kambio ya está abierto. Cierra la otra ventana si quieres volver a abrirlo.",
    },
    "en": {
        "page_title": "Currencies",
        "subtitle": "ECB (primary source) · Some via USD peg · Bank of Russia (+ currencies and cross-checking for ECB and pegs)",
        "refresh": "↻  Refresh",
        "amount": "Amount",
        "clear_amount": "Clear amount",
        "base_currency": "Base currency",
        "organize_currencies": "Organize currencies",
        "tab_converter": "Converter",
        "tab_verification": "Verification",
        "tab_sources": "Sources",
        "tab_currencies": "Currencies",
        "tab_groups": "Groups",
        "tab_options": "Options",
        "verify_intro": "The CBR is used as a second reading, not as a replacement for the ECB. For optional Latin American currencies, the BCB may provide an independent indicative cross-check. The Dates column makes it clear when the references belong to different days.",
        "currencies_help": "Tick the currencies you want to see and drag them to change the order. The label and colour identify its region. Changes are saved automatically.",
        "groups_help": "Create currency groups, reorder them and assign each currency to a group. In the converter, cards are shown in compact grouped blocks.",
        "group_assignment_help": "Assign each currency to the group you prefer. You can select several rows and apply the same group to all of them at once.",
        "bulk_group_label": "Bulk assignment",
        "bulk_group_apply": "Apply group to selected",
        "bulk_group_apply_count": "Apply to {count} selected",
        "bulk_group_no_selection": "Select one or more currencies in the table.",
        "bulk_group_done": "Group applied to {count} currencies.",
        "sort_by": "Sort by",
        "sort_code": "Code A–Z",
        "sort_region": "Region",
        "currency_column": "Currency",
        "region_column": "Region",
        "source_missing_short": "Not published",
        "source_download_failed_short": "Download failed",
        "source_missing_banner": "Calculation stopped for safety",
        "new_group": "New group",
        "add_group": "Add group",
        "remove_group": "Delete group",
        "reset_groups": "Reset groups",
        "group_color": "Group color…",
        "group_color_tip": "Change the selected group's color. The Converter uses a muted version of it.",
        "group_color_no_selection": "Select a group first to change its color.",
        "show_all": "Show all",
        "primary_only": "Primary only",
        "reset_order": "Reset order",
        "undo": "↶ Undo",
        "undo_none": "Nothing to undo",
        "undo_done": "Change undone",
        "undo_tip": "Undo recent currency and group changes made during this session. Up to 10 steps are kept.",
        "source_none": "No data",
        "update_tooltip": "Up to date: both sources were reached during this check and the app is using the newest publication found from each one.\nECB/CBR · latest publication: date of the newest publication found.\nLocal copy: that source could not be checked again, so the last successful saved download is used; a newer publication may exist but could not yet be confirmed.",
        "options_help": "Choose the interface language and how you want currencies to be shown.",
        "language": "Language",
        "currency_labels": "Currency labels",
        "flag_position": "Flag position in Converter",
        "flag_before": "Before code / name",
        "flag_after_code": "After code (EUR 🇪🇺)",
        "flag_after": "After currency symbol",
        "flag_hint": "Only affects Converter cards. You can place the flag before the code, immediately after the code/name, or after the currency symbol.",
        "symbol_position": "Currency symbol position in Converter",
        "symbol_before_all": "Before flag/code (€ 🇪🇺 EUR)",
        "symbol_before_code": "Before code (🇪🇺 € EUR)",
        "symbol_after_code": "After code (🇪🇺 EUR €)",
        "symbol_after": "At the end",
        "symbol_hint": "The currency symbol and flag are positioned independently. Left-side positions adapt to the selected flag position.",
        "rounding": "Result rounding",
        "round_auto": "Automatic",
        "round_zero": "No decimals",
        "round_one": "1 decimal",
        "round_two": "2 decimals",
        "rounding_hint": "Currencies without a fractional minor unit (for example, JPY) are always shown without decimals.",
        "zero_fraction": "Show exact decimal zeros",
        "zero_fraction_hide": "Hide .00 / ,00 (default)",
        "zero_fraction_keep": "Show and copy .00 / ,00",
        "zero_fraction_hint": "When the rounded result is exact, you can hide trailing zeros or keep them both on screen and in copied values.",
        "decimal_separator": "Show decimal separator",
        "decimal_currency": "By currency/country",
        "decimal_comma": "Comma (1.234,56)",
        "decimal_dot": "Point (1,234.56)",
        "decimal_hint": "By currency/country uses a common convention associated with each currency (for example, EUR with a comma and GBP/USD with a point).",
        "verification_display": "Show verification in Converter",
        "verification_always": "Always show",
        "verification_issues": "Warnings or problems only",
        "verification_display_hint": "With «Warnings or problems only», consistent cross-checks and confirmed pegs are hidden; warning or high-difference badges reappear in yellow or red.",
        "latam_status_label": "LATAM",
        "latam_optional_title": "Optional Latin American currencies",
        "latam_optional_hint": "Enable only the currencies you want to use. Each currency uses an official reference from its monetary authority and, when the Central Bank of Bolivia publishes that currency, an indicative BCB cross-check is added. Sources refresh when a currency is enabled or disabled.",
        "latam_bcb_note": "The BCB table states that its non-USD currency quotations are indicative; they are used only as a secondary cross-check.",
        "label_code": "Code (JPY)",
        "label_name": "Name (Japanese yen)",
        "label_both": "Code + name",
        "english": "English",
        "spanish": "Spanish",
        "base_badge": "BASE",
        "copy_value": "Copy value",
        "card_click": "Click the card to use that currency as the base currency.",
        "group_currencies": "currencies",
        "group_currency": "currency",
        "group_default_primary": "Primary",
        "group_default_gulf": "Gulf",
        "group_default_east": "Eastern Europe",
        "group_default_other": "Other",
        "status_ready": "Ready",
        "amount_placeholder": "Type an amount…",
        "source_row_none": "Single source in this app",
        "reference_disclaimer": "Reference rates only · Not transaction rates or financial, accounting, tax or legal advice · Verify important values with the official source",
        "not_available": "Not available",
        "same_date_note": "Same date",
        "settings_saved": "Saved",
        "already_open_title": "Application already open",
        "already_open_text": "Libre Kambio is already open. Close the other window if you want to open it again.",
    },
}

def ui_text(language: str, key: str) -> str:
    language = language if language in UI_TEXTS else "es"
    return UI_TEXTS[language].get(key, UI_TEXTS["es"].get(key, key))

def localized_verification_status(status: str, language: str) -> str:
    if language != "en":
        return status
    mapping = {
        "Sin segunda fuente": "No second source",
        "Fuente no publica": "Not published by source",
        "Fuente no disponible": "Source unavailable",
        "Coherente": "Consistent",
        "Revisar": "Review",
        "Diferencia alta": "High difference",
        "Peg confirmado": "Peg confirmed",
        "Peg: revisar": "Peg: review",
        "Peg no coincide": "Peg mismatch",
    }
    return mapping.get(status, status)


def localized_date_note(note: str, language: str) -> str:
    if language != "en":
        return note
    if note == "Misma fecha":
        return "Same date"
    if note == "CBR +1 día":
        return "CBR +1 day"
    if note == "CBR −1 día":
        return "CBR −1 day"
    if note.startswith("CBR +") and note.endswith(" días"):
        return note[:-5] + " days"
    if note.startswith("CBR -") and note.endswith(" días"):
        return note[:-5] + " days"
    return note


def currency_name(code: str, language: str = "es") -> str:
    meta = META.get(code, {})
    return str(meta.get(language, meta.get("es", code)))

def currency_symbol(code: str) -> str:
    return str(META.get(code, {}).get("symbol", code))

def currency_flag(code: str) -> str:
    return str(META.get(code, {}).get("flag", ""))

def currency_label(code: str, language: str = "es", mode: str = "code") -> str:
    code = str(code).upper()
    name = currency_name(code, language)
    if mode == "name":
        return name
    if mode == "both":
        return f"{code} · {name}"
    return code

def canonical_default_group(group_name: str) -> str:
    aliases = {
        "Primary": "Principales", "Primary currencies": "Principales",
        "Gulf": "Golfo",
        "Eastern Europe": "Europa Este",
        "Other": "Otras",
    }
    return aliases.get(group_name, group_name)

def localized_group_name(group_name: str, language: str) -> str:
    canonical = canonical_default_group(group_name)
    mapping = {
        "Principales": ui_text(language, "group_default_primary"),
        "Golfo": ui_text(language, "group_default_gulf"),
        "Europa Este": ui_text(language, "group_default_east"),
        "Otras": ui_text(language, "group_default_other"),
    }
    return mapping.get(canonical, canonical)

def _unique_codes(codes) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for code in codes:
        value = str(code).upper()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


BASE_SUPPORTED_CODES = _unique_codes(list(PRIMARY) + sorted(code for code in META.keys() if code not in LATAM_EXTRA_CODES))


def _unique_names(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        name = str(value).strip()
        if name and name not in seen:
            seen.add(name)
            result.append(name)
    return result


def _localize_number(text: str, decimal_separator: str) -> str:
    if decimal_separator == ",":
        return text.replace(",", "X").replace(".", ",").replace("X", ".")
    return text


def _smart_decimals(value: float) -> int:
    av = abs(value)
    if av >= 1000:
        return 4
    if av >= 1:
        return 6
    return 8


def fmt_number(value: float, decimal_separator: str = ",", grouping: bool = True) -> str:
    decimals = _smart_decimals(value)
    text = f"{value:,.{decimals}f}" if grouping else f"{value:.{decimals}f}"
    text = text.rstrip("0").rstrip(".")
    return _localize_number(text, decimal_separator)


def fmt_currency_amount(
    value: float,
    code: str,
    rounding_mode: str = "2",
    decimal_separator_mode: str = "currency",
    grouping: bool = True,
    keep_zero_fraction: bool = False,
) -> str:
    separator = currency_decimal_separator(code, decimal_separator_mode)
    decimals = effective_rounding_decimals(code, rounding_mode)
    if decimals is None:
        return fmt_number(value, decimal_separator=separator, grouping=grouping)
    text = f"{value:,.{decimals}f}" if grouping else f"{value:.{decimals}f}"
    localized = _localize_number(text, separator)
    return localized if keep_zero_fraction else strip_zero_fraction(localized, separator)


def fmt_currency_copy(
    value: float,
    code: str,
    rounding_mode: str = "2",
    decimal_separator_mode: str = "currency",
    keep_zero_fraction: bool = False,
) -> str:
    # Clipboard output deliberately never contains thousands/grouping separators.
    return fmt_currency_amount(
        value, code, rounding_mode=rounding_mode,
        decimal_separator_mode=decimal_separator_mode, grouping=False,
        keep_zero_fraction=keep_zero_fraction,
    )


def settings_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    path = base / "libre-kambio-currency" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def normalize_group_name(raw: str) -> str:
    return " ".join(str(raw or "").strip().split())


def default_group_order() -> list[str]:
    return ["Principales", "Golfo", "Europa Este", "Otras"]


def default_group_for(code: str) -> str:
    code = str(code).upper()
    if code in {"AED", "SAR", "QAR", "BHD", "OMR"}:
        return "Golfo"
    if code in {"RUB", "UAH"}:
        return "Europa Este"
    if code in PRIMARY:
        return "Principales"
    return "Otras"


def ensure_group_defaults(group_order, currency_groups, codes) -> tuple[list[str], dict[str, str]]:
    order = _unique_names(group_order or default_group_order())
    if "Otras" not in order:
        order.append("Otras")
    mapping: dict[str, str] = {}
    for code in _unique_codes(codes):
        group = normalize_group_name((currency_groups or {}).get(code, default_group_for(code)))
        if not group:
            group = default_group_for(code)
        if group not in order:
            order.append(group)
        mapping[code] = group
    return order, mapping


DEFAULT_GROUP_COLORS = {
    "Principales": "#596676",
    "Golfo": "#6d675e",
    "Europa Este": "#587268",
    "Otras": "#6b6270",
}
GROUP_COLOR_FALLBACKS = ["#5f6f82", "#75645b", "#60766f", "#70657a", "#6c7080", "#76606a"]


def normalize_group_color(value: object, fallback: str = "#606a78") -> str:
    color = QColor(str(value or ""))
    if not color.isValid():
        color = QColor(fallback)
    return color.name()


def default_group_color(name: str) -> str:
    canonical = canonical_default_group(name)
    if canonical in DEFAULT_GROUP_COLORS:
        return DEFAULT_GROUP_COLORS[canonical]
    idx = sum(ord(ch) for ch in str(name)) % len(GROUP_COLOR_FALLBACKS)
    return GROUP_COLOR_FALLBACKS[idx]


def ensure_group_colors(group_order: list[str], group_colors: dict[str, str] | None) -> dict[str, str]:
    incoming = group_colors or {}
    return {name: normalize_group_color(incoming.get(name), default_group_color(name)) for name in group_order}


FLAG_POSITIONS = {"before", "after_code", "after"}


def normalize_flag_position(value: object) -> str:
    position = str(value or "").lower()
    return position if position in FLAG_POSITIONS else "before"


SYMBOL_POSITIONS = {"before_all", "before_code", "after_code", "after"}


def normalize_symbol_position(value: object) -> str:
    position = str(value or "").lower()
    return position if position in SYMBOL_POSITIONS else "after"


def load_preferences() -> tuple[list[str], set[str], list[str], dict[str, str], dict[str, str], str, str, bool, str, str, str, str, str, bool, set[str]]:
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
        order = _unique_codes(data.get("currency_order", []))
        visible = set(_unique_codes(data.get("visible_currencies", [])))
        if not order:
            order = list(PRIMARY)
        if not visible:
            visible = set(PRIMARY)
        group_order, currency_groups = ensure_group_defaults(
            data.get("group_order", default_group_order()),
            data.get("currency_groups", {}),
            order,
        )
        language_manual = bool(data.get("language_manual", False))
        language = resolve_language(data.get("language"), language_manual)
        label_mode = str(data.get("label_mode", "code")).lower()
        if label_mode not in {"code", "name", "both"}:
            label_mode = "code"
        rounding_mode = normalize_rounding_mode(data.get("rounding_mode", "2"), data.get("round_two_decimals", False))
        group_colors = ensure_group_colors(group_order, data.get("group_colors", {}))
        decimal_separator_mode = normalize_decimal_separator_mode(data.get("decimal_separator_mode", "currency"))
        flag_position = normalize_flag_position(data.get("flag_position", "before"))
        symbol_position = normalize_symbol_position(data.get("symbol_position", "after"))
        verification_display_mode = normalize_verification_display_mode(data.get("verification_display_mode", "always"))
        keep_zero_fraction = bool(data.get("keep_zero_fraction", False))
        latam_enabled = {code for code in _unique_codes(data.get("latam_enabled", [])) if code in LATAM_EXTRA_CODES}
        return order, visible, group_order, currency_groups, group_colors, language, label_mode, language_manual, rounding_mode, decimal_separator_mode, flag_position, symbol_position, verification_display_mode, keep_zero_fraction, latam_enabled
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        order = list(PRIMARY)
        visible = set(PRIMARY)
        group_order, currency_groups = ensure_group_defaults(default_group_order(), {}, order)
        group_colors = ensure_group_colors(group_order, {})
        return order, visible, group_order, currency_groups, group_colors, detect_system_language(), "code", False, "2", "currency", "before", "after", "always", False, set()


def save_preferences(
    order: list[str],
    visible: set[str],
    group_order: list[str],
    currency_groups: dict[str, str],
    group_colors: dict[str, str],
    language: str,
    label_mode: str,
    language_manual: bool,
    rounding_mode: str,
    decimal_separator_mode: str,
    flag_position: str,
    symbol_position: str,
    verification_display_mode: str,
    keep_zero_fraction: bool,
    latam_enabled: set[str],
) -> None:
    order = _unique_codes(order)
    visible = set(_unique_codes(visible))
    group_order, currency_groups = ensure_group_defaults(group_order, currency_groups, order)
    group_colors = ensure_group_colors(group_order, group_colors)
    payload = {
        "version": 13,
        "currency_order": order,
        "visible_currencies": [code for code in order if code in visible],
        "group_order": group_order,
        "currency_groups": {code: currency_groups.get(code, default_group_for(code)) for code in order},
        "group_colors": group_colors,
        "language": language,
        "language_manual": bool(language_manual),
        "label_mode": label_mode,
        "rounding_mode": normalize_rounding_mode(rounding_mode),
        "decimal_separator_mode": normalize_decimal_separator_mode(decimal_separator_mode),
        "flag_position": normalize_flag_position(flag_position),
        "symbol_position": normalize_symbol_position(symbol_position),
        "verification_display_mode": normalize_verification_display_mode(verification_display_mode),
        "keep_zero_fraction": bool(keep_zero_fraction),
        "latam_enabled": [code for code in LATAM_EXTRA_CODES if code in set(latam_enabled)],
    }
    path = settings_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def lock_path() -> Path:
    return settings_path().with_name("instance.lock")


class SingleInstanceLock:
    def __init__(self):
        self.handle = None

    def acquire(self) -> bool:
        path = lock_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = open(path, "a+")
        try:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.handle.seek(0)
            self.handle.truncate()
            self.handle.write(str(os.getpid()))
            self.handle.flush()
            return True
        except OSError:
            return False

    def release(self):
        if self.handle is not None:
            try:
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                self.handle.close()
            except OSError:
                pass
            self.handle = None


class WorkerSignals(QObject):
    done = Signal(object)
    failed = Signal(str)


class UpdateWorker(QRunnable):
    def __init__(self, latam_enabled: set[str] | None = None):
        super().__init__()
        self.signals = WorkerSignals()
        self.latam_enabled = set(latam_enabled or ())

    def run(self):
        try:
            self.signals.done.emit(update_rates(self.latam_enabled))
        except Exception as exc:
            self.signals.failed.emit(str(exc))


class OrganizerTable(QTableWidget):
    """Flat currency organizer with manual mouse reordering.

    Native Qt item-view drag/drop is deliberately DISABLED.  QTableView has
    special move/overwrite semantics and QAbstractItemView can remove source
    rows after an accepted MoveAction.  We only use mouse press/move/release
    to calculate an insertion position, then move the complete row ourselves.
    Therefore dropping over a currency can never overwrite, delete or nest it.
    """

    orderChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(0, 3, parent)
        self._press_pos = None
        self._dragged_code: str | None = None
        self._manual_dragging = False
        self._insert_row = -1

        # Critical safety choice: no Qt DnD at all.  Reordering is implemented
        # below with ordinary mouse events, so the model never receives a drop.
        self.setDragEnabled(False)
        self.setAcceptDrops(False)
        self.viewport().setAcceptDrops(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.setDropIndicatorShown(False)
        self.setDragDropOverwriteMode(False)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)

        # Custom insertion line used only as visual feedback for our manual
        # reorder operation.  It is not Qt's native drop indicator.
        self._drop_line = QFrame(self.viewport())
        self._drop_line.setFixedHeight(2)
        self._drop_line.setStyleSheet('background-color: rgba(104, 176, 220, 0.65); border: none;')
        self._drop_line.hide()

    def count(self) -> int:
        return self.rowCount()

    def currency_item(self, row: int):
        return self.item(row, 0)

    def code_at(self, row: int) -> str | None:
        item = self.currency_item(row)
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _row_for_code(self, code: str | None) -> int:
        if not code:
            return -1
        for row in range(self.rowCount()):
            if self.code_at(row) == code:
                return row
        return -1

    def move_row(self, source_row: int, target_row: int) -> bool:
        """Move a complete table row and emit orderChanged exactly once."""
        count = self.rowCount()
        if not (0 <= source_row < count):
            return False
        target_row = max(0, min(target_row, count))
        if source_row < target_row:
            target_row -= 1
        if target_row == source_row:
            return True

        self.blockSignals(True)
        try:
            cells = [self.takeItem(source_row, col) for col in range(self.columnCount())]
            self.removeRow(source_row)
            target_row = max(0, min(target_row, self.rowCount()))
            self.insertRow(target_row)
            for col, cell in enumerate(cells):
                if cell is not None:
                    self.setItem(target_row, col, cell)
            self.selectRow(target_row)
            self.setCurrentCell(target_row, 0)
        finally:
            self.blockSignals(False)
        self.orderChanged.emit()
        return True

    def _insert_row_for_y(self, y: int) -> int:
        """Return a between-rows insertion index for a viewport y coordinate."""
        count = self.rowCount()
        if count <= 0:
            return 0
        row = self.rowAt(y)
        if row < 0:
            first_top = self.rowViewportPosition(0)
            return 0 if y < first_top else count
        top = self.rowViewportPosition(row)
        height = max(1, self.rowHeight(row))
        return row if y < top + height / 2 else row + 1

    def _show_insert_line(self, insert_row: int):
        count = self.rowCount()
        if count <= 0:
            self._drop_line.hide()
            return
        if insert_row <= 0:
            y = self.rowViewportPosition(0)
        elif insert_row >= count:
            last = count - 1
            y = self.rowViewportPosition(last) + self.rowHeight(last)
        else:
            y = self.rowViewportPosition(insert_row)
        self._drop_line.setGeometry(0, max(0, int(y) - 1), self.viewport().width(), 2)
        self._drop_line.raise_()
        self._drop_line.show()

    def _auto_scroll(self, y: int):
        margin = 24
        bar = self.verticalScrollBar()
        if y < margin:
            bar.setValue(max(bar.minimum(), bar.value() - 1))
        elif y > self.viewport().height() - margin:
            bar.setValue(min(bar.maximum(), bar.value() + 1))

    def _reset_manual_drag(self):
        self._press_pos = None
        self._dragged_code = None
        self._manual_dragging = False
        self._insert_row = -1
        self._drop_line.hide()
        self.viewport().unsetCursor()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            row = self.rowAt(pos.y())
            self._press_pos = pos
            self._dragged_code = self.code_at(row) if row >= 0 else None
            self._manual_dragging = False
            self._insert_row = -1
        else:
            self._reset_manual_drag()

    def mouseMoveEvent(self, event):
        if (
            self._dragged_code
            and self._press_pos is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            pos = event.position().toPoint()
            distance = (pos - self._press_pos).manhattanLength()
            if not self._manual_dragging and distance >= QApplication.startDragDistance():
                self._manual_dragging = True
                self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            if self._manual_dragging:
                self._auto_scroll(pos.y())
                self._insert_row = self._insert_row_for_y(pos.y())
                self._show_insert_line(self._insert_row)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._manual_dragging and self._dragged_code and event.button() == Qt.MouseButton.LeftButton:
            source_row = self._row_for_code(self._dragged_code)
            insert_row = self._insert_row_for_y(event.position().toPoint().y())
            self._reset_manual_drag()
            if source_row >= 0:
                self.move_row(source_row, insert_row)
            event.accept()
            return
        self._reset_manual_drag()
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._drop_line.isVisible() and self._insert_row >= 0:
            self._show_insert_line(self._insert_row)


class CurrencyCard(QFrame):
    clicked = Signal(str)
    copy_requested = Signal(str)

    def __init__(self, code: str, language: str = "es", label_mode: str = "code", flag_position: str = "before", symbol_position: str = "after"):
        super().__init__()
        self.code = code
        self.language = language
        self.label_mode = label_mode
        self.flag_position = normalize_flag_position(flag_position)
        self.symbol_position = normalize_symbol_position(symbol_position)
        self.current_text = ""
        self.current_value: float | None = None
        self.setObjectName("currencyCard")
        self.setProperty("baseSelected", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(92)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        box = QVBoxLayout(self)
        box.setContentsMargins(16, 12, 14, 12)
        box.setSpacing(7)

        top = QHBoxLayout()
        title_wrap = QHBoxLayout()
        title_wrap.setSpacing(8)
        self.title_wrap = title_wrap
        self.title = QLabel()
        self.title.setObjectName("cardTitle")
        title_wrap.addWidget(self.title)
        self.base_badge = QLabel(ui_text(language, "base_badge"))
        self.base_badge.setObjectName("cardBaseBadge")
        self.base_badge.hide()
        title_wrap.addWidget(self.base_badge)
        title_wrap.addStretch(1)
        top.addLayout(title_wrap, 1)

        unit_box = QHBoxLayout()
        unit_box.setSpacing(8)
        self.unit_box = unit_box
        if code in {"AED", "SAR"}:
            symbol_widget = QLabel()
            symbol_widget.setObjectName("officialCurrencySymbol")
            asset = Path(__file__).resolve().with_name("aed-symbol.png" if code == "AED" else "sar-symbol.png")
            pix = QPixmap(str(asset))
            if not pix.isNull():
                symbol_widget.setPixmap(pix.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            symbol_widget.setToolTip("Official currency symbol")
        else:
            symbol_widget = QLabel(currency_symbol(code))
            symbol_widget.setObjectName("cardUnit")
            symbol_widget.setStyleSheet("font-size:20px; font-weight:700;")
        self.symbol_widget = symbol_widget
        unit_box.addWidget(self.symbol_widget)
        self.flag_label = QLabel(currency_flag(code))
        self.flag_label.setObjectName("cardFlag")
        self.flag_label.setStyleSheet("font-size:21px;")
        unit_box.addWidget(self.flag_label)
        top.addLayout(unit_box)
        box.addLayout(top)

        lower = QHBoxLayout()
        self.value = QLabel("")
        self.value.setObjectName("cardValue")
        lower.addWidget(self.value)
        lower.addStretch(1)

        self.copy_btn = QToolButton()
        self.copy_btn.setObjectName("copyButton")
        copy_icon = QIcon.fromTheme("edit-copy")
        if not copy_icon.isNull():
            self.copy_btn.setIcon(copy_icon)
            self.copy_btn.setIconSize(QSize(24, 24))
        else:
            self.copy_btn.setText("⧉")
        self.copy_btn.setMinimumSize(40, 40)
        self.copy_btn.setToolTip(ui_text(language, "copy_value"))
        self.copy_btn.setAutoRaise(True)
        self.copy_btn.clicked.connect(lambda: self.copy_requested.emit(self.code))
        lower.addWidget(self.copy_btn)

        self.status = QLabel("")
        self.status.setObjectName("statusNeutral")
        self.status.setMinimumWidth(62)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lower.addWidget(self.status)
        box.addLayout(lower)
        self._arrange_header_tokens()
        self.refresh_language(language, label_mode)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.code)
        super().mousePressEvent(event)

    def set_value(self, value: float, rounding_mode: str = "2", decimal_separator_mode: str = "currency", keep_zero_fraction: bool = False):
        self.current_value = value
        self.current_text = fmt_currency_amount(
            value, self.code, rounding_mode=rounding_mode,
            decimal_separator_mode=decimal_separator_mode, grouping=True,
            keep_zero_fraction=keep_zero_fraction,
        )
        self.value.setText(self.current_text)

    def set_status(self, text: str, level: str = "neutral", tooltip: str = ""):
        self.status.setText(text)
        self.status.setVisible(bool(text))
        object_name = {
            "good": "statusGood",
            "warn": "statusWarn",
            "bad": "statusBad",
        }.get(level, "statusNeutral")
        self.status.setObjectName(object_name)
        self.status.setToolTip(tooltip)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def set_selected(self, selected: bool):
        self.setProperty("baseSelected", selected)
        self.base_badge.setVisible(selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def _arrange_header_tokens(self):
        for widget in (self.title, self.flag_label, self.symbol_widget):
            self.title_wrap.removeWidget(widget)
            self.unit_box.removeWidget(widget)

        left_widgets = []
        if self.symbol_position == "before_all":
            left_widgets.append(self.symbol_widget)
        if self.flag_position == "before":
            left_widgets.append(self.flag_label)
        if self.symbol_position == "before_code":
            left_widgets.append(self.symbol_widget)
        left_widgets.append(self.title)
        if self.symbol_position == "after_code":
            left_widgets.append(self.symbol_widget)
        if self.flag_position == "after_code":
            left_widgets.append(self.flag_label)

        for index, widget in enumerate(left_widgets):
            self.title_wrap.insertWidget(index, widget)

        if self.symbol_position == "after":
            self.unit_box.addWidget(self.symbol_widget)
        if self.flag_position == "after":
            self.unit_box.addWidget(self.flag_label)

        self.title.show()
        self.flag_label.show()
        self.symbol_widget.show()

    def set_flag_position(self, position: str):
        self.flag_position = normalize_flag_position(position)
        self._arrange_header_tokens()

    def set_symbol_position(self, position: str):
        self.symbol_position = normalize_symbol_position(position)
        self._arrange_header_tokens()

    def refresh_language(self, language: str, label_mode: str):
        self.language = language
        self.label_mode = label_mode
        self.title.setText(currency_label(self.code, language, label_mode))
        self.base_badge.setText(ui_text(language, "base_badge"))
        self.copy_btn.setToolTip(ui_text(language, "copy_value"))
        self.setToolTip(ui_text(language, "card_click"))


class MainWindow(QMainWindow):
    def __init__(self, auto_refresh: bool = True):
        super().__init__()
        self.snapshot: RatesSnapshot | None = load_cache()
        self.cards: dict[str, CurrencyCard] = {}
        self.pool = QThreadPool.globalInstance()
        self.currency_order, self.visible_codes, self.group_order, self.currency_groups, self.group_colors, self.language, self.label_mode, self.language_manual, self.rounding_mode, self.decimal_separator_mode, self.flag_position, self.symbol_position, self.verification_display_mode, self.keep_zero_fraction, self.latam_enabled = load_preferences()
        self._building_currency_list = False
        self._building_group_list = False
        self._building_group_table = False
        self.group_assignment_sort = "region"
        self._undo_stack: list[dict[str, object]] = []
        self._undo_limit = 10
        self._history_suspended = False

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1240, 790)
        self.setMinimumSize(930, 620)
        self._sync_currency_preferences()
        self._build_ui()
        self._apply_style()
        self._populate_currency_combo()
        self._populate_organizer()
        self._populate_group_editor()
        self.amount.setFocus(Qt.FocusReason.OtherFocusReason)
        self._render()
        if auto_refresh:
            self.refresh_rates(initial=True)

    def _supported_codes(self) -> list[str]:
        return _unique_codes(list(BASE_SUPPORTED_CODES) + [code for code in LATAM_EXTRA_CODES if code in self.latam_enabled])

    def _all_codes(self) -> list[str]:
        supported = self._supported_codes()
        codes = [code for code in _unique_codes(self.currency_order) if code in supported]
        for code in supported:
            if code not in codes:
                codes.append(code)
        return _unique_codes(codes)

    def _save_preferences(self):
        save_preferences(self.currency_order, self.visible_codes, self.group_order, self.currency_groups, self.group_colors, self.language, self.label_mode, self.language_manual, self.rounding_mode, self.decimal_separator_mode, self.flag_position, self.symbol_position, self.verification_display_mode, self.keep_zero_fraction, self.latam_enabled)

    def _organization_snapshot(self) -> dict[str, object]:
        return {
            "currency_order": list(self.currency_order),
            "visible_codes": sorted(self.visible_codes),
            "group_order": list(self.group_order),
            "currency_groups": dict(self.currency_groups),
            "group_colors": dict(self.group_colors),
        }

    def _push_undo_state(self):
        if self._history_suspended:
            return
        state = self._organization_snapshot()
        if self._undo_stack and self._undo_stack[-1] == state:
            return
        self._undo_stack.append(state)
        if len(self._undo_stack) > self._undo_limit:
            self._undo_stack.pop(0)
        self._update_undo_buttons()

    def _update_undo_buttons(self):
        count = len(self._undo_stack)
        label = f"{ui_text(self.language, 'undo')} ({count})" if count else ui_text(self.language, "undo")
        for name in ("undo_currencies_btn", "undo_groups_btn"):
            btn = getattr(self, name, None)
            if btn is not None:
                btn.setText(label)
                btn.setEnabled(bool(count))
                btn.setToolTip(ui_text(self.language, "undo_tip"))

    def _undo_last_organization_change(self):
        if not self._undo_stack:
            self.statusBar().showMessage(ui_text(self.language, "undo_none"), 3000)
            return
        state = self._undo_stack.pop()
        self._history_suspended = True
        try:
            self.currency_order = _unique_codes(state.get("currency_order", []))
            self.visible_codes = set(_unique_codes(state.get("visible_codes", [])))
            self.group_order = _unique_names(state.get("group_order", []))
            self.currency_groups = {str(k).upper(): str(v) for k, v in dict(state.get("currency_groups", {})).items()}
            self.group_colors = ensure_group_colors(self.group_order, dict(state.get("group_colors", {})))
            self.currency_order, self.visible_codes = sanitize_currency_state(
                self.currency_order, self.visible_codes, self._supported_codes(), PRIMARY
            )
            self.group_order, self.currency_groups = ensure_group_defaults(
                self.group_order, self.currency_groups, self.currency_order
            )
            self._save_preferences()
            self._populate_organizer()
            self._populate_group_editor()
            self._populate_currency_combo()
            self._rebuild_cards()
            self._render_sources()
            self._render()
        finally:
            self._history_suspended = False
            self._update_undo_buttons()
        self.statusBar().showMessage(ui_text(self.language, "undo_done"), 3000)

    def _sync_currency_preferences(self):
        self.currency_order, self.visible_codes = sanitize_currency_state(
            self.currency_order, self.visible_codes, self._supported_codes(), PRIMARY
        )
        self.group_order, self.currency_groups = ensure_group_defaults(
            self.group_order, self.currency_groups, self.currency_order
        )
        self.group_colors = ensure_group_colors(self.group_order, self.group_colors)
        self._save_preferences()

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("rootWidget")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(12)

        hero = QFrame()
        hero.setObjectName("heroFrame")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(16, 12, 16, 14)
        hero_layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(14)
        self.icon_label = QLabel()
        self.icon_label.setObjectName("heroIcon")
        icon_path = Path(__file__).resolve().with_name("icon.svg")
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            self.icon_label.setPixmap(icon.pixmap(62, 62))
        header.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignTop)

        titlebox = QVBoxLayout()
        self.title_label = QLabel()
        self.title_label.setObjectName("pageTitle")
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("subtitle")
        titlebox.addWidget(self.title_label)
        titlebox.addWidget(self.subtitle_label)
        header.addLayout(titlebox)
        header.addStretch(1)

        self.update_label = QLabel()
        self.update_label.setObjectName("updateLabel")
        self.update_label.setTextFormat(Qt.TextFormat.RichText)
        self.update_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.update_label.setToolTip(ui_text(self.language, "update_tooltip"))
        header.addWidget(self.update_label)

        self.refresh_btn = QPushButton()
        self.refresh_btn.clicked.connect(self.refresh_rates)
        header.addWidget(self.refresh_btn)
        hero_layout.addLayout(header)

        controls = QFrame()
        controls.setObjectName("controls")
        row = QHBoxLayout(controls)
        row.setContentsMargins(14, 10, 14, 10)
        self.amount_label = QLabel()
        row.addWidget(self.amount_label)

        self.amount = QLineEdit()
        self.amount.setObjectName("amountInput")
        self.amount.setMinimumWidth(190)
        self.amount.textChanged.connect(self._render)
        row.addWidget(self.amount)

        self.clear_amount_btn = QToolButton()
        self.clear_amount_btn.setObjectName("clearAmountButton")
        self.clear_amount_btn.setText("×")
        self.clear_amount_btn.setMinimumSize(38, 38)
        self.clear_amount_btn.clicked.connect(self._clear_amount)
        row.addWidget(self.clear_amount_btn)

        self.base_label = QLabel()
        row.addWidget(self.base_label)
        self.base = QComboBox()
        self.base.setMinimumWidth(260)
        self.base.currentIndexChanged.connect(self._render)
        row.addWidget(self.base)
        row.addStretch(1)

        row.addStretch(1)
        self.nav_tabs = QTabBar()
        self.nav_tabs.setDocumentMode(True)
        self.nav_tabs.setDrawBase(False)
        self.nav_tabs.setExpanding(False)
        self.nav_tabs.setUsesScrollButtons(True)
        row.addWidget(self.nav_tabs)
        hero_layout.addWidget(controls)
        outer.addWidget(hero)

        self.tabs = QTabWidget()
        self.tabs.tabBar().hide()
        outer.addWidget(self.tabs, 1)

        converter_tab = QWidget()
        converter_layout = QVBoxLayout(converter_tab)
        converter_layout.setContentsMargins(0, 8, 0, 0)
        self.source_warning = QLabel()
        self.source_warning.setObjectName("sourceWarning")
        self.source_warning.setWordWrap(True)
        self.source_warning.hide()
        converter_layout.addWidget(self.source_warning)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.cards_host = QWidget()
        self.cards_grid = QGridLayout(self.cards_host)
        self.cards_grid.setContentsMargins(2, 2, 2, 2)
        self.cards_grid.setHorizontalSpacing(12)
        self.cards_grid.setVerticalSpacing(8)
        scroll.setWidget(self.cards_host)
        converter_layout.addWidget(scroll)
        self.tabs.addTab(converter_tab, "")

        verify_tab = QWidget()
        verify_layout = QVBoxLayout(verify_tab)
        verify_layout.setContentsMargins(0, 8, 0, 0)
        self.verify_intro = QLabel()
        self.verify_intro.setWordWrap(True)
        self.verify_intro.setObjectName("subtitle")
        verify_layout.addWidget(self.verify_intro)
        self.verify_table = QTableWidget(0, 7)
        self.verify_table.setHorizontalHeaderLabels(["Moneda", "Principal (por EUR)", "CBR cruzado", "Diferencia", "Estado", "Fechas", "Peg USD"])
        self.verify_table.verticalHeader().setVisible(False)
        self.verify_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verify_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.verify_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        verify_layout.addWidget(self.verify_table, 1)
        self.tabs.addTab(verify_tab, "")

        self.sources_tab = QWidget()
        sources_layout = QVBoxLayout(self.sources_tab)
        sources_layout.setContentsMargins(0, 8, 0, 0)
        self.source_summary = QLabel()
        self.source_summary.setObjectName("sourceSummary")
        self.source_summary.setTextFormat(Qt.TextFormat.RichText)
        self.source_summary.setWordWrap(True)
        sources_layout.addWidget(self.source_summary)
        self.reference_disclaimer = QLabel()
        self.reference_disclaimer.setObjectName("subtitle")
        self.reference_disclaimer.setWordWrap(True)
        sources_layout.addWidget(self.reference_disclaimer)
        self.sources_table = QTableWidget(0, 5)
        self.sources_table.setHorizontalHeaderLabels(["Moneda", "Fuente principal", "Cálculo", "Comprobación", "Enlaces oficiales"])
        self.sources_table.verticalHeader().setVisible(False)
        self.sources_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sources_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        sources_layout.addWidget(self.sources_table, 1)
        self.tabs.addTab(self.sources_tab, "")

        self.organize_tab = QWidget()
        organize_layout = QVBoxLayout(self.organize_tab)
        organize_layout.setContentsMargins(0, 8, 0, 0)
        self.organizer_help = QLabel()
        self.organizer_help.setWordWrap(True)
        self.organizer_help.setObjectName("subtitle")
        organize_layout.addWidget(self.organizer_help)
        self.currency_list = OrganizerTable()
        self.currency_list.setHorizontalHeaderLabels([ui_text(self.language, "currency_column"), ui_text(self.language, "region_column"), ""])
        self.currency_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.currency_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.currency_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.currency_list.itemChanged.connect(self._on_currency_item_changed)
        self.currency_list.orderChanged.connect(self._on_currency_rows_moved)
        organize_layout.addWidget(self.currency_list, 1)
        organizer_buttons = QHBoxLayout()
        self.show_all_btn = QPushButton()
        self.show_all_btn.clicked.connect(self._show_all_currencies)
        organizer_buttons.addWidget(self.show_all_btn)
        self.primary_only_btn = QPushButton()
        self.primary_only_btn.clicked.connect(self._primary_currencies_only)
        organizer_buttons.addWidget(self.primary_only_btn)
        self.reset_order_btn = QPushButton()
        self.reset_order_btn.clicked.connect(self._reset_currency_order)
        organizer_buttons.addWidget(self.reset_order_btn)
        self.undo_currencies_btn = QPushButton()
        self.undo_currencies_btn.clicked.connect(self._undo_last_organization_change)
        organizer_buttons.addWidget(self.undo_currencies_btn)
        organizer_buttons.addStretch(1)
        organize_layout.addLayout(organizer_buttons)
        self.tabs.addTab(self.organize_tab, "")

        self.groups_tab = QWidget()
        groups_layout = QVBoxLayout(self.groups_tab)
        groups_layout.setContentsMargins(0, 8, 0, 0)
        self.groups_help = QLabel()
        self.groups_help.setWordWrap(True)
        self.groups_help.setObjectName("subtitle")
        groups_layout.addWidget(self.groups_help)
        split = QHBoxLayout()
        left_box = QVBoxLayout()
        add_row = QHBoxLayout()
        self.group_name_edit = QLineEdit()
        add_row.addWidget(self.group_name_edit, 1)
        self.add_group_btn = QPushButton()
        self.add_group_btn.clicked.connect(self._add_group)
        add_row.addWidget(self.add_group_btn)
        left_box.addLayout(add_row)
        self.group_list = QListWidget()
        self.group_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.group_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.group_list.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        self.group_list.itemChanged.connect(self._on_group_item_changed)
        self.group_list.currentItemChanged.connect(self._update_group_color_button)
        self.group_list.model().rowsMoved.connect(self._on_group_rows_moved)
        left_box.addWidget(self.group_list, 1)
        left_buttons = QHBoxLayout()
        self.remove_group_btn = QPushButton()
        self.remove_group_btn.clicked.connect(self._remove_selected_group)
        left_buttons.addWidget(self.remove_group_btn)
        self.reset_groups_btn = QPushButton()
        self.reset_groups_btn.clicked.connect(self._reset_groups)
        left_buttons.addWidget(self.reset_groups_btn)
        self.group_color_btn = QPushButton()
        self.group_color_btn.clicked.connect(self._choose_selected_group_color)
        left_buttons.addWidget(self.group_color_btn)
        self.undo_groups_btn = QPushButton()
        self.undo_groups_btn.clicked.connect(self._undo_last_organization_change)
        left_buttons.addWidget(self.undo_groups_btn)
        left_box.addLayout(left_buttons)
        split.addLayout(left_box, 1)
        right_box = QVBoxLayout()
        sort_row = QHBoxLayout()
        self.group_sort_label = QLabel()
        sort_row.addWidget(self.group_sort_label)
        self.group_sort_combo = QComboBox()
        self.group_sort_combo.addItem("Código A–Z", "code")
        self.group_sort_combo.addItem("Región", "region")
        self.group_sort_combo.currentIndexChanged.connect(self._on_group_sort_changed)
        sort_row.addWidget(self.group_sort_combo)
        sort_row.addStretch(1)
        right_box.addLayout(sort_row)
        self.assignment_help = QLabel()
        self.assignment_help.setWordWrap(True)
        self.assignment_help.setObjectName("subtitle")
        right_box.addWidget(self.assignment_help)
        bulk_row = QHBoxLayout()
        self.bulk_group_label = QLabel()
        bulk_row.addWidget(self.bulk_group_label)
        self.bulk_group_combo = QComboBox()
        self.bulk_group_combo.setMinimumWidth(190)
        bulk_row.addWidget(self.bulk_group_combo)
        self.bulk_group_apply_btn = QPushButton()
        self.bulk_group_apply_btn.clicked.connect(self._apply_group_to_selected)
        bulk_row.addWidget(self.bulk_group_apply_btn)
        bulk_row.addStretch(1)
        right_box.addLayout(bulk_row)
        self.group_assign_table = QTableWidget(0, 4)
        self.group_assign_table.setHorizontalHeaderLabels(["Moneda", "Región", "Visible", "Grupo"])
        self.group_assign_table.verticalHeader().setVisible(False)
        self.group_assign_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.group_assign_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.group_assign_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.group_assign_table.itemSelectionChanged.connect(self._update_bulk_group_controls)
        self.group_assign_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.group_assign_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.group_assign_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.group_assign_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        right_box.addWidget(self.group_assign_table, 1)
        split.addLayout(right_box, 2)
        groups_layout.addLayout(split, 1)
        self.tabs.addTab(self.groups_tab, "")

        self.options_tab = QWidget()
        options_layout = QVBoxLayout(self.options_tab)
        options_layout.setContentsMargins(0, 8, 0, 0)
        self.options_help = QLabel()
        self.options_help.setWordWrap(True)
        self.options_help.setObjectName("subtitle")
        options_layout.addWidget(self.options_help)
        opt_lang = QHBoxLayout()
        self.language_label = QLabel()
        opt_lang.addWidget(self.language_label)
        self.language_combo = QComboBox()
        self.language_combo.addItem("Español", "es")
        self.language_combo.addItem("English", "en")
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        opt_lang.addWidget(self.language_combo)
        opt_lang.addStretch(1)
        options_layout.addLayout(opt_lang)
        opt_labels = QHBoxLayout()
        self.label_mode_label = QLabel()
        opt_labels.addWidget(self.label_mode_label)
        self.label_mode_combo = QComboBox()
        self.label_mode_combo.addItem("Código (JPY)", "code")
        self.label_mode_combo.addItem("Nombre (Yen japonés)", "name")
        self.label_mode_combo.addItem("Código + nombre", "both")
        self.label_mode_combo.currentIndexChanged.connect(self._on_label_mode_changed)
        opt_labels.addWidget(self.label_mode_combo)
        opt_labels.addStretch(1)
        options_layout.addLayout(opt_labels)

        opt_flag = QHBoxLayout()
        self.flag_position_label = QLabel()
        opt_flag.addWidget(self.flag_position_label)
        self.flag_position_combo = QComboBox()
        self.flag_position_combo.addItem("Antes del código / nombre", "before")
        self.flag_position_combo.addItem("Después del código (EUR 🇪🇺)", "after_code")
        self.flag_position_combo.addItem("Después del símbolo", "after")
        self.flag_position_combo.currentIndexChanged.connect(self._on_flag_position_changed)
        opt_flag.addWidget(self.flag_position_combo)
        opt_flag.addStretch(1)
        options_layout.addLayout(opt_flag)
        self.flag_position_hint = QLabel()
        self.flag_position_hint.setObjectName("subtitle")
        self.flag_position_hint.setWordWrap(True)
        options_layout.addWidget(self.flag_position_hint)

        opt_symbol = QHBoxLayout()
        self.symbol_position_label = QLabel()
        opt_symbol.addWidget(self.symbol_position_label)
        self.symbol_position_combo = QComboBox()
        self.symbol_position_combo.addItem("Antes de bandera/código (€ 🇪🇺 EUR)", "before_all")
        self.symbol_position_combo.addItem("Antes del código (🇪🇺 € EUR)", "before_code")
        self.symbol_position_combo.addItem("Después del código (🇪🇺 EUR €)", "after_code")
        self.symbol_position_combo.addItem("Al final", "after")
        self.symbol_position_combo.currentIndexChanged.connect(self._on_symbol_position_changed)
        opt_symbol.addWidget(self.symbol_position_combo)
        opt_symbol.addStretch(1)
        options_layout.addLayout(opt_symbol)
        self.symbol_position_hint = QLabel()
        self.symbol_position_hint.setObjectName("subtitle")
        self.symbol_position_hint.setWordWrap(True)
        options_layout.addWidget(self.symbol_position_hint)

        opt_round = QHBoxLayout()
        self.rounding_label = QLabel()
        opt_round.addWidget(self.rounding_label)
        self.rounding_combo = QComboBox()
        self.rounding_combo.addItem("Automático", "auto")
        self.rounding_combo.addItem("Sin decimales", "0")
        self.rounding_combo.addItem("1 decimal", "1")
        self.rounding_combo.addItem("2 decimales", "2")
        self.rounding_combo.currentIndexChanged.connect(self._on_rounding_changed)
        opt_round.addWidget(self.rounding_combo)
        opt_round.addStretch(1)
        options_layout.addLayout(opt_round)
        self.rounding_hint = QLabel()
        self.rounding_hint.setObjectName("subtitle")
        self.rounding_hint.setWordWrap(True)
        options_layout.addWidget(self.rounding_hint)

        opt_zero_fraction = QHBoxLayout()
        self.zero_fraction_label = QLabel()
        opt_zero_fraction.addWidget(self.zero_fraction_label)
        self.zero_fraction_combo = QComboBox()
        self.zero_fraction_combo.addItem("Ocultar ,00 / .00", False)
        self.zero_fraction_combo.addItem("Mostrar y copiar ,00 / .00", True)
        self.zero_fraction_combo.currentIndexChanged.connect(self._on_zero_fraction_changed)
        opt_zero_fraction.addWidget(self.zero_fraction_combo)
        opt_zero_fraction.addStretch(1)
        options_layout.addLayout(opt_zero_fraction)
        self.zero_fraction_hint = QLabel()
        self.zero_fraction_hint.setObjectName("subtitle")
        self.zero_fraction_hint.setWordWrap(True)
        options_layout.addWidget(self.zero_fraction_hint)

        opt_decimal = QHBoxLayout()
        self.decimal_separator_label = QLabel()
        opt_decimal.addWidget(self.decimal_separator_label)
        self.decimal_separator_combo = QComboBox()
        self.decimal_separator_combo.addItem("Según divisa/país", "currency")
        self.decimal_separator_combo.addItem("Coma (1.234,56)", "comma")
        self.decimal_separator_combo.addItem("Punto (1,234.56)", "dot")
        self.decimal_separator_combo.currentIndexChanged.connect(self._on_decimal_separator_changed)
        opt_decimal.addWidget(self.decimal_separator_combo)
        opt_decimal.addStretch(1)
        options_layout.addLayout(opt_decimal)
        self.decimal_separator_hint = QLabel()
        self.decimal_separator_hint.setObjectName("subtitle")
        self.decimal_separator_hint.setWordWrap(True)
        options_layout.addWidget(self.decimal_separator_hint)

        opt_verification = QHBoxLayout()
        self.verification_display_label = QLabel()
        opt_verification.addWidget(self.verification_display_label)
        self.verification_display_combo = QComboBox()
        self.verification_display_combo.addItem("Mostrar siempre", "always")
        self.verification_display_combo.addItem("Solo avisos o problemas", "issues")
        self.verification_display_combo.currentIndexChanged.connect(self._on_verification_display_changed)
        opt_verification.addWidget(self.verification_display_combo)
        opt_verification.addStretch(1)
        options_layout.addLayout(opt_verification)
        self.verification_display_hint = QLabel()
        self.verification_display_hint.setObjectName("subtitle")
        self.verification_display_hint.setWordWrap(True)
        options_layout.addWidget(self.verification_display_hint)

        self.latam_optional_title = QLabel()
        self.latam_optional_title.setStyleSheet("font-weight: 800; margin-top: 8px;")
        options_layout.addWidget(self.latam_optional_title)
        self.latam_optional_hint = QLabel()
        self.latam_optional_hint.setObjectName("subtitle")
        self.latam_optional_hint.setWordWrap(True)
        options_layout.addWidget(self.latam_optional_hint)
        self.latam_checkboxes: dict[str, QCheckBox] = {}
        latam_row1 = QHBoxLayout()
        latam_row2 = QHBoxLayout()
        for index, code in enumerate(LATAM_EXTRA_CODES):
            checkbox = QCheckBox()
            checkbox.setChecked(code in self.latam_enabled)
            checkbox.toggled.connect(lambda checked, c=code: self._on_latam_currency_toggled(c, checked))
            self.latam_checkboxes[code] = checkbox
            (latam_row1 if index < 3 else latam_row2).addWidget(checkbox)
        latam_row1.addStretch(1)
        latam_row2.addStretch(1)
        options_layout.addLayout(latam_row1)
        options_layout.addLayout(latam_row2)
        self.latam_bcb_note = QLabel()
        self.latam_bcb_note.setObjectName("subtitle")
        self.latam_bcb_note.setWordWrap(True)
        options_layout.addWidget(self.latam_bcb_note)

        options_layout.addStretch(1)
        self.tabs.addTab(self.options_tab, "")

        self.nav_tabs.currentChanged.connect(self.tabs.setCurrentIndex)
        self.tabs.currentChanged.connect(self.nav_tabs.setCurrentIndex)

        self.statusBar().showMessage(ui_text(self.language, "status_ready"))
        self._apply_language()
        self._rebuild_cards()
    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { font-size: 14px; }
            QLabel { color: palette(window-text); }
            QPushButton, QToolButton { color: palette(button-text); }
            QComboBox, QTableWidget, QListWidget, QTreeWidget, QLineEdit { color: palette(text); }
            QHeaderView::section { color: palette(button-text); }
            QTabBar::tab { color: palette(window-text); }
            QStatusBar { color: palette(window-text); }
            QToolTip { color: palette(tooltip-text); background-color: palette(tooltip-base); }

            QWidget#rootWidget { background-color: #061327; }
            QLabel#pageTitle { font-size: 28px; font-weight: 850; color: #f3f7ff; }
            QLabel#subtitle { color: #b8c5dd; }
            QLabel#updateLabel { color: #eef4ff; font-weight: 700; min-width: 360px; }
            QLabel#sourceSummary { color: palette(window-text); padding: 10px; border: 1px solid palette(mid); border-radius: 8px; }
            QLabel#sourceWarning { color: #fff1d0; background-color: rgba(75, 47, 8, 0.78); border: 1px solid #d3a13c; border-radius: 9px; padding: 8px 11px; font-weight: 700; }

            QFrame#heroFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #031228, stop:0.48 #0d2a60, stop:1 #08152d);
                border: 1px solid #2a70e0; border-radius: 18px;
            }
            QLabel#heroIcon { background: transparent; min-width: 70px; }
            QFrame#controls { background-color: rgba(1, 8, 22, 0.62); border: 1px solid #1f4d8f; border-radius: 14px; }

            QFrame#currencyCard { background-color: rgba(1, 9, 22, 0.96); border: 1px solid #163866; border-radius: 12px; }
            QFrame#currencyCard:hover { border-color: #3e87d0; }
            QFrame#currencyCard[baseSelected="true"] { background-color: rgba(5, 18, 38, 0.98); border: 2px solid #65a9b7; }
            QLabel#cardTitle { font-size: 18px; font-weight: 800; color: #f2f6ff; }
            QLabel#cardUnit { color: #dbe6f7; }
            QLabel#cardValue { font-size: 21px; font-weight: 700; color: #ffffff; }
            QLabel#cardBaseBadge { color: #071519; background-color: #6fb2bd; border: 1px solid #83c0c9; font-size: 11px; font-weight: 900; padding: 2px 7px; border-radius: 9px; }
            QToolButton#copyButton { padding: 2px 6px; font-size: 24px; font-weight: 900; }
            QToolButton#clearAmountButton { padding: 2px 6px; font-size: 23px; font-weight: 800; }

            QLabel#statusGood { color: #dce7df; font-size: 12px; font-weight: 800; padding: 4px 7px; border: 1px solid #486354; background-color: rgba(21, 34, 28, 0.50); border-radius: 9px; }
            QLabel#statusWarn { color: #f4ead0; font-size: 12px; font-weight: 800; padding: 4px 7px; border: 1px solid #8d7735; background-color: rgba(35, 29, 12, 0.50); border-radius: 9px; }
            QLabel#statusBad { color: #f4dede; font-size: 12px; font-weight: 800; padding: 4px 7px; border: 1px solid #9a4a4a; background-color: rgba(42, 18, 18, 0.55); border-radius: 9px; }
            QLabel#statusNeutral { font-size: 11px; color: palette(placeholder-text); }

            QFrame#groupHeader { background: transparent; border: 0; }
            QLabel#groupPill { padding: 3px 10px; border-radius: 9px; font-size: 13px; font-weight: 800; }
            QFrame#lineFrame { background-color: transparent; }
            QFrame#lineFrame QFrame { background-color: rgba(111, 125, 145, 0.12); max-height: 1px; }

            QScrollArea, QTabWidget::pane { border: 0; background: transparent; }
            QTableWidget, QListWidget, QTreeWidget, QComboBox, QLineEdit { background-color: rgba(3, 10, 22, 0.92); border: 1px solid #324d78; border-radius: 8px; }
            QHeaderView::section { background-color: rgba(34, 42, 58, 0.92); border: 0; padding: 8px; }
            QListWidget::item:selected { color: #ffffff; border: 1px solid #73bfff; border-radius: 6px; }
            QPushButton { padding: 9px 13px; background-color: rgba(29, 35, 47, 0.92); border: 1px solid #5a6f95; border-radius: 10px; }
            QPushButton:hover { border-color: #7cc8ff; }
            QToolButton { background-color: rgba(29, 35, 47, 0.92); border: 1px solid #5a6f95; border-radius: 8px; }
            QComboBox, QLineEdit { padding: 8px; }
            QTabBar::tab { background-color: rgba(20, 26, 40, 0.88); border: 1px solid #2c4c80; border-bottom: none; padding: 7px 12px; border-top-left-radius: 8px; border-top-right-radius: 8px; }
            QTabBar::tab:selected { background-color: rgba(8, 18, 36, 0.96); border-color: #5cb7ff; }
            QTabBar::tab:!selected { margin-top: 3px; }
        """)
    def _display_currency_item(self, code: str) -> str:
        flag = currency_flag(code)
        base = currency_label(code, self.language, self.label_mode)
        if self.label_mode == "code":
            suffix = f"   {currency_symbol(code)}"
        elif self.label_mode == "name":
            suffix = f"   {currency_symbol(code)}"
        else:
            suffix = f"   {currency_symbol(code)}"
        return f"{flag}  {base}{suffix}"

    def _management_currency_item(self, code: str) -> str:
        """Stable management label: always ISO code + localized name."""
        return f"{currency_flag(code)}  {code} · {currency_name(code, self.language)}   {currency_symbol(code)}"

    def _populate_currency_combo(self):
        current = self.base.currentData() if hasattr(self, "base") else "EUR"
        self.base.blockSignals(True)
        self.base.clear()
        for code in self._all_codes():
            if self.snapshot and code not in self.snapshot.rates_per_eur:
                continue
            self.base.addItem(self._display_currency_item(code), code)
        idx = self.base.findData(current or "EUR")
        if idx < 0:
            idx = self.base.findData("EUR")
        self.base.setCurrentIndex(max(0, idx))
        self.base.blockSignals(False)

    def _populate_organizer(self):
        self._building_currency_list = True
        self.currency_list.blockSignals(True)
        try:
            self.currency_list.clearContents()
            codes = _unique_codes(self._all_codes())
            self.currency_list.setRowCount(len(codes))
            self.currency_list.setHorizontalHeaderLabels([ui_text(self.language, "currency_column"), ui_text(self.language, "region_column"), ""])
            for row, code in enumerate(codes):
                region = currency_region_name(code, self.language)
                missing_source = self.snapshot.source_missing.get(code) if self.snapshot else None
                missing_suffix = f"  ⚠ {ui_text(self.language, 'source_missing_short')} ({missing_source})" if missing_source else ""

                currency_item = QTableWidgetItem(self._management_currency_item(code) + missing_suffix)
                currency_item.setData(Qt.ItemDataRole.UserRole, code)
                currency_item.setFlags(
                    currency_item.flags()
                    | Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsDragEnabled
                )
                currency_item.setCheckState(Qt.CheckState.Checked if code in self.visible_codes else Qt.CheckState.Unchecked)

                region_item = QTableWidgetItem(region)
                region_item.setData(Qt.ItemDataRole.UserRole, region)
                region_item.setForeground(QColor(currency_region_color(code)))
                region_item.setToolTip(region)

                spacer_item = QTableWidgetItem("")
                spacer_item.setForeground(QColor("#0b162a"))

                if missing_source:
                    tip = self._source_missing_message(code)
                    currency_item.setToolTip(tip)
                    region_item.setToolTip(tip)

                self.currency_list.setItem(row, 0, currency_item)
                self.currency_list.setItem(row, 1, region_item)
                self.currency_list.setItem(row, 2, spacer_item)
        finally:
            self.currency_list.blockSignals(False)
            self._building_currency_list = False

    def _populate_group_editor(self):
        self._populate_group_list()
        self._populate_group_assignments()

    def _populate_group_list(self):
        self._building_group_list = True
        current_name = None
        current_item = self.group_list.currentItem() if hasattr(self, "group_list") else None
        if current_item is not None:
            current_name = normalize_group_name(current_item.data(Qt.ItemDataRole.UserRole) or current_item.text())
        self.group_list.clear()
        self.group_colors = ensure_group_colors(self.group_order, self.group_colors)
        selected_row = -1
        for row, name in enumerate(self.group_order):
            item = QListWidgetItem(localized_group_name(name, self.language))
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            pix = QPixmap(14, 14)
            pix.fill(QColor(self.group_colors.get(name, default_group_color(name))))
            item.setIcon(QIcon(pix))
            item.setToolTip(self.group_colors.get(name, default_group_color(name)))
            self.group_list.addItem(item)
            if current_name == name:
                selected_row = row
        if selected_row >= 0:
            self.group_list.setCurrentRow(selected_row)
        elif self.group_list.count():
            self.group_list.setCurrentRow(0)
        self._building_group_list = False
        self._update_group_color_button()

    def _populate_group_assignments(self):
        self._building_group_table = True
        codes = region_sorted_codes(self.currency_order) if self.group_assignment_sort == "region" else alphabetical_codes(self.currency_order)
        self.group_assign_table.setRowCount(len(codes))
        for row, code in enumerate(codes):
            row_color = QColor(currency_region_color(code))
            label = QTableWidgetItem(self._management_currency_item(code))
            label.setData(Qt.ItemDataRole.UserRole, code)
            region = QTableWidgetItem(currency_region_name(code, self.language))
            visible = QTableWidgetItem("Yes" if self.language == "en" and code in self.visible_codes else "No" if self.language == "en" else "Sí" if code in self.visible_codes else "No")
            for cell in (label, region, visible):
                cell.setBackground(row_color)
                cell.setForeground(QColor("#f3f7ff"))
            missing_source = self.snapshot.source_missing.get(code) if self.snapshot else None
            if missing_source:
                label.setToolTip(self._source_missing_message(code))
                region.setToolTip(self._source_missing_message(code))
                visible.setToolTip(self._source_missing_message(code))
            self.group_assign_table.setItem(row, 0, label)
            self.group_assign_table.setItem(row, 1, region)
            self.group_assign_table.setItem(row, 2, visible)
            combo = QComboBox()
            for group in self.group_order:
                combo.addItem(localized_group_name(group, self.language), group)
            combo.setStyleSheet(f"QComboBox {{ background-color: {currency_region_color(code)}; }}")
            current_group = self.currency_groups.get(code, default_group_for(code))
            idx = combo.findData(current_group)
            combo.setCurrentIndex(max(0, idx))
            combo.currentIndexChanged.connect(lambda _=0, c=code, cb=combo: self._on_currency_group_changed(c, cb.currentData()))
            self.group_assign_table.setCellWidget(row, 3, combo)
        self._refresh_bulk_group_combo()
        self._building_group_table = False
        self._update_bulk_group_controls()

    def _rebuild_cards(self):
        self.cards.clear()
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        row = 0
        columns = 3
        for group_name in self.group_order:
            codes = [c for c in self.currency_order if c in self.visible_codes and self.currency_groups.get(c, default_group_for(c)) == group_name]
            if not codes:
                continue
            header = self._make_group_header(group_name, len(codes))
            self.cards_grid.addWidget(header, row, 0, 1, columns)
            row += 1
            col = 0
            for code in codes:
                card = CurrencyCard(code, self.language, self.label_mode, self.flag_position, self.symbol_position)
                card.clicked.connect(self._set_base_from_card)
                card.copy_requested.connect(self._copy_card_value)
                self.cards[code] = card
                self.cards_grid.addWidget(card, row, col)
                col += 1
                if col >= columns:
                    col = 0
                    row += 1
            if col != 0:
                row += 1
        self.cards_grid.setRowStretch(row + 1, 1)

    def _make_group_header(self, group_name: str, count: int) -> QWidget:
        frame = QFrame()
        frame.setObjectName("groupHeader")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        pill = QLabel()
        pill.setObjectName("groupPill")

        chosen = QColor(self.group_colors.get(group_name, default_group_color(group_name)))
        if not chosen.isValid():
            chosen = QColor(default_group_color(group_name))
        # User-selected colours are deliberately muted in the converter so
        # group decoration never competes with the numeric result itself.
        border = chosen.darker(145)
        bg = QColor(chosen)
        bg = bg.darker(330)
        line_color = f"rgba({chosen.red()}, {chosen.green()}, {chosen.blue()}, 0.26)"

        name = localized_group_name(group_name, self.language)
        currency_word = ui_text(self.language, "group_currency") if count == 1 else ui_text(self.language, "group_currencies")
        pill.setText(f"{name}  ·  {count} {currency_word}")
        pill.setStyleSheet(f"background-color:{bg.name()}; border:1px solid {border.name()}; color:#dce4ef;")
        layout.addSpacing(8)
        layout.addWidget(pill, 0, Qt.AlignmentFlag.AlignBottom)
        line_wrap = QFrame()
        line_wrap.setObjectName("lineFrame")
        line_layout = QHBoxLayout(line_wrap)
        line_layout.setContentsMargins(0, 0, 0, 0)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color:{line_color}; min-height:1px; max-height:1px; border:none;")
        line_layout.addWidget(line, 1, Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(line_wrap, 1, Qt.AlignmentFlag.AlignBottom)
        return frame

    def _apply_language(self):
        self.title_label.setText(ui_text(self.language, "page_title"))
        self.subtitle_label.setText(ui_text(self.language, "subtitle"))
        self.update_label.setToolTip(ui_text(self.language, "update_tooltip"))
        self.refresh_btn.setText(ui_text(self.language, "refresh"))
        self.amount_label.setText(ui_text(self.language, "amount"))
        self.amount.setPlaceholderText(ui_text(self.language, "amount_placeholder"))
        self.clear_amount_btn.setToolTip(ui_text(self.language, "clear_amount"))
        self.base_label.setText(ui_text(self.language, "base_currency"))
        tab_keys = ["tab_converter", "tab_verification", "tab_sources", "tab_currencies", "tab_groups", "tab_options"]
        while self.nav_tabs.count() < len(tab_keys):
            self.nav_tabs.addTab("")
        for index, key in enumerate(tab_keys):
            label = ui_text(self.language, key)
            self.tabs.setTabText(index, label)
            self.nav_tabs.setTabText(index, label)
        self.verify_intro.setText(ui_text(self.language, "verify_intro"))
        self.reference_disclaimer.setText(ui_text(self.language, "reference_disclaimer"))
        self.organizer_help.setText(ui_text(self.language, "currencies_help"))
        if hasattr(self, "currency_list"):
            self.currency_list.setHorizontalHeaderLabels([ui_text(self.language, "currency_column"), ui_text(self.language, "region_column"), ""])
        self.groups_help.setText(ui_text(self.language, "groups_help"))
        self.assignment_help.setText(ui_text(self.language, "group_assignment_help"))
        self.group_sort_label.setText(ui_text(self.language, "sort_by"))
        self.group_sort_combo.blockSignals(True)
        self.group_sort_combo.setItemText(0, ui_text(self.language, "sort_code"))
        self.group_sort_combo.setItemText(1, ui_text(self.language, "sort_region"))
        self.group_sort_combo.setCurrentIndex(max(0, self.group_sort_combo.findData(self.group_assignment_sort)))
        self.group_sort_combo.blockSignals(False)
        self.bulk_group_label.setText(ui_text(self.language, "bulk_group_label"))
        self._refresh_bulk_group_combo()
        self._update_bulk_group_controls()
        self.add_group_btn.setText(ui_text(self.language, "add_group"))
        self.group_name_edit.setPlaceholderText(ui_text(self.language, "new_group"))
        self.remove_group_btn.setText(ui_text(self.language, "remove_group"))
        self.reset_groups_btn.setText(ui_text(self.language, "reset_groups"))
        self.group_color_btn.setText(ui_text(self.language, "group_color"))
        self.group_color_btn.setToolTip(ui_text(self.language, "group_color_tip"))
        self._update_group_color_button()
        self.show_all_btn.setText(ui_text(self.language, "show_all"))
        self.primary_only_btn.setText(ui_text(self.language, "primary_only"))
        self.reset_order_btn.setText(ui_text(self.language, "reset_order"))
        self._update_undo_buttons()
        self.options_help.setText(ui_text(self.language, "options_help"))
        self.language_label.setText(ui_text(self.language, "language"))
        self.label_mode_label.setText(ui_text(self.language, "currency_labels"))
        self.language_combo.blockSignals(True)
        self.language_combo.setItemText(0, ui_text(self.language, "spanish"))
        self.language_combo.setItemText(1, ui_text(self.language, "english"))
        self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(self.language)))
        self.language_combo.blockSignals(False)
        self.label_mode_combo.blockSignals(True)
        self.label_mode_combo.setItemText(0, ui_text(self.language, "label_code"))
        self.label_mode_combo.setItemText(1, ui_text(self.language, "label_name"))
        self.label_mode_combo.setItemText(2, ui_text(self.language, "label_both"))
        self.label_mode_combo.setCurrentIndex(max(0, self.label_mode_combo.findData(self.label_mode)))
        self.label_mode_combo.blockSignals(False)
        self.flag_position_label.setText(ui_text(self.language, "flag_position"))
        self.flag_position_combo.blockSignals(True)
        self.flag_position_combo.setItemText(0, ui_text(self.language, "flag_before"))
        self.flag_position_combo.setItemText(1, ui_text(self.language, "flag_after_code"))
        self.flag_position_combo.setItemText(2, ui_text(self.language, "flag_after"))
        self.flag_position_combo.setCurrentIndex(max(0, self.flag_position_combo.findData(self.flag_position)))
        self.flag_position_combo.blockSignals(False)
        self.flag_position_hint.setText(ui_text(self.language, "flag_hint"))
        self.symbol_position_label.setText(ui_text(self.language, "symbol_position"))
        self.symbol_position_combo.blockSignals(True)
        self.symbol_position_combo.setItemText(0, ui_text(self.language, "symbol_before_all"))
        self.symbol_position_combo.setItemText(1, ui_text(self.language, "symbol_before_code"))
        self.symbol_position_combo.setItemText(2, ui_text(self.language, "symbol_after_code"))
        self.symbol_position_combo.setItemText(3, ui_text(self.language, "symbol_after"))
        self.symbol_position_combo.setCurrentIndex(max(0, self.symbol_position_combo.findData(self.symbol_position)))
        self.symbol_position_combo.blockSignals(False)
        self.symbol_position_hint.setText(ui_text(self.language, "symbol_hint"))
        self.rounding_label.setText(ui_text(self.language, "rounding"))
        self.rounding_combo.blockSignals(True)
        self.rounding_combo.setItemText(0, ui_text(self.language, "round_auto"))
        self.rounding_combo.setItemText(1, ui_text(self.language, "round_zero"))
        self.rounding_combo.setItemText(2, ui_text(self.language, "round_one"))
        self.rounding_combo.setItemText(3, ui_text(self.language, "round_two"))
        self.rounding_combo.setCurrentIndex(max(0, self.rounding_combo.findData(self.rounding_mode)))
        self.rounding_combo.blockSignals(False)
        self.rounding_hint.setText(ui_text(self.language, "rounding_hint"))
        self.zero_fraction_label.setText(ui_text(self.language, "zero_fraction"))
        self.zero_fraction_combo.blockSignals(True)
        self.zero_fraction_combo.setItemText(0, ui_text(self.language, "zero_fraction_hide"))
        self.zero_fraction_combo.setItemText(1, ui_text(self.language, "zero_fraction_keep"))
        self.zero_fraction_combo.setCurrentIndex(1 if self.keep_zero_fraction else 0)
        self.zero_fraction_combo.blockSignals(False)
        self.zero_fraction_hint.setText(ui_text(self.language, "zero_fraction_hint"))
        self.decimal_separator_label.setText(ui_text(self.language, "decimal_separator"))
        self.decimal_separator_combo.blockSignals(True)
        self.decimal_separator_combo.setItemText(0, ui_text(self.language, "decimal_currency"))
        self.decimal_separator_combo.setItemText(1, ui_text(self.language, "decimal_comma"))
        self.decimal_separator_combo.setItemText(2, ui_text(self.language, "decimal_dot"))
        self.decimal_separator_combo.setCurrentIndex(max(0, self.decimal_separator_combo.findData(self.decimal_separator_mode)))
        self.decimal_separator_combo.blockSignals(False)
        self.decimal_separator_hint.setText(ui_text(self.language, "decimal_hint"))
        self.verification_display_label.setText(ui_text(self.language, "verification_display"))
        self.verification_display_combo.blockSignals(True)
        self.verification_display_combo.setItemText(0, ui_text(self.language, "verification_always"))
        self.verification_display_combo.setItemText(1, ui_text(self.language, "verification_issues"))
        self.verification_display_combo.setCurrentIndex(max(0, self.verification_display_combo.findData(self.verification_display_mode)))
        self.verification_display_combo.blockSignals(False)
        self.verification_display_hint.setText(ui_text(self.language, "verification_display_hint"))
        self.latam_optional_title.setText(ui_text(self.language, "latam_optional_title"))
        self.latam_optional_hint.setText(ui_text(self.language, "latam_optional_hint"))
        self.latam_bcb_note.setText(ui_text(self.language, "latam_bcb_note"))
        for code, checkbox in self.latam_checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setText(f"{code} · {currency_name(code, self.language)}")
            checkbox.setChecked(code in self.latam_enabled)
            checkbox.blockSignals(False)
        self.verify_table.setHorizontalHeaderLabels([
            "Currency" if self.language == "en" else "Moneda",
            "Principal (per EUR)" if self.language == "en" else "Principal (por EUR)",
            "Cross-check" if self.language == "en" else "Comprobación cruzada",
            "Difference" if self.language == "en" else "Diferencia",
            "Status" if self.language == "en" else "Estado",
            "Dates" if self.language == "en" else "Fechas",
            "USD peg",
        ])
        self.sources_table.setHorizontalHeaderLabels([
            "Currency" if self.language == "en" else "Moneda",
            "Primary source" if self.language == "en" else "Fuente principal",
            "Calculation" if self.language == "en" else "Cálculo",
            "Check" if self.language == "en" else "Comprobación",
            "Official links" if self.language == "en" else "Enlaces oficiales",
        ])
        self.group_assign_table.setHorizontalHeaderLabels([
            "Currency" if self.language == "en" else "Moneda",
            "Region" if self.language == "en" else "Región",
            "Visible",
            "Group" if self.language == "en" else "Grupo",
        ])
        # The update header contains localized status text too.  Regenerate it
        # whenever the interface language changes, otherwise it can remain in
        # the previous language even though the rest of the UI has switched.
        self._update_date_label()

    def _on_language_changed(self):
        self.language = self.language_combo.currentData() or "es"
        self.language_manual = True
        self._apply_language()
        self._populate_currency_combo()
        self._populate_organizer()
        self._populate_group_editor()
        self._rebuild_cards()
        self._save_preferences()
        self._render()

    def _on_label_mode_changed(self):
        self.label_mode = self.label_mode_combo.currentData() or "code"
        self._populate_currency_combo()
        self._populate_organizer()
        self._populate_group_editor()
        self._rebuild_cards()
        self._save_preferences()
        self._render()

    def _on_flag_position_changed(self):
        self.flag_position = normalize_flag_position(self.flag_position_combo.currentData())
        for card in self.cards.values():
            card.set_flag_position(self.flag_position)
            card.set_symbol_position(self.symbol_position)
        self._save_preferences()

    def _on_symbol_position_changed(self):
        self.symbol_position = normalize_symbol_position(self.symbol_position_combo.currentData())
        for card in self.cards.values():
            card.set_symbol_position(self.symbol_position)
        self._save_preferences()

    def _on_rounding_changed(self):
        self.rounding_mode = normalize_rounding_mode(self.rounding_combo.currentData())
        self._save_preferences()
        self._render()

    def _on_zero_fraction_changed(self):
        self.keep_zero_fraction = bool(self.zero_fraction_combo.currentData())
        self._save_preferences()
        self._render()

    def _on_decimal_separator_changed(self):
        self.decimal_separator_mode = normalize_decimal_separator_mode(self.decimal_separator_combo.currentData())
        self._save_preferences()
        self._render()

    def _on_verification_display_changed(self):
        self.verification_display_mode = normalize_verification_display_mode(self.verification_display_combo.currentData())
        self._save_preferences()
        self._render()

    def _on_latam_currency_toggled(self, code: str, checked: bool):
        code = str(code).upper()
        if code not in LATAM_EXTRA_CODES:
            return
        if checked:
            self.latam_enabled.add(code)
            if code not in self.currency_order:
                self.currency_order.append(code)
            self.visible_codes.add(code)
            self.currency_groups.setdefault(code, "Otras")
        else:
            self.latam_enabled.discard(code)
            self.visible_codes.discard(code)
        self._save_preferences()
        self._populate_organizer()
        self._populate_group_editor()
        self._populate_currency_combo()
        self._rebuild_cards()
        self._render()
        self.refresh_rates(initial=False)

    def _on_group_sort_changed(self):
        self.group_assignment_sort = self.group_sort_combo.currentData() or "code"
        self._populate_group_assignments()

    def _save_organizer_state(self, record_history: bool = True):
        if record_history:
            self._push_undo_state()
        order: list[str] = []
        visible: set[str] = set()
        for row in range(self.currency_list.count()):
            item = self.currency_list.currency_item(row)
            if item is None:
                continue
            code = item.data(Qt.ItemDataRole.UserRole)
            order.append(code)
            if item.checkState() == Qt.CheckState.Checked:
                visible.add(code)
        if not visible:
            visible.add("EUR")
            for row in range(self.currency_list.count()):
                item = self.currency_list.currency_item(row)
                if item is not None and item.data(Qt.ItemDataRole.UserRole) == "EUR":
                    self._building_currency_list = True
                    item.setCheckState(Qt.CheckState.Checked)
                    self._building_currency_list = False
                    break
            self.statusBar().showMessage("Debe quedar al menos una moneda visible; se ha mantenido EUR.", 5000)
        # Never persist a truncated organizer list. A drag/drop UI glitch must
        # not be able to remove a supported currency from the saved order.
        clean_order = _unique_codes(order)
        expected_codes = _unique_codes(self._all_codes())
        missing_codes = [code for code in expected_codes if code not in clean_order]
        rebuild_organizer = bool(missing_codes)
        if missing_codes:
            clean_order.extend(missing_codes)
            self.statusBar().showMessage(
                "Se ha protegido el orden: ninguna divisa se ha eliminado."
                if self.language == "es"
                else "Order protected: no currency was removed.",
                5000,
            )

        previous_visible = set(self.visible_codes)
        self.currency_order = clean_order
        protected_visible = set(code for code in visible if code in self.currency_order)
        # If a row vanished only because of a transient UI problem, preserve
        # its previous checked/visible state as well as its order entry.
        protected_visible.update(code for code in missing_codes if code in previous_visible)
        self.visible_codes = protected_visible
        self.group_order, self.currency_groups = ensure_group_defaults(self.group_order, self.currency_groups, self.currency_order)
        self._save_preferences()
        if rebuild_organizer:
            self._populate_organizer()
        self._populate_group_assignments()
        self._rebuild_cards()
        self._render()

    def _on_currency_item_changed(self, _item, _column=0):
        if not self._building_currency_list:
            self._save_organizer_state()

    def _on_currency_rows_moved(self, *_):
        if not self._building_currency_list:
            self._save_organizer_state()

    def _show_all_currencies(self):
        self._push_undo_state()
        self._building_currency_list = True
        for row in range(self.currency_list.count()):
            item = self.currency_list.currency_item(row)
            if item is not None:
                item.setCheckState(Qt.CheckState.Checked)
        self._building_currency_list = False
        self._save_organizer_state(record_history=False)

    def _primary_currencies_only(self):
        self._push_undo_state()
        self._building_currency_list = True
        for row in range(self.currency_list.count()):
            item = self.currency_list.currency_item(row)
            if item is None:
                continue
            code = item.data(Qt.ItemDataRole.UserRole)
            item.setCheckState(Qt.CheckState.Checked if code in PRIMARY else Qt.CheckState.Unchecked)
        self._building_currency_list = False
        self._save_organizer_state(record_history=False)

    def _reset_currency_order(self):
        self._push_undo_state()
        extras = [c for c in _unique_codes(self._all_codes()) if c not in PRIMARY]
        self.currency_order = _unique_codes(list(PRIMARY) + sorted(extras))
        self.group_order, self.currency_groups = ensure_group_defaults(self.group_order, self.currency_groups, self.currency_order)
        self._save_preferences()
        self._populate_organizer()
        self._populate_group_assignments()
        self._rebuild_cards()
        self._render_sources()

    def _add_group(self):
        name = normalize_group_name(self.group_name_edit.text())
        if not name:
            self.statusBar().showMessage("Write a group name." if self.language == "en" else "Escribe un nombre de grupo.", 4000)
            return
        if name in self.group_order:
            self.statusBar().showMessage("That group already exists." if self.language == "en" else "Ese grupo ya existe.", 4000)
            self.group_name_edit.clear()
            return
        self._push_undo_state()
        self.group_order.append(name)
        self.group_colors[name] = default_group_color(name)
        self._save_preferences()
        self.group_name_edit.clear()
        self._populate_group_editor()
        self.statusBar().showMessage((f"Group created: {name}" if self.language == "en" else f"Grupo creado: {name}"), 3000)

    def _remove_selected_group(self):
        item = self.group_list.currentItem()
        if not item:
            self.statusBar().showMessage("Select a group to delete." if self.language == "en" else "Selecciona un grupo para eliminarlo.", 4000)
            return
        name = normalize_group_name(item.data(Qt.ItemDataRole.UserRole) or item.text())
        if len(self.group_order) <= 1:
            self.statusBar().showMessage("At least one group must remain." if self.language == "en" else "Debe quedar al menos un grupo.", 4000)
            return
        self._push_undo_state()
        fallback = "Otras" if name != "Otras" else next((g for g in self.group_order if g != name), "Otras")
        if fallback not in self.group_order and fallback != name:
            self.group_order.append(fallback)
        for code, group in list(self.currency_groups.items()):
            if group == name:
                self.currency_groups[code] = fallback
        self.group_order = [g for g in self.group_order if g != name]
        self.group_colors.pop(name, None)
        self.group_order, self.currency_groups = ensure_group_defaults(self.group_order, self.currency_groups, self.currency_order)
        self.group_colors = ensure_group_colors(self.group_order, self.group_colors)
        self._save_preferences()
        self._populate_group_editor()
        self._rebuild_cards()
        self.statusBar().showMessage((f"Group deleted: {name}" if self.language == "en" else f"Grupo eliminado: {name}"), 3000)

    def _on_group_item_changed(self, item):
        if self._building_group_list:
            return
        old_name = normalize_group_name(item.data(Qt.ItemDataRole.UserRole) or "")
        new_name = normalize_group_name(item.text())
        if not new_name:
            self._building_group_list = True
            item.setText(localized_group_name(old_name or "Otras", self.language))
            self._building_group_list = False
            self.statusBar().showMessage("Group name cannot be empty." if self.language == "en" else "El nombre del grupo no puede estar vacío.", 4000)
            return
        if new_name != old_name and new_name in self.group_order:
            self._building_group_list = True
            item.setText(localized_group_name(old_name, self.language))
            self._building_group_list = False
            self.statusBar().showMessage("Another group already uses that name." if self.language == "en" else "Ya existe otro grupo con ese nombre.", 4000)
            return
        if new_name == old_name:
            return
        self._push_undo_state()
        self.group_order = [new_name if g == old_name else g for g in self.group_order]
        self.currency_groups = {code: (new_name if group == old_name else group) for code, group in self.currency_groups.items()}
        old_color = self.group_colors.pop(old_name, default_group_color(old_name))
        self.group_colors[new_name] = old_color
        item.setData(Qt.ItemDataRole.UserRole, new_name)
        self._save_preferences()
        self._populate_group_assignments()
        self._rebuild_cards()
        self.statusBar().showMessage((f"Group renamed: {old_name} → {new_name}" if self.language == "en" else f"Grupo renombrado: {old_name} → {new_name}"), 4000)

    def _on_group_rows_moved(self, *_):
        if self._building_group_list:
            return
        self._push_undo_state()
        self.group_order = [normalize_group_name(self.group_list.item(row).data(Qt.ItemDataRole.UserRole) or self.group_list.item(row).text()) for row in range(self.group_list.count())]
        self.group_order, self.currency_groups = ensure_group_defaults(self.group_order, self.currency_groups, self.currency_order)
        self._save_preferences()
        self._populate_group_assignments()
        self._rebuild_cards()

    def _update_group_color_button(self, *_):
        if not hasattr(self, "group_color_btn"):
            return
        item = self.group_list.currentItem() if hasattr(self, "group_list") else None
        if item is None:
            self.group_color_btn.setEnabled(False)
            self.group_color_btn.setStyleSheet("")
            return
        name = normalize_group_name(item.data(Qt.ItemDataRole.UserRole) or item.text())
        color = self.group_colors.get(name, default_group_color(name))
        self.group_color_btn.setEnabled(True)
        self.group_color_btn.setStyleSheet(f"QPushButton {{ border-left: 14px solid {color}; }}")

    def _choose_selected_group_color(self):
        item = self.group_list.currentItem()
        if item is None:
            self.statusBar().showMessage(ui_text(self.language, "group_color_no_selection"), 4000)
            return
        name = normalize_group_name(item.data(Qt.ItemDataRole.UserRole) or item.text())
        initial = QColor(self.group_colors.get(name, default_group_color(name)))
        color = QColorDialog.getColor(initial, self, ui_text(self.language, "group_color"))
        if not color.isValid():
            return
        self._push_undo_state()
        self.group_colors[name] = color.name()
        self._save_preferences()
        self._populate_group_list()
        self._rebuild_cards()

    def _update_bulk_group_controls(self):
        if not hasattr(self, "bulk_group_apply_btn"):
            return
        selection = self.group_assign_table.selectionModel() if hasattr(self, "group_assign_table") else None
        rows = sorted({index.row() for index in selection.selectedRows()}) if selection else []
        if selection and not rows:
            rows = sorted({index.row() for index in selection.selectedIndexes()})
        count = len(rows)
        self.bulk_group_apply_btn.setEnabled(count > 0)
        if count:
            self.bulk_group_apply_btn.setText(ui_text(self.language, "bulk_group_apply_count").format(count=count))
        else:
            self.bulk_group_apply_btn.setText(ui_text(self.language, "bulk_group_apply"))

    def _refresh_bulk_group_combo(self):
        if not hasattr(self, "bulk_group_combo"):
            return
        current = self.bulk_group_combo.currentData()
        self.bulk_group_combo.blockSignals(True)
        self.bulk_group_combo.clear()
        for group in self.group_order:
            self.bulk_group_combo.addItem(localized_group_name(group, self.language), group)
        idx = self.bulk_group_combo.findData(current)
        self.bulk_group_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.bulk_group_combo.blockSignals(False)

    def _apply_group_to_selected(self):
        selection = self.group_assign_table.selectionModel()
        rows = sorted({index.row() for index in selection.selectedRows()}) if selection else []
        if selection and not rows:
            rows = sorted({index.row() for index in selection.selectedIndexes()})
        if not rows:
            self.statusBar().showMessage(ui_text(self.language, "bulk_group_no_selection"), 4000)
            return
        group_name = normalize_group_name(self.bulk_group_combo.currentData())
        if not group_name:
            return
        codes: list[str] = []
        for row in rows:
            item = self.group_assign_table.item(row, 0)
            if item is None:
                continue
            code = str(item.data(Qt.ItemDataRole.UserRole) or "").upper()
            if code:
                codes.append(code)
        if not codes:
            return
        self._push_undo_state()
        if group_name not in self.group_order:
            self.group_order.append(group_name)
        for code in codes:
            self.currency_groups[code] = group_name
        self._save_preferences()
        self._populate_group_assignments()
        self._rebuild_cards()
        msg = ui_text(self.language, "bulk_group_done").format(count=len(codes))
        self.statusBar().showMessage(msg, 4000)

    def _on_currency_group_changed(self, code: str, group_name: str):
        if self._building_group_table:
            return
        self._push_undo_state()
        group_name = normalize_group_name(group_name)
        if not group_name:
            return
        if group_name not in self.group_order:
            self.group_order.append(group_name)
            self.group_colors[group_name] = default_group_color(group_name)
            self._populate_group_list()
        self.currency_groups[code] = group_name
        self._save_preferences()
        self._rebuild_cards()

    def _reset_groups(self):
        self._push_undo_state()
        self.group_order, self.currency_groups = ensure_group_defaults(default_group_order(), {}, self.currency_order)
        self.group_colors = ensure_group_colors(self.group_order, {})
        self._save_preferences()
        self._populate_group_editor()
        self._rebuild_cards()
        self.statusBar().showMessage("Groups reset." if self.language == "en" else "Grupos restaurados.", 3000)

    def _set_base_from_card(self, code: str):
        idx = self.base.findData(code)
        if idx >= 0:
            self.base.setCurrentIndex(idx)

    def _clear_amount(self):
        self.amount.clear()
        self.amount.setFocus(Qt.FocusReason.OtherFocusReason)

    def _copy_card_value(self, code: str):
        card = self.cards.get(code)
        if not card or card.current_value is None or not card.current_text or card.current_text == "—":
            return
        copy_text = fmt_currency_copy(
            card.current_value, code, rounding_mode=self.rounding_mode,
            decimal_separator_mode=self.decimal_separator_mode,
            keep_zero_fraction=self.keep_zero_fraction,
        )
        QApplication.clipboard().setText(copy_text)
        msg = f"Copied: {copy_text} {code}" if self.language == "en" else f"Copiado: {copy_text} {code}"
        self.statusBar().showMessage(msg, 3000)

    def refresh_rates(self, initial=False):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Refreshing…" if self.language == "en" else "Actualizando…")
        self.statusBar().showMessage("Querying ECB and Bank of Russia…" if self.language == "en" else "Consultando BCE y Banco de Rusia…")
        worker = UpdateWorker(self.latam_enabled)
        worker.signals.done.connect(self._on_rates)
        worker.signals.failed.connect(self._on_rate_error)
        self.pool.start(worker)

    def _on_rates(self, snapshot: RatesSnapshot):
        self.snapshot = snapshot
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText(ui_text(self.language, "refresh"))
        self._sync_currency_preferences()
        self._populate_currency_combo()
        self._populate_organizer()
        self._populate_group_editor()
        self._rebuild_cards()
        self._render()
        if snapshot.errors:
            prefix = "Partial update: " if self.language == "en" else "Actualización parcial: "
            self.statusBar().showMessage(prefix + " · ".join(snapshot.errors), 15000)
        else:
            self.statusBar().showMessage("Rates updated successfully" if self.language == "en" else "Tipos actualizados correctamente", 5000)

    def _on_rate_error(self, message: str):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText(ui_text(self.language, "refresh"))
        if self.snapshot:
            prefix = "Could not update; using local copy: " if self.language == "en" else "No se pudo actualizar; usando copia local: "
            self.statusBar().showMessage(prefix + message, 15000)
            self._update_date_label()
        else:
            QMessageBox.warning(self, "Could not retrieve rates" if self.language == "en" else "No se pudieron obtener los tipos", message)
            self.statusBar().showMessage("No rates available" if self.language == "en" else "Sin tipos disponibles")

    def _human_date(self, iso_date: str | None, include_today: bool = True) -> str:
        if not iso_date:
            return "—"
        try:
            value = datetime.strptime(iso_date, "%Y-%m-%d").date()
        except ValueError:
            return iso_date
        shown = value.strftime("%d/%m/%Y")
        if include_today and value == datetime.now().date():
            return f"Today · {shown}" if self.language == "en" else f"Hoy · {shown}"
        return shown

    def _source_marker(self, cached: bool, available: bool = True) -> str:
        if not available:
            return "—"
        if cached:
            return "◷ local copy" if self.language == "en" else "◷ copia local"
        return "✓"

    def _snapshot_check_time(self) -> str:
        raw = getattr(self.snapshot, "fetched_at", "") if self.snapshot else ""
        if isinstance(raw, str) and raw:
            try:
                value = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone()
                return value.strftime("%d/%m/%Y · %H:%M")
            except (ValueError, TypeError):
                pass
        return datetime.now().astimezone().strftime("%d/%m/%Y · %H:%M")

    def _latam_download_status_line(self) -> str:
        if not self.snapshot or not self.latam_enabled:
            return ""
        statuses = getattr(self.snapshot, "latam_fetch_status", {}) or {}

        groups: list[str] = []
        for state, symbol in (("fresh", "✓"), ("cached", "◷"), ("missing", "⚠"), ("error", "✕")):
            codes = [code for code in LATAM_EXTRA_CODES if code in self.latam_enabled and statuses.get(code) == state]
            if codes:
                names = ", ".join(LATAM_SOURCE_NAMES.get(code, code) for code in codes)
                groups.append(f"{symbol} {names}")

        # A snapshot from an older cache may not yet contain the diagnostic map.
        unknown = [code for code in LATAM_EXTRA_CODES if code in self.latam_enabled and code not in statuses]
        if unknown:
            names = ", ".join(LATAM_SOURCE_NAMES.get(code, code) for code in unknown)
            groups.append(f"— {names}")

        bcb_state = str(getattr(self.snapshot, "bcb_fetch_status", "") or "")
        bcb_symbol = {
            "fresh": "✓", "cached": "◷", "partial": "⚠", "missing": "⚠", "error": "✕"
        }.get(bcb_state, "—")
        groups.append(f"{bcb_symbol} BCB")
        return f"<b>{ui_text(self.language, 'latam_status_label')}</b> " + " · ".join(groups)

    def _update_date_label(self):
        if not self.snapshot:
            self.update_label.setText("No data" if self.language == "en" else "Sin datos")
            return

        checked = self._snapshot_check_time()
        ecb_available = bool(self.snapshot.ecb_date)
        cbr_available = bool(self.snapshot.cbr_date and self.snapshot.cbr_rub_per_unit)
        ecb_fresh = ecb_available and not self.snapshot.ecb_cached
        cbr_fresh = cbr_available and not self.snapshot.cbr_cached
        pub_fresh = bool(self.snapshot.cbr_published_date) and not self.snapshot.cbr_published_cached
        latam_statuses = getattr(self.snapshot, "latam_fetch_status", {}) or {}
        optional_local_issue = any(
            latam_statuses.get(code) not in {None, "fresh"}
            for code in self.latam_enabled
        )
        bcb_status = str(getattr(self.snapshot, "bcb_fetch_status", "disabled") or "disabled")
        optional_bcb_issue = bool(self.latam_enabled) and bcb_status not in {"fresh", "disabled"}
        optional_issue = optional_local_issue or optional_bcb_issue

        if ecb_fresh and cbr_fresh and pub_fresh and not optional_issue:
            status_line = (
                f"<b>✓ Up to date · {checked}</b>"
                if self.language == "en"
                else f"<b>✓ Al día · {checked}</b>"
            )
        elif not ecb_fresh and not cbr_fresh:
            status_line = (
                f"<b>◷ Using saved data · last check {checked}</b>"
                if self.language == "en"
                else f"<b>◷ Usando datos guardados · última comprobación {checked}</b>"
            )
        else:
            status_line = (
                f"<b>◷ Partial update · {checked}</b>"
                if self.language == "en"
                else f"<b>◷ Actualización parcial · {checked}</b>"
            )

        ecb_date = self._human_date(self.snapshot.ecb_date, include_today=False)
        if self.language == "en":
            ecb_line = (
                f"<b>ECB</b> {self._source_marker(self.snapshot.ecb_cached, ecb_available)} "
                f"<span style='font-weight:400'>{'latest known publication' if self.snapshot.ecb_cached else 'latest publication'}: {ecb_date}</span>"
            )
        else:
            ecb_line = (
                f"<b>BCE</b> {self._source_marker(self.snapshot.ecb_cached, ecb_available)} "
                f"<span style='font-weight:400'>{'última publicación conocida' if self.snapshot.ecb_cached else 'última publicación'}: {ecb_date}</span>"
            )

        if self.snapshot.cbr_date or self.snapshot.cbr_published_date:
            cbr_pub = self._human_date(self.snapshot.cbr_published_date, include_today=False)
            local = self.snapshot.cbr_cached or self.snapshot.cbr_published_cached
            if self.language == "en":
                cbr_line = (
                    f"<b>CBR</b> {self._source_marker(local, cbr_available)} "
                    f"<span style='font-weight:400'>{'latest known publication' if local else 'latest publication'}: {cbr_pub}</span>"
                )
            else:
                cbr_line = (
                    f"<b>CBR</b> {self._source_marker(local, cbr_available)} "
                    f"<span style='font-weight:400'>{'última publicación conocida' if local else 'última publicación'}: {cbr_pub}</span>"
                )
        else:
            cbr_line = "<b>CBR</b> — not available" if self.language == "en" else "<b>CBR</b> — no disponible"

        top_lines = [status_line, ecb_line, cbr_line]
        latam_line = self._latam_download_status_line()
        if latam_line:
            top_lines.append(latam_line)
        self.update_label.setText("<br>".join(top_lines))
        details = [ui_text(self.language, "update_tooltip")]
        if self.snapshot.ecb_cached:
            details.append(
                "ECB: using the last successful local copy; a newer publication could not be confirmed."
                if self.language == "en"
                else "BCE: se usa la última copia local correcta; no se ha podido confirmar si existe una publicación posterior."
            )
        if self.snapshot.cbr_cached:
            details.append(
                "CBR: using the last successful local rate table; a newer publication could not be confirmed."
                if self.language == "en"
                else "CBR: se usa la última tabla de tipos guardada correctamente; no se ha podido confirmar si existe una publicación posterior."
            )
        elif self.snapshot.cbr_published_cached:
            details.append(
                "CBR: the rate table was updated, but the publication date could not be checked again; the last known publication date is shown."
                if self.language == "en"
                else "CBR: la tabla de tipos se actualizó, pero no se pudo volver a comprobar la fecha de publicación; se muestra la última fecha conocida."
            )
        statuses = getattr(self.snapshot, "latam_fetch_status", {}) or {}
        cached_latam = [code for code in LATAM_EXTRA_CODES if code in self.latam_enabled and statuses.get(code) == "cached"]
        missing_latam = [code for code in LATAM_EXTRA_CODES if code in self.latam_enabled and statuses.get(code) == "missing"]
        failed_latam = [code for code in LATAM_EXTRA_CODES if code in self.latam_enabled and statuses.get(code) == "error"]
        if cached_latam:
            joined = ", ".join(f"{code} ({LATAM_SOURCE_NAMES.get(code, code)})" for code in cached_latam)
            details.append(
                f"Optional currencies using their last successful local source copy: {joined}."
                if self.language == "en"
                else f"Divisas opcionales usando la última copia local correcta de su fuente: {joined}."
            )
        if missing_latam:
            joined = ", ".join(f"{code} ({LATAM_SOURCE_NAMES.get(code, code)})" for code in missing_latam)
            details.append(
                f"Official source reached, but the expected published rate was not found: {joined}."
                if self.language == "en"
                else f"Fuente oficial consultada, pero no se encontró el tipo publicado esperado: {joined}."
            )
        if failed_latam:
            joined = ", ".join(f"{code} ({LATAM_SOURCE_NAMES.get(code, code)})" for code in failed_latam)
            details.append(
                f"Official source could not be downloaded or read and no safe cached value was available: {joined}."
                if self.language == "en"
                else f"No se pudo descargar o leer la fuente oficial y no había una copia local segura: {joined}."
            )
        if optional_bcb_issue:
            bcb_error = str(getattr(self.snapshot, "bcb_fetch_error", "") or "")
            base = (
                "The BCB indicative secondary cross-check could not be refreshed completely."
                if self.language == "en"
                else "No se pudo actualizar completamente la comprobación secundaria indicativa del BCB."
            )
            details.append(f"{base} {bcb_error}".strip())
        self.update_label.setToolTip("\n\n".join(details))

    def _verification_dates_text(self, compact: bool = False) -> str:
        if not self.snapshot:
            return "—"
        ecb = self._human_date(self.snapshot.ecb_date, include_today=False)
        cbr_rate = self._human_date(self.snapshot.cbr_date, include_today=False)
        cbr_pub = self._human_date(self.snapshot.cbr_published_date, include_today=False)
        if compact:
            if self.language == "en":
                return f"ECB {ecb} · CBR rate {cbr_rate}"
            return f"BCE {ecb} · CBR tipo {cbr_rate}"
        if self.language == "en":
            return f"ECB reference: {ecb}; CBR official rate for: {cbr_rate} (published {cbr_pub})"
        return f"BCE referencia: {ecb}; CBR tipo oficial para: {cbr_rate} (publicado {cbr_pub})"

    def _verification_dates_for(self, code: str, v: dict[str, object], compact: bool = False) -> str:
        if not self.snapshot or not v.get("latam_extra"):
            return self._verification_dates_text(compact=compact)
        source = str(v.get("primary_label") or self.snapshot.latam_sources.get(code, code))
        local_date = self._human_date(self.snapshot.latam_dates.get(code), include_today=False)
        bcb_date = self._human_date(self.snapshot.bcb_date, include_today=False)
        if compact:
            return f"{source} {local_date} · BCB {bcb_date}"
        if self.language == "en":
            return f"{source} reference: {local_date}; BCB indicative quotation: {bcb_date}"
        return f"{source} referencia: {local_date}; BCB cotización indicativa: {bcb_date}"

    def _verification_tooltip(self, code: str, v: dict[str, object]) -> str:
        level = str(v.get("level", "neutral"))
        status_text = localized_verification_status(str(v.get("status", "")), self.language)
        date_text = self._verification_dates_for(code, v, compact=False)

        if code in USD_PEGS and v.get("peg") is not None:
            peg = float(v["peg"])
            expected = float(v["peg_expected"])
            peg_diff = float(v.get("peg_difference_pct") or 0.0)
            formula = f"USD/RUB ÷ {code}/RUB"
            if self.language == "en":
                verdict = {
                    "good": "The difference is ≤ 0.10%, so the configured USD peg is considered confirmed.",
                    "warn": "The difference is > 0.10% and ≤ 0.50%, so the peg should be reviewed.",
                    "bad": "The difference is > 0.50%, so the CBR cross-check no longer matches the configured peg.",
                }.get(level, "")
                return (
                    f"{status_text}. The app uses the fixed USD peg for {code} and checks it independently with CBR data. "
                    f"CBR cross-check ({formula}) = {peg:.6f} {code}/USD; configured peg = {expected:.4f}. "
                    f"Difference: {peg_diff:.4f}%. {verdict} Dates: {date_text}."
                )
            verdict = {
                "good": "La diferencia es ≤ 0,10 %, por lo que el peg USD configurado se considera confirmado.",
                "warn": "La diferencia es > 0,10 % y ≤ 0,50 %, por lo que conviene revisar el peg.",
                "bad": "La diferencia es > 0,50 %, por lo que la comprobación del CBR ya no coincide con el peg configurado.",
            }.get(level, "")
            return (
                f"{status_text}. La app usa el peg fijo con USD para {code} y lo contrasta de forma independiente con datos del CBR. "
                f"Comprobación CBR ({formula}) = {peg:.6f} {code}/USD; peg configurado = {expected:.4f}. "
                f"Diferencia: {peg_diff:.4f} %. {verdict} Fechas: {date_text}."
            )

        diff = v.get("difference_pct")
        main = v.get("main")
        cross = v.get("cross")
        if v.get("latam_extra") and diff is not None and main is not None and cross is not None:
            diff_f = float(diff)
            main_f = float(main)
            cross_f = float(cross)
            source = str(v.get("primary_label") or code)
            if self.language == "en":
                verdict = {
                    "good": "The difference is ≤ 1.5%, so both references are considered consistent.",
                    "warn": "The difference is > 1.5% and ≤ 3%, so the result should be reviewed.",
                    "bad": "The difference is > 3%, so the references differ significantly.",
                }.get(level, "")
                return (
                    f"{status_text}. Main calculation: official {source} {code}/USD reference combined with ECB EUR/USD = {fmt_number(main_f)} {code}/EUR. "
                    f"Indicative BCB cross-check = {fmt_number(cross_f)} {code}/EUR. Difference: {diff_f:.3f}%. {verdict} "
                    f"Dates: {date_text}. The BCB states that non-USD currency quotations in this table are indicative, so they are used only as a secondary cross-check."
                )
            verdict = {
                "good": "La diferencia es ≤ 1,5 %, por lo que ambas referencias se consideran coherentes.",
                "warn": "La diferencia es > 1,5 % y ≤ 3 %, por lo que conviene revisar el resultado.",
                "bad": "La diferencia es > 3 %, por lo que las referencias difieren de forma significativa.",
            }.get(level, "")
            return (
                f"{status_text}. Cálculo principal: referencia oficial {source} {code}/USD combinada con EUR/USD del BCE = {fmt_number(main_f)} {code}/EUR. "
                f"Comprobación indicativa del BCB = {fmt_number(cross_f)} {code}/EUR. Diferencia: {diff_f:.3f} %. {verdict} "
                f"Fechas: {date_text}. El BCB indica que las cotizaciones de monedas distintas del USD en esta tabla son indicativas, por lo que se usan solo como comprobación secundaria."
            )
        if diff is None or main is None or cross is None:
            return "No second source is available for this currency." if self.language == "en" else "No hay una segunda fuente disponible para comprobar esta moneda."

        diff = float(diff)
        main = float(main)
        cross = float(cross)
        if self.language == "en":
            verdict = {
                "good": "The difference is ≤ 1.5%, so both sources are considered consistent.",
                "warn": "The difference is > 1.5% and ≤ 3%, so the result should be reviewed.",
                "bad": "The difference is > 3%, so the two references differ significantly.",
            }.get(level, "")
            return (
                f"{status_text}. ECB reference: {fmt_number(main)} {code}/EUR. "
                f"Independent CBR cross-check via RUB: {fmt_number(cross)} {code}/EUR. "
                f"Difference: {diff:.3f}%. {verdict} Dates: {date_text}. "
                "Small differences can be normal because the two central banks may publish reference rates for different dates or calculation times."
            )
        verdict = {
            "good": "La diferencia es ≤ 1,5 %, por lo que ambas referencias se consideran coherentes.",
            "warn": "La diferencia es > 1,5 % y ≤ 3 %, por lo que conviene revisar el resultado.",
            "bad": "La diferencia es > 3 %, por lo que las dos referencias difieren de forma significativa.",
        }.get(level, "")
        return (
            f"{status_text}. Referencia BCE: {fmt_number(main)} {code}/EUR. "
            f"Comprobación independiente del CBR vía RUB: {fmt_number(cross)} {code}/EUR. "
            f"Diferencia: {diff:.3f} %. {verdict} Fechas: {date_text}. "
            "Pequeñas diferencias pueden ser normales porque ambos bancos centrales pueden publicar referencias correspondientes a fechas u horas de cálculo distintas."
        )

    def _is_cbr_only(self, code: str) -> bool:
        return primary_source_for(code) == "CBR"

    def _source_missing_message(self, code: str) -> str:
        if not self.snapshot:
            return ""
        code = code.upper()
        source = self.snapshot.source_missing.get(code)
        if not source:
            return ""
        source_label = "BCE" if self.language == "es" and source == "ECB" else source
        latam_state = (getattr(self.snapshot, "latam_fetch_status", {}) or {}).get(code)
        detail = (getattr(self.snapshot, "latam_fetch_errors", {}) or {}).get(code, "")
        if latam_state == "error":
            if self.language == "en":
                text = (
                    f"{code}: the official {source_label} source could not be downloaded or read. "
                    "The calculation has been stopped because no safe current or cached value is available."
                )
            else:
                text = (
                    f"{code}: no se pudo descargar o leer la fuente oficial {source_label}. "
                    "El cálculo se ha detenido porque no hay un valor actual ni una copia local segura disponible."
                )
            return f"{text} {detail}".strip()
        if self.language == "en":
            return (
                f"{code} is not present in the current {source_label} publication. "
                "The calculation has been stopped for safety; the app will not reuse an older value or silently switch to another source."
            )
        return (
            f"{code} no figura en la publicación actual de {source_label}. "
            "El cálculo se ha detenido por seguridad; la app no reutiliza un valor antiguo ni cambia silenciosamente a otra fuente."
        )

    def _update_source_warning(self):
        if not hasattr(self, "source_warning"):
            return
        if not self.snapshot:
            self.source_warning.hide()
            return
        affected = [code for code in self.currency_order if code in self.visible_codes and code in self.snapshot.source_missing]
        if not affected:
            self.source_warning.hide()
            self.source_warning.clear()
            return

        statuses = getattr(self.snapshot, "latam_fetch_status", {}) or {}
        def shown_source(code):
            src = self.snapshot.source_missing[code]
            return "BCE" if self.language == "es" and src == "ECB" else src

        failed = [code for code in affected if statuses.get(code) == "error"]
        missing = [code for code in affected if code not in failed]
        chunks: list[str] = []
        if failed:
            label = "Download failed" if self.language == "en" else "Descarga fallida"
            chunks.append(label + ": " + ", ".join(f"{code} ({shown_source(code)})" for code in failed))
        if missing:
            label = "Not in current publication" if self.language == "en" else "No figura en la publicación actual"
            chunks.append(label + ": " + ", ".join(f"{code} ({shown_source(code)})" for code in missing))
        text = f"⚠ {ui_text(self.language, 'source_missing_banner')}: " + "; ".join(chunks) + "."
        self.source_warning.setText(text)
        self.source_warning.setToolTip("\n".join(self._source_missing_message(code) for code in affected))
        self.source_warning.show()

    def _verification_badge(self, code: str) -> tuple[str, str, str]:
        if not self.snapshot:
            return "", "neutral", ""
        if code in self.snapshot.source_missing:
            source = self.snapshot.source_missing[code]
            source_label = "BCE" if self.language == "es" and source == "ECB" else source
            return f"⚠ {source_label}", "warn", self._source_missing_message(code)
        if code == "EUR" or self._is_cbr_only(code):
            return "", "neutral", ""
        v = verification(code, self.snapshot)
        diff = v["difference_pct"]
        level = str(v.get("level", "neutral"))
        if code in USD_PEGS and v["peg"] is not None:
            text = "✓ peg" if level == "good" else ("⚠ peg" if level == "warn" else "! peg")
            return text, level, self._verification_tooltip(code, v)
        if diff is None:
            return "—", "neutral", self._verification_tooltip(code, v)
        symbol = "✓" if level == "good" else ("⚠" if level == "warn" else "!")
        text = f"{symbol} {float(diff):.2f} %".replace(".", ",")
        return text, level, self._verification_tooltip(code, v)

    def _render(self, *_):
        base_code = self.base.currentData() or "EUR"
        if not self.snapshot:
            for code, card in self.cards.items():
                card.value.setText("")
                card.current_text = ""
                card.current_value = None
                card.set_status("")
                card.set_selected(code == base_code)
            self._update_date_label()
            return
        if base_code not in self.snapshot.rates_per_eur:
            return
        amount = parse_amount_text(self.amount.text())
        for code, card in self.cards.items():
            card.set_selected(code == base_code)
            card.refresh_language(self.language, self.label_mode)
            card.set_flag_position(self.flag_position)
            card.set_symbol_position(self.symbol_position)
            if code in self.snapshot.source_missing:
                latam_state = (getattr(self.snapshot, "latam_fetch_status", {}) or {}).get(code)
                missing_key = "source_download_failed_short" if latam_state == "error" else "source_missing_short"
                card.value.setText(ui_text(self.language, missing_key))
                card.current_text = ""
                card.current_value = None
                source = self.snapshot.source_missing[code]
                source_label = "BCE" if self.language == "es" and source == "ECB" else source
                card.set_status(f"⚠ {source_label}", "warn", self._source_missing_message(code))
                continue
            if amount is None:
                card.value.setText("")
                card.current_text = ""
                card.current_value = None
                text, level, tip = self._verification_badge(code)
                if self.verification_display_mode == "issues" and level not in {"warn", "bad"}:
                    text, tip = "", ""
                card.set_status(text, level, tip)
                continue
            if code not in self.snapshot.rates_per_eur:
                card.value.setText(ui_text(self.language, "not_available"))
                card.current_text = ""
                card.current_value = None
                card.set_status("")
                continue
            card.set_value(convert(amount, base_code, code, self.snapshot), rounding_mode=self.rounding_mode, decimal_separator_mode=self.decimal_separator_mode, keep_zero_fraction=self.keep_zero_fraction)
            text, level, tip = self._verification_badge(code)
            if self.verification_display_mode == "issues" and level not in {"warn", "bad"}:
                text, tip = "", ""
            card.set_status(text, level, tip)
        self._render_verification()
        self._render_sources()
        self._update_source_warning()
        self._update_date_label()

    def _render_verification(self):
        if not self.snapshot:
            self.verify_table.setRowCount(0)
            return
        codes = [
            c for c in self.currency_order
            if c in self.visible_codes and c != "EUR" and not self._is_cbr_only(c)
        ]
        self.verify_table.setRowCount(len(codes))
        for row, code in enumerate(codes):
            v = verification(code, self.snapshot)
            main = v["main"]
            cross = v["cross"]
            diff = v["difference_pct"]
            peg = v["peg"]
            expected = v["peg_expected"]
            level = str(v.get("level", "neutral"))
            status_symbol = {"good": "✓", "warn": "⚠", "bad": "!"}.get(level, "—")
            values = [
                currency_label(code, self.language, self.label_mode),
                "—" if main is None else fmt_number(float(main)),
                "—" if cross is None else fmt_number(float(cross)),
                "—" if diff is None else f"{float(diff):.3f} %",
                f"{status_symbol} {localized_verification_status(str(v['status']), self.language)}",
                self._verification_dates_for(code, v, compact=True),
                "—" if peg is None else f"{float(peg):.6f} / {float(expected):.4f}",
            ]
            for col, txt in enumerate(values):
                item = QTableWidgetItem(txt)
                if col in {1, 2, 3, 6}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col in {4, 6}:
                    item.setToolTip(self._verification_tooltip(code, v))
                elif col == 5:
                    item.setToolTip(self._verification_dates_for(code, v, compact=False))
                self.verify_table.setItem(row, col, item)

    def _source_row(self, code: str) -> tuple[str, str, str, list[tuple[str, str]]]:
        if self.language == "en":
            if code == "AED":
                return ("ECB + USD peg", f"ECB EUR/USD × {AED_USD_PEG}", "CBR: USD/RUB ÷ AED/RUB", [("ECB", ECB_INFO_URL), ("CBUAE", CBUAE_URL), ("CBR", CBR_INFO_URL)])
            if code == "SAR":
                return ("ECB + USD peg", f"ECB EUR/USD × {SAR_USD_PEG}", "CBR: USD/RUB ÷ SAR/RUB", [("ECB", ECB_INFO_URL), ("SAMA", SAMA_URL), ("CBR", CBR_INFO_URL)])
            if code == "QAR":
                return ("ECB + USD peg", f"ECB EUR/USD × {QAR_USD_PEG}", "CBR: USD/RUB ÷ QAR/RUB", [("ECB", ECB_INFO_URL), ("QCB", QCB_URL), ("CBR", CBR_INFO_URL)])
            if code == "BHD":
                return ("ECB + USD peg", "ECB EUR/USD ÷ 2.659", "CBR: USD/RUB ÷ BHD/RUB", [("ECB", ECB_INFO_URL), ("CBB", CBB_URL), ("CBR", CBR_INFO_URL)])
            if code == "OMR":
                return ("ECB + USD peg", "ECB EUR/USD ÷ 2.6008", "CBR: USD/RUB ÷ OMR/RUB", [("ECB", ECB_INFO_URL), ("CBO", CBO_URL), ("CBR", CBR_INFO_URL)])
            if code == "RUB":
                return ("Bank of Russia", "Official CBR EUR/RUB", ui_text(self.language, "source_row_none"), [("CBR", CBR_INFO_URL)])
            if self._is_cbr_only(code):
                return ("Bank of Russia", f"CBR EUR/RUB ÷ {code}/RUB", ui_text(self.language, "source_row_none"), [("CBR", CBR_INFO_URL)])
            if code in LATAM_EXTRA_CODES:
                source = self.snapshot.latam_sources.get(code, LATAM_SOURCE_NAMES.get(code, code)) if self.snapshot else LATAM_SOURCE_NAMES.get(code, code)
                local_cached = bool(self.snapshot and code in self.snapshot.latam_cached_codes)
                source_display = f"{source} (local copy)" if local_cached else source
                has_bcb = bool(self.snapshot and code in self.snapshot.bcb_units_per_usd)
                check = ("BCB indicative cross-check (local copy)" if self.snapshot and self.snapshot.bcb_cached else "BCB indicative cross-check") if has_bcb else "No second source"
                links = [(source, LATAM_SOURCE_URLS[code]), ("ECB", ECB_INFO_URL)]
                if has_bcb:
                    links.append(("BCB", BCB_URL))
                return (f"{source_display} + ECB", f"{source} {code}/USD × ECB EUR/USD", check, links)
            if code == "EUR":
                return ("ECB", "Base currency = 1 EUR", "—", [("ECB", ECB_INFO_URL)])
            has_cbr = bool(self.snapshot and code in self.snapshot.cbr_rub_per_unit and "EUR" in self.snapshot.cbr_rub_per_unit)
            verification_text = "CBR cross-check via RUB" if has_cbr else "No second source"
            links = [("ECB", ECB_INFO_URL)]
            if has_cbr:
                links.append(("CBR", CBR_INFO_URL))
            return "ECB", "Reference rate per EUR", verification_text, links
        if code == "AED":
            return ("BCE + peg USD", f"EUR/USD BCE × {AED_USD_PEG}", "CBR: USD/RUB ÷ AED/RUB", [("BCE", ECB_INFO_URL), ("CBUAE", CBUAE_URL), ("CBR", CBR_INFO_URL)])
        if code == "SAR":
            return ("BCE + peg USD", f"EUR/USD BCE × {SAR_USD_PEG}", "CBR: USD/RUB ÷ SAR/RUB", [("BCE", ECB_INFO_URL), ("SAMA", SAMA_URL), ("CBR", CBR_INFO_URL)])
        if code == "QAR":
            return ("BCE + peg USD", f"EUR/USD BCE × {QAR_USD_PEG}", "CBR: USD/RUB ÷ QAR/RUB", [("BCE", ECB_INFO_URL), ("QCB", QCB_URL), ("CBR", CBR_INFO_URL)])
        if code == "BHD":
            return ("BCE + peg USD", "EUR/USD BCE ÷ 2,659", "CBR: USD/RUB ÷ BHD/RUB", [("BCE", ECB_INFO_URL), ("CBB", CBB_URL), ("CBR", CBR_INFO_URL)])
        if code == "OMR":
            return ("BCE + peg USD", "EUR/USD BCE ÷ 2,6008", "CBR: USD/RUB ÷ OMR/RUB", [("BCE", ECB_INFO_URL), ("CBO", CBO_URL), ("CBR", CBR_INFO_URL)])
        if code == "RUB":
            return ("Banco de Rusia", "EUR/RUB oficial del CBR", ui_text(self.language, "source_row_none"), [("CBR", CBR_INFO_URL)])
        if self._is_cbr_only(code):
            return ("Banco de Rusia", f"EUR/RUB ÷ {code}/RUB oficial del CBR", ui_text(self.language, "source_row_none"), [("CBR", CBR_INFO_URL)])
        if code in LATAM_EXTRA_CODES:
            source = self.snapshot.latam_sources.get(code, LATAM_SOURCE_NAMES.get(code, code)) if self.snapshot else LATAM_SOURCE_NAMES.get(code, code)
            local_cached = bool(self.snapshot and code in self.snapshot.latam_cached_codes)
            source_display = f"{source} (copia local)" if local_cached else source
            has_bcb = bool(self.snapshot and code in self.snapshot.bcb_units_per_usd)
            check = ("Comprobación indicativa BCB (copia local)" if self.snapshot and self.snapshot.bcb_cached else "Comprobación indicativa BCB") if has_bcb else "Sin segunda fuente"
            links = [(source, LATAM_SOURCE_URLS[code]), ("BCE", ECB_INFO_URL)]
            if has_bcb:
                links.append(("BCB", BCB_URL))
            return (f"{source_display} + BCE", f"{source} {code}/USD × EUR/USD BCE", check, links)
        if code == "EUR":
            return ("BCE", "Moneda base = 1 EUR", "—", [("BCE", ECB_INFO_URL)])
        has_cbr = bool(self.snapshot and code in self.snapshot.cbr_rub_per_unit and "EUR" in self.snapshot.cbr_rub_per_unit)
        verification_text = "CBR cruzado vía RUB" if has_cbr else "Sin segunda fuente"
        links = [("BCE", ECB_INFO_URL)]
        if has_cbr:
            links.append(("CBR", CBR_INFO_URL))
        return "BCE", "Tipo de referencia por EUR", verification_text, links

    def _render_sources(self):
        if not hasattr(self, "sources_table"):
            return
        if not self.snapshot:
            self.source_summary.setText("No data loaded." if self.language == "en" else "No hay datos cargados.")
            self.sources_table.setRowCount(0)
            return

        if self.language == "en":
            ecb_state = "cache" if self.snapshot.ecb_cached else "live download"
            cbr_state = "cache" if self.snapshot.cbr_cached else ("live download" if self.snapshot.cbr_rub_per_unit else "not available")
            self.source_summary.setText(
                f"<b>ECB:</b> {ecb_state} · data {self._human_date(self.snapshot.ecb_date, include_today=False)} &nbsp;&nbsp; "
                f"<b>CBR:</b> {cbr_state} · valid {self._human_date(self.snapshot.cbr_date, include_today=False)}. "
                "Each row only opens official sources used or consulted by the application."
            )
        else:
            ecb_state = "caché" if self.snapshot.ecb_cached else "descarga actual"
            cbr_state = "caché" if self.snapshot.cbr_cached else ("descarga actual" if self.snapshot.cbr_rub_per_unit else "no disponible")
            self.source_summary.setText(
                f"<b>BCE:</b> {ecb_state} · datos {self._human_date(self.snapshot.ecb_date, include_today=False)} &nbsp;&nbsp; "
                f"<b>CBR:</b> {cbr_state} · válido {self._human_date(self.snapshot.cbr_date, include_today=False)}. "
                "Los enlaces de cada fila abren únicamente las fuentes oficiales usadas o consultadas por la aplicación."
            )

        codes = [c for c in self.currency_order if c in self.visible_codes]
        self.sources_table.setRowCount(len(codes))
        for row, code in enumerate(codes):
            source, calculation, check, links = self._source_row(code)
            display = f"{currency_flag(code)} {currency_label(code, self.language, self.label_mode)}"
            if self.label_mode != "both":
                display += f" · {currency_name(code, self.language)}"
            for col, txt in enumerate((display, source, calculation, check)):
                self.sources_table.setItem(row, col, QTableWidgetItem(txt))

            link_widget = QWidget()
            link_layout = QHBoxLayout(link_widget)
            link_layout.setContentsMargins(0, 0, 0, 0)
            link_layout.setSpacing(4)
            for label, url in links:
                btn = QToolButton()
                btn.setText(label)
                btn.setToolTip(url)
                btn.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
                link_layout.addWidget(btn)
            link_layout.addStretch(1)
            self.sources_table.setCellWidget(row, 4, link_widget)

def crash_log_path() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    path = base / "libre-kambio-currency" / "crash.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_crash_log(exc: BaseException) -> Path:
    path = crash_log_path()
    try:
        path.write_text("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)), encoding="utf-8")
    except OSError:
        pass
    return path


def run_smoke_test() -> int:
    """Exercise the installed GUI without network access.

    This deliberately checks the regressions that previously escaped simple
    startup tests: cards being rebuilt after a refresh and left as ``—``,
    duplicate/disappearing currencies, base-currency clicks, and language
    switching. Preferences are not written during the smoke test.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Libre Kambio Currency")
    app.setApplicationVersion(APP_VERSION)
    app.setDesktopFileName("io.github.h2o7y.LibreKambioCurrency")
    window = MainWindow(auto_refresh=False)
    window.show()
    app.processEvents()
    if window.centralWidget() is None:
        raise RuntimeError("La ventana principal no se inicializó correctamente")

    # Optional Latin-American sources are opt-in. Test the Spanish labels
    # explicitly instead of assuming the Flatpak build environment uses a
    # Spanish locale.
    window.language = "es"
    window._apply_language()
    app.processEvents()
    if window.latam_enabled or any(cb.isChecked() for cb in window.latam_checkboxes.values()):
        raise RuntimeError("Las divisas hispanoamericanas opcionales deben estar desactivadas por defecto")
    symbol_items = [window.symbol_position_combo.itemText(i).lower() for i in range(window.symbol_position_combo.count())]
    if any("(actual)" in text or "(current)" in text for text in symbol_items):
        raise RuntimeError("Opciones conserva una etiqueta obsoleta '(actual)/(current)'")
    if not window.zero_fraction_label.text().startswith("Mostrar"):
        raise RuntimeError("La opción de ceros decimales no usa 'Mostrar' en español")
    if not window.decimal_separator_label.text().startswith("Mostrar"):
        raise RuntimeError("La opción de separador decimal no usa 'Mostrar' en español")
    if not window.verification_display_label.text().startswith("Mostrar"):
        raise RuntimeError("La opción de comprobación no usa 'Mostrar' en español")

    # Never mutate the user's real preferences from an installation smoke test.
    window._save_preferences = lambda: None
    window.currency_order = ["EUR", "JPY", "USD", "AED", "SAR", "RUB", "AUD"]
    window.visible_codes = set(window.currency_order)
    window.group_order = ["Principales", "Golfo", "Europa Este", "Otras"]
    window.currency_groups.update({
        "EUR": "Principales", "JPY": "Principales", "USD": "Principales",
        "AED": "Golfo", "SAR": "Golfo", "RUB": "Europa Este", "AUD": "Otras",
    })

    snapshot = RatesSnapshot(
        rates_per_eur={"EUR": 1.0, "JPY": 185.45, "USD": 1.17, "AED": 4.297825, "SAR": 4.3875, "RUB": 98.0, "AUD": 1.80},
        ecb_rates_per_eur={"EUR": 1.0, "JPY": 185.45, "USD": 1.17, "AUD": 1.80},
        cbr_rub_per_unit={"EUR": 98.0, "JPY": 0.5284, "USD": 84.0, "AED": 22.8725, "SAR": 22.4},
        ecb_date="2026-08-20",
        cbr_date="2026-08-21",
        cbr_published_date="2026-08-20",
        fetched_at="2026-08-21T00:00:00+00:00",
        errors=[],
        ecb_cached=False,
        cbr_cached=False,
        cbr_published_cached=False,
    )

    # Simulate a completed refresh. This must rebuild AND render the cards.
    window.amount.setText("40")
    window._on_rates(snapshot)
    app.processEvents()
    expected_codes = {"EUR", "JPY", "USD", "AED", "SAR", "RUB", "AUD"}
    if set(window.cards) != expected_codes:
        raise RuntimeError(f"Tarjetas inesperadas tras refrescar: {sorted(window.cards)}")
    if len(window.cards) != len(set(window.cards)):
        raise RuntimeError("Se han creado tarjetas de divisa duplicadas")
    if window.cards["EUR"].current_text != "40":
        raise RuntimeError("EUR no conservó la cantidad tras reconstruir las tarjetas o mostró decimales ,00 innecesarios")
    if not window.cards["USD"].current_text or window.cards["USD"].current_text == "—":
        raise RuntimeError("USD quedó sin renderizar después de la actualización")

    # Destructive organizer buttons must be undoable during the session.
    before_visible = set(window.visible_codes)
    window._populate_organizer()
    window._primary_currencies_only()
    app.processEvents()
    if "AUD" in window.visible_codes:
        raise RuntimeError("Solo principales no ocultó una moneda opcional durante el smoke test")
    if not window._undo_stack:
        raise RuntimeError("El cambio de organización no se añadió al historial de deshacer")
    window._undo_last_organization_change()
    app.processEvents()
    if set(window.visible_codes) != before_visible:
        raise RuntimeError("Deshacer no restauró correctamente las monedas visibles")

    # Reordering currencies in Monedas must update the persistent order and the
    # order of cards inside a group. The organizer is a flat QTableWidget, so
    # nesting rows is structurally impossible.
    window.visible_codes.update({"EUR", "USD", "AUD"})
    window.currency_groups["EUR"] = "Principales"
    window.currency_groups["USD"] = "Principales"
    window.currency_groups["AUD"] = "Principales"
    window.currency_order = ["EUR", "USD", "AUD"] + [c for c in window.currency_order if c not in {"EUR", "USD", "AUD"}]
    window._populate_organizer()
    aud_row = next((i for i in range(window.currency_list.count()) if window.currency_list.code_at(i) == "AUD"), -1)
    eur_row = next((i for i in range(window.currency_list.count()) if window.currency_list.code_at(i) == "EUR"), -1)
    if aud_row < 0 or eur_row < 0 or not window.currency_list.move_row(aud_row, eur_row):
        raise RuntimeError("No se pudo simular la reordenación de Monedas")
    app.processEvents()
    principals = [c for c in window.currency_order if c in window.visible_codes and window.currency_groups.get(c) == "Principales"]
    if principals.index("AUD") > principals.index("EUR"):
        raise RuntimeError("Mover una divisa en Monedas no actualizó currency_order")
    organizer_codes = [window.currency_list.code_at(i) for i in range(window.currency_list.count())]
    organizer_codes = [c for c in organizer_codes if c]
    if len(organizer_codes) != len(set(organizer_codes)):
        raise RuntimeError("Reordenar Monedas produjo divisas duplicadas")
    if not isinstance(window.currency_list, OrganizerTable):
        raise RuntimeError("Monedas no está usando el organizador plano esperado")
    if window.currency_list.dragEnabled() or window.currency_list.acceptDrops() or window.currency_list.viewport().acceptDrops():
        raise RuntimeError("Monedas todavía tiene activo el drag/drop nativo de Qt")
    if window.currency_list.dragDropMode() != QAbstractItemView.DragDropMode.NoDragDrop:
        raise RuntimeError("Monedas no ha desactivado completamente el drag/drop nativo")
    expected_codes = set(window._all_codes())
    if set(organizer_codes) != expected_codes:
        missing = sorted(expected_codes - set(organizer_codes))
        raise RuntimeError(f"Reordenar Monedas hizo desaparecer divisas: {missing}")
    # Rebuild order is based on currency_order; ensure the visual card positions
    # for the group follow it as well.
    positions = {}
    for idx in range(window.cards_grid.count()):
        w = window.cards_grid.itemAt(idx).widget()
        if isinstance(w, CurrencyCard) and w.code in {"AUD", "EUR", "USD"}:
            pos = window.cards_grid.getItemPosition(idx)
            positions[w.code] = (pos[0], pos[1])
    if not all(c in positions for c in ("AUD", "EUR", "USD")) or not (positions["AUD"] < positions["EUR"] < positions["USD"]):
        raise RuntimeError("El Conversor no respetó el nuevo orden de Monedas dentro del grupo")

    # Management views must always show ISO code + localized name, regardless
    # of the card/base label preference.
    window.label_mode = "name"
    window._populate_organizer()
    eur_items = [window.currency_list.item(i, 0).text() for i in range(window.currency_list.count()) if window.currency_list.code_at(i) == "EUR" and window.currency_list.item(i, 0) is not None]
    if not eur_items or "EUR · Euro" not in eur_items[0]:
        raise RuntimeError("Monedas no mantiene código + nombre independientemente de Opciones")

    # Currencies management view must keep region in its own second column.
    eur_row_index = next((i for i in range(window.currency_list.count()) if window.currency_list.code_at(i) == "EUR"), -1)
    eur_region_item = window.currency_list.item(eur_row_index, 1) if eur_row_index >= 0 else None
    if eur_region_item is None or window.currency_list.columnCount() < 2 or eur_region_item.text() != currency_region_name("EUR", window.language):
        raise RuntimeError("Monedas no muestra Región en una columna independiente")

    # Region colours must be stable for every currency in the same region.
    europe_colours = set()
    for i in range(window.currency_list.count()):
        code = window.currency_list.code_at(i)
        region_item = window.currency_list.item(i, 1)
        if code in {"EUR", "GBP", "PLN", "SEK", "CZK"} and region_item is not None:
            europe_colours.add(region_item.foreground().color().name())
    if len(europe_colours) > 1:
        raise RuntimeError("Monedas aplica colores distintos a divisas de la misma región")

    # The Groups assignment list can switch between ISO and region sorting.
    window.label_mode = "code"
    window.group_assignment_sort = "region"
    window._populate_group_assignments()
    region_codes = [str(window.group_assign_table.item(i, 0).data(Qt.ItemDataRole.UserRole)) for i in range(window.group_assign_table.rowCount())]
    expected_region_codes = region_sorted_codes(window.currency_order)
    if region_codes != expected_region_codes:
        raise RuntimeError("La ordenación por región en Grupos no funciona")

    # Multi-select group assignment must update all selected currencies in one
    # operation and remain undoable as a single history step.
    window.group_assign_table.clearSelection()
    selected_rows = [0, 1]
    selected_codes = []
    before_groups = dict(window.currency_groups)
    selection_model = window.group_assign_table.selectionModel()
    for row in selected_rows:
        item = window.group_assign_table.item(row, 0)
        if item is None:
            raise RuntimeError("No se pudo preparar la selección múltiple en Grupos")
        selected_codes.append(str(item.data(Qt.ItemDataRole.UserRole)))
        index = window.group_assign_table.model().index(row, 0)
        selection_model.select(index, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
    other_idx = window.bulk_group_combo.findData("Otras")
    if other_idx < 0:
        raise RuntimeError("No se encontró el grupo Otras para la asignación masiva")
    window.bulk_group_combo.setCurrentIndex(other_idx)
    window._apply_group_to_selected()
    app.processEvents()
    if any(window.currency_groups.get(code) != "Otras" for code in selected_codes):
        raise RuntimeError("La asignación masiva de grupo no actualizó todas las divisas seleccionadas")
    window._undo_last_organization_change()
    app.processEvents()
    if any(window.currency_groups.get(code) != before_groups.get(code) for code in selected_codes):
        raise RuntimeError("Deshacer no restauró la asignación masiva de grupos")

    window.group_assignment_sort = "code"
    window._populate_group_assignments()
    code_order = [window.group_assign_table.item(i, 0).text() for i in range(window.group_assign_table.rowCount())]
    if not code_order or "AED ·" not in code_order[0]:
        raise RuntimeError("La ordenación A–Z en Grupos no funciona")

    # A currency omitted by a freshly reached primary source must never be
    # calculated from another bank or an old value.
    missing_snapshot = RatesSnapshot(
        rates_per_eur={"EUR": 1.0, "USD": 1.17, "AED": 4.297825, "SAR": 4.3875, "RUB": 98.0},
        ecb_rates_per_eur={"EUR": 1.0, "USD": 1.17},
        cbr_rub_per_unit={"EUR": 98.0, "USD": 84.0, "AUD": 60.0, "AED": 22.8725, "SAR": 22.4},
        ecb_date="2026-08-21", cbr_date="2026-08-21", cbr_published_date="2026-08-20",
        fetched_at="2026-08-21T00:00:00+00:00", errors=[], source_missing={"AUD": "ECB"},
    )
    window.label_mode = "code"
    window._on_rates(missing_snapshot)
    window.amount.setText("40")
    window._render()
    app.processEvents()
    if window.cards["AUD"].current_text:
        raise RuntimeError("AUD se calculó aunque su fuente principal ya no lo publicaba")
    if "No publicado" not in window.cards["AUD"].value.text() and "Not published" not in window.cards["AUD"].value.text():
        raise RuntimeError("No se muestra el aviso de moneda no publicada")
    if window.base.findData("AUD") >= 0:
        raise RuntimeError("Una moneda no publicada sigue disponible como moneda base")
    if not window.source_warning.isVisible():
        raise RuntimeError("No se muestra el aviso de seguridad de fuente")

    # Restore the full snapshot for the remaining UI checks.
    window._on_rates(snapshot)

    # Clicking another card must change the base without losing the input.
    window._set_base_from_card("USD")
    window._render()
    app.processEvents()
    if window.base.currentData() != "USD":
        raise RuntimeError("No se pudo cambiar la moneda base a USD")
    if window.amount.text() != "40":
        raise RuntimeError("Cambiar la moneda base borró la cantidad")

    # Language switching must update the visible interface immediately.
    window.language = "en"
    window._apply_language()
    if window.title_label.text() != "Currencies":
        raise RuntimeError("La traducción inglesa no se aplicó correctamente")
    if not window.zero_fraction_label.text().startswith("Show") or not window.decimal_separator_label.text().startswith("Show") or not window.verification_display_label.text().startswith("Show"):
        raise RuntimeError("Las opciones nuevas no mantienen traducciones coherentes al inglés")
    window.language = "es"
    window._apply_language()
    window._render()
    app.processEvents()
    if window.title_label.text() != "Divisas":
        raise RuntimeError("No se pudo volver a español")

    window._update_date_label()
    if "BCE" not in window.update_label.text() and "ECB" not in window.update_label.text():
        raise RuntimeError("El estado de actualización no se ha renderizado")
    if "Al día" not in window.update_label.text():
        raise RuntimeError(f"La cabecera no muestra el estado compacto Al día: {window.update_label.text()}")
    if "última publicación" not in window.update_label.text():
        raise RuntimeError("La cabecera no usa la etiqueta compacta última publicación")

    # Verification tooltips must explain why a status is considered valid.
    usd_rows = [r for r in range(window.verify_table.rowCount()) if window.verify_table.item(r, 0) and "USD" in window.verify_table.item(r, 0).text()]
    if not usd_rows:
        raise RuntimeError("No se encontró USD en la tabla de verificación")
    usd_tip = window.verify_table.item(usd_rows[0], 4).toolTip()
    if "1,5" not in usd_tip and "1.5" not in usd_tip:
        raise RuntimeError("El tooltip de Coherente no explica el umbral de verificación")
    if ("CBR +1" in usd_tip or "BCE referencia:" not in usd_tip
            or "CBR tipo oficial para:" not in usd_tip or "publicado" not in usd_tip):
        raise RuntimeError(f"El tooltip de fechas no distingue fecha de referencia BCE, tipo CBR y publicación CBR: {usd_tip}")

    window.verification_display_mode = "issues"
    window._render()
    if window.cards["USD"].status.isVisible():
        raise RuntimeError("La opción Solo avisos no oculta una comprobación coherente")
    window.verification_display_mode = "always"
    window._render()

    aed_rows = [r for r in range(window.verify_table.rowCount()) if window.verify_table.item(r, 0) and "AED" in window.verify_table.item(r, 0).text()]
    if not aed_rows:
        raise RuntimeError("No se encontró AED en la tabla de verificación")
    aed_tip = window.verify_table.item(aed_rows[0], 4).toolTip()
    if "USD/RUB" not in aed_tip or ("0,10" not in aed_tip and "0.10" not in aed_tip):
        raise RuntimeError("El tooltip de Peg confirmado no explica fórmula y umbral")

    # Rounding modes and decimal-separator preference must be applied.
    window.base.setCurrentIndex(window.base.findData("EUR"))
    window.amount.setText("1")
    window.decimal_separator_mode = "currency"
    for mode, expected in (("0", "1"), ("1", "1.2"), ("2", "1.17")):
        window.rounding_mode = mode
        window._render()
        if window.cards["USD"].current_text != expected:
            raise RuntimeError(f"El modo de redondeo {mode} no se aplicó correctamente")

    window.rounding_mode = "2"
    window.decimal_separator_mode = "comma"
    window.amount.setText("4000")
    window._render()
    displayed = window.cards["USD"].current_text
    if displayed != "4.680":
        raise RuntimeError(f"La visualización con coma no elimina ,00 correctamente: {displayed!r}")
    window._copy_card_value("USD")
    copied = QApplication.clipboard().text()
    if copied != "4680":
        raise RuntimeError(f"Copiar debe eliminar agrupación y ,00 cuando la fracción es cero: {copied!r}")

    window.decimal_separator_mode = "dot"
    window._render()
    if window.cards["USD"].current_text != "4,680":
        raise RuntimeError("La visualización con punto no elimina .00 correctamente")
    window._copy_card_value("USD")
    if QApplication.clipboard().text() != "4680":
        raise RuntimeError("La copia con separador decimal punto debe eliminar .00")

    # Zero-minor-unit currencies must never display artificial decimals.
    window.rounding_mode = "2"
    window.decimal_separator_mode = "currency"
    window.amount.setText("1")
    window._render()
    jpy_card = window.cards.get("JPY")
    if jpy_card is None:
        raise RuntimeError(f"El smoke test necesita JPY visible para comprobar sus decimales; tarjetas presentes: {sorted(window.cards)}")
    if "," in jpy_card.current_text or "." in jpy_card.current_text:
        raise RuntimeError("JPY mostró decimales aunque ISO 4217 no define unidad fraccionaria")

    # Exact .00/,00 is hidden by default, but can be explicitly preserved for
    # both display and clipboard output.
    window.base.setCurrentIndex(window.base.findData("EUR"))
    window.amount.setText("100")
    window.rounding_mode = "2"
    window.decimal_separator_mode = "comma"
    window.keep_zero_fraction = False
    window._render()
    if window.cards["EUR"].current_text != "100":
        raise RuntimeError("Los ceros decimales exactos no se ocultan por defecto")
    window.keep_zero_fraction = True
    window._render()
    if window.cards["EUR"].current_text != "100,00":
        raise RuntimeError("La opción de conservar ceros no muestra ,00 en pantalla")
    if fmt_currency_copy(100.0, "EUR", "2", "comma", keep_zero_fraction=True) != "100,00":
        raise RuntimeError("La opción de conservar ceros no mantiene ,00 al copiar")
    window.keep_zero_fraction = False

    # Verify that explicit language and rounding choices survive a settings round-trip.
    save_preferences(
        ["EUR", "USD"], {"EUR", "USD"}, ["Principales", "Otras"],
        {"EUR": "Principales", "USD": "Principales"}, {"Principales": "#445566", "Otras": "#665544"},
        "en", "code", True, "1", "dot", "after", "before_code", "issues", True, {"ARS", "PEN"},
    )
    loaded = load_preferences()
    if loaded[5] != "en" or loaded[7] is not True:
        raise RuntimeError("La selección manual de idioma no se guardó correctamente")
    if loaded[8] != "1":
        raise RuntimeError("La opción de redondeo no se guardó correctamente")
    if loaded[9] != "dot":
        raise RuntimeError("El separador decimal no se guardó correctamente")
    if loaded[4].get("Principales") != "#445566":
        raise RuntimeError("El color personalizado de grupo no se guardó correctamente")
    if loaded[10] != "after":
        raise RuntimeError("La posición de la bandera no se guardó correctamente")
    if loaded[11] != "before_code":
        raise RuntimeError("La posición del símbolo no se guardó correctamente")
    if loaded[12] != "issues":
        raise RuntimeError("La opción de visibilidad de comprobación no se guardó correctamente")
    if loaded[13] is not True:
        raise RuntimeError("La opción de conservar ceros decimales no se guardó correctamente")
    if loaded[14] != {"ARS", "PEN"}:
        raise RuntimeError("Las divisas hispanoamericanas opcionales no se guardaron correctamente")

    # Flag position must be switchable without rebuilding or losing the card.
    eur_card = window.cards.get("EUR")
    if eur_card is None:
        raise RuntimeError("El smoke test necesita EUR visible para comprobar la posición de la bandera")
    eur_card.set_flag_position("before")
    if eur_card.title_wrap.indexOf(eur_card.flag_label) != 0 or eur_card.unit_box.indexOf(eur_card.flag_label) >= 0:
        raise RuntimeError("La bandera no se colocó antes del código/nombre")
    eur_card.set_flag_position("after_code")
    if eur_card.title_wrap.indexOf(eur_card.flag_label) != 1 or eur_card.unit_box.indexOf(eur_card.flag_label) >= 0:
        raise RuntimeError("La bandera no se colocó justo después del código/nombre")
    eur_card.set_flag_position("after")
    for symbol_pos in ("before_all", "before_code", "after_code", "after"):
        eur_card.set_symbol_position(symbol_pos)

    if eur_card.unit_box.indexOf(eur_card.flag_label) < 0 or eur_card.title_wrap.indexOf(eur_card.flag_label) >= 0:
        raise RuntimeError("La bandera no se colocó después del símbolo")

    window.close()
    app.processEvents()
    print("SMOKE_TEST_OK")
    return 0


def main():
    smoke_test = "--smoke-test" in sys.argv
    if smoke_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        smoke_root = Path(tempfile.mkdtemp(prefix="currency-converter-smoke-"))
        os.environ["XDG_CONFIG_HOME"] = str(smoke_root / "config")
        os.environ["XDG_DATA_HOME"] = str(smoke_root / "data")

    _order, _visible, _group_order, _currency_groups, _group_colors, language, _label_mode, _language_manual, _rounding_mode, _decimal_separator_mode, _flag_position, _symbol_position, _verification_display_mode, _keep_zero_fraction, _latam_enabled = load_preferences()
    qt_argv = [arg for arg in sys.argv if arg != "--smoke-test"]
    app = QApplication(qt_argv)
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().with_name("icon.svg"))))
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Libre Kambio Currency")
    app.setApplicationVersion(APP_VERSION)
    app.setDesktopFileName("io.github.h2o7y.LibreKambioCurrency")

    try:
        if smoke_test:
            return run_smoke_test()

        instance_lock = SingleInstanceLock()
        if not instance_lock.acquire():
            QMessageBox.information(None, ui_text(language, "already_open_title"), ui_text(language, "already_open_text"))
            return 0
        app.aboutToQuit.connect(instance_lock.release)

        window = MainWindow(auto_refresh=True)
        window.show()
        return app.exec()
    except BaseException as exc:
        path = write_crash_log(exc)
        message = (
            f"The application could not start.\n\n{exc}\n\nDiagnostic log: {path}"
            if language == "en"
            else f"La aplicación no ha podido iniciarse.\n\n{exc}\n\nRegistro de diagnóstico: {path}"
        )
        if not smoke_test:
            try:
                QMessageBox.critical(None, APP_NAME, message)
            except Exception:
                pass
        print(message, file=sys.stderr)
        print("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
