import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from etl import config
from etl.clean import SIN_OPERADOR, transform
from etl.comunas import load_censo, match_comuna, match_region, normalize
from etl.snapshot import SCHEMAS, main, should_run_scheduled, validate

FIXTURE = Path(__file__).parent / "fixtures" / "api_sample.json"
CONTACT_VALUES = ("contacto@example.com", "+56900000000", "+56911111111", "Calle Falsa 123", "111111111", "example.com")


@pytest.fixture
def raw():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_censo_tiene_346_comunas():
    assert len(load_censo()) == 346


@pytest.mark.parametrize(
    "api_name, cut",
    [("Vina del Mar", "05109"), ("Las Condes", "13114"), ("SANTIAGO", "13101"), ("Llay-Llay", "05703"), ("Til Til", "13303"), ("Paiguano", "04105"), ("Cabo de Hornos (ex Navarino)", "12201")],
)
def test_match_comuna(api_name, cut):
    assert match_comuna(api_name).codigo_comuna == cut


def test_match_region():
    assert match_region("Libertador Bernardo OHiggins") == "06"
    assert match_region("Metropolitana") == "13"
    assert normalize("O'Higgins") == "ohiggins"


def test_transform_counts_and_derived_fields(raw):
    t = transform(raw, "2026-11-10")
    assert (len(t["locations"]), len(t["evses"]), len(t["connectors"]), len(t["tariffs"])) == (2, 3, 4, 2)
    evses = {e["evse_uid"]: e for e in t["evses"]}
    assert evses[11]["speed"] == "Lento" and evses[11]["current_type"] == "AC"
    assert evses[12]["speed"] == "Rápido" and evses[12]["current_type"] == "DC"
    locs = {l["location_id"]: l for l in t["locations"]}
    assert locs[1]["codigo_comuna"] == "05109" and locs[1]["region"] == "Valparaíso"
    assert locs[1]["connection_date"] is None  # 0001-01-01 se descarta
    assert locs[2]["operator"] == SIN_OPERADOR
    assert locs[2]["codigo_region"] == "06"  # comuna sin calce: región por alias
    assert t["_unmatched"] == ["Comuna Inventada (Libertador Bernardo OHiggins)"]
    assert {c["standard"] for c in t["connectors"]} == {"Tipo 2", "CCS 2", "CHAdeMO", "No informado"}


def test_no_contact_data_leaks(raw):
    blob = json.dumps(transform(raw, "2026-11-10"), ensure_ascii=False)
    for value in CONTACT_VALUES:
        assert value not in blob


def test_rows_match_schema(raw):
    t = transform(raw, "2026-11-10")
    for name, schema in SCHEMAS.items():
        for row in t[name]:
            assert set(row) == set(schema.names), name


def test_validate_rejects_small_or_broken():
    with pytest.raises(ValueError):
        validate({"no": "lista"})
    with pytest.raises(ValueError):
        validate([{"location_id": 1, "evses": [], "commune": "x", "region": "y", "coordinates": {}}])


def test_scheduled_window():
    from datetime import datetime
    assert should_run_scheduled(datetime(2026, 11, 10, 0, 5, tzinfo=config.TZ))
    assert not should_run_scheduled(datetime(2026, 11, 10, 23, 5, tzinfo=config.TZ))


def test_main_writes_parquet(tmp_path, monkeypatch):
    monkeypatch.setattr("etl.snapshot.MIN_LOCATIONS", 1)
    monkeypatch.setattr("etl.snapshot.MIN_EVSES", 1)
    assert main(["--out", str(tmp_path), "--input", str(FIXTURE), "--date", "2026-11-10"]) == 0
    day = tmp_path / "2026" / "2026-11-10"
    assert pq.read_table(day / "evses.parquet").num_rows == 3
    assert "2026-11-10" in (tmp_path / "manifest.csv").read_text()
    # segunda ejecución sin --force no reescribe
    assert main(["--out", str(tmp_path), "--input", str(FIXTURE), "--date", "2026-11-10"]) == 0


def test_build_db_from_two_snapshots(tmp_path, monkeypatch):
    import duckdb

    from etl.build_db import build

    monkeypatch.setattr("etl.snapshot.MIN_LOCATIONS", 1)
    monkeypatch.setattr("etl.snapshot.MIN_EVSES", 1)
    snaps = tmp_path / "snapshots"
    for day in ("2026-11-10", "2026-11-11"):
        assert main(["--out", str(snaps), "--input", str(FIXTURE), "--date", day]) == 0
    db = tmp_path / "monitor.duckdb"
    build(snaps, db)
    con = duckdb.connect(str(db), read_only=True)
    assert con.execute("select count(*) from evses").fetchone()[0] == 3
    assert con.execute("select count(*) from fotos").fetchone()[0] == 2
    # el EVSE 12 está fuera de línea en ambas fotos: racha de 2 días
    assert con.execute("select racha_fuera_dias from disponibilidad_evse where evse_uid = 12").fetchone()[0] == 2
    assert con.execute("select count(*) from cobertura_comunal").fetchone()[0] == 346
    types = {r[0] for r in con.execute("select data_type from information_schema.columns").fetchall()}
    assert "HUGEINT" not in types
