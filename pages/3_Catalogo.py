import pandas as pd
import streamlit as st

from auth import require_login
from nav import show_nav
from queries import create_template, get_templates_with_tasks, save_template_tasks

st.set_page_config(page_title="Catálogo de servicios", page_icon=":material/checklist:")

require_login()
show_nav()

st.title("Catálogo de servicios")
st.caption(
    "Define las tareas de cada servicio. Los cambios solo afectan a servicios nuevos; "
    "los ya registrados conservan el texto con el que se guardaron."
)

flash = st.session_state.pop("flash", None)
if flash:
    st.toast(flash)

PT_COLS = ["EV", "PHEV", "HEV", "ICE"]
COLS = ["Orden", "Sección", "Tarea", "Adicional"] + PT_COLS


def clean(value):
    return None if pd.isna(value) else value


templates = get_templates_with_tasks()

with st.expander("Crear un servicio nuevo"):
    with st.form("new_template", clear_on_submit=True):
        new_name = st.text_input("Nombre del servicio")
        if st.form_submit_button("Crear"):
            if not new_name.strip():
                st.error("Escribe un nombre.")
            else:
                try:
                    create_template(new_name.strip())
                except Exception as e:
                    st.error(f"No se pudo crear: {e}")
                else:
                    st.rerun()

if not templates:
    st.info("Todavía no hay servicios.")
    st.stop()

by_id = {t["id"]: t for t in templates}
tpl_id = st.selectbox(
    "Servicio", options=list(by_id), format_func=lambda i: by_id[i]["name"]
)
tpl = by_id[tpl_id]

st.markdown(
    "En **EV, PHEV, HEV e ICE** marca a qué motorizaciones aplica cada tarea "
    "(si no marcas ninguna, aplica a todas). **Adicional** es un trabajo opcional que no "
    "se incluye por defecto. Para agregar una tarea usa la fila vacía del final; para borrar "
    "una, selecciónala y usa el ícono de papelera. La tabla se edita mejor desde la computadora."
)

data = []
for t in tpl["tasks"]:
    pts = t.get("powertrains")
    row = {
        "Orden": t["sort_order"],
        "Sección": t["section"],
        "Tarea": t["task"],
        "Adicional": t["is_extra"],
    }
    for p in PT_COLS:
        row[p] = pts is None or p in pts
    data.append(row)
df = pd.DataFrame(data, columns=COLS)

# El contador evita que la tabla mezcle ediciones viejas con datos recién guardados
ver = st.session_state.get(f"cat_ver_{tpl_id}", 0)

edited = st.data_editor(
    df,
    num_rows="dynamic",
    hide_index=True,
    key=f"tasks_editor_{tpl_id}_{ver}",
    column_config={
        "Orden": st.column_config.NumberColumn("Orden", step=1, width="small"),
        "Sección": st.column_config.TextColumn("Sección"),
        "Tarea": st.column_config.TextColumn("Tarea", width="large"),
        "Adicional": st.column_config.CheckboxColumn("Adicional", default=False),
        "EV": st.column_config.CheckboxColumn("EV", default=True),
        "PHEV": st.column_config.CheckboxColumn("PHEV", default=True),
        "HEV": st.column_config.CheckboxColumn("HEV", default=True),
        "ICE": st.column_config.CheckboxColumn("ICE", default=True),
    },
)

if st.button("Guardar cambios", type="primary"):
    tasks = []
    for _, r in edited.iterrows():
        task = clean(r["Tarea"])
        if not task or not str(task).strip():
            continue
        section = clean(r["Sección"])
        order = clean(r["Orden"])
        ticked = [p for p in PT_COLS if clean(r[p])]
        tasks.append(
            {
                "section": str(section).strip() if section else "General",
                "task": str(task).strip(),
                "powertrains": None if len(ticked) in (0, len(PT_COLS)) else ticked,
                "is_extra": bool(clean(r["Adicional"])),
                "sort_order": int(order) if order is not None else 999,
            }
        )
    tasks.sort(key=lambda t: t["sort_order"])
    try:
        save_template_tasks(tpl_id, tasks)
    except Exception as e:
        st.error(f"No se pudo guardar: {e}")
    else:
        st.session_state[f"cat_ver_{tpl_id}"] = ver + 1
        st.session_state["flash"] = "Catálogo actualizado"
        st.rerun()