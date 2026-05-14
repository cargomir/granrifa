import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import db
from streamlit_autorefresh import st_autorefresh

def mostrar_contador_expiracion(id_compra: str):
    tiempo = db.tiempo_restante_compra(id_compra)

    if not tiempo["tiene_reservas"]:
        return

    if tiempo["segundos_restantes"] <= 0:
        st.warning("Las reservas de esta compra ya expiraron o están por liberarse.")
        return

    segundos = int(tiempo["segundos_restantes"])

    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segundos_final = segundos % 60

    texto_tiempo = f"{horas:02}:{minutos:02}:{segundos_final:02}"

    st.info(
        f"⏳ Tiempo restante para confirmar el pago de esta compra: "
        f"**{texto_tiempo}**"
    )

def _limpiar_formulario_numero():
    for k in [
        "numeros_seleccionados",
        "nombre_comprador_input",
        "telefono_input",
        "correo_input",
        "comprador_buscado",
    ]:
        st.session_state.pop(k, None)

    st.session_state["telefono_key_version"] = (
            st.session_state.get("telefono_key_version", 0) + 1
    )

def _mostrar_reservados(id_compra: str):
    if not id_compra:
        return
    
    numeros = db.numeros_de_compra(id_compra)
    if not numeros:
        st.info("Aún no hay números reservados en esta compra.")
        return

    df = pd.DataFrame(numeros)
    df = df.rename(columns={
    "numero": "Número",
    "nombre_comprador": "Comprador",
    "estado": "Estado",
    "precio_unitario": "Precio unitario"
    })

    df = df[["Número", "Comprador", "Estado", "Precio unitario"]]

    # Formato precio
    df["Precio unitario"] = df["Precio unitario"].apply(
        lambda x: f"${x:,.0f}".replace(",", ".")
    )

    # Emoji estado
    df["Estado"] = df["Estado"].replace({
        "reservado": "🟨 Reservado",
        "pagado": "🟥 Pagado",
        "disponible": "🟩 Disponible"
    })

    html_tabla = """
    <style>
    .tabla-reservados {
        width: 100%;
        border-collapse: collapse;
        border-radius: 12px;
        overflow: hidden;
        font-size: 15px;
        margin-top: 10px;
        margin-bottom: 20px;
    }

    .tabla-reservados th {
        background-color: #f3f4f6;
        font-weight: 700;
        text-align: center;
        padding: 12px;
        border-bottom: 1px solid #e5e7eb;
    }

    .tabla-reservados td {
        text-align: center;
        padding: 11px;
        border-bottom: 1px solid #e5e7eb;
    }

    .tabla-reservados tr:nth-child(even) {
        background-color: #fafafa;
    }

    .tabla-reservados tr:hover {
        background-color: #f1f5f9;
    }
    </style>

    <table class="tabla-reservados">
        <thead>
            <tr>
                <th>Número</th>
                <th>Comprador</th>
                <th>Estado</th>
                <th>Precio unitario</th>
            </tr>
        </thead>
        <tbody>
    """

    for _, row in df.iterrows():

        html_tabla += f"""
        <tr>
            <td>{row['Número']}</td>
            <td>{row['Comprador']}</td>
            <td>{row['Estado']}</td>
            <td>{row['Precio unitario']}</td>
        </tr>
        """

    html_tabla += """
        </tbody>
    </table>
    """

    components.html(html_tabla, height=220, scrolling=False)


def render_vendedor():
    col_logo, col_titulo = st.columns([1, 8])

    with col_logo:
        st.image("logo.png", width=120)

    with col_titulo:
        st.markdown(
            "<h1 style='margin-top:10px;'>Perfil vendedor</h1>",
            unsafe_allow_html=True
        )

    st_autorefresh(interval=30000, key="refresh_vendedor")

    config = db.obtener_configuracion()
    p_actual = float(config["p"])
    t_actual = int(config["t"])

    if "id_compra_activa" not in st.session_state:
        st.session_state.id_compra_activa = None
    if "nombre_vendedor_activo" not in st.session_state:
        st.session_state.nombre_vendedor_activo = None
    if "compras_cerradas_sesion" not in st.session_state:
        st.session_state.compras_cerradas_sesion = []
    
    st.info(f"Vendedor activo: **{st.session_state.nombre_vendedor_activo}**")

    # -----------------------------
    # Paso 1: Selección de número
    # -----------------------------
    st.subheader("Paso 1 — Selección de número")

    disponibles = db.listar_numeros_disponibles()

    if not disponibles:
        st.warning("No hay números disponibles en este momento.")
        _mostrar_reservados(st.session_state.id_compra_activa)
        return

    st.markdown("""
    <style>

    button[kind="pills"] {
        background-color: #E3F2FD !important;
        color: #1565C0 !important;
        border: 1px solid #1565C0 !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }

    button[kind="pills"][aria-pressed="true"] {
        background-color: #1565C0 !important;
        color: white !important;
        border: 1px solid #1565C0 !important;
    }

    div[data-testid="stPills"] div[role="group"] {
        display: grid !important;
        grid-template-columns: repeat(auto-fit, minmax(85px, 1fr)) !important;
        gap: 6px !important;
    }

    div[data-testid="stPills"] button {
        width: 100% !important;
    }

    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="
        font-size:18px;
        font-weight:700;
        margin-bottom:16px;
    ">
    A continuación se muestran los números disponibles. Pincha todos los números que deseas comprar.
    </div>
    """, unsafe_allow_html=True)

    numeros_seleccionados = st.pills(
        "",
        disponibles,
        selection_mode="multi",
        key="numeros_seleccionados",
        format_func=lambda x: f"Número {x}"
    )

    if numeros_seleccionados:
        total_estimado = len(numeros_seleccionados) * p_actual

        st.info(
            f"Seleccionaste {len(numeros_seleccionados)} número(s). "
            f"Total parcial: ${total_estimado:,.0f}".replace(",", ".")
        )

    st.caption("La lista se actualiza automáticamente cada 30 segundos para bloquear números tomados por otros vendedores.")
    
    # -----------------------------
    # Paso 2: Datos comprador
    # -----------------------------
    st.subheader("Paso 2 — Datos del comprador")

    st.session_state.setdefault("nombre_comprador_input", "")
    st.session_state.setdefault("telefono_input", "")
    st.session_state.setdefault("correo_input", "")
    st.session_state.setdefault("comprador_buscado", "")

    nombre_actual = st.text_input(
        "Nombre comprador",
        key="nombre_comprador_input",
        placeholder="Ej: Patricio Achurra"
    )
    # Autocompletado simple:
    # Si el nombre cambia y existe en el directorio, se rellenan teléfono y correo.
    if nombre_actual and nombre_actual != st.session_state.get("comprador_buscado", ""):
        comprador = db.obtener_comprador_por_nombre(nombre_actual.strip())
        st.session_state["comprador_buscado"] = nombre_actual
        if comprador:
            telefono_completo = comprador.get("telefono") or ""

            if telefono_completo.startswith("+56"):
                telefono_visible = telefono_completo[3:]
            else:
                telefono_visible = telefono_completo

            st.session_state["telefono_input"] = telefono_completo
            st.session_state[
                f"telefono_input_visible_{st.session_state.get('telefono_key_version', 0)}"
            ] = telefono_visible
            st.session_state["correo_input"] = comprador.get("correo") or ""

            st.toast("Datos del comprador encontrados y autocompletados.")
            st.rerun()

    col_prefijo, col_numero = st.columns([1, 5])

    with col_prefijo:
        st.text_input(
            "Código",
            value="+56",
            disabled=True
        )

    st.session_state.setdefault("telefono_key_version", 0)

    with col_numero:
        telefono_numero = st.text_input(
            "Teléfono",
            key=f"telefono_input_visible_{st.session_state.telefono_key_version}",
            placeholder="Ej: 987654321"
        )

    telefono = f"+56{telefono_numero.strip()}"
        
    correo = st.text_input(
        "Correo",
        key="correo_input",
        placeholder="Ej: pato_achurra@mail.com"
    )

    pagado_alumno = st.checkbox(
        f"El valor de los números será pagado directamente a **{st.session_state.nombre_vendedor_activo}**",
        value=True
    )


    if not pagado_alumno:

        horas = t_actual // 60
        minutos = t_actual % 60

        if minutos == 0:
            tiempo_texto = f"{horas} hora(s)"
        else:
            tiempo_texto = f"{horas} hora(s) y {minutos} minuto(s)"

        st.warning(
            f"""
    ⚠️ Solo desmarca esta opción si deseas pagar mediante transferencia a la cuenta del curso.

    En ese caso, deberás enviar el comprobante de pago a la tesorera de la directiva de apoderados dentro de un plazo máximo de **{tiempo_texto}**.

    Después de ese tiempo, los números seleccionados volverán a estar disponibles automáticamente.
    """
        )

    # -----------------------------
    # Paso 3: Botones de acción
    # -----------------------------
    col_izq, col_centro, col_der = st.columns([1, 1, 1])

    def reservar():
        if not nombre_actual.strip():
            st.error("Debes ingresar el nombre del comprador.")
            return

        ok_tel, msg_tel = db.validar_telefono(telefono)

        if not ok_tel:
            st.error(msg_tel)
            return

        ok_correo, msg_correo = db.validar_correo(correo)

        if not ok_correo:
            st.error(msg_correo)
            return

        id_comprador = db.upsert_comprador(nombre_actual, telefono, correo)
        
        if not numeros_seleccionados:
            st.error("Debes seleccionar al menos un número.")
            return

        id_compra_actual = db.crear_compra(
            st.session_state.nombre_vendedor_activo,
            pagado_alumno=pagado_alumno
        )

        st.session_state.id_compra_activa = id_compra_actual

        errores = []
        exitos = []

        for num in numeros_seleccionados:
            ok, msg = db.reservar_numero_atomico(
                numero=int(num),
                id_compra=id_compra_actual,
                id_comprador=id_comprador,
                precio_unitario=p_actual
            )

            if ok:
                exitos.append(num)
            else:
                errores.append(msg)

        if exitos:
            st.success(
                "Números reservados correctamente: " +
                ", ".join(str(x) for x in exitos)
            )

        if pagado_alumno and exitos:
            db.marcar_numeros_compra_pagados(id_compra_actual)

        if errores:
            for e in errores:
                st.error(e)

        if errores and not exitos:
            return

        id_compra_cerrada = id_compra_actual

        if id_compra_cerrada not in st.session_state.compras_cerradas_sesion:
            st.session_state.compras_cerradas_sesion = (
                st.session_state.compras_cerradas_sesion + [id_compra_cerrada]
            )

        _limpiar_formulario_numero()
        st.session_state.id_compra_activa = None

        st.rerun()

    formulario_incompleto = (
        not numeros_seleccionados
        or not nombre_actual.strip()
        or not telefono_numero.strip()
        or not correo.strip()
    )

    with col_centro:
        if st.button(
            "Finalizar compra",
            type="primary",
            disabled=formulario_incompleto,
            width=250
        ):
            reservar()

    ventas_alumno = db.compras_por_alumno(
        st.session_state.nombre_vendedor_activo
    )

    if ventas_alumno:
        st.divider()
        st.subheader("Ventas realizadas por este alumno")

        total_ventas = len(ventas_alumno)

        for i, compra in enumerate(ventas_alumno, start=1):

            numero_venta = total_ventas - i + 1

            st.markdown(f"### Venta {numero_venta}")

            st.write(f"**Fecha:** {compra['fecha_hora_compra']}")
            st.write(f"**Comprador:** {compra['comprador']}")
            st.write(f"**Estado pago:** {compra['pagado']}")
            st.write(f"**Forma de pago:** {compra['forma_pago']}")
            st.write(f"**Cantidad de números:** {compra['cantidad']}")
            st.write(
                f"**Total:** ${compra['total']:,.0f}".replace(",", ".")
            )
            st.write(f"**Números:** {compra['numeros']}")

            if compra["pagado"] != "Sí":
                horas = t_actual // 60
                minutos = t_actual % 60

                if minutos == 0:
                    tiempo_texto = f"{horas} hora(s)"
                else:
                    tiempo_texto = f"{horas} hora(s) y {minutos} minuto(s)"

                st.markdown(
                    f"""
    > ⚠️ El pago debe transferirse a la cuenta del curso en un plazo máximo de {tiempo_texto} desde la reserva.  
    > Si no se confirma el pago, los números volverán a estar disponibles automáticamente.

    ### Datos de transferencia

    - **Nombre:** Susan Velozo Catalán  
    - **Correo electrónico:** susanvelozo@hotmail.com  
    - **Tipo de cuenta:** Vista  
    - **RUT:** 16.956.509-0  
    - **Banco:** Mercado Pago  
    - **Nº de cuenta:** 1097008263
    """
                )

                mostrar_contador_expiracion(compra["id_compra"])

            _mostrar_reservados(compra["id_compra"])