import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import random
from io import BytesIO


import db

def dataframe_a_excel(df: pd.DataFrame):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="datos")

    return output.getvalue()

def dataframe_a_excel(df: pd.DataFrame):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="numeros")

    return output.getvalue()

def mostrar_tabla_estilizada(df: pd.DataFrame, height: int = 260):
    html = """
    <style>
    .tabla-estilizada {
        width: 100%;
        border-collapse: collapse;
        border-radius: 12px;
        overflow: hidden;
        font-size: 15px;
        margin-top: 10px;
        margin-bottom: 20px;
    }

    .tabla-estilizada th {
        background-color: #f3f4f6;
        font-weight: 700;
        text-align: center;
        padding: 12px;
        border-bottom: 1px solid #e5e7eb;
    }

    .tabla-estilizada td {
        text-align: center;
        padding: 11px;
        border-bottom: 1px solid #e5e7eb;
    }

    .tabla-estilizada tr:nth-child(even) {
        background-color: #fafafa;
    }

    .tabla-estilizada tr:hover {
        background-color: #f1f5f9;
    }
    </style>

    <table class="tabla-estilizada">
        <thead>
            <tr>
    """

    for col in df.columns:
        html += f"<th>{col}</th>"

    html += """
            </tr>
        </thead>
        <tbody>
    """

    for _, row in df.iterrows():
        html += "<tr>"
        for col in df.columns:
            html += f"<td>{row[col]}</td>"
        html += "</tr>"

    html += """
        </tbody>
    </table>
    """

    components.html(html, height=height, scrolling=True)

def render_administrador():
    col_logo, col_titulo = st.columns([1, 8])

    with col_logo:
        st.image("logo.png", width=120)

    with col_titulo:
        st.markdown(
            "<h1 style='margin-top:10px;'>Perfil administrador</h1>",
            unsafe_allow_html=True
        )

    tab1, tab2, tab3, tab4 = st.tabs([
        "Gestión de compras",
        "Resumen",
        "Tirar rifa",
        "Administración"        
    ])

    with tab1:
        render_gestion_compras()

    with tab2:
        render_resumen()

    with tab3:
        render_tirar_rifa()

    with tab4:
        render_administracion()

def render_gestion_compras():
    st.subheader("Compras activas pendientes de pago")

    pendientes = db.compras_pendientes()

    if not pendientes:
        st.info("No hay compras pendientes con números reservados vigentes.")
    else:
        for compra in pendientes:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns(4)
                col1.write("**ID compra**")
                col1.caption(compra["id_compra"])
                col2.metric("Cantidad", compra["cantidad"])
                col3.metric("Total a pagar", f"${compra['total']:,.0f}".replace(",", "."))
                col4.metric("Minutos restantes", compra["tiempo_restante_min"])

                st.write(f"**Vendedor:** {compra['nombre_alumno_vendedor']}")
                st.write(f"**Fecha compra:** {compra['fecha_hora_compra']}")

                with st.expander("Confirmar pago"):
                    forma_pago = st.selectbox(
                        "Forma de pago",
                        ["", "Efectivo", "Transferencia"],
                        key=f"forma_{compra['id_compra']}",
                        format_func=lambda x: "Seleccione una opción" if x == "" else x
                    )

                    if st.button(
                        "Confirmar",
                        key=f"confirmar_{compra['id_compra']}",
                        type="primary",
                        disabled=forma_pago == ""
                    ):
                        db.confirmar_pago_compra(compra["id_compra"], forma_pago)
                        st.success("Pago confirmado. Todos los números de la compra quedaron pagados.")
                        st.rerun()

    st.divider()

    with st.expander("Compras pagadas"):
        pagadas = db.compras_pagadas()

        if not pagadas:
            st.info("Aún no hay compras pagadas.")
        else:
            df = pd.DataFrame(pagadas)
            columnas = [
                "id_compra",
                "fecha_hora_compra",
                "nombre_alumno_vendedor",
                "forma_pago",
                "cantidad",
                "total",
                "numeros"
            ]
            df = df.rename(columns={
                "id_compra": "ID compra",
                "fecha_hora_compra": "Fecha compra",
                "nombre_alumno_vendedor": "Vendedor",
                "forma_pago": "Forma pago",
                "cantidad": "Cantidad",
                "total": "Total",
                "numeros": "Números"
            })
            mostrar_tabla_estilizada(
                df[
                    [
                        "ID compra",
                        "Fecha compra",
                        "Vendedor",
                        "Forma pago",
                        "Cantidad",
                        "Total",
                        "Números"
                    ]
                ],
                height=320
            )


def render_dashboard_visual():
    st.divider()
    st.subheader("Tablas resumen")

    datos = db.dashboard_admin()
    df = pd.DataFrame(datos["numeros"])

    if df.empty:
        st.info("No hay datos para mostrar.")
        return

    st.markdown("### Números por estado")

    tabla_estado = (
        df.groupby("estado")
        .size()
        .reset_index(name="cantidad")
        .sort_values("estado")
    )

    tabla_estado = tabla_estado.rename(columns={
        "estado": "Estado",
        "cantidad": "Cantidad"
    })
    
    mostrar_tabla_estilizada(tabla_estado, height=220)

    st.markdown("### Números asociados por vendedor")

    df_vendedor = df[df["vendedor"].notna()].copy()

    if df_vendedor.empty:
        st.info("Aún no hay números asociados a vendedores.")
    else:
        tabla_vendedor = (
            df_vendedor
            .groupby(["vendedor", "estado"])
            .size()
            .reset_index(name="cantidad")
            .sort_values(["vendedor", "estado"])
        )

        tabla_vendedor = tabla_vendedor.rename(columns={
            "vendedor": "Vendedor",
            "estado": "Estado",
            "cantidad": "Cantidad"
        })

        mostrar_tabla_estilizada(tabla_vendedor, height=250)

def render_resumen():
    st.subheader("Estado de números")

    estados = db.resumen_estados()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total números pagados", estados["pagados"])
    c2.metric("Total números reservados", estados["reservados"])
    c3.metric("Total números disponibles", estados["disponibles"])

    st.divider()
    st.subheader("Recaudación")

    rec = db.resumen_recaudacion()
    r1, r2, r3 = st.columns(3)
    r1.metric("Monto recaudado en efectivo", f"${rec['efectivo']:,.0f}".replace(",", "."))
    r2.metric("Monto recaudado por transferencia", f"${rec['transferencia']:,.0f}".replace(",", "."))
    r3.metric("Monto total recaudado", f"${rec['total']:,.0f}".replace(",", "."))
    
    render_dashboard_visual()


def render_administracion():
    st.subheader("Configuración de la rifa")

    config = db.obtener_configuracion()

    with st.form("form_configuracion"):
        n = st.number_input("Cantidad total de números (n)", min_value=1, step=1, value=int(config["n"]))
        p = st.number_input("Precio por número (p)", min_value=0, step=100, value=int(config["p"]))
        t_horas = st.number_input(
            "Tiempo máximo de reserva en horas",
            min_value=1,
            step=1,
            value=max(1, int(config["t"]) // 60)
        )

        t = t_horas * 60

        clave_vendedor = st.text_input("Clave vendedor", value=config.get("clave_vendedor", ""), type="password")
        clave_admin = st.text_input("Clave administrador", value=config.get("clave_admin", ""), type="password")

        guardar = st.form_submit_button("Guardar configuración", type="primary")

    if guardar:
        n_actual = int(config["n"])

        n_final = int(n)

        db.guardar_configuracion(
            n=n_final,
            p=int(p),
            t=int(t),
            clave_vendedor=clave_vendedor,
            clave_admin=clave_admin
        )

        
        if n_final < n_actual:
            db.reiniciar_numeros_rifa(n_final)
            insertados = n_final
        else:
            insertados = db.asegurar_numeros_hasta_n(n_final)

        if insertados > 0:
            st.success(f"Configuración guardada. Se agregaron {insertados} números nuevos.")
        else:
            st.success("Configuración guardada. No fue necesario agregar números nuevos.")

        st.rerun()

    st.divider()
    st.subheader("Exportación")

    datos_numeros = db.exportar_todos_los_numeros()
    df_numeros = pd.DataFrame(datos_numeros)

    excel_numeros = dataframe_a_excel(df_numeros)

    st.download_button(
        label="📥 Descargar todos los números en Excel",
        data=excel_numeros,
        file_name="todos_los_numeros_rifa.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def render_tirar_rifa():

    config = db.obtener_configuracion()
    n = int(config["n"])

    st.markdown(
        f"""
        <h1 style='text-align:center; color:#1565C0;'>
            Sorteo de la rifa
        </h1>

        <p style='
            text-align:center;
            color:#1565C0;
            font-size:18px;
            margin-bottom:30px;
        '>
            Al apretar el botón rojo se generará un número aleatorio entre
            <strong>1</strong> y <strong>{n}</strong>.
        </p>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([2, 1, 2])

    with col2:
        if st.button("🎰 Sacar un número", type="primary", width="stretch"):
            st.session_state["numero_ganador"] = random.randint(1, n)

    ganador = st.session_state.get("numero_ganador")

    if ganador is not None:

        html_ganador = f"""
        <div style="
            max-width: 420px;
            margin: 28px auto;
            background: linear-gradient(135deg, #1565C0, #42A5F5);
            border-radius: 28px;
            padding: 34px 26px;
            text-align: center;
            color: white;
            box-shadow: 0 16px 36px rgba(21,101,192,0.35);
        ">

            <div style="
                font-size:18px;
                font-weight:700;
                letter-spacing:1px;
                text-transform:uppercase;
                opacity:0.9;
            ">
                🎉 Número ganador 🎉
            </div>

            <div style="
                font-size:96px;
                font-weight:900;
                line-height:1;
                margin:18px 0;
            ">
                {ganador}
            </div>

            <div style="
                font-size:15px;
                opacity:0.9;
            ">
                Resultado generado aleatoriamente
            </div>

        </div>
        """

        components.html(html_ganador, height=320)