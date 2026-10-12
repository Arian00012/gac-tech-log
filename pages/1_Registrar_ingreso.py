import re
from nav import show_nav
import streamlit as st

from auth import require_login
from constants import ENTRY_TYPE_LABELS, STATUS_ICONS, STATUS_LABELS
from queries import (
    find_vehicle,
    get_active_checklist_items,
    has_open_stay,
    register_entry,
)

st.set_page_config(page_title="Registrar ingreso", page_icon="📝")

require_login()
show_nav()

st.title("📝 Registrar ingreso")

# Mensaje de éxito del registro anterior
flash = st.session_state.pop("flash", None)
if flash:
    st.success(flash)
    st.page_link("app.py", label="Ver autos en el taller", icon="🚗")

# El contador permite vaciar el formulario solo cuando el registro fue exitoso
n = st.session_state.get("form_n", 0)

items = get_active_checklist_items()
initial_statuses = [k for k in STATUS_LABELS if k != "delivered"]

with st.form(f"entry_form_{n}"):
    vin = st.text_input("VIN", max_chars=17, placeholder="17 caracteres", key=f"vin_{n}")
    entry_type = st.radio(
        "Tipo de ingreso",
        options=list(ENTRY_TYPE_LABELS),
        format_func=ENTRY_TYPE_LABELS.get,
        horizontal=True,
        key=f"type_{n}",
    )
    model = st.text_input("Modelo", key=f"model_{n}")
    c1, c2 = st.columns(2)
    exterior = c1.text_input("Color exterior", key=f"ext_{n}")
    interior = c2.text_input("Color interior", key=f"int_{n}")

    st.subheader("Batería")
    b1, b2 = st.columns(2)
    pct = b1.number_input(
        "Carga (%)", min_value=0, max_value=100, value=None, step=1, key=f"pct_{n}"
    )
    km = b2.number_input(
        "Autonomía (km)", min_value=0, value=None, step=1, key=f"km_{n}"
    )

    status = st.selectbox(
        "Estado inicial",
        options=initial_statuses,
        format_func=lambda k: f"{STATUS_ICONS[k]} {STATUS_LABELS[k]}",
        key=f"status_{n}",
    )
    location = st.text_input("Ubicación actual (opcional)", key=f"loc_{n}")

    st.subheader("Checklist de llegada")
    checklist = {}
    for item in items:
        checklist[item["id"]] = st.radio(
            item["label"],
            options=["present", "missing"],
            format_func={"present": "Tiene", "missing": "Falta"}.get,
            horizontal=True,
            key=f"chk_{item['code']}_{n}",
        )

    notes = st.text_area("Notas", key=f"notes_{n}")
    submitted = st.form_submit_button("Registrar ingreso", type="primary")

if submitted:
    vin_clean = vin.strip().upper()

    if not re.fullmatch(r"[A-Z0-9]{17}", vin_clean):
        st.error("El VIN debe tener exactamente 17 caracteres (letras y números).")
        st.stop()

    existing = find_vehicle(vin_clean)
    if existing and has_open_stay(existing["id"]):
        st.error("Este VIN ya tiene un ingreso abierto: el auto sigue en el taller.")
        st.stop()

    try:
        register_entry(
            vin=vin_clean,
            entry_type=entry_type,
            status=status,
            model=model.strip(),
            exterior_color=exterior.strip(),
            interior_color=interior.strip(),
            location=location.strip(),
            battery_pct=pct,
            battery_km=km,
            notes=notes.strip(),
            checklist=checklist,
        )
    except Exception as e:
        st.error(f"No se pudo registrar: {e}")
        st.stop()

    st.session_state["flash"] = f"Ingreso registrado: {vin_clean}"
    st.session_state["form_n"] = n + 1
    st.rerun()