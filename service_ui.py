import streamlit as st

from narrative import build_service_narrative, fmt_km, service_title
from queries import delete_service, record_service

EXC_LABELS = {
    "corrected": "Corregido",
    "finding": "Hallazgo",
    "not_done": "No realizado",
    "na": "No aplica",
}


def _applies(task: dict, powertrain: str | None) -> bool:
    pts = task.get("powertrains")
    return pts is None or powertrain is None or powertrain in pts


def render_service_tab(stay: dict, vehicle: dict, services: list[dict], templates: list[dict], done) -> None:
    sid = stay["id"]
    pt = vehicle.get("powertrain")

    # Servicios ya registrados en este ingreso
    for svc in services:
        st.markdown(f"**{service_title(svc)}**")
        st.write(build_service_narrative(vehicle["vin"], svc, stay))
        with st.form(f"svc_del_{svc['id']}"):
            ok = st.checkbox("Confirmo eliminar este registro", key=f"svc_del_ok_{svc['id']}")
            if st.form_submit_button("Eliminar registro"):
                if not ok:
                    st.error("Marca la confirmación.")
                else:
                    delete_service(svc["id"])
                    done("Registro eliminado")
        st.divider()

    st.markdown("**Registrar servicio**")
    if not templates:
        st.caption("Aún no hay servicios definidos. Créalos en la página Catálogo.")
        return

    # El contador vacía los campos después de guardar
    ver = st.session_state.get(f"svc_ver_{sid}", 0)

    by_tpl = {t["id"]: t for t in templates}
    tpl_id = st.selectbox(
        "Servicio",
        options=list(by_tpl),
        format_func=lambda i: by_tpl[i]["name"],
        key=f"svc_tpl_{sid}_{ver}",
    )
    tpl = by_tpl[tpl_id]
    k = f"{sid}_{ver}_{tpl_id}"

    tasks = [t for t in tpl["tasks"] if _applies(t, pt)]
    base = [t for t in tasks if not t["is_extra"]]
    extras = [t for t in tasks if t["is_extra"]]
    by_id = {t["id"]: t for t in tasks}

    odo = stay.get("odometer_km")
    intervals = [None] + list(range(5000, 155000, 5000))
    default = max(5000, round(odo / 5000) * 5000) if odo else None
    interval = st.selectbox(
        "Intervalo del servicio",
        options=intervals,
        index=intervals.index(default) if default in intervals else 0,
        format_func=lambda v: "Sin intervalo" if v is None else f"{fmt_km(v)} km",
        key=f"svc_int_{k}",
    )

    st.caption(
        "Las tareas se registran como realizadas sin novedad. "
        "Marca abajo solo las que tuvieron alguna novedad."
    )
    if st.checkbox(f"Ver las {len(base)} tareas incluidas", key=f"svc_view_{k}"):
        current = None
        for t in base:
            if t["section"] != current:
                current = t["section"]
                st.markdown(f"**{current}**")
            st.write(f"- {t['task']}")

    exc_ids = st.multiselect(
        "Tareas con novedad (corregidas, hallazgos, no realizadas o que no aplican)",
        options=[t["id"] for t in base],
        format_func=lambda i: by_id[i]["task"],
        key=f"svc_exc_{k}",
    )
    exceptions: dict[int, tuple[str, str]] = {}
    for tid in exc_ids:
        t = by_id[tid]
        st.markdown(f"**{t['task']}**")
        state = st.radio(
            t["task"],
            options=list(EXC_LABELS),
            format_func=EXC_LABELS.get,
            horizontal=True,
            key=f"svc_est_{k}_{tid}",
            label_visibility="collapsed",
        )
        note = st.text_input(
            "Detalle",
            placeholder="Detalle (obligatorio en hallazgos)",
            key=f"svc_nota_{k}_{tid}",
            label_visibility="collapsed",
        )
        exceptions[tid] = (state, note.strip())

    extra_ids = []
    if extras:
        extra_ids = st.multiselect(
            "Trabajos adicionales realizados",
            options=[t["id"] for t in extras],
            format_func=lambda i: by_id[i]["task"],
            key=f"svc_ext_{k}",
        )

    if st.button("Guardar servicio", type="primary", key=f"svc_save_{k}"):
        for tid, (state, note) in exceptions.items():
            if state == "finding" and not note:
                st.error(f"Describe el hallazgo: {by_id[tid]['task']}")
                return

        records = []
        for t in base:
            state, note = "done", None
            if t["id"] in exceptions:
                state, note = exceptions[t["id"]]
                if state == "na":
                    continue
            records.append(
                {
                    "section": t["section"],
                    "task": t["task"],
                    "is_extra": False,
                    "state": state,
                    "note": note or None,
                    "sort_order": t["sort_order"],
                }
            )
        for t in extras:
            if t["id"] in extra_ids:
                records.append(
                    {
                        "section": t["section"],
                        "task": t["task"],
                        "is_extra": True,
                        "state": "done",
                        "note": None,
                        "sort_order": t["sort_order"],
                    }
                )

        record_service(sid, tpl["name"], interval, records)
        st.session_state[f"svc_ver_{sid}"] = ver + 1
        done("Servicio registrado")