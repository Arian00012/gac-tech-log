import hmac
import streamlit as st


def require_login() -> None:
    """Detiene la app hasta que se ingrese la contraseña correcta."""
    if st.session_state.get("authenticated"):
        return

    st.title("GAC Tech Log")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar", type="primary"):
        if hmac.compare_digest(password, st.secrets["APP_PASSWORD"]):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta")

    st.stop()