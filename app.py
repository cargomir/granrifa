import streamlit as st
import db
from vendedor import render_vendedor
from administrador import render_administrador


st.set_page_config(
    page_title="Gestión de Rifa",
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

        st.markdown(
            """
            <p style='
                text-align: center;
                font-weight: bold;
                color: #1565C0;
                font-size: 30px;
                margin-bottom: 6px;
            '>
            Bienvenido a la gran rifa del 8° A del Colegio Gabriela Mistral
            </p>

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

        config = db.obtener_configuracion()

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
            ["Alumno", "Administrador"],
            horizontal=True
        )

        nombre_alumno = None

        if perfil == "Alumno":
            alumnos = db.listar_alumnos()

            if not alumnos:
                st.warning("No hay alumnos cargados en la tabla 'alumnos'.")
                return

            nombre_alumno = st.selectbox(
                options=[None] + alumnos,
                format_func=lambda x: "Selecciona el nombre del estudiante al que le comprarás los números" if x is None else x
            )

        clave = st.text_input(
            "Contraseña",
            type="password"
        )

        if st.button("Ingresar", type="primary", width="stretch"):

            if perfil == "Alumno" and nombre_alumno is not None and clave == config["clave_vendedor"]:
                st.session_state.autenticado = True
                st.session_state.perfil = "vendedor"
                st.session_state.nombre_vendedor_activo = nombre_alumno
                st.success("Acceso alumno correcto.")
                st.rerun()

            elif perfil == "Administrador" and clave == config["clave_admin"]:
                st.session_state.autenticado = True
                st.session_state.perfil = "administrador"
                st.success("Acceso administrador correcto.")
                st.rerun()

            else:
                st.error("Contraseña incorrecta.")

def barra_superior():

    col_vacia, col_boton = st.columns([8, 1])

    with col_boton:
        if st.button("Cerrar sesión", type="primary", width="stretch"):
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
