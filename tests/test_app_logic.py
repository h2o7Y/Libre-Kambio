import unittest

from app_logic import (
    detect_system_language,
    parse_amount_text,
    resolve_language,
    sanitize_currency_state,
    unique_codes,
    alphabetical_codes,
    region_sorted_codes,
    currency_region_color,
    currency_region_name,
    normalize_verification_display_mode,
    strip_zero_fraction,
    REGION_BY_CODE,
    currency_minor_units,
    effective_rounding_decimals,
    normalize_rounding_mode,
    normalize_decimal_separator_mode,
    currency_decimal_separator,
)


class AmountParsingTests(unittest.TestCase):
    def test_empty_is_none(self):
        self.assertIsNone(parse_amount_text(""))

    def test_spaces_are_ignored(self):
        self.assertEqual(parse_amount_text(" 12 345,5 "), 12345.5)

    def test_decimal_comma(self):
        self.assertEqual(parse_amount_text("12,5"), 12.5)

    def test_decimal_dot(self):
        self.assertEqual(parse_amount_text("12.5"), 12.5)

    def test_spanish_grouping(self):
        self.assertEqual(parse_amount_text("1.234,56"), 1234.56)

    def test_english_grouping(self):
        self.assertEqual(parse_amount_text("1,234.56"), 1234.56)

    def test_negative_number(self):
        self.assertEqual(parse_amount_text("-15,25"), -15.25)

    def test_invalid_is_none(self):
        self.assertIsNone(parse_amount_text("abc"))

    def test_nan_is_rejected(self):
        self.assertIsNone(parse_amount_text("nan"))

    def test_positive_infinity_is_rejected(self):
        self.assertIsNone(parse_amount_text("inf"))

    def test_negative_infinity_is_rejected(self):
        self.assertIsNone(parse_amount_text("-inf"))

    def test_overflow_is_rejected(self):
        self.assertIsNone(parse_amount_text("1e9999"))


class LanguageTests(unittest.TestCase):
    def test_spanish_spain_is_spanish(self):
        self.assertEqual(detect_system_language({"LANG": "es_ES.UTF-8"}), "es")

    def test_spanish_latam_is_spanish(self):
        self.assertEqual(detect_system_language({"LANG": "es_MX.UTF-8"}), "es")

    def test_english_is_english(self):
        self.assertEqual(detect_system_language({"LANG": "en_GB.UTF-8"}), "en")

    def test_non_spanish_is_english(self):
        self.assertEqual(detect_system_language({"LANG": "de_DE.UTF-8"}), "en")

    def test_c_locale_is_english(self):
        self.assertEqual(detect_system_language({"LANG": "C"}), "en")

    def test_no_locale_is_english(self):
        self.assertEqual(detect_system_language({}), "en")

    def test_lc_all_has_priority(self):
        env = {"LC_ALL": "en_US.UTF-8", "LANG": "es_ES.UTF-8"}
        self.assertEqual(detect_system_language(env), "en")

    def test_manual_language_wins(self):
        self.assertEqual(resolve_language("es", True, {"LANG": "en_US.UTF-8"}), "es")

    def test_old_non_manual_setting_is_redetected(self):
        self.assertEqual(resolve_language("es", False, {"LANG": "fr_FR.UTF-8"}), "en")


class CurrencyStateTests(unittest.TestCase):
    def test_unique_codes_removes_duplicates_case_insensitive(self):
        self.assertEqual(unique_codes(["eur", "EUR", "usd", "USD"]), ["EUR", "USD"])

    def test_supported_currency_never_disappears_from_order(self):
        order, visible = sanitize_currency_state(
            ["EUR", "USD"], {"EUR", "USD"}, ["EUR", "USD", "JPY"], ["EUR", "USD", "JPY"]
        )
        self.assertEqual(order, ["EUR", "USD", "JPY"])
        self.assertEqual(visible, {"EUR", "USD"})

    def test_unknown_currency_is_removed_without_touching_visibility(self):
        order, visible = sanitize_currency_state(
            ["EUR", "FAKE", "USD"], {"EUR", "FAKE"}, ["EUR", "USD"], ["EUR", "USD"]
        )
        self.assertEqual(order, ["EUR", "USD"])
        self.assertEqual(visible, {"EUR"})

    def test_empty_visibility_uses_defaults(self):
        _, visible = sanitize_currency_state([], set(), ["EUR", "USD", "JPY"], ["EUR", "JPY"])
        self.assertEqual(visible, {"EUR", "JPY"})

    def test_refresh_does_not_uncheck_currency(self):
        supported = ["EUR", "USD", "JPY", "GBP"]
        order, visible = sanitize_currency_state(
            ["EUR", "JPY", "USD", "GBP"], {"EUR", "JPY", "GBP"}, supported, supported
        )
        # Network availability is intentionally not an input to this function.
        order2, visible2 = sanitize_currency_state(order, visible, supported, supported)
        self.assertEqual(order2, order)
        self.assertEqual(visible2, visible)


class RoundingTests(unittest.TestCase):
    def test_zero_minor_unit_currencies(self):
        for code in ("JPY", "KRW", "VND", "ISK"):
            self.assertEqual(currency_minor_units(code), 0, msg=code)

    def test_three_minor_unit_currencies(self):
        self.assertEqual(currency_minor_units("BHD"), 3)
        self.assertEqual(currency_minor_units("OMR"), 3)

    def test_zero_minor_unit_ignores_requested_decimals(self):
        for mode in ("auto", "0", "1", "2"):
            self.assertEqual(effective_rounding_decimals("JPY", mode), 0)

    def test_fixed_rounding_modes(self):
        self.assertEqual(effective_rounding_decimals("USD", "0"), 0)
        self.assertEqual(effective_rounding_decimals("USD", "1"), 1)
        self.assertEqual(effective_rounding_decimals("USD", "2"), 2)

    def test_auto_keeps_smart_format_for_fractional_currency(self):
        self.assertIsNone(effective_rounding_decimals("USD", "auto"))

    def test_legacy_two_decimal_setting_migrates(self):
        self.assertEqual(normalize_rounding_mode(None, True), "2")
        self.assertEqual(normalize_rounding_mode(None, False), "auto")




class DecimalSeparatorTests(unittest.TestCase):
    def test_explicit_comma_and_dot(self):
        self.assertEqual(currency_decimal_separator("GBP", "comma"), ",")
        self.assertEqual(currency_decimal_separator("EUR", "dot"), ".")

    def test_currency_mode_common_conventions(self):
        self.assertEqual(currency_decimal_separator("EUR", "currency"), ",")
        self.assertEqual(currency_decimal_separator("GBP", "currency"), ".")
        self.assertEqual(currency_decimal_separator("USD", "currency"), ".")
        self.assertEqual(currency_decimal_separator("BRL", "currency"), ",")

    def test_invalid_mode_falls_back_to_currency(self):
        self.assertEqual(normalize_decimal_separator_mode("bad"), "currency")

class RegionTests(unittest.TestCase):
    def test_common_region_labels(self):
        self.assertEqual(currency_region_name("EUR", "es"), "Europa Occidental")
        self.assertEqual(currency_region_name("JPY", "en"), "East Asia")
        self.assertEqual(currency_region_name("AED", "es"), "Oriente Medio y Golfo")
        self.assertEqual(currency_region_name("BRL", "es"), "América Centro y Sur")
        self.assertEqual(currency_region_name("CUP", "es"), "América del Norte")

    def test_region_colours_are_defined(self):
        self.assertTrue(currency_region_color("EUR").startswith("#"))
        self.assertNotEqual(currency_region_color("EUR"), currency_region_color("AED"))

    def test_same_region_always_has_same_colour(self):
        for codes in [
            ["EUR", "GBP", "PLN", "SEK", "CZK"],
            ["JPY", "CNY", "HKD", "KRW", "MNT"],
            ["AED", "SAR", "TRY", "BHD", "QAR", "OMR"],
            ["USD", "CAD", "MXN", "CUP"],
        ]:
            colours = {currency_region_color(code) for code in codes}
            self.assertEqual(len(colours), 1, msg=codes)

    def test_cuba_is_classified_in_north_america_family(self):
        self.assertEqual(REGION_BY_CODE["CUP"], "north_america")

    def test_europe_uses_green_family(self):
        self.assertEqual(currency_region_color("EUR"), "#275d3d")
        self.assertEqual(currency_region_color("RUB"), "#2f7a50")

    def test_asian_regions_use_warm_family_except_central_asia(self):
        warm = {
            currency_region_color("AED"),
            currency_region_color("JPY"),
            currency_region_color("INR"),
            currency_region_color("THB"),
        }
        self.assertEqual(warm, {"#6e675d", "#b58116", "#d17912", "#9f8b1f"})
        self.assertEqual(currency_region_color("KZT"), "#59616d")

    def test_american_regions_use_related_colour_family(self):
        self.assertEqual(currency_region_color("USD"), "#a34e82")
        self.assertEqual(currency_region_color("BRL"), "#8d3f5f")

    def test_africa_uses_brown_family(self):
        self.assertEqual(currency_region_color("ZAR"), "#6b4423")

    def test_alphabetical_codes_are_iso_sorted_without_duplicates(self):
        self.assertEqual(alphabetical_codes(["usd", "EUR", "aed", "USD"]), ["AED", "EUR", "USD"])

    def test_region_sort_groups_regions_then_iso_code(self):
        ordered = region_sorted_codes(["JPY", "EUR", "AED", "GBP", "CNY", "SAR", "USD"])
        self.assertEqual(ordered, ["EUR", "GBP", "AED", "SAR", "CNY", "JPY", "USD"])

    def test_all_current_app_currency_codes_have_explicit_region(self):
        expected = {
            "EUR", "JPY", "GBP", "PLN", "SEK", "TRY", "USD", "CZK", "AED", "SAR", "RUB", "UAH",
            "AUD", "BRL", "CAD", "CHF", "CNY", "DKK", "HKD", "HUF", "IDR", "ILS", "INR", "ISK",
            "KRW", "MXN", "MYR", "NOK", "NZD", "PHP", "RON", "SGD", "THB", "ZAR", "AZN", "DZD",
            "AMD", "BHD", "BYN", "BOB", "VND", "EGP", "IRR", "QAR", "CUP", "MMK", "GEL", "MDL",
            "NGN", "TMT", "OMR", "RSD", "KGS", "TJS", "BDT", "KZT", "MNT", "UZS", "ETB",
        }
        self.assertTrue(expected.issubset(REGION_BY_CODE.keys()))


class DisplayPolicyTests(unittest.TestCase):
    def test_zero_fraction_is_removed_for_comma_decimal(self):
        self.assertEqual(strip_zero_fraction("55.400,00", ","), "55.400")
        self.assertEqual(strip_zero_fraction("55.400,50", ","), "55.400,50")

    def test_zero_fraction_is_removed_for_point_decimal(self):
        self.assertEqual(strip_zero_fraction("55,400.00", "."), "55,400")
        self.assertEqual(strip_zero_fraction("55,400.50", "."), "55,400.50")

    def test_verification_display_mode_normalizes(self):
        self.assertEqual(normalize_verification_display_mode("issues"), "issues")
        self.assertEqual(normalize_verification_display_mode("always"), "always")
        self.assertEqual(normalize_verification_display_mode("nonsense"), "always")



class LatinAmericaDisplayTests(unittest.TestCase):
    def test_optional_latam_currencies_use_central_south_america_region(self):
        for code in ("ARS", "CLP", "COP", "PYG", "PEN", "UYU"):
            self.assertEqual(REGION_BY_CODE[code], "latin_america")

    def test_clp_and_pyg_have_no_decimal_minor_unit(self):
        self.assertEqual(currency_minor_units("CLP"), 0)
        self.assertEqual(currency_minor_units("PYG"), 0)

    def test_optional_latam_currency_decimal_convention_uses_comma(self):
        for code in ("ARS", "CLP", "COP", "PYG", "PEN", "UYU"):
            self.assertEqual(currency_decimal_separator(code, "currency"), ",")

if __name__ == "__main__":
    unittest.main()
