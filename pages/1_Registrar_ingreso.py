import streamlit as st

from auth import require_login
from constants import (
    ENTRY_TYPE_LABELS,
    FUEL_LEVELS,
    HAS_CHARGE,
    HAS_FUEL,
    POWERTRAIN_LABELS,
    STATUS_LABELS,
)
from nav import show_nav
from queries import (
    count_stays,
    find_vehicle,
    get_active_checklist_items,
    has_open_stay,
    register_entry,
)
from utils import normalize_vin

st.set_page_config(page_title="Registrar ingreso", page_icon=":material/add_circle:")

require_login()
show_nav()

st.title("Registrar ingreso")

flash = st.session_state.pop("flash", None)
if flash:
    st.success(flash)

# El contador permite vaciar todo solo cuando el registro fue exitoso
n = st.session_state.get("form_n", 0)

# --- 1. VIN: se evalúa fuera del formulario para reconocer la historia ---
raw_vin = st.text_input(
    "VIN (se guardan los últimos 8 caracteres)",
    placeholder="Pega el VIN completo o solo los últimos 8",
    key=f"vin_{n}",
)
vin = normalize_vin(raw_vin)

if not raw_vin:
    st.stop()

if vin is None:
    st.error("El VIN debe tener al menos 8 letras o números.")
    st.stop()

existing = find_vehicle(vin)

if existing is None:
    st.info(f"**{vin}**: vehículo nuevo. Se abrirá su historia.")
elif has_open_stay(existing["id"]):
    st.error(f"**{vin}** ya está en el taller con un ingreso abierto.")
    st.stop()
else:
    visits = count_stays(existing["id"])
    st.success(
        f"**{vin}**: ya tiene historia ({visits} ingreso(s) anterior(es)). "
        "Este será un ingreso nuevo."
    )

ex = existing or {}
suffix = f"{n}_{vin}"  # al cambiar el VIN, los campos se reinician con los datos correctos

# --- 2. Datos que cambian los campos del formulario (también fuera del form) ---
entry_type = st.radio(
    "Tipo de ingreso",
    options=list(ENTRY_TYPE_LABELS),
    format_func=ENTRY_TYPE_LABELS.get,
    horizontal=True,
    key=f"type_{suffix}",
)

pt_options = list(POWERTRAIN_LABELS)
pt_default = (
    pt_options.index(ex["powertrain"]) if ex.get("powertrain") in pt_options else None
)
powertrain = st.selectbox(
    "Tipo de motorización",
    options=pt_options,
    index=pt_default,
    format_func=POWERTRAIN_LABELS.get,
    placeholder="Elige una opción",
    key=f"pt_{suffix}",
)

items = get_active_checklist_items() if entry_type == "PDI" else []
initial_statuses = [k for k in STATUS_LABELS if k != "delivered"]

# --- 3. Formulario ---
with st.form(f"entry_form_{suffix}"):
    model = st.text_input("Modelo", value=ex.get("model") or "", key=f"model_{suffix}")
    c1, c2 = st.columns(2)
    exterior = c1.text_input(
        "Color exterior", value=ex.get("exterior_color") or "", key=f"ext_{suffix}"
    )
    interior = c2.text_input(
        "Color interior", value=ex.get("interior_color") or "", key=f"int_{suffix}"
    )

    odometer = st.number_input(
        "Odómetro (km)", min_value=0, value=None, step=1, key=f"odo_{suffix}"
    )
    arrival_condition = st.text_area(
        "Estado de llegada (golpes, rayones, observaciones graves)",
        key=f"cond_{suffix}",
    )

    ot_number = ""
    requested_work = ""
    if entry_type != "PDI":
        st.subheader("Orden de trabajo")
        ot_number = st.text_input("N° de OT", key=f"ot_{suffix}")
        requested_work = st.text_area("Trabajo solicitado en la OT", key=f"work_{suffix}")

    pct = None
    km = None
    fuel_level = None
    if powertrain in HAS_CHARGE or powertrain in HAS_FUEL:
        st.subheader("Energía")
    if powertrain in HAS_CHARGE:
        b1, b2 = st.columns(2)
        pct = b1.number_input(
            "Carga (%)", min_value=0, max_value=100, value=None, step=1, key=f"pct_{suffix}"
        )
        km = b2.number_input(
            "Autonomía (km)", min_value=0, value=None, step=1, key=f"km_{suffix}"
        )
    if powertrain in HAS_FUEL:
        fuel_level = st.radio(
            "Combustible (tanque)",
            options=FUEL_LEVELS,
            index=None,
            horizontal=True,
            key=f"fuel_{suffix}",
        )

    status = st.selectbox(
        "Estado inicial",
        options=initial_statuses,
        format_func=STATUS_LABELS.get,
        key=f"status_{suffix}",
    )
    location = st.text_input("Ubicación actual (opcional)", key=f"loc_{suffix}")

    checklist = {}
    if items:
        st.subheader("Checklist de llegada")
        for item in items:
            checklist[item["id"]] = st.radio(
                item["label"],
                options=["present", "missing"],
                format_func={"present": "Tiene", "missing": "Falta"}.get,
                horizontal=True,
                key=f"chk_{item['code']}_{suffix}",
            )

    notes = st.text_area("Notas", key=f"notes_{suffix}")
    submitted = st.form_submit_button("Registrar ingreso", type="primary")

if submitted:
    if powertrain is None:
        st.error("Elige el tipo de motorización.")
        st.stop()

    try:
        register_entry(
            vin=vin,
            entry_type=entry_type,
            status=status,
            powertrain=powertrain,
            model=model.strip(),
            exterior_color=exterior.strip(),
            interior_color=interior.strip(),
            odometer_km=odometer,
            arrival_condition=arrival_condition.strip(),
            ot_number=ot_number.strip(),
            requested_work=requested_work.strip(),
            location=location.strip(),
            battery_pct=pct,
            battery_km=km,
            fuel_level=fuel_level,
            notes=notes.strip(),
            checklist=checklist,
        )
    except Exception as e:
        st.error(f"No se pudo registrar: {e}")
        st.stop()

    st.session_state["flash"] = f"Ingreso registrado: {vin}"
    st.session_state["form_n"] = n + 1
    st.rerun()