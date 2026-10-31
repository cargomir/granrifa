import ast
from pathlib import Path
import unittest


source = Path(__file__).resolve().parents[1] / "administrador.py"
tree = ast.parse(source.read_text(encoding="utf-8"))
tree.body = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name == "resumen_por_estudiante"]
namespace = {}
exec(compile(tree, str(source), "exec"), namespace)
resumen = namespace["resumen_por_estudiante"]


class ResumenTests(unittest.TestCase):
    def test_respeta_orden_de_lista_aunque_no_sea_alfabetico(self):
        filas = resumen(["Zoe", "Luis", "Ana"], [
            {"vendedor": "Ana", "estado": "pagado", "numero": 1},
        ])
        self.assertEqual([fila["Estudiante"] for fila in filas], ["Zoe", "Luis", "Ana"])

    def test_estudiante_sin_ventas_aparece_con_cero(self):
        fila = resumen(["Ana"], [])[0]
        self.assertEqual(fila["Vendidos (pagados)"], 0)
        self.assertEqual(fila["Faltan para la meta"], 10)
        self.assertTrue(fila["Avance"].startswith("🔴"))

    def test_limites_de_avance(self):
        for cantidad, simbolo in [(0, "🔴"), (5, "🔴"), (6, "🟡"),
                                   (9, "🟡"), (10, "✅"), (11, "✅")]:
            with self.subTest(cantidad=cantidad):
                numeros = [{"vendedor": "Ana", "estado": "pagado", "numero": i}
                           for i in range(1, cantidad + 1)]
                fila = resumen(["Ana"], numeros)[0]
                self.assertTrue(fila["Avance"].startswith(simbolo))
                self.assertEqual(fila["Faltan para la meta"], max(0, 10 - cantidad))

    def test_reservas_no_cuentan_como_ventas_y_se_conserva_el_padron(self):
        filas = resumen(["Ana", "Luis"], [
            {"vendedor": "Ana", "estado": "reservado", "numero": 2},
            {"vendedor": None, "estado": "disponible", "numero": 3},
        ])
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[0]["Vendidos (pagados)"], 0)
        self.assertEqual(filas[0]["Reservados"], 1)
        self.assertEqual(filas[0]["Números reservados"], "2")

    def test_conserva_vendedor_historico_fuera_del_padron(self):
        filas = resumen(["Ana"], [{"vendedor": "Luis", "estado": "pagado", "numero": 1}])
        self.assertEqual([fila["Estudiante"] for fila in filas], ["Ana", "Luis"])


if __name__ == "__main__":
    unittest.main()
