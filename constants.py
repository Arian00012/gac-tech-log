STATUS_LABELS = {
    "in_workshop": "En taller",
    "to_bodyshop": "Debe ir al chapero",
    "at_bodyshop": "En chapero",
    "waiting_part": "Esperando repuesto",
    "needs_charge": "Necesita carga",
    "ready_for_delivery": "Lista para entrega",
    "delivered": "Entregada",
}

STATUS_COLORS = {
    "in_workshop": "blue",
    "to_bodyshop": "orange",
    "at_bodyshop": "violet",
    "waiting_part": "yellow",
    "needs_charge": "red",
    "ready_for_delivery": "green",
    "delivered": "gray",
}

ENTRY_TYPE_LABELS = {
    "PDI": "PDI",
    "OT": "OT",
    "EMERGENCY": "Emergencia",
}

POWERTRAIN_LABELS = {
    "EV": "Eléctrico",
    "PHEV": "Híbrido enchufable",
    "HEV": "Híbrido",
    "ICE": "Gasolina",
}

CHECK_STATE_LABELS = {
    "present": "Tiene",
    "missing": "Falta",
    "arrived_later": "Llegó después",
}

# Motorizaciones con batería que se carga y/o con tanque de combustible
HAS_CHARGE = {"EV", "PHEV"}
HAS_FUEL = {"ICE", "HEV", "PHEV"}

FUEL_LEVELS = ["0", "1/4", "1/2", "3/4", "1"]


def status_badge(status: str) -> str:
    """Etiqueta de color para mostrar un estado."""
    return f":{STATUS_COLORS[status]}-badge[{STATUS_LABELS[status]}]"