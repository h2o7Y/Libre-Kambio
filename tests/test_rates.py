import json
import unittest
from unittest.mock import patch

from rates import (
    AED_USD_PEG,
    SAR_USD_PEG,
    QAR_USD_PEG,
    BHD_USD_PEG,
    OMR_USD_PEG,
    RatesSnapshot,
    cbr_peg_value,
    convert,
    parse_cbr_last_updated_html,
    parse_cbr_xml,
    parse_ecb_xml,
    verification,
    percent_difference,
    cbr_cross_units_per_eur,
    _merge_snapshot,
    primary_source_for,
    _apply_latam_extras,
)
from latam_rates import LatamRate, LatamPublicationError

ECB_SAMPLE = b'''<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
<Cube><Cube time="2026-08-20"><Cube currency="USD" rate="1.1700"/><Cube currency="JPY" rate="185.00"/><Cube currency="PLN" rate="4.31"/></Cube></Cube>
</gesmes:Envelope>'''

CBR_PAGE_SAMPLE = b'''<html><body><div>Last updated on: 20.08.2026</div></body></html>'''

CBR_SAMPLE = b'''<?xml version="1.0" encoding="windows-1251"?>
<ValCurs Date="21.08.2026" name="Foreign Currency Market">
<Valute ID="R01235"><NumCode>840</NumCode><CharCode>USD</CharCode><Nominal>1</Nominal><Name>US Dollar</Name><Value>85,1293</Value></Valute>
<Valute ID="R01239"><NumCode>978</NumCode><CharCode>EUR</CharCode><Nominal>1</Nominal><Name>Euro</Name><Value>98,5457</Value></Valute>
<Valute ID="R01230"><NumCode>784</NumCode><CharCode>AED</CharCode><Nominal>1</Nominal><Name>UAE Dirham</Name><Value>23,1802</Value></Valute>
<Valute ID="R01240"><NumCode>682</NumCode><CharCode>SAR</CharCode><Nominal>1</Nominal><Name>Saudi Riyal</Name><Value>22,7011</Value></Valute>
<Valute ID="R00000"><NumCode>048</NumCode><CharCode>BHD</CharCode><Nominal>1</Nominal><Name>Bahraini Dinar</Name><Value>226,35</Value></Valute>
<Valute ID="R00001"><NumCode>634</NumCode><CharCode>QAR</CharCode><Nominal>1</Nominal><Name>Qatari Riyal</Name><Value>23,3872</Value></Valute>
<Valute ID="R00002"><NumCode>512</NumCode><CharCode>OMR</CharCode><Nominal>1</Nominal><Name>Omani Rial</Name><Value>221,38</Value></Valute>
<Valute ID="R01370"><NumCode>985</NumCode><CharCode>PLN</CharCode><Nominal>1</Nominal><Name>Polish Zloty</Name><Value>22,8170</Value></Valute>
<Valute ID="R01720"><NumCode>980</NumCode><CharCode>UAH</CharCode><Nominal>10</Nominal><Name>Hryvnia</Name><Value>18,6834</Value></Valute>
</ValCurs>'''


class RatesTests(unittest.TestCase):
    def snapshot(self):
        ecb, ecb_date = parse_ecb_xml(ECB_SAMPLE)
        cbr, cbr_date = parse_cbr_xml(CBR_SAMPLE)
        rates = dict(ecb)
        rates["AED"] = rates["USD"] * AED_USD_PEG
        rates["SAR"] = rates["USD"] * SAR_USD_PEG
        rates["RUB"] = cbr["EUR"]
        rates["UAH"] = cbr["EUR"] / cbr["UAH"]
        return RatesSnapshot(rates, ecb, cbr, ecb_date, cbr_date, "2026-08-20", "x", [])

    def test_ecb_parser(self):
        rates, date = parse_ecb_xml(ECB_SAMPLE)
        self.assertEqual(date, "2026-08-20")
        self.assertEqual(rates["USD"], 1.17)

    def test_cbr_parser_nominal(self):
        rates, date = parse_cbr_xml(CBR_SAMPLE)
        self.assertEqual(date, "2026-08-21")
        self.assertAlmostEqual(rates["USD"], 85.1293)

    def test_cbr_publication_date_parser(self):
        self.assertEqual(parse_cbr_last_updated_html(CBR_PAGE_SAMPLE), "2026-08-20")

    def test_conversion(self):
        s = self.snapshot()
        self.assertAlmostEqual(convert(1.0, "EUR", "AED", s), 1.17 * AED_USD_PEG)
        self.assertAlmostEqual(convert(100.0, "AED", "EUR", s), 100.0 / (1.17 * AED_USD_PEG))

    def test_peg_cross_check(self):
        s = self.snapshot()
        self.assertAlmostEqual(cbr_peg_value("AED", s), AED_USD_PEG, places=4)
        self.assertAlmostEqual(cbr_peg_value("SAR", s), SAR_USD_PEG, places=4)
        self.assertEqual(verification("AED", s)["status"], "Peg confirmado")
        self.assertEqual(verification("SAR", s)["status"], "Peg confirmado")

    def test_date_gap_is_explicit(self):
        s = self.snapshot()
        result = verification("PLN", s)
        self.assertEqual(result["date_gap_days"], 1)
        self.assertEqual(result["date_note"], "CBR +1 día")

    def test_cbr_uah_nominal_and_conversion(self):
        s = self.snapshot()
        # CBR sample quotes 10 UAH, parser normalizes to RUB per 1 UAH.
        self.assertAlmostEqual(s.cbr_rub_per_unit["UAH"], 1.86834)
        self.assertAlmostEqual(s.rates_per_eur["UAH"], 98.5457 / 1.86834)
        self.assertAlmostEqual(convert(1.0, "EUR", "UAH", s), 98.5457 / 1.86834)

    def test_eur_rub_and_uah_are_not_fake_cross_checks(self):
        s = self.snapshot()
        self.assertEqual(verification("EUR", s)["status"], "Sin segunda fuente")
        self.assertEqual(verification("RUB", s)["status"], "Sin segunda fuente")
        self.assertEqual(verification("UAH", s)["status"], "Sin segunda fuente")

    def test_cache_load_marks_sources_as_cached(self):
        s = self.snapshot()
        raw = s.to_json()
        loaded = RatesSnapshot.from_json(raw)
        self.assertTrue(loaded.ecb_cached)
        self.assertTrue(loaded.cbr_cached)
        self.assertTrue(loaded.cbr_published_cached)

    def test_percent_difference_is_symmetric(self):
        self.assertAlmostEqual(percent_difference(100.0, 101.0), percent_difference(101.0, 100.0))

    def test_percent_difference_zero(self):
        self.assertEqual(percent_difference(0.0, 0.0), 0.0)

    def test_cbr_cross_check_for_pln(self):
        s = self.snapshot()
        expected = s.cbr_rub_per_unit["EUR"] / s.cbr_rub_per_unit["PLN"]
        self.assertAlmostEqual(cbr_cross_units_per_eur("PLN", s), expected)

    def test_cbr_cross_check_missing_currency_returns_none(self):
        self.assertIsNone(cbr_cross_units_per_eur("GBP", self.snapshot()))

    def test_invalid_ecb_xml_raises(self):
        with self.assertRaises(Exception):
            parse_ecb_xml(b"<bad")

    def test_empty_ecb_rates_raise(self):
        with self.assertRaises(ValueError):
            parse_ecb_xml(b'<gesmes:Envelope xmlns:gesmes="x"><Cube time="2026-08-20"/></gesmes:Envelope>')

    def test_invalid_cbr_xml_raises(self):
        with self.assertRaises(Exception):
            parse_cbr_xml(b"<bad")

    def test_empty_cbr_rates_raise(self):
        with self.assertRaises(ValueError):
            parse_cbr_xml(b'<ValCurs Date="21.08.2026"></ValCurs>')

    def test_missing_cbr_publication_date_returns_none(self):
        self.assertIsNone(parse_cbr_last_updated_html(b"<html>No date here</html>"))

    def test_merge_uses_previous_ecb_when_fetch_fails(self):
        prev = self.snapshot()
        merged = _merge_snapshot(
            None, None, prev.cbr_rub_per_unit, prev.cbr_date, prev.cbr_published_date, ["BCE: offline"], prev,
            ecb_fetch_ok=False, cbr_fetch_ok=True, cbr_publication_fetch_ok=True,
        )
        self.assertTrue(merged.ecb_cached)
        self.assertEqual(merged.ecb_date, prev.ecb_date)
        self.assertEqual(merged.rates_per_eur["USD"], prev.rates_per_eur["USD"])

    def test_merge_uses_previous_cbr_when_fetch_fails(self):
        prev = self.snapshot()
        merged = _merge_snapshot(
            prev.ecb_rates_per_eur, prev.ecb_date, None, None, None, ["CBR: offline"], prev,
            ecb_fetch_ok=True, cbr_fetch_ok=False, cbr_publication_fetch_ok=False,
        )
        self.assertTrue(merged.cbr_cached)
        self.assertEqual(merged.cbr_date, prev.cbr_date)
        self.assertEqual(merged.rates_per_eur["RUB"], prev.rates_per_eur["RUB"])

    def test_cached_cbr_never_pairs_with_new_publication_date(self):
        prev = self.snapshot()
        merged = _merge_snapshot(
            prev.ecb_rates_per_eur, prev.ecb_date, None, None, "2026-08-22", [], prev,
            ecb_fetch_ok=True, cbr_fetch_ok=False, cbr_publication_fetch_ok=True,
        )
        self.assertEqual(merged.cbr_published_date, prev.cbr_published_date)
        self.assertTrue(merged.cbr_published_cached)

    def test_missing_usd_stops_usd_and_peg_calculations_without_crashing_app(self):
        merged = _merge_snapshot(
            {"EUR": 1.0, "JPY": 185.0}, "2026-08-20", {}, None, None, [], None,
            ecb_fetch_ok=True, cbr_fetch_ok=False, cbr_publication_fetch_ok=False,
        )
        self.assertNotIn("USD", merged.rates_per_eur)
        for code in ("AED", "SAR", "QAR", "BHD", "OMR"):
            self.assertNotIn(code, merged.rates_per_eur)
        self.assertEqual(merged.source_missing["USD"], "ECB")
        for code in ("AED", "SAR", "QAR", "BHD", "OMR"):
            self.assertEqual(merged.source_missing[code], "ECB")

    def test_merge_derives_cbr_only_currency(self):
        ecb, ecb_date = parse_ecb_xml(ECB_SAMPLE)
        cbr, cbr_date = parse_cbr_xml(CBR_SAMPLE)
        merged = _merge_snapshot(
            ecb, ecb_date, cbr, cbr_date, "2026-08-20", [], None,
            ecb_fetch_ok=True, cbr_fetch_ok=True, cbr_publication_fetch_ok=True,
        )
        self.assertIn("UAH", merged.rates_per_eur)
        self.assertAlmostEqual(merged.rates_per_eur["UAH"], cbr["EUR"] / cbr["UAH"])
        self.assertEqual(verification("UAH", merged)["status"], "Sin segunda fuente")
        self.assertIsNone(cbr_cross_units_per_eur("UAH", merged))

    def test_fresh_ecb_omission_is_not_backfilled_from_cbr(self):
        prev = self.snapshot()
        ecb = dict(prev.ecb_rates_per_eur)
        ecb["AUD"] = 1.80
        prev.rates_per_eur["AUD"] = 1.80
        cbr = dict(prev.cbr_rub_per_unit)
        cbr["AUD"] = 60.0
        fresh_ecb = {k: v for k, v in ecb.items() if k != "AUD"}
        merged = _merge_snapshot(
            fresh_ecb, "2026-08-21", cbr, "2026-08-21", "2026-08-20", [], prev,
            ecb_fetch_ok=True, cbr_fetch_ok=True, cbr_publication_fetch_ok=True,
        )
        self.assertNotIn("AUD", merged.rates_per_eur)
        self.assertEqual(merged.source_missing.get("AUD"), "ECB")

    def test_fresh_cbr_omission_does_not_reuse_old_cbr_only_rate(self):
        prev = self.snapshot()
        prev.rates_per_eur["UAH"] = 50.0
        cbr = {k: v for k, v in prev.cbr_rub_per_unit.items() if k != "UAH"}
        merged = _merge_snapshot(
            prev.ecb_rates_per_eur, "2026-08-21", cbr, "2026-08-21", "2026-08-20", [], prev,
            ecb_fetch_ok=True, cbr_fetch_ok=True, cbr_publication_fetch_ok=True,
        )
        self.assertNotIn("UAH", merged.rates_per_eur)
        self.assertEqual(merged.source_missing.get("UAH"), "CBR")

    def test_cbr_network_failure_may_use_last_successful_cached_rate(self):
        prev = self.snapshot()
        merged = _merge_snapshot(
            prev.ecb_rates_per_eur, "2026-08-21", None, None, None, ["CBR offline"], prev,
            ecb_fetch_ok=True, cbr_fetch_ok=False, cbr_publication_fetch_ok=False,
        )
        self.assertIn("UAH", merged.rates_per_eur)
        self.assertTrue(merged.cbr_cached)

    def test_source_missing_survives_cache_serialization(self):
        s = self.snapshot()
        s.source_missing = {"AUD": "ECB", "UAH": "CBR"}
        loaded = RatesSnapshot.from_json(s.to_json())
        self.assertEqual(loaded.source_missing, s.source_missing)


    def test_additional_usd_pegs_are_calculated_from_ecb_usd(self):
        ecb = {"EUR": 1.0, "USD": 1.2}
        cbr = {"EUR": 100.0, "USD": 84.0, "QAR": 84.0 / QAR_USD_PEG, "BHD": 84.0 / BHD_USD_PEG, "OMR": 84.0 / OMR_USD_PEG}
        merged = _merge_snapshot(
            ecb, "2026-08-21", cbr, "2026-08-21", "2026-08-20", [], None,
            ecb_fetch_ok=True, cbr_fetch_ok=True, cbr_publication_fetch_ok=True,
        )
        self.assertAlmostEqual(merged.rates_per_eur["QAR"], 1.2 * QAR_USD_PEG)
        self.assertAlmostEqual(merged.rates_per_eur["BHD"], 1.2 * BHD_USD_PEG)
        self.assertAlmostEqual(merged.rates_per_eur["OMR"], 1.2 * OMR_USD_PEG)


    def test_cbr_omission_does_not_disable_usd_peg_currency(self):
        ecb = {"EUR": 1.0, "USD": 1.2}
        cbr = {"EUR": 100.0, "USD": 84.0}  # QAR deliberately omitted from CBR
        merged = _merge_snapshot(
            ecb, "2026-08-21", cbr, "2026-08-21", "2026-08-20", [], None,
            ecb_fetch_ok=True, cbr_fetch_ok=True, cbr_publication_fetch_ok=True,
        )
        self.assertAlmostEqual(merged.rates_per_eur["QAR"], 1.2 * QAR_USD_PEG)
        self.assertNotIn("QAR", merged.source_missing)
        self.assertIsNone(cbr_peg_value("QAR", merged))

    def test_additional_pegs_use_ecb_as_primary_source(self):
        for code in ("QAR", "BHD", "OMR"):
            self.assertEqual(primary_source_for(code), "ECB")

    def test_additional_pegs_can_be_cross_checked_with_cbr(self):
        snapshot = RatesSnapshot(
            rates_per_eur={"EUR": 1.0, "USD": 1.2, "QAR": 4.368},
            ecb_rates_per_eur={"EUR": 1.0, "USD": 1.2},
            cbr_rub_per_unit={"EUR": 100.0, "USD": 84.0, "QAR": 84.0 / QAR_USD_PEG},
            ecb_date="2026-08-21", cbr_date="2026-08-21", cbr_published_date="2026-08-20",
            fetched_at="2026-08-21T00:00:00+00:00", errors=[]
        )
        v = verification("QAR", snapshot)
        self.assertEqual(v["status"], "Peg confirmado")
        self.assertAlmostEqual(v["peg_expected"], QAR_USD_PEG)

    def test_primary_source_policy(self):
        self.assertEqual(primary_source_for("AUD"), "ECB")
        self.assertEqual(primary_source_for("UAH"), "CBR")
        self.assertEqual(primary_source_for("AED"), "ECB")
        self.assertEqual(primary_source_for("XDR"), "")

    def test_round_trip_conversion_is_stable(self):
        s = self.snapshot()
        for code in ["EUR", "USD", "JPY", "PLN", "AED", "SAR", "RUB", "UAH"]:
            if code not in s.rates_per_eur:
                continue
            converted = convert(123.456, "EUR", code, s)
            back = convert(converted, code, "EUR", s)
            self.assertAlmostEqual(back, 123.456, places=9, msg=code)



class OptionalLatamRatesTests(unittest.TestCase):
    def base_snapshot(self):
        return RatesSnapshot(
            rates_per_eur={"EUR": 1.0, "USD": 1.2},
            ecb_rates_per_eur={"EUR": 1.0, "USD": 1.2},
            cbr_rub_per_unit={"RUB": 1.0, "EUR": 100.0, "USD": 83.0},
            ecb_date="2026-08-20", cbr_date="2026-08-21", cbr_published_date="2026-08-20",
            fetched_at="x", errors=[],
        )

    @patch("rates.fetch_bcb_rates", return_value=({"ARS": 1490.0}, "2026-08-20"))
    @patch("rates.fetch_latam_rate", return_value=LatamRate("ARS", 1500.0, "2026-08-20", "BCRA"))
    def test_enabled_latam_uses_local_official_rate_and_bcb_cross_check(self, _local, _bcb):
        s = self.base_snapshot()
        errors = []
        _apply_latam_extras(s, {"ARS"}, None, errors)
        self.assertEqual(errors, [])
        self.assertAlmostEqual(s.rates_per_eur["ARS"], 1800.0)
        self.assertAlmostEqual(s.bcb_units_per_usd["ARS"], 1490.0)
        self.assertEqual(s.latam_fetch_status["ARS"], "fresh")
        self.assertEqual(s.bcb_fetch_status, "fresh")
        v = verification("ARS", s)
        self.assertTrue(v["latam_extra"])
        self.assertEqual(v["primary_label"], "BCRA")
        self.assertEqual(v["check_source"], "BCB")
        self.assertAlmostEqual(v["cross"], 1788.0)

    @patch("rates.fetch_latam_rate")
    @patch("rates.fetch_bcb_rates")
    def test_disabled_latam_does_not_fetch_or_enter_rates(self, bcb, local):
        s = self.base_snapshot()
        _apply_latam_extras(s, set(), None, [])
        local.assert_not_called()
        bcb.assert_not_called()
        self.assertNotIn("ARS", s.rates_per_eur)
        self.assertEqual(s.latam_units_per_usd, {})

    @patch("rates.fetch_bcb_rates", side_effect=OSError("offline"))
    @patch("rates.fetch_latam_rate", side_effect=OSError("offline"))
    def test_latam_source_failure_uses_cached_value_and_marks_it_cached(self, _local, _bcb):
        previous = self.base_snapshot()
        previous.latam_units_per_usd = {"ARS": 1480.0}
        previous.latam_dates = {"ARS": "2026-08-19"}
        previous.latam_sources = {"ARS": "BCRA"}
        previous.bcb_units_per_usd = {"ARS": 1475.0}
        previous.bcb_date = "2026-08-19"
        s = self.base_snapshot()
        errors = []
        _apply_latam_extras(s, {"ARS"}, previous, errors)
        self.assertIn("ARS", s.latam_cached_codes)
        self.assertEqual(s.latam_fetch_status["ARS"], "cached")
        self.assertTrue(s.bcb_cached)
        self.assertEqual(s.bcb_fetch_status, "cached")
        self.assertAlmostEqual(s.rates_per_eur["ARS"], 1776.0)
        self.assertTrue(errors)

    @patch("rates.fetch_bcb_rates", side_effect=OSError("offline"))
    @patch("rates.fetch_latam_rate", side_effect=OSError("offline"))
    def test_latam_source_failure_without_cache_marks_source_missing(self, _local, _bcb):
        s = self.base_snapshot()
        _apply_latam_extras(s, {"ARS"}, None, [])
        self.assertEqual(s.source_missing.get("ARS"), "BCRA")
        self.assertEqual(s.latam_fetch_status["ARS"], "error")
        self.assertEqual(s.bcb_fetch_status, "error")
        self.assertNotIn("ARS", s.rates_per_eur)


    @patch("rates.fetch_bcb_rates", return_value=({}, None))
    @patch("rates.fetch_latam_rate", side_effect=LatamPublicationError("rate absent"))
    def test_fresh_optional_publication_without_rate_does_not_reuse_cache(self, _local, _bcb):
        previous = self.base_snapshot()
        previous.latam_units_per_usd = {"ARS": 1480.0}
        previous.latam_dates = {"ARS": "2026-08-19"}
        previous.latam_sources = {"ARS": "BCRA"}
        s = self.base_snapshot()
        _apply_latam_extras(s, {"ARS"}, previous, [])
        self.assertEqual(s.source_missing.get("ARS"), "BCRA")
        self.assertEqual(s.latam_fetch_status["ARS"], "missing")
        self.assertNotIn("ARS", s.rates_per_eur)
        self.assertNotIn("ARS", s.latam_cached_codes)

    def test_latam_primary_source_policy(self):
        self.assertEqual(primary_source_for("ARS"), "BCRA")
        self.assertEqual(primary_source_for("CLP"), "BCCh")
        self.assertEqual(primary_source_for("COP"), "BanRep")
        self.assertEqual(primary_source_for("PYG"), "BCP")
        self.assertEqual(primary_source_for("PEN"), "BCRP")
        self.assertEqual(primary_source_for("UYU"), "BCU")

if __name__ == "__main__":
    unittest.main()
