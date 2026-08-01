import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import db
from streamlit_autorefresh import st_autorefresh

def _limpiar_formulario_numero():
    for k in [
        "numeros_seleccionados",
        "nombre_comprador_input",
        "telefono_numero_input",
        "correo_input",
        "comprador_buscado",
        "pagado_alumno"
    ]:
        st.session_state.pop(k, None)

    st.session_state["pagado_alumno"] = True

def render_vendedor():

    # Evita que el refresco automático interrumpa la escritura o un toque en móvil.
    formulario_en_uso = bool(
        st.session_state.get("numeros_seleccionados")
        or st.session_state.get("nombre_comprador_input", "").strip()
        or st.session_state.get("telefono_numero_input", "").strip()
        or st.session_state.get("correo_input", "").strip()
    )
    procesando_compra = st.session_state.get("procesando_compra", False)

    if not formulario_en_uso and not procesando_compra:
        st_autorefresh(interval=90000, key="refresh_vendedor")

    config = db.obtener_configuracion()
    p_actual = float(config["p"])
    t_actual = int(config["t"])

    if "nombre_vendedor_activo" not in st.session_state:
        st.session_state.nombre_vendedor_activo = None
    
    st.info(f"Vendedor activo: **{st.session_state.nombre_vendedor_activo}**")

    # -----------------------------
    # Paso 1: Selección de número
    # -----------------------------
    st.subheader("Paso 1 — Selección de número")

    disponibles = db.listar_numeros_disponibles()

    if not disponibles:
        st.warning("No hay números disponibles en este momento.")
        return

    st.markdown("""
    <style>

    /* Mejoras generales para pantallas táctiles */
    div[data-testid="stButton"] > button {
        min-height: 56px !important;
        padding: 12px 18px !important;
        border-radius: 14px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        touch-action: manipulation !important;
        -webkit-tap-highlight-color: transparent !important;
        user-select: none !important;
    }

    div[data-testid="stButton"] > button:active {
        transform: scale(0.985);
    }

    @media (max-width: 640px) {
        div[data-testid="stButton"] > button {
            min-height: 60px !important;
            font-size: 19px !important;
        }
    }

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
    A continuación se muestran los números disponibles. Pincha todos los números a comprar.
    </div>
    """, unsafe_allow_html=True)

    numeros_seleccionados = st.pills(
        "Selecciona los números",
        disponibles,
        selection_mode="multi",
        key="numeros_seleccionados",
        format_func=lambda x: f"Número {x}",
        label_visibility="collapsed"
    )

    if numeros_seleccionados:
        total_estimado = len(numeros_seleccionados) * p_actual

        st.info(
            f"Seleccionaste {len(numeros_seleccionados)} número(s). "
            f"Total parcial: ${total_estimado:,.0f}".replace(",", ".")
        )

    st.caption("La lista se actualiza automáticamente cada 90 segundos para bloquear números tomados por otros vendedores.")
    
    # -----------------------------
    # Paso 2: Datos comprador
    # -----------------------------
    st.subheader("Paso 2 — Datos del comprador")

    st.session_state.setdefault("nombre_comprador_input", "")
    st.session_state.setdefault("telefono_numero_input", "")
    st.session_state.setdefault("correo_input", "")
    st.session_state.setdefault("comprador_buscado", "")

    nombre_actual = st.text_input(
        "Nombre comprador (obligatorio)",
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

            st.session_state["telefono_numero_input"] = telefono_visible
            st.session_state["correo_input"] = comprador.get("correo") or ""

            st.toast("Datos del comprador encontrados y autocompletados.")
            st.rerun()

    col_prefijo, col_numero = st.columns([1, 8])

    with col_prefijo:
        st.text_input(
            "Código (automático)",
            value="+56",
            disabled=True
        )

    with col_numero:
        telefono_numero = st.text_input(
            "Teléfono (obligatorio)",
            key="telefono_numero_input",
            placeholder="Ej: 987654321"
        )

    telefono = f"+56{telefono_numero.strip()}"
        
    correo = st.text_input(
        "Correo (opcional)",
        key="correo_input",
        placeholder="Ej: pato_achurra@mail.com"
    )

    pagado_alumno = st.checkbox(
        f"Los números serán pagados directamente a **{st.session_state.nombre_vendedor_activo}**",
        value=True,
        key="pagado_alumno"
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

    En ese caso, deberás enviar el comprobante de pago a la directiva de los apoderados del curso dentro de un plazo máximo de **{tiempo_texto}**.
    Después de ese tiempo, si el pago aún no ha sido confirmado dentro de la aplicación por la directiva, los números seleccionados volverán a estar disponibles automáticamente.
    """
        )

    # -----------------------------
    # Paso 3: Botones de acción
    # -----------------------------
    
    def reservar():
        if not nombre_actual.strip():
            st.error("Debes ingresar el nombre del comprador.")
            return False

        ok_tel, msg_tel = db.validar_telefono(telefono)

        if not ok_tel:
            st.error(msg_tel)
            return False

        ok_correo, msg_correo = db.validar_correo(correo)

        if not ok_correo:
            st.error(msg_correo)
            return False

        id_comprador = db.upsert_comprador(nombre_actual, telefono, correo)
        
        if not numeros_seleccionados:
            st.error("Debes seleccionar al menos un número.")
            return False

        id_compra_actual = db.crear_compra(
            st.session_state.nombre_vendedor_activo,
            pagado_alumno=pagado_alumno
        )

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
            st.session_state["mensaje_confirmacion"] = (
                "Números reservados correctamente: " +
                ", ".join(str(x) for x in exitos)
            )

        if pagado_alumno and exitos:
            db.marcar_numeros_compra_pagados(id_compra_actual)

        if errores:
            for e in errores:
                st.error(e)

        if errores and not exitos:
            return False

        _limpiar_formulario_numero()
        return True

    formulario_incompleto = (
        not numeros_seleccionados
        or not nombre_actual.strip()
        or not telefono_numero.strip()
    )

    procesando_compra = st.session_state.get("procesando_compra", False)

    if not pagado_alumno:

        horas = t_actual // 60
        minutos = t_actual % 60

        if minutos == 0:
            tiempo_texto = f"{horas} hora(s)"
        else:
            tiempo_texto = f"{horas} hora(s) y {minutos} minuto(s)"

        st.info(
            f"""
        ⚠️ El pago debe transferirse a la cuenta del curso en un plazo máximo de **{tiempo_texto}** desde la reserva.

        Si no se confirma el pago, los números volverán a estar disponibles automáticamente.

        ### Datos de transferencia

        - **Nombre:** Susan Velozo Catalán
        - **Correo electrónico:** susanvelozo@hotmail.com
        - **Tipo de cuenta:** Vista
        - **RUT:** 16.956.509-0
        - **Banco:** Mercado Pago
        - **Nº de cuenta:** 1097008263
        """
        )

        # st.code es nativo de Streamlit y ofrece botón de copia sin usar iframe.
        st.caption("Puedes copiar los datos con el botón del recuadro:")
        st.code(
            "Nombre: Susan Velozo Catalán\n"
            "Correo: susanvelozo@hotmail.com\n"
            "Tipo de cuenta: Vista\n"
            "RUT: 16.956.509-0\n"
            "Banco: Mercado Pago\n"
            "Nº de cuenta: 1097008263",
            language=None,
        )

    clave_boton = (
        "finalizar_compra_transferencia"
        if not pagado_alumno
        else "finalizar_compra_directa"
    )

    boton_finalizar = st.button(
        "Procesando compra…" if procesando_compra else "Finalizar compra",
        type="primary",
        disabled=formulario_incompleto or procesando_compra,
        use_container_width=True,
        key=clave_boton,
    )

    if boton_finalizar:
        st.session_state["procesando_compra"] = True
        compra_exitosa = False

        try:
            with st.spinner("Reservando los números seleccionados…"):
                compra_exitosa = reservar()
        except Exception as exc:
            st.error(f"No fue posible finalizar la compra: {exc}")
        finally:
            st.session_state["procesando_compra"] = False

        if compra_exitosa:
            st.rerun()

    st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)

    if "mensaje_confirmacion" in st.session_state:
        st.success(st.session_state["mensaje_confirmacion"])
        st.session_state.pop("mensaje_confirmacion", None)

    ventas_alumno = db.compras_por_alumno(
        st.session_state.nombre_vendedor_activo
    )

    if ventas_alumno:

        st.divider()
        st.subheader("Ventas realizadas por este alumno")

        total_ventas = len(ventas_alumno)

        filas = []

        for i, compra in enumerate(ventas_alumno, start=1):

            numero_venta = total_ventas - i + 1

            estado = (
                "🟥 Pagado"
                if compra["pagado"] == "Sí"
                else "🟨 Pendiente"
            )

            filas.append({
                "N° venta": numero_venta,
                "ID compra": compra["id_compra"],
                "Fecha y hora": compra["fecha_hora_compra"],
                "Comprador": compra["comprador"],
                "Estado": estado,
                "Números": compra["numeros"]
            })

        df_ventas = pd.DataFrame(filas)

        html_tabla = """
        <style>
        .tabla-ventas {
            width: 100%;
            border-collapse: collapse;
            border-radius: 12px;
            overflow: hidden;
            font-size: 15px;
            margin-top: 10px;
            margin-bottom: 20px;
        }

        .tabla-ventas th {
            background-color: #f3f4f6;
            font-weight: 700;
            text-align: center;
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }

       .tabla-ventas td {
            text-align: center;
            padding: 11px;
            border-bottom: 1px solid #e5e7eb;
            background-color: #ffffff !important;
            color: #111827 !important;
        }

        .tabla-ventas tr:nth-child(even) {
            background-color: #f9fafb !important;
        }

        .tabla-ventas tr:hover {
            background-color: #eaf2ff !important;
            color: #111827 !important;
        }
        </style>

        <table class="tabla-ventas">
            <thead>
                <tr>
        """

        for col in df_ventas.columns:
            html_tabla += f"<th>{col}</th>"

        html_tabla += "</tr></thead><tbody>"

        for _, row in df_ventas.iterrows():

            html_tabla += "<tr>"

            for col in df_ventas.columns:
                html_tabla += f"<td>{row[col]}</td>"

            html_tabla += "</tr>"

        html_tabla += "</tbody></table>"

        components.html(html_tabla, height=450, scrolling=True)