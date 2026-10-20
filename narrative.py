def fmt_km(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text


def service_title(service: dict) -> str:
    name = service["template_name"]
    if service.get("interval_km"):
        return f"{name} de {fmt_km(service['interval_km'])} km"
    return name


def build_service_narrative(vin: str, service: dict, stay: dict) -> str:
    title = lower_first(service_title(service))
    opening = f"Vehículo con VIN {vin} acude a taller para su {title}"
    if stay.get("ot_number"):
        opening += f" (OT {stay['ot_number']})"
    if stay.get("odometer_km") is not None:
        opening += f", con {fmt_km(stay['odometer_km'])} km de odómetro"
    opening += "."

    tasks = service["tasks"]
    base = [t for t in tasks if not t["is_extra"]]
    extras = [t for t in tasks if t["is_extra"]]
    paragraphs = [opening]

    # Tareas realizadas, agrupadas por sección
    sections: dict[str, list[str]] = {}
    for t in base:
        if t["state"] not in ("done", "corrected"):
            continue
        text = lower_first(t["task"])
        note = t.get("note")
        if t["state"] == "corrected":
            text += f" (corregido: {note})" if note else " (corregido)"
        elif note:
            text += f" ({note})"
        sections.setdefault(t["section"], []).append(text)
    if sections:
        parts = [f"{lower_first(sec)}: {', '.join(items)}" for sec, items in sections.items()]
        paragraphs.append("En taller se realizó, " + "; ".join(parts) + ".")

    if extras:
        items = []
        for t in extras:
            text = lower_first(t["task"])
            if t.get("note"):
                text += f" ({t['note']})"
            items.append(text)
        paragraphs.append("Trabajos adicionales: " + ", ".join(items) + ".")

    findings = [t for t in base if t["state"] == "finding"]
    if findings:
        items = [f"{lower_first(t['task'])}: {t['note']}" for t in findings]
        paragraphs.append("Hallazgos durante la revisión: " + "; ".join(items) + ".")

    not_done = [t for t in base if t["state"] == "not_done"]
    if not_done:
        items = []
        for t in not_done:
            text = lower_first(t["task"])
            if t.get("note"):
                text += f" ({t['note']})"
            items.append(text)
        paragraphs.append("No se realizó: " + "; ".join(items) + ".")

    return "\n\n".join(paragraphs)