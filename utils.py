import re
from datetime import datetime, timedelta, timezone

LOCAL_TZ = timezone(timedelta(hours=-4))  # Bolivia, sin horario de verano

def normalize_vin(raw: str) -> str | None:
    """Devuelve los últimos 8 caracteres del VIN en mayúsculas, o None si no es válido."""
    cleaned = re.sub(r"[\s\-]", "", raw or "").upper()
    if len(cleaned) < 8 or not re.fullmatch(r"[A-Z0-9]+", cleaned):
        return None
    return cleaned[-8:]

def fmt_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    return datetime.fromisoformat(iso).astimezone(LOCAL_TZ).strftime("%d/%m/%Y %H:%M")