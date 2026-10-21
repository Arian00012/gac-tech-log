import re
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from auth import require_login
from constants import ENTRY_TYPE_LABELS, STATUS_LABELS
from nav import show_nav
from queries import get_open_stays, lookup_vins
from ui import stat_cards
from utils import fmt_dt

st.set_page_config(page_title="Verificar lista", page_icon=":material/fact_check:")

require_login()
show_nav()

st.title("Verificar lista de vehículos")
st.caption(
    "Pega una columna del Excel con VIN completos o solo los últimos dígitos "
    "(entre 3 y 8 caracteres). Un dato por línea."
)

raw = st.text_area("Lista", height=200, placeholder="3031\n4455\nA1B2C3D4")

if st.button("Verificar", type="primary"):
    tokens: list[str] = []
    for part in re.split(r"[\s,;]+", raw):
        t = re.sub(r"[^A-Za-z0-9]", "", part).upper()[-8:]
        if t and t not in tokens:
            tokens.append(t)
    too_short = [t for t in tokens if len(t) < 3]
    tokens = [t for t in tokens if len(t) >= 3]

    if not tokens:
        st.error("No encontré datos válidos en la lista.")
        st.stop()
    if too_short:
        st.caption("Se ignoraron por ser muy cortos: " + ", ".join(too_short))

    results = lookup_vins(tokens)
    now = datetime.now(timezone.utc)

    rows = []
    counts = {"En taller": 0, "Fuera del taller": 0, "Sin registro": 0}
    for t in tokens:
        matches = results.get(t, [])
        if not matches:
            counts["Sin registro"] += 1
            rows.append(
                {
                    "Dato de la lista": t,
                    "VIN": "—",
                    "Resultado": "Sin registro",
                    "Estado": "",
                    "Ubicación": "",
                    "Detalle": "No hay historia con estos dígitos",
                }
            )
            continue
        note = f" (coincide con {len(matches)} vehículos)" if len(matches) > 1 else ""
        for m in matches:
            stay = m["stay"]
            base = {"Dato de la lista": t, "VIN": m["vin"]}
            if stay and not stay.get("exited_at"):
                days = (now - datetime.fromisoformat(stay["entered_at"])).days
                counts["En taller"] += 1
                rows.append(
                    {
                        **base,
                        "Resultado": "En taller",
                        "Estado": STATUS_LABELS[stay["status"]],
                        "Ubicación": stay.get("location") or "",
                        "Detalle": f"{ENTRY_TYPE_LABELS[stay['entry_type']]} · {days} día(s){note}",
                    }
                )
            else:
                counts["Fuera del taller"] += 1
                if stay:
                    detail = f"Última salida {fmt_dt(stay['exited_at'])}"
                else:
                    detail = "Sin ingresos registrados"
                rows.append(
                    {
                        **base,
                        "Resultado": "Fuera del taller",
                        "Estado": "",
                        "Ubicación": "",
                        "Detalle": detail + note,
                    }
                )

    # Autos que sí están en el taller según la app, pero no aparecen en la lista
    extra = []
    for s in get_open_stays():
        vin = s["vehicles"]["vin"]
        if not any(vin.endswith(t) for t in tokens):
            days = (now - datetime.fromisoformat(s["entered_at"])).days
            extra.append(
                {
                    "VIN": vin,
                    "Tipo": ENTRY_TYPE_LABELS[s["entry_type"]],
                    "Estado": STATUS_LABELS[s["status"]],
                    "Ubicación": s.get("location") or "",
                    "Días en taller": days,
                }
            )

    stat_cards(
        [
            ("En la lista", len(tokens)),
            ("En taller", counts["En taller"]),
            ("Fuera del taller", counts["Fuera del taller"]),
            ("Sin registro", counts["Sin registro"]),
            ("En taller y no en la lista", len(extra)),
        ]
    )

    df = pd.DataFrame(rows)
    st.subheader("Resultado de la lista")
    st.dataframe(df, hide_index=True)
    st.download_button(
        "Descargar resultado (CSV)",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name="verificacion_lista.csv",
        mime="text/csv",
        on_click="ignore",
    )

    st.subheader("En el taller según la app, pero no en la lista")
    if extra:
        st.dataframe(pd.DataFrame(extra), hide_index=True)
    else:
        st.caption("Todos los vehículos que están en el taller aparecen en la lista.")