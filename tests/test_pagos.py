"""Regresiones de pagos sin conexión ni credenciales de Supabase."""
import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
import unittest


class Query:
    def __init__(self, client, table):
        self.client, self.table = client, table
        self.operation = "select"

    def __getattr__(self, name):
        def chain(*args, **kwargs):
            self.client.calls.append((self.table, name, args))
            if name in ("insert", "update"):
                self.operation = name
                self.client.payloads.append((self.table, name, args[0]))
            return self
        return chain

    def execute(self):
        result = self.client.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(data=result)


class Client:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.payloads = []
        self.calls = []

    def table(self, name):
        return Query(self, name)


def load_functions(client):
    source = Path(__file__).resolve().parents[1] / "db.py"
    names = {"_data", "crear_compra", "compras_pendientes", "confirmar_pago_compra", "rechazar_reserva"}
    tree = ast.parse(source.read_text(encoding="utf-8"))
    tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = dict(Any=Any, Dict=Dict, List=List, datetime=datetime,
                     timedelta=timedelta, ZONA_CHILE=timezone.utc, supabase=client,
                     liberar_reservas_expiradas=lambda: None,
                     obtener_configuracion=lambda: {"t": 60},
                     parsear_fecha_supabase=datetime.fromisoformat)
    exec(compile(tree, str(source), "exec"), namespace)
    return namespace


def numero(estado="reservado", pagado="No", numero=1):
    return {"id_compra": "compra-1", "numero": numero, "estado": estado,
            "precio_unitario": 1000, "fecha_hora_reserva": None,
            "compradores": {"nombre_comprador": "Comprador"},
            "compras": {"pagado": pagado, "nombre_alumno_vendedor": "Alumno",
                        "fecha_hora_compra": None}}


class PagosTests(unittest.TestCase):
    def test_reserva_visible_aunque_compra_diga_pagada(self):
        client = Client([numero(pagado="Sí")], [])
        compras = load_functions(client)["compras_pendientes"]()
        self.assertEqual(compras[0]["numeros"], "1")
        self.assertFalse(compras[0]["puede_rechazar"])

    def test_pago_de_numeros_con_compra_pendiente_es_recuperable(self):
        client = Client([numero(estado="pagado")], [])
        self.assertEqual(len(load_functions(client)["compras_pendientes"]()), 1)

    def test_pago_consistente_no_aparece_pendiente(self):
        client = Client([numero(estado="pagado", pagado="Sí")], [])
        self.assertEqual(load_functions(client)["compras_pendientes"](), [])

    def test_error_de_red_no_se_convierte_en_lista_vacia(self):
        with self.assertRaisesRegex(RuntimeError, "red"):
            load_functions(Client(RuntimeError("red")))["compras_pendientes"]()

    def test_consulta_recupera_paginas_adicionales(self):
        client = Client([numero()], [numero(numero=2)], [])
        compras = load_functions(client)["compras_pendientes"]()
        self.assertEqual(compras[0]["cantidad"], 2)

    def test_compra_inaccesible_se_informa(self):
        fila = numero()
        fila["compras"] = None
        with self.assertRaisesRegex(RuntimeError, "compra accesible"):
            load_functions(Client([fila], []))["compras_pendientes"]()

    def test_pago_directo_empieza_pendiente(self):
        client = Client([{"id_compra": "compra-1"}])
        load_functions(client)["crear_compra"]("Alumno", pagado_alumno=True)
        self.assertEqual(client.payloads[0][2]["pagado"], "No")

    def test_transferencia_desactivada_bloquea_sesion_antigua(self):
        client = Client()
        funciones = load_functions(client)
        funciones["obtener_configuracion"] = lambda: {"transferencias_habilitadas": False}
        with self.assertRaisesRegex(ValueError, "desactivó"):
            funciones["crear_compra"]("Alumno", pagado_alumno=False)
        self.assertEqual(client.payloads, [])

    def test_pago_directo_permitido_con_transferencias_desactivadas(self):
        client = Client([{"id_compra": "compra-1"}])
        funciones = load_functions(client)
        funciones["obtener_configuracion"] = lambda: {"transferencias_habilitadas": False}
        self.assertEqual(funciones["crear_compra"]("Alumno", pagado_alumno=True), "compra-1")

    def test_transferencia_permitida_si_esta_habilitada(self):
        client = Client([{"id_compra": "compra-1"}])
        funciones = load_functions(client)
        funciones["obtener_configuracion"] = lambda: {"transferencias_habilitadas": True}
        self.assertEqual(funciones["crear_compra"]("Alumno", pagado_alumno=False), "compra-1")

    def test_confirmacion_interrumpida_se_puede_reintentar(self):
        client = Client([numero()], RuntimeError("red"), [], [{"numero": 1}], [{}])
        confirmar = load_functions(client)["confirmar_pago_compra"]
        with self.assertRaisesRegex(RuntimeError, "red"):
            confirmar("compra-1", "Transferencia")
        confirmar("compra-1", "Transferencia")
        self.assertEqual(client.payloads[-1][2], {"pagado": "Sí", "forma_pago": "Transferencia"})

    def test_compra_expirada_no_se_marca_pagada(self):
        client = Client([], [])
        with self.assertRaisesRegex(RuntimeError, "expirado"):
            load_functions(client)["confirmar_pago_compra"]("compra-1", "Transferencia")
        self.assertFalse(any(table == "compras" for table, _, _ in client.payloads))

    def test_rechazo_libera_solo_numeros_reservados_de_la_compra_elegida(self):
        client = Client([{"id_compra": "compra-1"}], [numero(), numero(numero=2)])
        rechazar = load_functions(client)["rechazar_reserva"]
        self.assertEqual(rechazar("compra-1"), 2)
        self.assertIn(("compras", "eq", ("pagado", "No")), client.calls)
        self.assertIn(("numeros", "eq", ("id_compra", "compra-1")), client.calls)
        self.assertIn(("numeros", "eq", ("estado", "reservado")), client.calls)
        self.assertEqual(client.payloads, [("numeros", "update", {
            "estado": "disponible", "id_compra": None, "id_comprador": None,
            "fecha_hora_reserva": None, "precio_unitario": None,
        })])

    def test_rechazo_no_actualiza_una_compra_ya_pagada(self):
        client = Client([])
        self.assertEqual(load_functions(client)["rechazar_reserva"]("compra-1"), 0)
        self.assertEqual(client.payloads, [])

    def test_rechazo_repetido_no_libera_numeros_nuevamente(self):
        client = Client([{"id_compra": "compra-1"}], [])
        self.assertEqual(load_functions(client)["rechazar_reserva"]("compra-1"), 0)


if __name__ == "__main__":
    unittest.main()
