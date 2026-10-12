import streamlit as st


def show_nav() -> None:
    c1, c2 = st.columns(2)
    c1.page_link("app.py", label="Autos en taller", icon="🚗")
    c2.page_link("pages/1_Registrar_ingreso.py", label="Registrar ingreso", icon="📝")