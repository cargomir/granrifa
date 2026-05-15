import streamlit as st
import pandas as pd
import db
from vendedor import render_vendedor
from administrador import render_administrador


st.set_page_config(
    page_title="La Gran Rifa",
    page_icon="🎟️",
    layout="wide"
)


def inicializar_estado():
    st.session_state.setdefault("autenticado", False)
    st.session_state.setdefault("perfil", None)


def cerrar_sesion():
    claves_a_borrar = [
        "autenticado",
        "perfil",
        "id_compra_activa",
        "nombre_vendedor_activo",
        "nombre_comprador_input",
        "telefono_input",
        "correo_input",
        "comprador_buscado",
    ]

    for k in claves_a_borrar:
        st.session_state.pop(k, None)

    st.rerun()


def login():

    col1, col2, col3 = st.columns([1,2,1])

    with col2:

        logo1, logo2, logo3 = st.columns([1,2,1])

        with logo2:
            st.image("logo.png", width=350)
        
        config = db.obtener_configuracion()

        st.markdown(
            f"""
            <p style='
                text-align: center;
                font-weight: bold;
                color: #1565C0;
                font-size: 30px;
                margin-bottom: 6px;
            '>
            {config.get("bienvenida", "Bienvenido a la gran rifa")}
            </p>
            """,
            unsafe_allow_html=True
        )

        premios = config.get("premios")
        fecha_rifa = config.get("fecha_rifa")

        if fecha_rifa:
            fecha_dt = pd.to_datetime(fecha_rifa)

            meses = {
                1: "enero",
                2: "febrero",
                3: "marzo",
                4: "abril",
                5: "mayo",
                6: "junio",
                7: "julio",
                8: "agosto",
                9: "septiembre",
                10: "octubre",
                11: "noviembre",
                12: "diciembre"
            }

            fecha_rifa = (
                f"{fecha_dt.day} de "
                f"{meses[fecha_dt.month]} "
                f"{fecha_dt.year}"
            )

        if premios or fecha_rifa:
            st.markdown(
                f"""
                <div style="
                    background-color:#E3F2FD;
                    border:2px solid #1565C0;
                    border-radius:14px;
                    padding:16px;
                    margin:16px 0 16px 0;
                    color:#0D47A1;
                    font-size:17px;
                    text-align:center;
                ">
                    {f"<p><strong>Premios principales:</strong><br>{premios}</p>" if premios else ""}
                    {f"<p><strong>Fecha de lanzamiento:</strong><br>{fecha_rifa}</p>" if fecha_rifa else ""}
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown(
            """
            <p style='
                text-align: center;
                font-weight: bold;
                color: #D32F2F;
                font-size: 18px;
                margin-top: 0px;
            '>
            Selecciona tu perfil y luego ingresa tu contraseña
            </p>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown("""
            <style>

            /* Radio buttons */
            div[role="radiogroup"] label {
                background-color: #E3F2FD;
                padding: 10px 18px;
                border-radius: 12px;
                border: 2px solid #1565C0;
                margin-right: 10px;
                color: #1565C0 !important;
                font-weight: bold;
            }

            /* Radio seleccionado */
            div[role="radiogroup"] label[data-baseweb="radio"] input:checked + div {
                color: #1565C0 !important;
            }

            /* Contenedor input */
            div[data-baseweb="input"] {
                border: 2px solid #1565C0 !important;
                border-radius: 10px !important;
                overflow: hidden;
            }

            /* Input interno */
            div[data-baseweb="input"] input {
                border: none !important;
                box-shadow: none !important;
            }

            /* Botón ingresar */
            .stButton > button {
                background-color: #1565C0;
                color: white;
                font-weight: bold;
                border-radius: 12px;
                border: none;
                height: 50px;
                font-size: 18px;
            }

            /* Hover botón */
            .stButton > button:hover {
                background-color: #0D47A1;
                color: white;
            }

            </style>
            """, unsafe_allow_html=True)

        perfil = st.radio(
            "Perfil de acceso",
            ["Alumno/Apoderado", "Administrador"],
            horizontal=True
        )

        nombre_alumno = None

        if perfil == "Alumno/Apoderado":
            alumnos = db.listar_alumnos()

            if not alumnos:
                st.warning("No hay alumnos cargados en la tabla 'alumnos'.")
                return

            nombre_alumno = st.selectbox(
                "Nombre alumno/a",
                alumnos,
                index=None,
                placeholder="Selecciona al estudiante que venderá el número"
            )

        clave = st.text_input(
            "Contraseña",
            type="password"
        )

        if st.button("Ingresar", type="primary", width="stretch"):

            if perfil == "Alumno/Apoderado":

                if nombre_alumno is None:
                    st.error("Debes seleccionar un alumno.")
                    return

                if clave != config["clave_vendedor"]:
                    st.error("Contraseña incorrecta.")
                    return

                st.session_state.autenticado = True
                st.session_state.perfil = "vendedor"
                st.session_state.nombre_vendedor_activo = nombre_alumno
                st.rerun()

            elif perfil == "Administrador" and clave == config["clave_admin"]:
                st.session_state.autenticado = True
                st.session_state.perfil = "administrador"
                st.rerun()

            else:
                st.error("Contraseña incorrecta.")

def barra_superior():

    if st.session_state.perfil == "vendedor":
        titulo = "Perfil vendedor"
    else:
        titulo = "Perfil administrador"

    col_logo, col_titulo, col_boton = st.columns([1, 6, 1])

    with col_logo:
        st.image("logo.png", width=200)

    with col_titulo:
        st.markdown(
            f"<h1 style='margin-top:50px;'>{titulo}</h1>",
            unsafe_allow_html=True
        )

    with col_boton:
        st.markdown(
            """
            <div style='height:80px;'></div>
            """,
            unsafe_allow_html=True
        )

        if st.button(
            "Cerrar sesión",
            type="primary",
            width="stretch"
        ):
            cerrar_sesion()

def main():
    inicializar_estado()

    if not st.session_state.autenticado:
        login()
        return

    barra_superior()

    if st.session_state.perfil == "vendedor":
        render_vendedor()

    elif st.session_state.perfil == "administrador":
        render_administrador()

    else:
        st.error("Perfil no reconocido.")
        cerrar_sesion()


if __name__ == "__main__":
    main()
