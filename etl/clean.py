"""Transforma el JSON de la API en cuatro tablas planas y limpias.

Regla de privacidad: se usa una LISTA BLANCA de campos. Nada que no esté
escrito explícitamente aquí llega a la foto diaria. En particular nunca se
guardan email, teléfonos, sitios web, direcciones de empresas, RUT, número de
cliente ni documentos de factibilidad.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from .comunas import match_comuna, match_region, region_name
from .config import FAST_KW

# Estándares de conector tal como vienen -> nombre que mostramos.
STANDARDS = {
    "tipo 1": "Tipo 1",
    "tipo 2": "Tipo 2",
    "ccs 1": "CCS 1",
    "ccs 2": "CCS 2",
    "chademo": "CHAdeMO",
    "gb/t dc": "GB/T DC",
    "gb/t ac": "GB/T AC",
}

STATUSES = {"DISPONIBLE", "OCUPADO", "NO DISPONIBLE", "FUERA DE LINEA"}

SIN_OPERADOR = "Sin operador informado"


def _f(v: Any) -> float | None:
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def _s(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _date(v: Any) -> str | None:
    """Fechas ISO plausibles; descarta valores de relleno como 0001-01-01."""
    s = _s(v)
    if not s:
        return None
    try:
        d = date.fromisoformat(s[:10])
    except ValueError:
        return None
    return d.isoformat() if 2010 <= d.year <= 2100 else None


def _standard(v: Any) -> str:
    s = _s(v)
    if not s:
        return "No informado"
    return STANDARDS.get(s.lower(), "No informado")


def _status(v: Any) -> str:
    s = (_s(v) or "").upper()
    return s if s in STATUSES else "DESCONOCIDO"


def _operator(loc: dict) -> str:
    opc = loc.get("OPC") or {}
    name = _s(opc.get("normalized_name"))
    if not name or name.lower() == SIN_OPERADOR.lower():
        return SIN_OPERADOR
    return name


def transform(raw: list[dict], snapshot_date: str) -> dict[str, list[dict]]:
    locations: list[dict] = []
    evses: list[dict] = []
    connectors: list[dict] = []
    tariffs: list[dict] = []
    unmatched: set[str] = set()

    for loc in raw:
        location_id = loc["location_id"]
        comuna = match_comuna(loc.get("commune"))
        if comuna:
            codigo_region = comuna.codigo_region
            nombre_region = comuna.nombre_region
        else:
            unmatched.add(f"{loc.get('commune')} ({loc.get('region')})")
            codigo_region = match_region(loc.get("region"))
            nombre_region = region_name(codigo_region) or _s(loc.get("region"))
        coords = loc.get("coordinates") or {}
        opening = loc.get("opening_times") or {}

        locations.append(
            {
                "snapshot_date": snapshot_date,
                "location_id": location_id,
                "folio_irve": loc.get("folio_IRVE"),
                "name": _s(loc.get("name")),
                "address": _s(loc.get("address")),
                "commune_raw": _s(loc.get("commune")),
                "codigo_comuna": comuna.codigo_comuna if comuna else None,
                "comuna": comuna.nombre_comuna if comuna else _s(loc.get("commune")),
                "codigo_region": codigo_region,
                "region": nombre_region,
                "lat": _f(coords.get("latitude")),
                "lon": _f(coords.get("longitude")),
                "operator": _operator(loc),
                "is_test": "prueba" in (_operator(loc) + " " + (_s(loc.get("name")) or "")).lower(),
                "installation_type": _s(loc.get("charging_instalation_type")),
                "parking_type": _s(loc.get("parking_type")),
                "is_24_7": bool(opening.get("twentyfourseven")),
                "is_private_institution": bool(loc.get("institucion_privada")),
                "data_confirmed": bool(loc.get("datos_IRVE_confirmados")),
                "connection_date": _date(loc.get("connection_date")),
                "revision_date": _date(loc.get("revision_date")),
                "last_updated": _s(loc.get("last_updated")),
            }
        )

        for evse in loc.get("evses") or []:
            evse_uid = evse["evse_uid"]
            conns = evse.get("connectors") or []
            power_types = {(_s(c.get("power_type")) or "").upper() for c in conns}
            max_kw = _f(evse.get("max_electric_power"))
            if max_kw is None and conns:
                max_kw = max((_f(c.get("max_electric_power")) or 0) for c in conns)
            evses.append(
                {
                    "snapshot_date": snapshot_date,
                    "evse_uid": evse_uid,
                    "evse_id": _s(evse.get("evse_id")),
                    "location_id": location_id,
                    "status": _status(evse.get("status")),
                    "max_power_kw": max_kw,
                    "speed": "Rápido" if (max_kw or 0) >= FAST_KW else "Lento",
                    "current_type": "DC" if "DC" in power_types else "AC",
                    "n_connectors": len(conns),
                    "brand": _s(evse.get("brand")),
                    "model": _s(evse.get("model")),
                    "exclusive_use": bool(evse.get("uso_exclusivo")),
                    "simultaneous_charging": bool(evse.get("permite_carga_simultanea")),
                    "payment_methods": ",".join(sorted(set(evse.get("payment_capabilities") or []))),
                    "activation_methods": ",".join(sorted(set(evse.get("activation_capabilities") or []))),
                    "last_updated": _s(evse.get("last_updated")),
                }
            )

            for c in conns:
                connector_id = c["connector_id"]
                connectors.append(
                    {
                        "snapshot_date": snapshot_date,
                        "connector_id": connector_id,
                        "evse_uid": evse_uid,
                        "location_id": location_id,
                        "standard": _standard(c.get("standard")),
                        "current_type": (_s(c.get("power_type")) or "").upper() or None,
                        "format": _s(c.get("format")),
                        "max_power_kw": _f(c.get("max_electric_power")),
                        "max_voltage": _f(c.get("max_voltage")),
                        "max_amperage": _f(c.get("max_amperage")),
                        "status": _status(c.get("status")),
                    }
                )
                for t in c.get("tariffs") or []:
                    elements = t.get("elements") or {}
                    for pc in elements.get("price_components") or []:
                        tariffs.append(
                            {
                                "snapshot_date": snapshot_date,
                                "tariff_id": t.get("tariff_id"),
                                "connector_id": connector_id,
                                "evse_uid": evse_uid,
                                "location_id": location_id,
                                "tariff_order": t.get("order_number"),
                                "component_order": pc.get("order_number"),
                                "dimension": _s(pc.get("tariff_dimension")),
                                "price_clp": _f(pc.get("price")),
                                "min_price_clp": _f(t.get("min_price")),
                                "max_price_clp": _f(t.get("max_price")),
                                "last_updated": _s(t.get("last_updated")),
                            }
                        )

    return {
        "locations": locations,
        "evses": evses,
        "connectors": connectors,
        "tariffs": tariffs,
        "_unmatched": sorted(unmatched),
    }
