import streamlit as st

LINKS = [
    ("app.py", "Taller", ":material/directions_car:"),
    ("pages/1_Registrar_ingreso.py", "Ingreso", ":material/add_circle:"),
    ("pages/2_Buscar_VIN.py", "Buscar", ":material/search:"),
    ("pages/4_Verificar_lista.py", "Verificar", ":material/fact_check:"),
    ("pages/3_Catalogo.py", "Catálogo", ":material/checklist:"),
]


def show_nav() -> None:
    try:
        box = st.container(horizontal=True)
    except TypeError:  # Streamlit antiguo: se apila en vertical
        box = st.container()
    with box:
        for path, label, icon in LINKS:
            st.page_link(path, label=label, icon=icon)