import streamlit as st


def show_nav() -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.page_link("app.py", label="Taller", icon=":material/directions_car:")
    c2.page_link(
        "pages/1_Registrar_ingreso.py", label="Ingreso", icon=":material/add_circle:"
    )
    c3.page_link("pages/2_Buscar_VIN.py", label="Buscar", icon=":material/search:")
    c4.page_link("pages/3_Catalogo.py", label="Catálogo", icon=":material/checklist:")