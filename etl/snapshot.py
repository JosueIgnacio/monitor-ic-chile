"""Toma la foto diaria: descarga la API, la limpia y la guarda en Parquet.

Uso:
    python -m etl.snapshot --out ../data/snapshots            # foto de hoy (hora de Chile)
    python -m etl.snapshot --out ... --scheduled              # modo cron: solo actúa cerca de las 00:00 de Chile
    python -m etl.snapshot --out ... --input api.json         # usa un JSON local en vez de descargar

Escribe snapshots/AAAA/AAAA-MM-DD/{locations,evses,connectors,tariffs}.parquet
y añade una línea a snapshots/manifest.csv.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .clean import transform
from .config import API_URL, MIN_EVSES, MIN_LOCATIONS, SNAPSHOT_TABLES, TZ, USER_AGENT

S, I, F, B = pa.string(), pa.int64(), pa.float64(), pa.bool_()

SCHEMAS: dict[str, pa.Schema] = {
    "locations": pa.schema(
        [
            ("snapshot_date", S), ("location_id", I), ("folio_irve", I), ("name", S),
            ("address", S), ("commune_raw", S), ("codigo_comuna", S), ("comuna", S),
            ("codigo_region", S), ("region", S), ("lat", F), ("lon", F), ("operator", S), ("is_test", B),
            ("installation_type", S), ("parking_type", S), ("is_24_7", B),
            ("is_private_institution", B), ("data_confirmed", B), ("connection_date", S),
            ("revision_date", S), ("last_updated", S),
        ]
    ),
    "evses": pa.schema(
        [
            ("snapshot_date", S), ("evse_uid", I), ("evse_id", S), ("location_id", I),
            ("status", S), ("max_power_kw", F), ("speed", S), ("current_type", S),
            ("n_connectors", I), ("brand", S), ("model", S), ("exclusive_use", B),
            ("simultaneous_charging", B), ("payment_methods", S), ("activation_methods", S),
            ("last_updated", S),
        ]
    ),
    "connectors": pa.schema(
        [
            ("snapshot_date", S), ("connector_id", I), ("evse_uid", I), ("location_id", I),
            ("standard", S), ("current_type", S), ("format", S), ("max_power_kw", F),
            ("max_voltage", F), ("max_amperage", F), ("status", S),
        ]
    ),
    "tariffs": pa.schema(
        [
            ("snapshot_date", S), ("tariff_id", I), ("connector_id", I), ("evse_uid", I),
            ("location_id", I), ("tariff_order", I), ("component_order", I), ("dimension", S),
            ("price_clp", F), ("min_price_clp", F), ("max_price_clp", F), ("last_updated", S),
        ]
    ),
}

MANIFEST_FIELDS = ["snapshot_date", "fetched_at_utc", "locations", "evses", "connectors", "tariffs", "unmatched_communes"]


def fetch(url: str = API_URL, attempts: int = 4) -> list[dict]:
    last: Exception | None = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001 - reintentamos cualquier fallo de red
            last = e
            wait = 2 ** (i + 2)
            print(f"Intento {i + 1} falló ({e}); reintento en {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"No se pudo descargar la API: {last}")


def validate(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        raise ValueError(f"Se esperaba una lista de ubicaciones, llegó {type(raw).__name__}")
    for key in ("location_id", "evses", "commune", "region", "coordinates"):
        missing = sum(1 for loc in raw if key not in loc)
        if missing:
            raise ValueError(f"La API cambió: a {missing} ubicaciones les falta '{key}'")
    n_evses = sum(len(loc.get("evses") or []) for loc in raw)
    if len(raw) < MIN_LOCATIONS or n_evses < MIN_EVSES:
        raise ValueError(f"Respuesta sospechosamente chica: {len(raw)} ubicaciones, {n_evses} EVSE")
    return raw


def should_run_scheduled(now_local: datetime) -> bool:
    """El cron corre a las 03:00 y 04:00 UTC; solo una cae cerca de las 00:00 en Chile.

    Aceptamos hasta las 02:59 locales por si GitHub atrasa el cron.
    """
    return now_local.hour < 3


def write_snapshot(tables: dict[str, list[dict]], out_dir: Path, snapshot_date: str) -> Path:
    day_dir = out_dir / snapshot_date[:4] / snapshot_date
    day_dir.mkdir(parents=True, exist_ok=True)
    for name in SNAPSHOT_TABLES:
        table = pa.Table.from_pylist(tables[name], schema=SCHEMAS[name])
        pq.write_table(table, day_dir / f"{name}.parquet", compression="zstd")
    return day_dir


def append_manifest(out_dir: Path, row: dict) -> None:
    path = out_dir / "manifest.csv"
    rows: list[dict] = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r["snapshot_date"] != row["snapshot_date"]]
    rows.append(row)
    rows.sort(key=lambda r: r["snapshot_date"])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, type=Path, help="Carpeta snapshots/ de la rama data")
    p.add_argument("--input", type=Path, help="JSON local en vez de descargar")
    p.add_argument("--date", help="Fecha de la foto (AAAA-MM-DD). Por defecto, hoy en Chile")
    p.add_argument("--scheduled", action="store_true", help="Modo cron: omite si no es la medianoche de Chile")
    p.add_argument("--force", action="store_true", help="Reescribe la foto si ya existe")
    args = p.parse_args(argv)

    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(TZ)
    snapshot_date = args.date or now_local.date().isoformat()

    if args.scheduled and not should_run_scheduled(now_local):
        print(f"Son las {now_local:%H:%M} en Chile; esta ejecución del cron no corresponde. Nada que hacer.")
        return 0
    day_dir = args.out / snapshot_date[:4] / snapshot_date
    if day_dir.exists() and not args.force:
        print(f"La foto {snapshot_date} ya existe; nada que hacer.")
        return 0

    raw = json.loads(args.input.read_text(encoding="utf-8")) if args.input else fetch()
    raw = validate(raw)
    tables = transform(raw, snapshot_date)
    write_snapshot(tables, args.out, snapshot_date)

    unmatched = tables["_unmatched"]
    append_manifest(
        args.out,
        {
            "snapshot_date": snapshot_date,
            "fetched_at_utc": now_utc.isoformat(timespec="seconds"),
            **{name: len(tables[name]) for name in SNAPSHOT_TABLES},
            "unmatched_communes": len(unmatched),
        },
    )
    print(
        f"Foto {snapshot_date}: "
        + ", ".join(f"{len(tables[n])} {n}" for n in SNAPSHOT_TABLES)
    )
    if unmatched:
        print("Comunas sin calce con el Censo (agregar a ALIASES en etl/comunas.py):")
        for u in unmatched:
            print(f"  - {u}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
