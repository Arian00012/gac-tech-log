import streamlit as st


def show_nav() -> None:
    c1, c2, c3 = st.columns(3)
    c1.page_link("app.py", label="En taller", icon="🚗")
    c2.page_link("pages/1_Registrar_ingreso.py", label="Ingreso", icon="📝")
    c3.page_link("pages/2_Buscar_VIN.py", label="Buscar", icon="🔎")