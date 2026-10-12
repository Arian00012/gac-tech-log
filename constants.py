STATUS_LABELS = {
    "in_workshop": "En taller",
    "to_bodyshop": "Debe ir al chapero",
    "at_bodyshop": "En chapero",
    "waiting_part": "Esperando repuesto",
    "needs_charge": "Necesita carga",
    "ready_for_delivery": "Lista para entrega",
    "delivered": "Entregada",
}

STATUS_ICONS = {
    "in_workshop": "🔧",
    "to_bodyshop": "➡️",
    "at_bodyshop": "🚚",
    "waiting_part": "⏳",
    "needs_charge": "🔋",
    "ready_for_delivery": "✅",
    "delivered": "📦",
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

# Motorizaciones donde tiene sentido registrar carga de batería
HAS_CHARGE = {"EV", "PHEV"}