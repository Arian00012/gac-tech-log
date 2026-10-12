from db import get_client
from datetime import datetime, timezone

def get_open_stays() -> list[dict]:
    """Estancias abiertas (autos que siguen en el taller), con datos del vehículo."""
    result = (
        get_client()
        .table("stays")
        .select("*, vehicles(vin, model, exterior_color, interior_color, powertrain)")
        .is_("exited_at", "null")
        .order("entered_at")
        .execute()
    )
    return result.data


def get_missing_items(stay_ids: list[int]) -> dict[int, list[dict]]:
    """Para cada estancia, los ítems del checklist que faltan (con su id)."""
    if not stay_ids:
        return {}
    result = (
        get_client()
        .table("stay_checklist")
        .select("id, stay_id, checklist_items(label)")
        .in_("stay_id", stay_ids)
        .eq("state", "missing")
        .execute()
    )
    missing: dict[int, list[dict]] = {}
    for row in result.data:
        missing.setdefault(row["stay_id"], []).append(
            {"id": row["id"], "label": row["checklist_items"]["label"]}
        )
    return missing
def find_vehicle(vin: str) -> dict | None:
    result = (
        get_client().table("vehicles").select("*").eq("vin", vin).limit(1).execute()
    )
    return result.data[0] if result.data else None


def has_open_stay(vehicle_id: int) -> bool:
    result = (
        get_client()
        .table("stays")
        .select("id")
        .eq("vehicle_id", vehicle_id)
        .is_("exited_at", "null")
        .limit(1)
        .execute()
    )
    return bool(result.data)


def get_active_checklist_items() -> list[dict]:
    result = (
        get_client()
        .table("checklist_items")
        .select("id, code, label")
        .eq("active", True)
        .order("sort_order")
        .execute()
    )
    return result.data


def register_entry(
    vin: str,
    entry_type: str,
    status: str,
    powertrain: str,
    model: str,
    exterior_color: str,
    interior_color: str,
    odometer_km: int | None,
    arrival_condition: str,
    ot_number: str,
    requested_work: str,
    location: str,
    battery_pct: int | None,
    battery_km: int | None,
    notes: str,
    checklist: dict[int, str],
) -> int:
    """Registra el ingreso de un auto. Si el VIN ya existe, reutiliza su historia."""
    client = get_client()

    fields = {
        k: v
        for k, v in {
            "powertrain": powertrain,
            "model": model,
            "exterior_color": exterior_color,
            "interior_color": interior_color,
        }.items()
        if v
    }

    vehicle = find_vehicle(vin)
    if vehicle is None:
        vehicle = client.table("vehicles").insert({"vin": vin, **fields}).execute().data[0]
    elif fields:
        client.table("vehicles").update(fields).eq("id", vehicle["id"]).execute()

    stay = (
        client.table("stays")
        .insert(
            {
                "vehicle_id": vehicle["id"],
                "entry_type": entry_type,
                "status": status,
                "location": location or None,
                "battery_pct_arrival": battery_pct,
                "battery_pct_current": battery_pct,
                "battery_km_arrival": battery_km,
                "battery_km_current": battery_km,
                "odometer_km": odometer_km,
                "arrival_condition": arrival_condition or None,
                "ot_number": ot_number or None,
                "requested_work": requested_work or None,
                "notes": notes or None,
            }
        )
        .execute()
        .data[0]
    )

    if checklist:
        client.table("stay_checklist").insert(
            [
                {"stay_id": stay["id"], "item_id": item_id, "state": state}
                for item_id, state in checklist.items()
            ]
        ).execute()

    client.table("status_log").insert(
        {"stay_id": stay["id"], "status": status, "note": "Ingreso al taller"}
    ).execute()

    return stay["id"]
def update_status(stay_id: int, status: str, note: str | None = None) -> None:
    client = get_client()
    client.table("stays").update({"status": status}).eq("id", stay_id).execute()
    client.table("status_log").insert(
        {"stay_id": stay_id, "status": status, "note": note or None}
    ).execute()


def update_location(stay_id: int, location: str) -> None:
    get_client().table("stays").update({"location": location or None}).eq(
        "id", stay_id
    ).execute()


def update_battery(stay_id: int, pct: int | None, km: int | None) -> None:
    get_client().table("stays").update(
        {"battery_pct_current": pct, "battery_km_current": km}
    ).eq("id", stay_id).execute()


def mark_item_arrived(stay_checklist_id: int, stay_id: int) -> bool:
    """Marca que llegó un faltante. Devuelve True si el PDI pasó solo a 'Lista para entrega'."""
    client = get_client()
    client.table("stay_checklist").update(
        {
            "state": "arrived_later",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", stay_checklist_id).execute()

    remaining = (
        client.table("stay_checklist")
        .select("id")
        .eq("stay_id", stay_id)
        .eq("state", "missing")
        .limit(1)
        .execute()
    )
    if remaining.data:
        return False

    stay = (
        client.table("stays")
        .select("status, entry_type")
        .eq("id", stay_id)
        .limit(1)
        .execute()
        .data[0]
    )
    if stay["entry_type"] == "PDI" and stay["status"] == "in_workshop":
        update_status(stay_id, "ready_for_delivery", "Checklist de llegada completo")
        return True
    return False


def register_exit(stay_id: int, note: str | None = None) -> None:
    client = get_client()
    client.table("stays").update(
        {
            "status": "delivered",
            "exited_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", stay_id).execute()
    client.table("status_log").insert(
        {
            "stay_id": stay_id,
            "status": "delivered",
            "note": note or "Salida del taller",
        }
    ).execute()
def count_stays(vehicle_id: int) -> int:
    result = (
        get_client()
        .table("stays")
        .select("id", count="exact")
        .eq("vehicle_id", vehicle_id)
        .execute()
    )
    return result.count or 0

def get_dtcs(stay_ids: list[int]) -> dict[int, list[dict]]:
    if not stay_ids:
        return {}
    result = (
        get_client()
        .table("stay_dtcs")
        .select("*")
        .in_("stay_id", stay_ids)
        .order("created_at")
        .execute()
    )
    out: dict[int, list[dict]] = {}
    for row in result.data:
        out.setdefault(row["stay_id"], []).append(row)
    return out


def add_dtc(stay_id: int, code: str, description: str, note: str) -> None:
    get_client().table("stay_dtcs").insert(
        {
            "stay_id": stay_id,
            "code": code,
            "description": description or None,
            "note": note or None,
        }
    ).execute()


def delete_dtc(dtc_id: int) -> None:
    get_client().table("stay_dtcs").delete().eq("id", dtc_id).execute()


def save_diagnosis(stay_id: int, diagnosis: str, work_done: str) -> None:
    get_client().table("stays").update(
        {"diagnosis": diagnosis or None, "work_done": work_done or None}
    ).eq("id", stay_id).execute()


def get_stays_for_vehicle(vehicle_id: int) -> list[dict]:
    result = (
        get_client()
        .table("stays")
        .select("*")
        .eq("vehicle_id", vehicle_id)
        .order("entered_at", desc=True)
        .execute()
    )
    return result.data


def get_checklist_for_stays(stay_ids: list[int]) -> dict[int, list[dict]]:
    if not stay_ids:
        return {}
    result = (
        get_client()
        .table("stay_checklist")
        .select("stay_id, state, updated_at, checklist_items(label, sort_order)")
        .in_("stay_id", stay_ids)
        .execute()
    )
    out: dict[int, list[dict]] = {}
    for row in result.data:
        out.setdefault(row["stay_id"], []).append(row)
    for rows in out.values():
        rows.sort(key=lambda r: r["checklist_items"]["sort_order"])
    return out


def get_status_log(stay_ids: list[int]) -> dict[int, list[dict]]:
    if not stay_ids:
        return {}
    result = (
        get_client()
        .table("status_log")
        .select("*")
        .in_("stay_id", stay_ids)
        .order("changed_at")
        .execute()
    )
    out: dict[int, list[dict]] = {}
    for row in result.data:
        out.setdefault(row["stay_id"], []).append(row)
    return out