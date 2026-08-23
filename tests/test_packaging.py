from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackagingPrivacyTests(unittest.TestCase):
    def test_no_user_settings_are_bundled(self):
        self.assertFalse(any(p.name == "settings.json" for p in ROOT.rglob("*")))

    def test_personal_group_name_is_not_shipped(self):
        forbidden = "musul" + "manes"
        textual_suffixes = {".py", ".md", ".json", ".xml", ".desktop", ".sh", ".txt"}
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in textual_suffixes:
                continue
            content = path.read_text(encoding="utf-8", errors="ignore").lower()
            self.assertNotIn(forbidden, content, msg=str(path))

    def test_default_groups_are_neutral(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('return ["Principales", "Golfo", "Europa Este", "Otras"]', main_source)

    def test_xdr_is_not_shipped_as_supported_currency(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertNotIn('"XDR": {', main_source)

    def test_management_views_are_forced_to_code_plus_name(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("def _management_currency_item", main_source)
        self.assertIn("{code} · {currency_name(code, self.language)}", main_source)

    def test_currency_region_is_a_separate_column(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("class OrganizerTable(QTableWidget)", main_source)
        self.assertIn('currency_item = QTableWidgetItem(self._management_currency_item(code) + missing_suffix)', main_source)
        self.assertIn('region_item.setForeground(QColor(currency_region_color(code)))', main_source)


    def test_currency_reorder_disables_native_qt_drag_drop(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        organizer = main_source[main_source.index("class OrganizerTable"):main_source.index("class CurrencyCard")]
        self.assertIn("setDragEnabled(False)", organizer)
        self.assertIn("setAcceptDrops(False)", organizer)
        self.assertIn("viewport().setAcceptDrops(False)", organizer)
        self.assertIn("DragDropMode.NoDragDrop", organizer)
        self.assertIn("def mouseMoveEvent", organizer)
        self.assertIn("def mouseReleaseEvent", organizer)
        self.assertNotIn("def startDrag", organizer)
        self.assertNotIn("def dropEvent", organizer)
        self.assertNotIn("def dropMimeData", organizer)
        self.assertNotIn("QTreeWidget", organizer)

    def test_currency_order_save_has_missing_currency_guard(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("missing_codes = [code for code in expected_codes if code not in clean_order]", main_source)
        self.assertIn("protected_visible.update", main_source)

    def test_currency_organizer_is_structurally_flat(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        organizer = main_source[main_source.index("class OrganizerTable"):main_source.index("class CurrencyCard")]
        self.assertIn("class OrganizerTable(QTableWidget)", organizer)
        self.assertIn("Native Qt item-view drag/drop is deliberately DISABLED", organizer)
        self.assertNotIn("QTreeWidgetItem", organizer)

    def test_currency_region_is_not_appended_to_currency_text(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertNotIn('self._management_currency_item(code)}    ·  {region}', main_source)

    def test_visible_app_name_is_libre_kambio(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        desktop = (ROOT / "io.github.h2o7y.LibreKambioCurrency.desktop").read_text(encoding="utf-8")
        self.assertIn('APP_NAME = "Libre Kambio"', main_source)
        self.assertIn('Name=Libre Kambio', desktop)


    def test_personal_github_id_and_no_legacy_brand_reference(self):
        textual_suffixes = {".py", ".md", ".json", ".xml", ".desktop", ".sh", ".txt"}
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in textual_suffixes:
                continue
            content = path.read_text(encoding="utf-8", errors="ignore").lower()
            self.assertNotIn("zen" + "shin", content, msg=str(path))
        manifest = (ROOT / "io.github.h2o7y.LibreKambioCurrency.json").read_text(encoding="utf-8")
        self.assertIn('"id": "io.github.h2o7y.LibreKambioCurrency"', manifest)

    def test_decimal_separator_options_and_copy_without_grouping(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('self.decimal_separator_combo.addItem("Según divisa/país", "currency")', main_source)
        self.assertIn('self.decimal_separator_combo.addItem("Coma (1.234,56)", "comma")', main_source)
        self.assertIn('self.decimal_separator_combo.addItem("Punto (1,234.56)", "dot")', main_source)
        self.assertIn('def fmt_currency_copy', main_source)
        self.assertIn('grouping=False', main_source)

    def test_options_expose_three_flag_positions(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('FLAG_POSITIONS = {"before", "after_code", "after"}', main_source)
        self.assertIn('self.flag_position_combo.addItem("Después del código (EUR 🇪🇺)", "after_code")', main_source)

    def test_options_expose_all_rounding_modes(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('"rounding": "Redondeo de resultados"', main_source)
        self.assertIn('self.rounding_combo.addItem("Sin decimales", "0")', main_source)
        self.assertIn('self.rounding_combo.addItem("1 decimal", "1")', main_source)
        self.assertIn('self.rounding_combo.addItem("2 decimales", "2")', main_source)
        self.assertIn('rounding_mode=self.rounding_mode', main_source)

    def test_rounding_respects_zero_minor_unit_currencies(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        logic_source = (ROOT / "app_logic.py").read_text(encoding="utf-8")
        self.assertIn('fmt_currency_amount', main_source)
        self.assertIn('ZERO_MINOR_UNIT_CODES', logic_source)
        self.assertIn('"JPY"', logic_source)

    def test_region_labels_use_requested_america_names(self):
        logic_source = (ROOT / "app_logic.py").read_text(encoding="utf-8")
        self.assertIn('"América Centro y Sur"', logic_source)
        self.assertIn('"CUP": "north_america"', logic_source)

    def test_groups_expose_region_sort_control(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("self.group_sort_combo", main_source)
        self.assertIn("region_sorted_codes", main_source)

    def test_groups_support_bulk_assignment(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("SelectionMode.ExtendedSelection", main_source)
        self.assertIn("def _apply_group_to_selected", main_source)
        self.assertIn("self.bulk_group_combo", main_source)
        self.assertIn("self.bulk_group_apply_btn", main_source)

    def test_converter_secondary_highlights_are_muted(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('border: 1px solid #486354', main_source)
        self.assertIn('border: 2px solid #65a9b7', main_source)
        self.assertIn('line_color = f"rgba({chosen.red()}, {chosen.green()}, {chosen.blue()}, 0.26)"', main_source)

    def test_group_colors_are_user_configurable_and_persisted(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("QColorDialog.getColor", main_source)
        self.assertIn('"group_colors": group_colors', main_source)
        self.assertIn("def _choose_selected_group_color", main_source)

    def test_bulk_group_controls_are_above_and_count_selection(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('"bulk_group_apply_count"', main_source)
        self.assertIn("itemSelectionChanged.connect(self._update_bulk_group_controls)", main_source)

    def test_currency_reorder_uses_explicit_organizer_signal(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("orderChanged = Signal()", main_source)
        self.assertIn("self.currency_list.orderChanged.connect(self._on_currency_rows_moved)", main_source)
        self.assertIn("def move_row", main_source)

    def test_language_refresh_regenerates_update_header(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("self._update_date_label()", main_source)

    def test_currency_rows_cannot_be_nested_by_widget_design(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        organizer = main_source.split("class OrganizerTable(QTableWidget):", 1)[1].split("class CurrencyCard", 1)[0]
        self.assertIn("self.setDragEnabled(False)", organizer)
        self.assertIn("self.setAcceptDrops(False)", organizer)
        self.assertIn("self.viewport().setAcceptDrops(False)", organizer)
        self.assertIn("self.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)", organizer)
        self.assertNotIn("QTreeWidget", organizer)

    def test_currency_drag_does_not_use_native_internal_move(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        organizer = main_source.split("class OrganizerTable(QTableWidget):", 1)[1].split("class CurrencyCard", 1)[0]
        self.assertIn("QAbstractItemView.DragDropMode.NoDragDrop", organizer)
        self.assertNotIn("QAbstractItemView.DragDropMode.DragDrop", organizer)
        self.assertNotIn("QAbstractItemView.DragDropMode.InternalMove", organizer)


    def test_group_reorder_disables_native_qt_drag_drop(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        organizer = main_source.split("class GroupOrganizerList(QListWidget):", 1)[1].split("class CurrencyCard", 1)[0]
        self.assertIn("self.setDragEnabled(False)", organizer)
        self.assertIn("self.setAcceptDrops(False)", organizer)
        self.assertIn("self.viewport().setAcceptDrops(False)", organizer)
        self.assertIn("QAbstractItemView.DragDropMode.NoDragDrop", organizer)
        self.assertIn("def mouseMoveEvent", organizer)
        self.assertIn("def mouseReleaseEvent", organizer)
        self.assertIn("def move_item", organizer)
        self.assertNotIn("QAbstractItemView.DragDropMode.InternalMove", organizer)

    def test_group_rows_cannot_be_drop_targets(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        population = main_source.split("def _populate_group_list", 1)[1].split("def _populate_group_assignments", 1)[0]
        self.assertIn("~Qt.ItemFlag.ItemIsDragEnabled", population)
        self.assertIn("~Qt.ItemFlag.ItemIsDropEnabled", population)
        self.assertNotIn("| Qt.ItemFlag.ItemIsDropEnabled", population)
        self.assertIn("self.group_list = GroupOrganizerList()", main_source)
        self.assertIn("self.group_list.orderChanged.connect(self._on_group_rows_moved)", main_source)


    def test_converter_exposes_symbol_position_option(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('SYMBOL_POSITIONS = {"before_all", "before_code", "after_code", "after"}', main_source)
        self.assertIn('self.symbol_position_combo', main_source)
        self.assertIn('def set_symbol_position', main_source)
        self.assertIn('"symbol_position": normalize_symbol_position(symbol_position)', main_source)

    def test_requested_subtitle_is_used(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('BCE (fuente principal) · Algunas peg USD · Banco de Rusia (+ divisas y comprobación cruzada para BCE y peg)', main_source)

    def test_converter_exposes_flag_position_option(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('"flag_position": "Posición de la bandera en Conversor"', main_source)
        self.assertIn('self.flag_position_combo.addItem("Antes del código / nombre", "before")', main_source)
        self.assertIn('self.flag_position_combo.addItem("Después del símbolo", "after")', main_source)
        self.assertIn('data.get("flag_position", "before")', main_source)
        self.assertIn('card.set_flag_position(self.flag_position)', main_source)

    def test_converter_can_hide_consistent_verification_badges(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('"verification_issues": "Solo avisos o problemas"', main_source)
        self.assertIn('self.verification_display_mode == "issues"', main_source)
        self.assertIn('verification_display_mode', main_source)

    def test_verification_dates_are_described_explicitly(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('CBR tipo oficial para:', main_source)
        self.assertIn('CBR official rate for:', main_source)

    def test_zero_fraction_option_is_exposed_and_defaults_to_hidden(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('"keep_zero_fraction", False', main_source)
        self.assertIn('"zero_fraction_hide": "Ocultar ,00 / .00 (predeterminado)"', main_source)
        self.assertIn('self.zero_fraction_combo.addItem("Mostrar y copiar ,00 / .00", True)', main_source)
        self.assertIn('keep_zero_fraction=self.keep_zero_fraction', main_source)

    def test_verification_date_tooltip_names_all_three_date_roles(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('BCE referencia:', main_source)
        self.assertIn('CBR tipo oficial para:', main_source)
        self.assertIn('(publicado {cbr_pub})', main_source)

    def test_empty_converter_cards_do_not_show_dash_placeholder(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('self.value = QLabel("")', main_source)
        self.assertIn('if amount is None:\n                card.value.setText("")', main_source)



    def test_option_labels_use_show_verbs_in_both_languages_and_no_stale_actual(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('"zero_fraction": "Mostrar ceros decimales exactos"', main_source)
        self.assertIn('"decimal_separator": "Mostrar separador decimal"', main_source)
        self.assertIn('"verification_display": "Mostrar comprobación en Conversor"', main_source)
        self.assertIn('"zero_fraction": "Show exact decimal zeros"', main_source)
        self.assertIn('"decimal_separator": "Show decimal separator"', main_source)
        self.assertIn('"verification_display": "Show verification in Converter"', main_source)
        self.assertNotIn('Al final (actual)', main_source)
        self.assertNotIn('At the end (current)', main_source)

    def test_optional_latam_currencies_are_individual_opt_in_controls(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        rates_source = (ROOT / "rates.py").read_text(encoding="utf-8")
        self.assertIn('LATAM_EXTRA_CODES', main_source)
        self.assertIn('self.latam_checkboxes', main_source)
        self.assertIn('latam_enabled = {code for code', main_source)
        self.assertIn('fetch_bcb_rates(enabled)', rates_source)
        self.assertIn('BCB (comprobación HISPAM)', rates_source)

    def test_optional_latam_currencies_are_not_in_base_supported_codes(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('BASE_SUPPORTED_CODES = _unique_codes(list(PRIMARY) + sorted(code for code in META.keys() if code not in LATAM_EXTRA_CODES))', main_source)

    def test_latam_rates_module_is_installed_in_flatpak(self):
        manifest = (ROOT / "io.github.h2o7y.LibreKambioCurrency.json").read_text(encoding="utf-8")
        build_script = (ROOT / "build-and-install-flatpak.sh").read_text(encoding="utf-8")
        self.assertIn('latam_rates.py', manifest)
        self.assertIn('install -Dm644 latam_rates.py', manifest)
        self.assertIn('py_compile main.py app_logic.py rates.py latam_rates.py', build_script)

    def test_smoke_test_forces_spanish_before_spanish_option_assertions(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        smoke = main_source.split("def run_smoke_test() -> int:", 1)[1]
        force_language = smoke.index('window.language = "es"')
        zero_check = smoke.index('window.zero_fraction_label.text().startswith("Mostrar")')
        self.assertLess(force_language, zero_check)
        self.assertIn("window._apply_language()", smoke[force_language:zero_check])

    def test_latam_source_download_state_is_visible_in_header_and_cards(self):
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        rates_source = (ROOT / "rates.py").read_text(encoding="utf-8")
        self.assertIn("def _latam_download_status_line", main_source)
        self.assertIn('"source_download_failed_short": "Descarga fallida"', main_source)
        self.assertIn('"source_download_failed_short": "Download failed"', main_source)
        self.assertIn("latam_fetch_status", rates_source)
        self.assertIn('fetch_status[code] = "missing"', rates_source)
        self.assertIn('fetch_status[code] = "error"', rates_source)
        self.assertIn("'latam_status_label': 'HISPAM'", main_source.replace('\"', "'"))
        self.assertIn("'latam_status_label': 'LATAM'", main_source.replace('\"', "'"))

if __name__ == "__main__":
    unittest.main()
