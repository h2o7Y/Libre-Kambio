import unittest

from latam_rates import (
    parse_bcra,
    parse_bcra_api,
    parse_bcra_series,
    parse_bcch,
    parse_banrep,
    parse_bcp,
    parse_bcrp_csv,
    parse_bcu,
    parse_bcu_soap,
    parse_bcb,
    PARSERS,
    BCCH_TABLE_URL,
    BCCH_TABLE_ALT_URL,
)


class LatamParserTests(unittest.TestCase):
    def test_bcra_a3500(self):
        data = b'''<html><body>Tipo de Cambio Mayorista ($ por USD) Comunicaci&oacute;n A 3500 - Referencia 11/08/2026 1.492,1790</body></html>'''
        r = parse_bcra(data)
        self.assertEqual(r.code, "ARS")
        self.assertAlmostEqual(r.units_per_usd, 1492.179)
        self.assertEqual(r.date, "2026-08-11")
        self.assertEqual(r.source, "BCRA")


    def test_bcra_v4_api_a3500(self):
        data = '''{"status":200,"results":[{"idVariable":5,"descripcion":"Tipo de Cambio Mayorista ($ por USD) Comunicaci\\u00f3n A 3500 - Referencia","periodicidad":"D","ultFechaInformada":"2026-08-21","ultValorInformado":1497.4321}]}'''.encode('ascii')
        r = parse_bcra_api(data)
        self.assertEqual(r.code, "ARS")
        self.assertAlmostEqual(r.units_per_usd, 1497.4321)
        self.assertEqual(r.date, "2026-08-21")
        self.assertEqual(r.source, "BCRA")


    def test_bcra_v4_catalog_discovers_a3500_without_fixed_id(self):
        data = '''{"status":200,"results":[{"idVariable":777,"descripcion":"Tipo de Cambio Mayorista ($ por USD) Comunicaci\u00f3n A 3500 - Referencia","categoria":"Principales Variables","periodicidad":"D","ultFechaInformada":"2026-08-21","ultValorInformado":1497.4321}]}'''.encode("utf-8")
        r = parse_bcra_api(data)
        self.assertEqual(r.code, "ARS")
        self.assertAlmostEqual(r.units_per_usd, 1497.4321)
        self.assertEqual(r.date, "2026-08-21")

    def test_bcra_v4_detailed_series_fallback(self):
        data = b'{"status":200,"results":[{"idVariable":5,"detalle":[{"fecha":"2026-08-20","valor":1495.1},{"fecha":"2026-08-21","valor":1497.4}]}]}'
        r = parse_bcra_series(data)
        self.assertEqual(r.code, "ARS")
        self.assertAlmostEqual(r.units_per_usd, 1497.4)
        self.assertEqual(r.date, "2026-08-21")

    def test_bcra_html_does_not_cross_into_unrelated_1993_base_date(self):
        data = b'''<html><body>
        Tipo de Cambio Mayorista ($ por USD) Comunicacion A 3500 - Referencia
        Otro contenido que no incluye la cotizacion actual.
        ''' + (b'x' * 400) + b'''
        Tasa de Intereses Moratorios (TIM) CCC, art. 768. Base 03/06/1993 (en %) 08/07/2026 157.900,5457
        </body></html>'''
        from latam_rates import LatamPublicationError
        with self.assertRaises(LatamPublicationError):
            parse_bcra(data)

    def test_bcch_dolar_observado(self):
        data = 'Período Valor (Pesos por Dólar) 18-ago-2026 914,19 17-ago-2026 913,15'.encode('utf-8')
        r = parse_bcch(data)
        self.assertEqual(r.code, "CLP")
        self.assertAlmostEqual(r.units_per_usd, 914.19)
        self.assertEqual(r.date, "2026-08-18")


    def test_bcch_current_single_series_latest_observation(self):
        data = b"Dolar observado Observaciones Unidad Frecuencia Codigo de serie 18.Ago.2026: 914,19 Actualizado: 17.Ago.2026"
        rate = parse_bcch(data)
        self.assertEqual(rate.code, "CLP")
        self.assertAlmostEqual(rate.units_per_usd, 914.19)
        self.assertEqual(rate.date, "2026-08-18")

    def test_bcch_current_daily_indicators_view(self):
        data = b"Indicadores diarios (18-ago-2026) Tipos de cambio Dolar observado 914,19 Pesos por Dolar"
        rate = parse_bcch(data)
        self.assertAlmostEqual(rate.units_per_usd, 914.19)
        self.assertEqual(rate.date, "2026-08-18")

    def test_bcch_current_bde_horizontal_table(self):
        data = "Serie 19.Ago.2026 20.Ago.2026 21.Ago.2026 24.Ago.2026 Dólar observado 922,12 920,26 923,23 918,17 Eliminar canasta".encode("utf-8")
        r = parse_bcch(data)
        self.assertEqual(r.code, "CLP")
        self.assertAlmostEqual(r.units_per_usd, 918.17)
        self.assertEqual(r.date, "2026-08-24")

    def test_bcch_live_full_bde_table_shape_august_22(self):
        # Exact shape exposed by the official full BDE table on 22/08/2026:
        # date headers are emitted first and the observed-dollar values follow.
        data = (
            "Tipos de cambio (pesos por dólar) Sel. Serie "
            "17.Ago.2026 18.Ago.2026 19.Ago.2026 20.Ago.2026 21.Ago.2026 24.Ago.2026 "
            "Dólar observado 913,15 914,19 922,12 920,26 923,23 918,17 "
            "Eliminar canasta"
        ).encode("utf-8")
        r = parse_bcch(data)
        self.assertEqual(r.code, "CLP")
        self.assertAlmostEqual(r.units_per_usd, 918.17)
        self.assertEqual(r.date, "2026-08-24")

    def test_bcch_full_bde_table_is_first_official_endpoint(self):
        self.assertEqual(PARSERS["CLP"][0][0], BCCH_TABLE_URL)
        self.assertEqual(PARSERS["CLP"][1][0], BCCH_TABLE_ALT_URL)

    def test_bcch_horizontal_table_keeps_nd_cell_alignment(self):
        data = (
            "Serie 20.Ago.2026 21.Ago.2026 22.Ago.2026 24.Ago.2026 "
            "Dólar observado 920,26 923,23 ND 918,17 Eliminar canasta"
        ).encode("utf-8")
        r = parse_bcch(data)
        self.assertAlmostEqual(r.units_per_usd, 918.17)
        self.assertEqual(r.date, "2026-08-24")

    def test_bcch_homepage_uses_explicit_next_dated_quote(self):
        data = "20 de agosto de 2026 Dólar Observado $920,26 /$923,23 (21 de agosto)".encode("utf-8")
        r = parse_bcch(data)
        self.assertAlmostEqual(r.units_per_usd, 923.23)
        self.assertEqual(r.date, "2026-08-21")


    def test_bcch_current_homepage_weekend_keeps_latest_business_day(self):
        data = "Programa operaciones 21 de agosto de 2026 UF $40.860,6 UTM $71.649,0 Dólar Observado $923,23 BEC Euro $1.077,66".encode("utf-8")
        r = parse_bcch(data)
        self.assertAlmostEqual(r.units_per_usd, 923.23)
        self.assertEqual(r.date, "2026-08-21")

    def test_bcch_english_bde_rendering(self):
        data = b"Nominal exchange rate Observed dollar Observations 17.Aug.2026: 913.15 14.Aug.2026: 913.20"
        r = parse_bcch(data)
        self.assertAlmostEqual(r.units_per_usd, 913.15)
        self.assertEqual(r.date, "2026-08-17")

    def test_bcch_windows_1252_does_not_lose_dolar_label(self):
        data = "21 de agosto de 2026 Dólar Observado $923,23".encode("cp1252")
        r = parse_bcch(data)
        self.assertAlmostEqual(r.units_per_usd, 923.23)
        self.assertEqual(r.date, "2026-08-21")

    def test_bcch_javascript_unicode_escape_label(self):
        data = br"21 de agosto de 2026 D\u00f3lar Observado $923,23"
        r = parse_bcch(data)
        self.assertAlmostEqual(r.units_per_usd, 923.23)
        self.assertEqual(r.date, "2026-08-21")

    def test_banrep_trm(self):
        data = 'Tasa de cambio representativa del mercado (TRM) 3.128,65 17/08/2026 Pesos por dólar'.encode('utf-8')
        r = parse_banrep(data)
        self.assertEqual(r.code, "COP")
        self.assertAlmostEqual(r.units_per_usd, 3128.65)
        self.assertEqual(r.date, "2026-08-17")

    def test_bcp_interbank_close(self):
        data = 'COTIZACIONES DEL 21 DE AGOSTO DE 2026 Cierre 21/08 6.009,15 6.003,76'.encode('utf-8')
        r = parse_bcp(data)
        self.assertEqual(r.code, "PYG")
        self.assertAlmostEqual(r.units_per_usd, 6009.15)
        self.assertEqual(r.date, "2026-08-21")

    def test_bcrp_interbank_average(self):
        data = b'19Ago26,3.34,3.35<br>20Ago26,3.35,3.36<br>'
        r = parse_bcrp_csv(data)
        self.assertEqual(r.code, "PEN")
        self.assertAlmostEqual(r.units_per_usd, 3.355)
        self.assertEqual(r.date, "2026-08-20")

    def test_bcrp_current_quoted_dotted_csv(self):
        data = 'Día/Mes/Año,"TC Interbancario Compra","TC Interbancario Venta"\n"19.Ago.26","3.34","3.35"\n"20.Ago.26","3.35","3.36"\n'.encode("latin-1")
        r = parse_bcrp_csv(data)
        self.assertEqual(r.code, "PEN")
        self.assertAlmostEqual(r.units_per_usd, 3.355)
        self.assertEqual(r.date, "2026-08-20")


    def test_bcu_official_soap_web_service(self):
        data = b'''<?xml version="1.0" encoding="utf-8"?>
        <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
          <SOAP-ENV:Body><wsbcucotizaciones.ExecuteResponse xmlns="Cotiza"><Salida>
            <respuestastatus><status>1</status><codigoerror>0</codigoerror><mensaje/></respuestastatus>
            <datoscotizaciones>
              <datoscotizaciones.dato><Fecha>2026-08-20</Fecha><Moneda>2222</Moneda><Nombre>DOLAR USA</Nombre><CodigoISO>USD</CodigoISO><TCC>40.182000</TCC><TCV>40.182000</TCV><ArbAct>1</ArbAct><FormaArbitrar>1</FormaArbitrar></datoscotizaciones.dato>
              <datoscotizaciones.dato><Fecha>2026-08-21</Fecha><Moneda>2222</Moneda><Nombre>DOLAR USA</Nombre><CodigoISO>USD</CodigoISO><TCC>40.250000</TCC><TCV>40.250000</TCV><ArbAct>1</ArbAct><FormaArbitrar>1</FormaArbitrar></datoscotizaciones.dato>
            </datoscotizaciones>
          </Salida></wsbcucotizaciones.ExecuteResponse></SOAP-ENV:Body>
        </SOAP-ENV:Envelope>'''
        r = parse_bcu_soap(data)
        self.assertEqual(r.code, "UYU")
        self.assertAlmostEqual(r.units_per_usd, 40.25)
        self.assertEqual(r.date, "2026-08-21")
        self.assertEqual(r.source, "BCU")

    def test_bcu_average_fund(self):
        data = 'DLS.PROMED.FONDO 07/08/2026 40,246 40,246 1'.encode('utf-8')
        r = parse_bcu(data)
        self.assertEqual(r.code, "UYU")
        self.assertAlmostEqual(r.units_per_usd, 40.246)
        self.assertEqual(r.date, "2026-08-07")


    def test_bcu_usd_billete_detailed_table_fallback(self):
        data = 'DLS. USA BILLETE 30/06/2026 40,116 40,116 1'.encode('utf-8')
        r = parse_bcu(data)
        self.assertEqual(r.code, "UYU")
        self.assertAlmostEqual(r.units_per_usd, 40.116)
        self.assertEqual(r.date, "2026-06-30")

    def test_bcu_official_homepage_quote(self):
        data = 'Cotizaciones cierre: 17/08/2026 US$ Billete 40,261 US$ Billete Euro 46,5941'.encode('utf-8')
        r = parse_bcu(data)
        self.assertEqual(r.code, "UYU")
        self.assertAlmostEqual(r.units_per_usd, 40.261)
        self.assertEqual(r.date, "2026-08-17")

    def test_bcb_indicative_cross_checks(self):
        data = '''TABLA DE COTIZACIONES DEL 19 DE AGOSTO DE 2026
        ARGENTINA PESO ARS 0.00771 1,495
        CHILE PESO CLP 0.01242 927.34
        COLOMBIA PESO COP 0.00372 3,100.88
        PARAGUAY GUARANI PYG 0.00192 6,011.7
        PERÚ NUEVO SOL PEN 3.4248 3.3637
        URUGUAY PESO UYU 0.28564 40.33
        * Las cotizaciones son indicativas a excepción del dólar estadounidense.
        '''.encode('utf-8')
        rates, date = parse_bcb(data)
        self.assertEqual(date, "2026-08-19")
        self.assertAlmostEqual(rates["ARS"], 1495.0)
        self.assertAlmostEqual(rates["CLP"], 927.34)
        self.assertAlmostEqual(rates["COP"], 3100.88)
        self.assertAlmostEqual(rates["PYG"], 6011.7)
        self.assertAlmostEqual(rates["PEN"], 3.3637)
        self.assertAlmostEqual(rates["UYU"], 40.33)


if __name__ == '__main__':
    unittest.main()
