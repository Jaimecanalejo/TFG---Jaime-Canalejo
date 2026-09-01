import unittest

import pandas as pd

from rsi_analysis import analizar_cruces_rsi, generar_comentario_local


class RsiAnalysisTests(unittest.TestCase):
    def test_cuenta_solo_entradas_en_cada_zona(self):
        indice = pd.date_range("2025-01-01", periods=10, freq="D")
        df = pd.DataFrame(
            {"RSI": [50, 29, 25, 35, 71, 75, 65, 28, 31, 72]},
            index=indice,
        )

        resultado = analizar_cruces_rsi(df)

        self.assertEqual(resultado["cruces_compra"], 2)
        self.assertEqual(resultado["cruces_venta"], 2)
        self.assertEqual(resultado["zona_actual"], "sobrecompra")
        self.assertEqual(len(resultado["fechas_compra"]), 2)
        self.assertEqual(len(resultado["fechas_venta"]), 2)

    def test_serie_sin_datos_rsi(self):
        resultado = analizar_cruces_rsi(pd.DataFrame({"RSI": [None, None]}))

        self.assertEqual(resultado["cruces_compra"], 0)
        self.assertEqual(resultado["cruces_venta"], 0)
        self.assertIsNone(resultado["rsi_actual"])

    def test_comentario_identifica_el_activo(self):
        resultado = analizar_cruces_rsi(pd.DataFrame({"RSI": [50, 25, 40, 75]}))

        comentario = generar_comentario_local("AAPL", resultado)

        self.assertIn("AAPL", comentario)
        self.assertIn("1 veces", comentario)


if __name__ == "__main__":
    unittest.main()
