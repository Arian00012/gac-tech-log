from datetime import datetime, timezone

import streamlit as st

from auth import require_login
from constants import (
    ENTRY_TYPE_LABELS,
    HAS_CHARGE,
    POWERTRAIN_LABELS,
    STATUS_ICONS,
    STATUS_LABELS,
)
from nav import show_nav
from queries import (
    add_dtc,
    delete_dtc,
    get_dtcs,
    get_missing_items,
    get_open_stays,
    mark_item_arrived,
    register_exit,
    save_diagnosis,
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
stay_ids = [s["id"] for s in stays]
missing_by_stay = get_missing_items(stay_ids)
dtcs_by_stay = get_dtcs(stay_ids)

if not stays:
    st.info("No hay autos en el taller en este momento.")
    st.stop()

# Resumen general y del chapero
to_send = [s for s in stays if s["status"] == "to_bodyshop"]
at_shop = [s for s in stays if s["status"] == "at_bodyshop"]

m1, m2, m3 = st.columns(3)
m1.metric("En taller", len(stays))
m2.metric("Por enviar", len(to_send))
m3.metric("En chapero", len(at_shop))

if to_send:
    st.caption("➡️ Por enviar al chapero: " + ", ".join(s["vehicles"]["vin"] for s in to_send))
if at_shop:
    st.caption("🚚 En chapero: " + ", ".join(s["vehicles"]["vin"] for s in at_shop))

# Filtro por estado, mostrando cuántos hay en cada uno
counts = {}
for s in stays:
    counts[s["status"]] = counts.get(s["status"], 0) + 1

selected = st.pills(
    "Filtrar por estado",
    options=[k for k in STATUS_LABELS if k in counts],
    format_func=lambda k: f"{STATUS_ICONS[k]} {STATUS_LABELS[k]} ({counts[k]})",
    selection_mode="multi",
)

visible = [s for s in stays if not selected or s["status"] in selected]

now = datetime.now(timezone.utc)


def done(message: str) -> None:
    st.session_state["flash"] = message
    st.rerun()


for s in visible:
    sid = s["id"]
    v = s["vehicles"]
    missing = missing_by_stay.get(sid, [])
    stay_dtcs = dtcs_by_stay.get(sid, [])
    days = (now - datetime.fromisoformat(s["entered_at"])).days
    has_charge = v.get("powertrain") in HAS_CHARGE or v.get("powertrain") is None

    with st.container(border=True):
        st.markdown(f"**{v['vin']}**")
        st.markdown(f"{STATUS_ICONS[s['status']]} **{STATUS_LABELS[s['status']]}**")

        details = [ENTRY_TYPE_LABELS[s["entry_type"]]]
        if v.get("powertrain"):
            details.append(POWERTRAIN_LABELS[v["powertrain"]])
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

        if s.get("ot_number") or s.get("requested_work"):
            ot = f"OT {s['ot_number']}" if s.get("ot_number") else "OT"
            if s.get("requested_work"):
                ot += f": {s['requested_work']}"
            st.caption("📋 " + ot)
        if stay_dtcs:
            st.caption("⚠️ DTC: " + ", ".join(d["code"] for d in stay_dtcs))
        if missing:
            st.warning("Falta: " + ", ".join(m["label"] for m in missing))
        if s.get("notes"):
            st.caption(f"📝 {s['notes']}")

        with st.expander("Gestionar"):
            tab_defs = [("state", "🔄 Estado"), ("loc", "📍 Lugar")]
            if has_charge:
                tab_defs.append(("bat", "🔋 Batería"))
            if s["entry_type"] == "PDI":
                tab_defs.append(("chk", "🧾 Faltantes"))
            tab_defs += [("dx", "🧪 Diagnóstico"), ("exit", "📤 Salida")]
            tabs = dict(zip([k for k, _ in tab_defs], st.tabs([l for _, l in tab_defs])))

            with tabs["state"]:
                options = [
                    k
                    for k in STATUS_LABELS
                    if k != "delivered" and (k != "needs_charge" or has_charge)
                ]
                if s["status"] not in options:
                    options.append(s["status"])
                with st.form(f"state_form_{sid}"):
                    new_status = st.selectbox(
                        "Nuevo estado",
                        options=options,
                        index=options.index(s["status"]),
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

            with tabs["loc"]:
                with st.form(f"loc_form_{sid}"):
                    new_loc = st.text_input(
                        "Ubicación actual",
                        value=s.get("location") or "",
                        key=f"loc_in_{sid}",
                    )
                    if st.form_submit_button("Guardar ubicación"):
                        update_location(sid, new_loc.strip())
                        done("Ubicación actualizada")

            if "bat" in tabs:
                with tabs["bat"]:
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

            if "chk" in tabs:
                with tabs["chk"]:
                    if not missing:
                        st.caption("Sin faltantes en este auto.")
                    for m in missing:
                        if st.button(f"✔ Llegó: {m['label']}", key=f"arrived_{m['id']}"):
                            auto_ready = mark_item_arrived(m["id"], sid)
                            if auto_ready:
                                done("Checklist completo: lista para entrega ✅")
                            else:
                                done(f"Llegó: {m['label']}")

            with tabs["dx"]:
                if stay_dtcs:
                    st.markdown("**Códigos DTC**")
                for d in stay_dtcs:
                    line = f"`{d['code']}`"
                    if d.get("description"):
                        line += f" — {d['description']}"
                    if d.get("note"):
                        line += f" ({d['note']})"
                    ca, cb = st.columns([5, 1])
                    ca.markdown(line)
                    if cb.button("🗑", key=f"deldtc_{d['id']}"):
                        delete_dtc(d["id"])
                        done("DTC eliminado")

                with st.form(f"dtc_form_{sid}", clear_on_submit=True):
                    dtc_code = st.text_input("Código DTC", key=f"dtc_code_{sid}")
                    dtc_desc = st.text_input(
                        "Descripción (opcional, la escribes tú)", key=f"dtc_desc_{sid}"
                    )
                    dtc_note = st.text_input("Nota (opcional)", key=f"dtc_note_{sid}")
                    if st.form_submit_button("Agregar DTC"):
                        if not dtc_code.strip():
                            st.error("Escribe el código.")
                        else:
                            add_dtc(
                                sid,
                                dtc_code.strip().upper(),
                                dtc_desc.strip(),
                                dtc_note.strip(),
                            )
                            done("DTC agregado")

                with st.form(f"dx_form_{sid}"):
                    dx = st.text_area(
                        "Diagnóstico",
                        value=s.get("diagnosis") or "",
                        placeholder=(
                            "Vehículo acude a taller por ..., se realizaron pruebas de ... "
                            "en el conector ... obteniendo ..., se determina ..."
                        ),
                        height=150,
                        key=f"dx_{sid}",
                    )
                    wd = st.text_area(
                        "Trabajo realizado",
                        value=s.get("work_done") or "",
                        height=120,
                        key=f"wd_{sid}",
                    )
                    if st.form_submit_button("Guardar diagnóstico"):
                        save_diagnosis(sid, dx.strip(), wd.strip())
                        done("Diagnóstico guardado")

            with tabs["exit"]:
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