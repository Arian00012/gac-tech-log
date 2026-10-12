from datetime import datetime, timezone

import streamlit as st

from auth import require_login
from constants import ENTRY_TYPE_LABELS, STATUS_ICONS, STATUS_LABELS
from nav import show_nav
from queries import (
    get_missing_items,
    get_open_stays,
    mark_item_arrived,
    register_exit,
    update_battery,
    update_location,
    update_status,
)

st.set_page_config(page_title="GAC Tech Log", page_icon="🚗")

require_login()
show_nav()

flash = st.session_state.pop("flash", None)
if flash:
    st.toast(flash, icon="✅")

st.title("🚗 Autos en el taller")

if st.button("Actualizar"):
    st.rerun()

stays = get_open_stays()
missing_by_stay = get_missing_items([s["id"] for s in stays])

st.metric("Autos actualmente en el taller", len(stays))

if not stays:
    st.info("No hay autos en el taller en este momento.")
    st.stop()

# Filtro por estado, mostrando cuántos hay en cada uno
counts = {}
for s in stays:
    counts[s["status"]] = counts.get(s["status"], 0) + 1

selected = st.pills(
    "Filtrar por estado",
    options=list(counts.keys()),
    format_func=lambda k: f"{STATUS_ICONS[k]} {STATUS_LABELS[k]} ({counts[k]})",
    selection_mode="multi",
)

visible = [s for s in stays if not selected or s["status"] in selected]

active_statuses = [k for k in STATUS_LABELS if k != "delivered"]
now = datetime.now(timezone.utc)


def done(message: str) -> None:
    st.session_state["flash"] = message
    st.rerun()


for s in visible:
    sid = s["id"]
    v = s["vehicles"]
    missing = missing_by_stay.get(sid, [])
    days = (now - datetime.fromisoformat(s["entered_at"])).days

    with st.container(border=True):
        st.markdown(f"**{v['vin']}**")
        st.markdown(f"{STATUS_ICONS[s['status']]} **{STATUS_LABELS[s['status']]}**")

        details = [ENTRY_TYPE_LABELS[s["entry_type"]]]
        if v.get("model"):
            details.append(v["model"])
        colors = " / ".join(
            c for c in (v.get("exterior_color"), v.get("interior_color")) if c
        )
        if colors:
            details.append(f"Color: {colors}")
        st.caption(" · ".join(details))

        info = [f"📅 {days} día(s) en taller"]
        if s.get("location"):
            info.append(f"📍 {s['location']}")
        battery = []
        if s.get("battery_pct_current") is not None:
            battery.append(f"{s['battery_pct_current']}%")
        if s.get("battery_km_current") is not None:
            battery.append(f"{s['battery_km_current']} km")
        if battery:
            info.append("🔋 " + " · ".join(battery))
        st.write("  ·  ".join(info))

        if missing:
            st.warning("Falta: " + ", ".join(m["label"] for m in missing))
        if s.get("notes"):
            st.caption(f"📝 {s['notes']}")

        with st.expander("Gestionar"):
            t_state, t_loc, t_bat, t_chk, t_exit = st.tabs(
                ["🔄 Estado", "📍 Lugar", "🔋 Batería", "🧾 Faltantes", "📤 Salida"]
            )

            with t_state:
                with st.form(f"state_form_{sid}"):
                    new_status = st.selectbox(
                        "Nuevo estado",
                        options=active_statuses,
                        index=active_statuses.index(s["status"]),
                        format_func=lambda k: f"{STATUS_ICONS[k]} {STATUS_LABELS[k]}",
                        key=f"state_sel_{sid}",
                    )
                    note = st.text_input("Nota (opcional)", key=f"state_note_{sid}")
                    if st.form_submit_button("Guardar estado"):
                        if new_status == s["status"] and not note.strip():
                            st.info("Sin cambios.")
                        else:
                            update_status(sid, new_status, note.strip())
                            done("Estado actualizado")

            with t_loc:
                with st.form(f"loc_form_{sid}"):
                    new_loc = st.text_input(
                        "Ubicación actual",
                        value=s.get("location") or "",
                        key=f"loc_in_{sid}",
                    )
                    if st.form_submit_button("Guardar ubicación"):
                        update_location(sid, new_loc.strip())
                        done("Ubicación actualizada")

            with t_bat:
                with st.form(f"bat_form_{sid}"):
                    b1, b2 = st.columns(2)
                    new_pct = b1.number_input(
                        "Carga (%)",
                        min_value=0,
                        max_value=100,
                        value=s.get("battery_pct_current"),
                        step=1,
                        key=f"bat_pct_{sid}",
                    )
                    new_km = b2.number_input(
                        "Autonomía (km)",
                        min_value=0,
                        value=s.get("battery_km_current"),
                        step=1,
                        key=f"bat_km_{sid}",
                    )
                    if st.form_submit_button("Guardar batería"):
                        update_battery(sid, new_pct, new_km)
                        done("Batería actualizada")

            with t_chk:
                if not missing:
                    st.caption("Sin faltantes en este auto.")
                for m in missing:
                    if st.button(f"✔ Llegó: {m['label']}", key=f"arrived_{m['id']}"):
                        mark_item_arrived(m["id"])
                        done(f"Llegó: {m['label']}")

            with t_exit:
                if missing:
                    st.warning(
                        "Sale con faltantes: " + ", ".join(m["label"] for m in missing)
                    )
                with st.form(f"exit_form_{sid}"):
                    exit_note = st.text_input(
                        "Nota de salida (opcional)", key=f"exit_note_{sid}"
                    )
                    confirm = st.checkbox(
                        "Confirmo la salida de este auto del taller",
                        key=f"exit_ok_{sid}",
                    )
                    if st.form_submit_button("Registrar salida"):
                        if not confirm:
                            st.error("Marca la confirmación para registrar la salida.")
                        else:
                            register_exit(sid, exit_note.strip())
                            done("Salida registrada")