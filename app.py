from datetime import datetime, timezone
from narrative import service_title
from service_ui import render_service_tab
import streamlit as st
import re
from ui import stat_cards

from auth import require_login
from constants import (
    CHECK_STATE_LABELS,
    ENTRY_TYPE_LABELS,
    FUEL_LEVELS,
    HAS_CHARGE,
    HAS_FUEL,
    POWERTRAIN_LABELS,
    STATUS_LABELS,
    status_badge,
)
from nav import show_nav
from queries import (
    add_dtc,
    add_note,
    delete_dtc,
    get_checklist_for_stays,
    get_dtcs,
    get_open_stays,
    get_recent_exits,
    get_stay_notes,
    register_exit,
    revert_exit,
    save_checklist,
    save_diagnosis,
    update_energy,
    update_location,
    update_status,
    get_templates_with_tasks,
    get_stay_services,

)
from utils import fmt_dt

st.set_page_config(page_title="GAC Tech Log", page_icon=":material/directions_car:")

require_login()
show_nav()

flash = st.session_state.pop("flash", None)
if flash:
    st.toast(flash)

st.title("Vehículos en taller")


def done(message: str) -> None:
    st.session_state["flash"] = message
    st.rerun()


def show_recent_exits() -> None:
    exits = get_recent_exits(7)
    if not exits:
        return
    with st.expander(f"Salidas recientes, últimos 7 días ({len(exits)})"):
        st.caption("Si una salida se registró por error, se puede revertir aquí.")
        for e in exits:
            v = e["vehicles"]
            with st.form(f"revert_form_{e['id']}"):
                st.markdown(
                    f"**{v['vin']}** · {ENTRY_TYPE_LABELS[e['entry_type']]} · "
                    f"salida {fmt_dt(e['exited_at'])}"
                )
                ok = st.checkbox("Confirmo revertir esta salida", key=f"rev_ok_{e['id']}")
                if st.form_submit_button("Revertir salida"):
                    if not ok:
                        st.error("Marca la confirmación para revertir.")
                    else:
                        err = revert_exit(e["id"])
                        if err:
                            st.error(err)
                        else:
                            done("Salida revertida")


if st.button("Actualizar"):
    st.rerun()

stays = get_open_stays()

if not stays:
    st.info("No hay vehículos en el taller en este momento.")
    show_recent_exits()
    st.stop()

stay_ids = [s["id"] for s in stays]
checklists = get_checklist_for_stays(stay_ids)
dtcs_by_stay = get_dtcs(stay_ids)
notes_by_stay = get_stay_notes(stay_ids)
services_by_stay = get_stay_services(stay_ids)
templates = get_templates_with_tasks()

# Resumen general y del chapero
to_send = [s for s in stays if s["status"] == "to_bodyshop"]
at_shop = [s for s in stays if s["status"] == "at_bodyshop"]

ready = [s for s in stays if s["status"] == "ready_for_delivery"]
waiting = [s for s in stays if s["status"] == "waiting_part"]

stat_cards(
    [
        ("En taller", len(stays)),
        ("Listos para entrega", len(ready)),
        ("Esperando repuesto", len(waiting)),
        ("Por enviar al chapero", len(to_send)),
        ("En chapero", len(at_shop)),
    ]
)

if to_send:
    st.caption("Por enviar al chapero: " + ", ".join(s["vehicles"]["vin"] for s in to_send))
if at_shop:
    st.caption("En chapero: " + ", ".join(s["vehicles"]["vin"] for s in at_shop))

# Búsqueda rápida y filtro por estado
search_raw = st.text_input(
    "Buscar vehículo", placeholder="Últimos dígitos del VIN, por ejemplo 3031"
)
query = re.sub(r"[^A-Za-z0-9]", "", search_raw).upper()

counts: dict[str, int] = {}
for s in stays:
    counts[s["status"]] = counts.get(s["status"], 0) + 1

selected = st.pills(
    "Filtrar por estado",
    options=[k for k in STATUS_LABELS if k in counts],
    format_func=lambda k: f"{STATUS_LABELS[k]} ({counts[k]})",
    selection_mode="multi",
)

if query:
    visible = [s for s in stays if query in s["vehicles"]["vin"]]
else:
    visible = [s for s in stays if not selected or s["status"] in selected]

if query and not visible:
    st.info(f"Ningún vehículo en el taller coincide con {query}.")
    history = lookup_vins([query], contains=True).get(query, [])
    if not history:
        st.caption("Tampoco hay registros anteriores con esos dígitos.")
    for h in history[:5]:
        stay = h["stay"]
        if stay and stay.get("exited_at"):
            st.write(
                f"{h['vin']}: salió el {fmt_dt(stay['exited_at'])} "
                f"({ENTRY_TYPE_LABELS[stay['entry_type']]})"
            )
        else:
            st.write(f"{h['vin']}: sin ingresos registrados")
    show_recent_exits()
    st.stop()
now = datetime.now(timezone.utc)

for s in visible:
    sid = s["id"]
    v = s["vehicles"]
    pt = v.get("powertrain")
    has_charge = pt is None or pt in HAS_CHARGE
    has_fuel = pt in HAS_FUEL
    rows = checklists.get(sid, [])
    missing = [r for r in rows if r["state"] == "missing"]
    stay_dtcs = dtcs_by_stay.get(sid, [])
    stay_notes = notes_by_stay.get(sid, [])
    stay_services = services_by_stay.get(sid, [])    
    days = (now - datetime.fromisoformat(s["entered_at"])).days

    with st.container(border=True):
        st.markdown(f"**{v['vin']}**  {status_badge(s['status'])}")

        details = [ENTRY_TYPE_LABELS[s["entry_type"]]]
        if pt:
            details.append(POWERTRAIN_LABELS[pt])
        if v.get("model"):
            details.append(v["model"])
        colors = " / ".join(
            c for c in (v.get("exterior_color"), v.get("interior_color")) if c
        )
        if colors:
            details.append(f"Color: {colors}")
        st.caption(" · ".join(details))

        info = [f"{days} día(s) en taller"]
        if s.get("location"):
            info.append(f"Ubicación: {s['location']}")
        energy = []
        if s.get("battery_pct_current") is not None:
            energy.append(f"{s['battery_pct_current']}%")
        if s.get("battery_km_current") is not None:
            energy.append(f"{s['battery_km_current']} km")
        if energy:
            info.append("Carga: " + " / ".join(energy))
        if s.get("fuel_current"):
            info.append(f"Combustible: {s['fuel_current']}")
        st.write("  ·  ".join(info))

        if s.get("ot_number") or s.get("requested_work"):
            ot = f"OT {s['ot_number']}" if s.get("ot_number") else "OT"
            if s.get("requested_work"):
                ot += f": {s['requested_work']}"
            st.caption(ot)
        if stay_dtcs:
            st.caption("DTC: " + ", ".join(d["code"] for d in stay_dtcs))
        if stay_services:
            st.caption("Servicio: " + ", ".join(service_title(x) for x in stay_services))    
        if missing:
            parts = []
            for m in missing:
                label = m["checklist_items"]["label"]
                parts.append(f"{label} ({m['note']})" if m.get("note") else label)
            st.warning("Falta: " + ", ".join(parts))
        if s.get("notes"):
            st.caption(f"Nota de ingreso: {s['notes']}")
        for n in stay_notes[-3:]:
            st.caption(f"{fmt_dt(n['created_at'])}: {n['body']}")

        with st.expander("Gestionar"):
            tab_defs = [("state", "Estado")]
            if has_charge or has_fuel:
                tab_defs.append(("energy", "Energía"))
            if s["entry_type"] == "PDI":
                tab_defs.append(("chk", "Checklist"))
            tab_defs.append(("dx", "Diagnóstico"))
            if s["entry_type"] != "PDI":
                tab_defs.append(("svc", "Servicio"))
            tab_defs += [("notes", "Notas"), ("exit", "Salida")]
            tabs = dict(zip([k for k, _ in tab_defs], st.tabs([l for _, l in tab_defs])))

            # --- Estado y ubicación ---
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
                        "Estado",
                        options=options,
                        index=options.index(s["status"]),
                        format_func=STATUS_LABELS.get,
                        key=f"state_sel_{sid}",
                    )
                    new_loc = st.text_input(
                        "Ubicación actual",
                        value=s.get("location") or "",
                        key=f"loc_in_{sid}",
                    )
                    note = st.text_input("Nota del cambio (opcional)", key=f"state_note_{sid}")
                    if st.form_submit_button("Guardar"):
                        status_changed = new_status != s["status"] or bool(note.strip())
                        loc_changed = new_loc.strip() != (s.get("location") or "")
                        if not status_changed and not loc_changed:
                            st.info("Sin cambios.")
                        else:
                            if status_changed:
                                update_status(sid, new_status, note.strip())
                            if loc_changed:
                                update_location(sid, new_loc.strip())
                            done("Cambios guardados")

            # --- Energía: batería y/o combustible ---
            if "energy" in tabs:
                with tabs["energy"]:
                    with st.form(f"energy_form_{sid}"):
                        values: dict = {}
                        if has_charge:
                            b1, b2 = st.columns(2)
                            values["battery_pct_current"] = b1.number_input(
                                "Carga (%)",
                                min_value=0,
                                max_value=100,
                                value=s.get("battery_pct_current"),
                                step=1,
                                key=f"bat_pct_{sid}",
                            )
                            values["battery_km_current"] = b2.number_input(
                                "Autonomía (km)",
                                min_value=0,
                                value=s.get("battery_km_current"),
                                step=1,
                                key=f"bat_km_{sid}",
                            )
                        if has_fuel:
                            current = s.get("fuel_current")
                            values["fuel_current"] = st.radio(
                                "Combustible (tanque)",
                                options=FUEL_LEVELS,
                                index=FUEL_LEVELS.index(current)
                                if current in FUEL_LEVELS
                                else None,
                                horizontal=True,
                                key=f"fuel_{sid}",
                            )
                        if st.form_submit_button("Guardar"):
                            update_energy(sid, values)
                            done("Datos actualizados")

            # --- Checklist de llegada (editable en cualquier momento) ---
            if "chk" in tabs:
                with tabs["chk"]:
                    if not rows:
                        st.caption("Este ingreso no tiene checklist.")
                    else:
                        state_keys = list(CHECK_STATE_LABELS)
                        with st.form(f"chk_form_{sid}"):
                            inputs = {}
                            for r in rows:
                                label = r["checklist_items"]["label"]
                                st.markdown(f"**{label}**")
                                state = st.radio(
                                    label,
                                    options=state_keys,
                                    index=state_keys.index(r["state"]),
                                    format_func=CHECK_STATE_LABELS.get,
                                    horizontal=True,
                                    key=f"chk_state_{r['id']}",
                                    label_visibility="collapsed",
                                )
                                item_note = st.text_input(
                                    "Nota",
                                    value=r.get("note") or "",
                                    placeholder="Ej.: prestado a otro vehículo",
                                    key=f"chk_note_{r['id']}",
                                    label_visibility="collapsed",
                                )
                                inputs[r["id"]] = (r, state, item_note.strip())
                            if st.form_submit_button("Guardar checklist"):
                                updates = [
                                    {"id": rid, "state": state, "note": item_note}
                                    for rid, (r, state, item_note) in inputs.items()
                                    if state != r["state"]
                                    or item_note != (r.get("note") or "")
                                ]
                                if not updates:
                                    st.info("Sin cambios.")
                                else:
                                    result = save_checklist(sid, updates)
                                    done(
                                        {
                                            "ready": "Checklist completo: lista para entrega",
                                            "reverted": "Hay faltantes: vuelve a En taller",
                                        }.get(result, "Checklist actualizado")
                                    )

            # --- Diagnóstico y DTC ---
            with tabs["dx"]:
                if stay_dtcs:
                    st.markdown("**Códigos DTC**")
                for d in stay_dtcs:
                    line = f"`{d['code']}`"
                    if d.get("description"):
                        line += f" — {d['description']}"
                    if d.get("note"):
                        line += f" ({d['note']})"
                    ca, cb = st.columns([4, 1])
                    ca.markdown(line)
                    if cb.button("Quitar", key=f"deldtc_{d['id']}"):
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
                    if "svc" in tabs:
                        with tabs["svc"]:
                            render_service_tab(s, v, stay_services, templates, done)

            # --- Notas posteriores al ingreso ---
            with tabs["notes"]:
                if s.get("notes"):
                    st.caption(f"Nota de ingreso: {s['notes']}")
                for n in stay_notes:
                    st.write(f"{fmt_dt(n['created_at'])} — {n['body']}")
                if not s.get("notes") and not stay_notes:
                    st.caption("Sin notas todavía.")
                with st.form(f"note_form_{sid}", clear_on_submit=True):
                    new_note = st.text_area("Nueva nota", key=f"note_in_{sid}")
                    if st.form_submit_button("Agregar nota"):
                        if not new_note.strip():
                            st.error("Escribe la nota.")
                        else:
                            add_note(sid, new_note.strip())
                            done("Nota agregada")

            # --- Salida ---
            with tabs["exit"]:
                if missing:
                    st.warning(
                        "Sale con faltantes: "
                        + ", ".join(m["checklist_items"]["label"] for m in missing)
                    )
                with st.form(f"exit_form_{sid}"):
                    exit_note = st.text_input(
                        "Nota de salida (opcional)", key=f"exit_note_{sid}"
                    )
                    confirm = st.checkbox(
                        "Confirmo la salida de este vehículo del taller",
                        key=f"exit_ok_{sid}",
                    )
                    if st.form_submit_button("Registrar salida"):
                        if not confirm:
                            st.error("Marca la confirmación para registrar la salida.")
                        else:
                            register_exit(sid, exit_note.strip())
                            done("Salida registrada")

show_recent_exits()