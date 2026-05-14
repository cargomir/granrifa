import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import unicodedata

from dotenv import load_dotenv
from supabase import create_client, Client
import re
from zoneinfo import ZoneInfo

ZONA_CHILE = ZoneInfo("America/Santiago")

load_dotenv()


def get_client() -> Client:
    """Crea cliente Supabase desde variables de entorno."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError(
            "Faltan variables de entorno SUPABASE_URL y/o SUPABASE_KEY. "
            "Configúralas en .env local o en los Secrets de Streamlit Cloud."
        )

    return create_client(url, key)


supabase: Client = get_client()


# ============================================================
# Utilidades generales
# ============================================================

def _data(resp):
    return resp.data if hasattr(resp, "data") else resp


def obtener_configuracion() -> Dict[str, Any]:
    resp = supabase.table("configuracion").select("*").eq("id", 1).single().execute()
    return _data(resp)


def guardar_configuracion(n: int, p: float, t: int, clave_vendedor: str, clave_admin: str) -> None:
    supabase.table("configuracion").update({
        "n": n,
        "p": p,
        "t": t,
        "clave_vendedor": clave_vendedor,
        "clave_admin": clave_admin
    }).eq("id", 1).execute()


def listar_alumnos() -> List[str]:
    resp = supabase.table("alumnos").select("nombre_alumno").order("nombre_alumno").execute()
    return [r["nombre_alumno"] for r in _data(resp)]


def crear_compra(nombre_alumno_vendedor: str, pagado_alumno: bool = False) -> str:
    resp = supabase.table("compras").insert({
        "nombre_alumno_vendedor": nombre_alumno_vendedor,
        "pagado": "Sí" if pagado_alumno else "No",
        "forma_pago": "Efectivo" if pagado_alumno else "Pendiente"
    }).execute()

    data = _data(resp)
    return data[0]["id_compra"]

def marcar_numeros_compra_pagados(id_compra: str) -> None:
    supabase.table("numeros").update({
        "estado": "pagado"
    }).eq("id_compra", id_compra).eq("estado", "reservado").execute()

def validar_telefono(telefono: str) -> tuple[bool, str]:
    """
    Valida teléfonos chilenos simples.
    Permite:
    +56912345678
    56912345678
    912345678
    """

    tel = re.sub(r"\s+", "", telefono or "")

    if tel == "":
        return True, ""

    if not re.fullmatch(r"(\+?56)?9\d{8}", tel):
        return False, (
            "El teléfono debe tener formato válido. "
            "Ejemplo: +56912345678"
        )

    return True, ""


def validar_correo(correo: str) -> tuple[bool, str]:
    """
    Validación básica de correo electrónico.
    """

    correo = (correo or "").strip().lower()

    if correo == "":
        return True, ""

    patron = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

    if not re.fullmatch(patron, correo):
        return False, "El correo electrónico no tiene un formato válido."

    return True, ""

def normalizar_nombre(nombre: str) -> str:
    """
    Normaliza nombres para evitar duplicados:
    - elimina espacios dobles
    - convierte a mayúsculas
    - elimina tildes
    """

    texto = " ".join((nombre or "").strip().upper().split())

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )

    return texto

def obtener_comprador_por_nombre(nombre_comprador: str) -> Optional[Dict[str, Any]]:
    nombre = normalizar_nombre(nombre_comprador)

    if not nombre:
        return None

    resp = (
        supabase.table("compradores")
        .select("*")
        .eq("nombre_comprador", nombre)
        .limit(1)
        .execute()
    )

    data = _data(resp)
    return data[0] if data else None


def upsert_comprador(nombre_comprador: str, telefono: str = "", correo: str = "") -> int:
    nombre = normalizar_nombre(nombre_comprador)

    if not nombre:
        raise ValueError("Debes ingresar el nombre del comprador.")

    existente = obtener_comprador_por_nombre(nombre)

    payload = {
        "nombre_comprador": nombre,
        "telefono": (telefono or "").strip() or None,
        "correo": (correo or "").strip().lower() or None,
    }

    if existente:
        resp = (
            supabase.table("compradores")
            .update(payload)
            .eq("id_comprador", existente["id_comprador"])
            .execute()
        )
        data = _data(resp)
        return data[0]["id_comprador"] if data else existente["id_comprador"]

    resp = supabase.table("compradores").insert(payload).execute()
    return _data(resp)[0]["id_comprador"]

def dashboard_admin() -> Dict[str, Any]:
    """
    Datos agregados para dashboard administrativo.
    """
    liberar_reservas_expiradas()

    datos_numeros = exportar_todos_los_numeros()

    return {
        "numeros": datos_numeros
    }

def exportar_todos_los_numeros() -> List[Dict[str, Any]]:
    """
    Exporta todos los números con información de compra,
    vendedor y comprador.
    """
    liberar_reservas_expiradas()

    resp = (
        supabase.table("numeros")
        .select(
            """
            numero,
            estado,
            fecha_hora_reserva,
            precio_unitario,
            compradores(nombre_comprador, telefono, correo),
            compras(fecha_hora_compra, nombre_alumno_vendedor, pagado, forma_pago)
            """
        )
        .order("numero")
        .execute()
    )

    data = _data(resp)

    salida = []

    for r in data:
        comprador = r.get("compradores") or {}
        compra = r.get("compras") or {}

        salida.append({
            "numero": r.get("numero"),
            "estado": r.get("estado"),
            "vendedor": compra.get("nombre_alumno_vendedor"),
            "comprador": comprador.get("nombre_comprador"),
            "telefono": comprador.get("telefono"),
            "correo": comprador.get("correo"),
            "precio_unitario": r.get("precio_unitario"),
            "pagado": compra.get("pagado"),
            "forma_pago": compra.get("forma_pago"),
            "fecha_hora_compra": (
                parsear_fecha_supabase(compra.get("fecha_hora_compra"))
                .strftime("%d-%m-%Y %H:%M:%S")
                if compra.get("fecha_hora_compra")
                else ""
            ),
            "fecha_hora_reserva": r.get("fecha_hora_reserva"),
        })

    return salida

def reiniciar_numeros_rifa(n):
    supabase.table("numeros").delete().neq("id_numero", 0).execute()

    nuevos = [
        {
            "numero": i,
            "estado": "disponible",
            "id_compra": None
        }
        for i in range(1, int(n) + 1)
    ]

    if nuevos:
        supabase.table("numeros").insert(nuevos).execute()
        
# ============================================================
# Expiración de reservas
# ============================================================

def liberar_reservas_expiradas() -> int:
    """
    Libera reservas vencidas.

    Regla:
    Un número reservado expira si:
      now() > fecha_hora_reserva + t minutos
    y la compra asociada sigue con pagado = 'No'.

    Implementación:
    1) Obtiene t desde configuración.
    2) Busca números reservados con fecha_hora_reserva anterior al umbral.
    3) Verifica que la compra asociada no esté pagada.
    4) Actualiza esos números a disponible y limpia campos de reserva.

    Nota:
    Los números pagados nunca se modifican.
    """
    config = obtener_configuracion()
    t = int(config["t"])
    ahora = datetime.now(timezone.utc)
    umbral = ahora - timedelta(minutes=t)

    resp = (
        supabase.table("numeros")
        .select("id_numero, id_compra, fecha_hora_reserva")
        .eq("estado", "reservado")
        .lt("fecha_hora_reserva", umbral.isoformat())
        .execute()
    )
    candidatos = _data(resp)

    if not candidatos:
        return 0

    ids_liberar = []
    for num in candidatos:
        id_compra = num.get("id_compra")
        if not id_compra:
            ids_liberar.append(num["id_numero"])
            continue

        compra_resp = (
            supabase.table("compras")
            .select("pagado")
            .eq("id_compra", id_compra)
            .limit(1)
            .execute()
        )
        compra = _data(compra_resp)
        if compra and compra[0]["pagado"] == "No":
            ids_liberar.append(num["id_numero"])

    if not ids_liberar:
        return 0

    supabase.table("numeros").update({
        "estado": "disponible",
        "id_compra": None,
        "id_comprador": None,
        "fecha_hora_reserva": None,
        "precio_unitario": None
    }).in_("id_numero", ids_liberar).execute()

    return len(ids_liberar)


def listar_numeros_disponibles() -> List[int]:
    liberar_reservas_expiradas()

    resp = (
        supabase.table("numeros")
        .select("numero")
        .eq("estado", "disponible")
        .order("numero")
        .execute()
    )
    return [r["numero"] for r in _data(resp)]

def listar_estado_numeros() -> List[Dict[str, Any]]:
    """
    Devuelve todos los números con su estado actual.
    Antes libera reservas expiradas.
    """
    liberar_reservas_expiradas()

    resp = (
        supabase.table("numeros")
        .select("numero, estado")
        .order("numero")
        .execute()
    )

    return _data(resp)


# ============================================================
# Reserva atómica anti-colisión vía RPC/PostgreSQL
# ============================================================

def reservar_numero_atomico(
    numero: int,
    id_compra: str,
    id_comprador: int,
    precio_unitario: float
) -> Tuple[bool, str]:
    """
    Reserva atómica usando una función RPC en Supabase/PostgreSQL.

    La lógica crítica queda dentro de PostgreSQL:
    solo reserva el número si todavía está en estado 'disponible'.
    """
    resp = supabase.rpc(
        "reservar_numero_rpc",
        {
            "p_numero": int(numero),
            "p_id_compra": id_compra,
            "p_id_comprador": int(id_comprador),
            "p_precio_unitario": float(precio_unitario),
        }
    ).execute()

    data = _data(resp)

    if not data:
        return False, "No se recibió respuesta desde Supabase."

    return bool(data[0]["ok"]), data[0]["mensaje"] 

def numeros_de_compra(id_compra: str) -> List[Dict[str, Any]]:
    resp = (
        supabase.table("numeros")
        .select("numero, estado, precio_unitario, compradores(nombre_comprador)")
        .eq("id_compra", id_compra)
        .order("numero")
        .execute()
    )

    data = _data(resp)
    salida = []
    for r in data:
        comprador = r.get("compradores") or {}
        salida.append({
            "numero": r["numero"],
            "estado": r["estado"],
            "precio_unitario": r.get("precio_unitario") or 0,
            "nombre_comprador": comprador.get("nombre_comprador", "")
        })
    return salida

def compras_por_alumno(nombre_alumno: str) -> List[Dict[str, Any]]:
    resp = (
        supabase.table("compras")
        .select("""
            id_compra,
            fecha_hora_compra,
            pagado,
            forma_pago,
            numeros(
                numero,
                estado,
                precio_unitario,
                compradores(nombre_comprador)
            )
        """)
        .eq("nombre_alumno_vendedor", nombre_alumno)
        .order("fecha_hora_compra", desc=True)
        .execute()
    )

    compras = _data(resp)
    salida = []

    for c in compras:
        nums = c.get("numeros", [])

        if not nums:
            continue

        total = sum(float(n.get("precio_unitario") or 0) for n in nums)

        compradores = sorted(set(
            (n.get("compradores") or {}).get("nombre_comprador", "")
            for n in nums
            if (n.get("compradores") or {}).get("nombre_comprador", "")
        ))

        salida.append({
            "id_compra": c["id_compra"],
            "fecha_hora_compra": (
                parsear_fecha_supabase(c.get("fecha_hora_compra")).strftime("%d-%m-%Y %H:%M:%S")
                if c.get("fecha_hora_compra")
                else ""
            ),
            "pagado": c.get("pagado"),
            "forma_pago": c.get("forma_pago"),
            "cantidad": len(nums),
            "total": total,
            "comprador": ", ".join(compradores),
            "numeros": ", ".join(str(n.get("numero")) for n in nums),
            "estados": ", ".join(str(n.get("estado")) for n in nums)
        })

    return salida

def tiempo_restante_compra(id_compra: str) -> Dict[str, Any]:
    """
    Calcula el tiempo restante de una compra pendiente.

    Usa la fecha_hora_reserva más antigua de los números reservados
    asociados a la compra.
    """
    config = obtener_configuracion()
    t = int(config["t"])

    resp = (
        supabase.table("numeros")
        .select("fecha_hora_reserva, estado")
        .eq("id_compra", id_compra)
        .eq("estado", "reservado")
        .execute()
    )

    filas = _data(resp)

    if not filas:
        return {
            "tiene_reservas": False,
            "segundos_restantes": 0,
            "texto": "Sin reservas activas"
        }

    fechas = []

    for f in filas:
        fecha = f.get("fecha_hora_reserva")
        if fecha:
            fecha_ok = parsear_fecha_supabase(fecha)

            if fecha_ok:
                fechas.append(fecha_ok)

    if not fechas:
        return {
            "tiene_reservas": False,
            "segundos_restantes": 0,
            "texto": "Sin reservas activas"
        }

    primera_reserva = min(fechas)
    expira = primera_reserva + timedelta(minutes=t)
    ahora = datetime.now(ZONA_CHILE)

    segundos = max(0, int((expira - ahora).total_seconds()))

    minutos = segundos // 60
    seg = segundos % 60

    return {
        "tiene_reservas": True,
        "segundos_restantes": segundos,
        "texto": f"{minutos:02d}:{seg:02d}"
    }

# ============================================================
# Administración
# ============================================================
def parsear_fecha_supabase(fecha):
    if not fecha:
        return None

    fecha_txt = str(fecha).replace("Z", "+00:00")

    if "." in fecha_txt:
        parte1, parte2 = fecha_txt.split(".", 1)

        if "+" in parte2:
            micro, zona = parte2.split("+", 1)
            micro = micro.ljust(6, "0")[:6]
            fecha_txt = f"{parte1}.{micro}+{zona}"

        elif "-" in parte2:
            micro, zona = parte2.split("-", 1)
            micro = micro.ljust(6, "0")[:6]
            fecha_txt = f"{parte1}.{micro}-{zona}"

    dt_utc = datetime.fromisoformat(fecha_txt)

    return dt_utc.astimezone(ZONA_CHILE)

def compras_pendientes() -> List[Dict[str, Any]]:
    try:
        liberar_reservas_expiradas()
        config = obtener_configuracion()
        t = int(config["t"])

        resp = (
            supabase.table("numeros")
            .select("id_compra, precio_unitario, fecha_hora_reserva, compras(id_compra, fecha_hora_compra, nombre_alumno_vendedor, pagado)")
            .eq("estado", "reservado")
            .execute()
        )

    except Exception as e:
        print("Error en compras_pendientes:", e)
        return []

    filas = _data(resp)
    grupos: Dict[str, Dict[str, Any]] = {}

    for r in filas:
        compra = r.get("compras") or {}
        if not compra or compra.get("pagado") != "No":
            continue

        idc = r["id_compra"]
        if idc not in grupos:
            grupos[idc] = {
                "id_compra": idc,
                "fecha_hora_compra": (
                    parsear_fecha_supabase(compra.get("fecha_hora_compra"))
                    .strftime("%d-%m-%Y %H:%M:%S")
                    if compra.get("fecha_hora_compra")
                    else ""
                ),
                "nombre_alumno_vendedor": compra.get("nombre_alumno_vendedor"),
                "cantidad": 0,
                "total": 0,
                "fechas_reserva": []
            }

        grupos[idc]["cantidad"] += 1
        grupos[idc]["total"] += float(r.get("precio_unitario") or 0)
        if r.get("fecha_hora_reserva"):
            grupos[idc]["fechas_reserva"].append(r["fecha_hora_reserva"])

    resultado = []
    ahora = datetime.now(ZONA_CHILE)

    for g in grupos.values():
        fechas = []
        for f in g.pop("fechas_reserva"):
            try:
                fecha_ok = parsear_fecha_supabase(f)

                if fecha_ok:
                    fechas.append(fecha_ok)

            except Exception:
                pass

        if fechas:
            primera = min(fechas)
            expira = primera + timedelta(minutes=t)
            restantes = max(0, int((expira - ahora).total_seconds() // 60))
        else:
            restantes = 0

        g["tiempo_restante_min"] = restantes
        resultado.append(g)

    return sorted(resultado, key=lambda x: x["fecha_hora_compra"] or "", reverse=True)


def confirmar_pago_compra(id_compra: str, forma_pago: str) -> None:
    # 1. Primero actualiza los números reservados de esa compra
    resp_numeros = (
        supabase.table("numeros")
        .update({
            "estado": "pagado"
        })
        .eq("id_compra", id_compra)
        .eq("estado", "reservado")
        .execute()
    )

    numeros_actualizados = _data(resp_numeros)

    if not numeros_actualizados:
        raise RuntimeError(
            "No se encontraron números reservados para esta compra. "
            "Es posible que la reserva haya expirado o ya haya sido modificada."
        )

    # 2. Luego marca la compra como pagada
    supabase.table("compras").update({
        "pagado": "Sí",
        "forma_pago": forma_pago
    }).eq("id_compra", id_compra).execute()


def compras_pagadas() -> List[Dict[str, Any]]:

    resp = (
        supabase.table("compras")
        .select("""
            id_compra,
            fecha_hora_compra,
            nombre_alumno_vendedor,
            forma_pago,
            numeros(
                numero,
                precio_unitario
            )
        """)
        .eq("pagado", "Sí")
        .order("fecha_hora_compra", desc=True)
        .execute()
    )

    compras = _data(resp)

    salida = []

    for c in compras:

        nums = c.get("numeros", [])

        total = sum(
            float(n.get("precio_unitario") or 0)
            for n in nums
        )

        salida.append({
            "id_compra": c["id_compra"],

            "fecha_hora_compra": (
                parsear_fecha_supabase(c.get("fecha_hora_compra"))
                .strftime("%d-%m-%Y %H:%M:%S")
                if c.get("fecha_hora_compra")
                else ""
            ),

            "nombre_alumno_vendedor": c.get("nombre_alumno_vendedor"),
            "forma_pago": c.get("forma_pago"),

            "cantidad": len(nums),

            "total": total,

            "numeros": ", ".join(
                str(n.get("numero"))
                for n in nums
            )
        })

    return salida


def asegurar_numeros_hasta_n(n_nuevo: int) -> int:
    resp = supabase.table("numeros").select("numero").execute()
    existentes = {r["numero"] for r in _data(resp)}

    faltantes = [
        {"numero": i, "estado": "disponible"}
        for i in range(1, n_nuevo + 1)
        if i not in existentes
    ]

    if faltantes:
        supabase.table("numeros").insert(faltantes).execute()

    return len(faltantes)


def resumen_estados() -> Dict[str, int]:
    liberar_reservas_expiradas()

    resp = supabase.table("numeros").select("estado").execute()
    estados = [r["estado"] for r in _data(resp)]

    return {
        "pagados": estados.count("pagado"),
        "reservados": estados.count("reservado"),
        "disponibles": estados.count("disponible"),
    }


def resumen_recaudacion() -> Dict[str, float]:
    resp = (
        supabase.table("numeros")
        .select("precio_unitario, compras(forma_pago)")
        .eq("estado", "pagado")
        .execute()
    )

    efectivo = 0.0
    transferencia = 0.0

    for r in _data(resp):
        compra = r.get("compras") or {}
        monto = float(r.get("precio_unitario") or 0)

        if compra.get("forma_pago") == "Efectivo":
            efectivo += monto
        elif compra.get("forma_pago") == "Transferencia":
            transferencia += monto

    return {
        "efectivo": efectivo,
        "transferencia": transferencia,
        "total": efectivo + transferencia,
    }
