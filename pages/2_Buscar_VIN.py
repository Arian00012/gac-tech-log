from datetime import datetime, timezone

import streamlit as st

from auth import require_login
from constants import (
    ENTRY_TYPE_LABELS,
    POWERTRAIN_LABELS,
    STATUS_ICONS,
    STATUS_LABELS,
)
from nav import show_nav
from queries import (
    find_vehicle,
    get_checklist_for_stays,
    get_dtcs,
    get_status_log,
    get_stays_for_vehicle,
)
from utils import fmt_dt, normalize_vin

st.set_page_config(page_title="Buscar VIN", page_icon="🔎")

require_login()
show_nav()

st.title("🔎 Historia por VIN")

raw_vin = st.text_input(
    "VIN (se usan los últimos 8 caracteres)",
    placeholder="Pega el VIN completo o solo los últimos 8",
)
if not raw_vin:
    st.stop()

vin = normalize_vin(raw_vin)
if vin is None:
    st.error("El VIN debe tener al menos 8 letras o números.")
    st.stop()

vehicle = find_vehicle(vin)
if vehicle is None:
    st.info(f"No hay historia para **{vin}**. Se abre al registrar su primer ingreso.")
    st.page_link("pages/1_Registrar_ingreso.py", label="Registrar ingreso", icon="📝")
    st.stop()

st.subheader(vin)
bits = []
if vehicle.get("model"):
    bits.append(vehicle["model"])
if vehicle.get("powertrain"):
    bits.append(POWERTRAIN_LABELS[vehicle["powertrain"]])
colors = " / ".join(
    c for c in (vehicle.get("exterior_color"), vehicle.get("interior_color")) if c
)
if colors:
    bits.append(f"Color: {colors}")
if bits:
    st.caption(" · ".join(bits))

stays = get_stays_for_vehicle(vehicle["id"])
ids = [s["id"] for s in stays]
checklists = get_checklist_for_stays(ids)
dtcs = get_dtcs(ids)
logs = get_status_log(ids)

st.metric("Ingresos registrados", len(stays))

now = datetime.now(timezone.utc)
CHECK_ICONS = {"present": "✅", "missing": "❌", "arrived_later": "✅"}
CHECK_TEXT = {"present": "Tiene", "missing": "Falta", "arrived_later": "Llegó después"}


def show_text(label: str, text: str | None) -> None:
    if text:
        st.markdown(f"**{label}**")
        st.write(text)


for i, s in enumerate(stays):
    sid = s["id"]
    title = (
        f"{fmt_dt(s['entered_at'])} · {ENTRY_TYPE_LABELS[s['entry_type']]} · "
        f"{STATUS_ICONS[s['status']]} {STATUS_LABELS[s['status']]}"
    )
    with st.expander(title, expanded=(i == 0)):
        start = datetime.fromisoformat(s["entered_at"])
        end = datetime.fromisoformat(s["exited_at"]) if s.get("exited_at") else now
        st.write(f"📥 Entrada: {fmt_dt(s['entered_at'])}")
        if s.get("exited_at"):
            st.write(f"📤 Salida: {fmt_dt(s['exited_at'])}")
        else:
            st.write("📤 Sigue en el taller")
        st.write(f"⏱ {(end - start).days} día(s) en taller")

        if s.get("ot_number"):
            st.write(f"📋 OT: {s['ot_number']}")
        if s.get("odometer_km") is not None:
            st.write(f"🛣 Odómetro: {s['odometer_km']} km")
        if s.get("location"):
            st.write(f"📍 {s['location']}")
        battery = []
        if s.get("battery_pct_arrival") is not None:
            battery.append(f"{s['battery_pct_arrival']}%")
        if s.get("battery_km_arrival") is not None:
            battery.append(f"{s['battery_km_arrival']} km")
        if battery:
            st.write("🔋 Batería al llegar: " + " · ".join(battery))

        show_text("Estado de llegada", s.get("arrival_condition"))
        show_text("Trabajo solicitado", s.get("requested_work"))

        if checklists.get(sid):
            st.markdown("**Checklist de llegada**")
            for row in checklists[sid]:
                line = (
                    f"{CHECK_ICONS[row['state']]} {row['checklist_items']['label']}"
                    f" — {CHECK_TEXT[row['state']]}"
                )
                if row["state"] == "arrived_later":
                    line += f" ({fmt_dt(row['updated_at'])})"
                st.write(line)

        if dtcs.get(sid):
            st.markdown("**Códigos DTC**")
            for d in dtcs[sid]:
                line = f"`{d['code']}`"
                if d.get("description"):
                    line += f" — {d['description']}"
                if d.get("note"):
                    line += f" ({d['note']})"
                st.markdown(line)

        show_text("Diagnóstico", s.get("diagnosis"))
        show_text("Trabajo realizado", s.get("work_done"))
        show_text("Notas", s.get("notes"))

        if logs.get(sid):
            st.markdown("**Bitácora de estados**")
            for row in logs[sid]:
                line = (
                    f"{fmt_dt(row['changed_at'])} — "
                    f"{STATUS_ICONS.get(row['status'], '')} "
                    f"{STATUS_LABELS.get(row['status'], row['status'])}"
                )
                if row.get("note"):
                    line += f" · {row['note']}"
                st.write(line)