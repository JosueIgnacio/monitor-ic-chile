"""Construye la base DuckDB que lee el dashboard a partir de todas las fotos diarias.

Uso:
    python -m etl.build_db --snapshots ../data/snapshots [--out dashboard/sources/monitor/monitor.duckdb]

La base se regenera completa en cada build (unos segundos); no se guarda en git.
Toda la lógica de negocio (qué es "operativo", rachas, altas y bajas) vive aquí
en SQL, para que las páginas de Evidence solo filtren y grafiquen.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

from .config import CENSO_CSV, DB_PATH, SNAPSHOT_TABLES

# Orden geográfico norte -> sur para listar regiones.
REGION_ORDER = ["15", "01", "02", "03", "04", "05", "13", "06", "07", "16", "08", "09", "14", "10", "11", "12"]

# Nombres cortos para gráficos y filtros.
REGION_SHORT = {
    "15": "Arica y Parinacota", "01": "Tarapacá", "02": "Antofagasta", "03": "Atacama",
    "04": "Coquimbo", "05": "Valparaíso", "13": "Metropolitana", "06": "O'Higgins",
    "07": "Maule", "16": "Ñuble", "08": "Biobío", "09": "La Araucanía", "14": "Los Ríos",
    "10": "Los Lagos", "11": "Aysén", "12": "Magallanes",
}

OPERATIONAL = "('DISPONIBLE', 'OCUPADO')"


def build(snapshots: Path, out: Path) -> None:
    files = {t: sorted(snapshots.glob(f"*/*/{t}.parquet")) for t in SNAPSHOT_TABLES}
    if not files["evses"]:
        raise SystemExit(f"No hay fotos en {snapshots}")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.duckdb")
    tmp.unlink(missing_ok=True)
    con = duckdb.connect(str(tmp))

    # --- Referencias -------------------------------------------------------
    con.execute(
        "create table regiones (codigo_region varchar, region varchar, orden integer)"
    )
    con.executemany(
        "insert into regiones values (?, ?, ?)",
        [(c, REGION_SHORT[c], i + 1) for i, c in enumerate(REGION_ORDER)],
    )
    con.execute(
        f"""
        create table comunas as
        select c.codigo_comuna, c.nombre_comuna as comuna, c.codigo_region, r.region, r.orden as orden_region,
               c.poblacion_censada::integer as poblacion
        from read_csv('{CENSO_CSV}', all_varchar = true) c
        join regiones r using (codigo_region)
        """
    )

    # --- Historia completa -------------------------------------------------
    for t, paths in files.items():
        lst = ", ".join(f"'{p}'" for p in paths)
        con.execute(f"create table {t}_hist as select * from read_parquet([{lst}], union_by_name = true)")
    # Registros de prueba que a veces aparecen en la fuente (operador "... prueba ...").
    # Las fotos antiguas pueden no traer la columna is_test: la recalculamos aquí.
    con.execute("alter table locations_hist add column if not exists is_test boolean")
    con.execute(
        "update locations_hist set is_test = coalesce(is_test, false)"
        " or lower(coalesce(operator, '') || ' ' || coalesce(name, '')) like '%prueba%'"
    )
    con.execute("create table registros_prueba as select distinct location_id, name, operator from locations_hist where is_test")
    for t in ("evses", "connectors", "tariffs"):
        con.execute(f"delete from {t}_hist where location_id in (select location_id from registros_prueba)")
    con.execute("delete from locations_hist where is_test")
    con.execute("alter table locations_hist add column region_corta varchar")
    con.execute(
        "update locations_hist l set region_corta = r.region from regiones r where r.codigo_region = l.codigo_region"
    )
    con.execute("update locations_hist set region_corta = coalesce(region_corta, region, 'Sin región')")

    con.execute(
        """
        create table fotos as
        select snapshot_date::date as fecha, count(*) as evses
        from evses_hist group by 1 order by 1
        """
    )
    latest = con.execute("select max(snapshot_date) from evses_hist").fetchone()[0]

    # EVSE con sus atributos de ubicación, para toda la historia.
    con.execute(
        """
        create table evse_hist_full as
        select e.snapshot_date::date as fecha, e.evse_uid, e.evse_id, e.location_id, e.status,
               e.status in ('DISPONIBLE', 'OCUPADO') as operativo,
               case e.status when 'DISPONIBLE' then 'Disponible' when 'OCUPADO' then 'Ocupado'
                    when 'NO DISPONIBLE' then 'No disponible' when 'FUERA DE LINEA' then 'Fuera de línea'
                    else 'Desconocido' end as estado,
               case e.status when 'DISPONIBLE' then 1 when 'OCUPADO' then 2 when 'NO DISPONIBLE' then 3
                    when 'FUERA DE LINEA' then 4 else 5 end as orden_estado,
               e.max_power_kw, e.speed, e.current_type,
               l.name as ubicacion, l.operator as operador, l.region_corta as region, l.codigo_region,
               l.comuna, l.codigo_comuna, l.installation_type
        from evses_hist e
        join locations_hist l on l.location_id = e.location_id and l.snapshot_date = e.snapshot_date
        """
    )

    # --- Estado actual -----------------------------------------------------
    con.execute(
        f"""
        create table ubicaciones as
        select l.location_id, l.name as ubicacion, l.address as direccion, l.comuna, l.codigo_comuna,
               l.region_corta as region, l.codigo_region, coalesce(r.orden, 99) as orden_region,
               l.lat, l.lon, l.operator as operador,
               coalesce(l.installation_type, 'No informado') as tipo_instalacion,
               case when l.installation_type ilike '%interurbana%' then 'Interurbana' else 'Urbana / otra' end as ambito,
               coalesce(l.parking_type, 'No informado') as tipo_estacionamiento,
               l.is_24_7 as abierto_24_7,
               count(e.evse_uid) as evses,
               count(e.evse_uid) filter (where e.status in {OPERATIONAL}) as evses_operativos,
               max(e.max_power_kw) as potencia_max_kw,
               case when max(e.max_power_kw) >= 50 then 'Rápida' else 'Lenta' end as carga,
               case
                 when count(e.evse_uid) = 0 then 'Sin puntos'
                 when count(e.evse_uid) filter (where e.status in {OPERATIONAL}) = count(e.evse_uid) then 'Todo operativo'
                 when count(e.evse_uid) filter (where e.status in {OPERATIONAL}) = 0 then 'Nada operativo'
                 else 'Parcial'
               end as estado_ubicacion
        from locations_hist l
        left join evses_hist e on e.location_id = l.location_id and e.snapshot_date = l.snapshot_date
        left join regiones r on r.codigo_region = l.codigo_region
        where l.snapshot_date = '{latest}'
        group by all
        """
    )
    con.execute(
        f"""
        create table evses as
        select h.*, coalesce(r.orden, 99) as orden_region,
               e.brand as marca, e.model as modelo,
               e.payment_methods as medios_pago, e.activation_methods as medios_activacion,
               case
                 when h.max_power_kw is null then 'Sin dato'
                 when h.max_power_kw <= 10 then '0 – 10 kW'
                 when h.max_power_kw <= 22 then '11 – 22 kW'
                 when h.max_power_kw < 50 then '23 – 49 kW'
                 when h.max_power_kw <= 150 then '50 – 150 kW'
                 else 'Más de 150 kW'
               end as tramo_potencia
        from evse_hist_full h
        join evses_hist e on e.evse_uid = h.evse_uid and e.snapshot_date::date = h.fecha
        left join regiones r on r.codigo_region = h.codigo_region
        where h.fecha = '{latest}'
        """
    )
    con.execute(
        f"""
        create table conectores as
        select c.connector_id, c.evse_uid, c.location_id, c.standard as estandar, c.current_type as corriente,
               c.max_power_kw, c.status,
               case
                 when c.max_power_kw is null then 'Sin dato'
                 when c.max_power_kw <= 10 then '0 – 10 kW'
                 when c.max_power_kw <= 22 then '11 – 22 kW'
                 when c.max_power_kw < 50 then '23 – 49 kW'
                 when c.max_power_kw <= 150 then '50 – 150 kW'
                 else 'Más de 150 kW'
               end as tramo_potencia,
               case
                 when c.max_power_kw is null then 9
                 when c.max_power_kw <= 10 then 1
                 when c.max_power_kw <= 22 then 2
                 when c.max_power_kw < 50 then 3
                 when c.max_power_kw <= 150 then 4
                 else 5
               end as orden_tramo,
               e.operador, e.region, e.codigo_region, e.comuna, e.codigo_comuna
        from connectors_hist c
        join evses e on e.evse_uid = c.evse_uid
        where c.snapshot_date = '{latest}'
        """
    )
    # Tarifas de energía ($/kWh) vigentes, una por conector (la de menor orden).
    con.execute(
        f"""
        create table tarifas as
        select t.connector_id, c.corriente, c.estandar, c.operador, c.region, c.codigo_region, c.comuna,
               c.codigo_comuna, t.price_clp as precio_kwh
        from tariffs_hist t
        join conectores c on c.connector_id = t.connector_id
        where t.snapshot_date = '{latest}' and t.dimension = 'ENERGIA' and t.price_clp > 0
        qualify row_number() over (partition by t.connector_id order by t.tariff_order, t.component_order) = 1
        """
    )

    # --- Territorio --------------------------------------------------------
    con.execute(
        """
        create table cobertura_comunal as
        select c.codigo_comuna, c.comuna, c.codigo_region, c.region, c.orden_region, c.poblacion,
               count(distinct u.location_id) as ubicaciones,
               coalesce(sum(u.evses), 0) as evses,
               coalesce(sum(u.evses_operativos), 0) as evses_operativos,
               coalesce(sum(u.evses), 0) > 0 as con_infraestructura,
               round(coalesce(sum(u.evses), 0) * 100000.0 / nullif(c.poblacion, 0), 1) as evses_100k
        from comunas c
        left join ubicaciones u on u.codigo_comuna = c.codigo_comuna
        group by 1, 2, 3, 4, 5, 6
        """
    )
    con.execute(
        """
        create table cobertura_regional as
        select codigo_region, region, orden_region, sum(poblacion) as poblacion,
               count(*) as comunas, count(*) filter (where con_infraestructura) as comunas_con,
               sum(ubicaciones) as ubicaciones, sum(evses) as evses, sum(evses_operativos) as evses_operativos,
               round(sum(evses) * 100000.0 / sum(poblacion), 1) as evses_100k
        from cobertura_comunal group by all
        """
    )

    # --- Series diarias ----------------------------------------------------
    con.execute(
        """
        create table serie_diaria as
        select fecha, region, codigo_region, comuna, codigo_comuna, operador, speed as velocidad, current_type as corriente,
               estado, orden_estado, count(*) as evses, count(*) filter (where operativo) as evses_operativos
        from evse_hist_full group by all
        """
    )
    con.execute(
        """
        create table serie_red as
        select h.fecha,
               count(distinct h.location_id) as ubicaciones,
               count(*) as evses,
               count(*) filter (where h.operativo) as evses_operativos,
               count(*) filter (where h.operativo) / count(*) as disponibilidad,
               count(*) filter (where h.speed = 'Rápido') as evses_rapidos
        from evse_hist_full h group by 1 order by 1
        """
    )
    con.execute(
        """
        create table serie_conectores as
        select snapshot_date::date as fecha, count(*) as conectores from connectors_hist group by 1 order by 1
        """
    )

    # --- Disponibilidad por EVSE -------------------------------------------
    # Racha actual: días consecutivos (hasta la última foto) sin estar operativo.
    con.execute(
        f"""
        create table disponibilidad_evse as
        with dias as (
          select h.*, dense_rank() over (order by h.fecha) as n_foto from evse_hist_full h
        ),
        ultima_ok as (
          select evse_uid, max(n_foto) filter (where operativo) as ultima_foto_ok, max(n_foto) as ultima_foto,
                 count(*) as dias_observados, count(*) filter (where operativo) as dias_operativos,
                 count(*) filter (where not operativo) as dias_fuera
          from dias group by 1
        ),
        total as (select max(n_foto) as n from dias)
        select e.evse_uid, e.evse_id, e.location_id, e.ubicacion, e.operador, e.region, e.codigo_region, e.comuna,
               e.codigo_comuna, e.estado, e.max_power_kw, e.speed,
               u.dias_observados, u.dias_operativos, u.dias_fuera,
               u.dias_operativos / u.dias_observados as disponibilidad,
               case when e.operativo then 0 else u.ultima_foto - coalesce(u.ultima_foto_ok, 0) end as racha_fuera_dias,
               u.ultima_foto_ok is null as nunca_operativo
        from evses e join ultima_ok u using (evse_uid)
        """
    )

    # --- Altas y bajas -----------------------------------------------------
    con.execute(
        """
        create table altas_bajas as
        with f as (select fecha, lag(fecha) over (order by fecha) as anterior from fotos),
        cur as (select fecha, evse_uid from evse_hist_full)
        select f.fecha, 'Alta' as tipo, c.evse_uid
        from f join cur c on c.fecha = f.fecha
        where f.anterior is not null
          and not exists (select 1 from cur p where p.fecha = f.anterior and p.evse_uid = c.evse_uid)
        union all
        select f.fecha, 'Baja' as tipo, p.evse_uid
        from f join cur p on p.fecha = f.anterior
        where not exists (select 1 from cur c where c.fecha = f.fecha and c.evse_uid = p.evse_uid)
        """
    )
    con.execute(
        """
        create table altas_bajas_detalle as
        select a.fecha, a.tipo, a.evse_uid, h.evse_id, h.ubicacion, h.operador, h.region, h.codigo_region, h.comuna, h.codigo_comuna, h.max_power_kw
        from altas_bajas a
        join evse_hist_full h on h.evse_uid = a.evse_uid
          and h.fecha = case when a.tipo = 'Alta' then a.fecha else (select max(fecha) from fotos where fecha < a.fecha) end
        """
    )

    # --- Estimación histórica (fecha de declaración) -----------------------
    # La API no trae fecha de instalación confiable. Usamos la primera fecha
    # razonable entre connection_date y revision_date como estimación.
    con.execute(
        f"""
        create table historia_estimada as
        with base as (
          select location_id, least(try_cast(connection_date as date), try_cast(revision_date as date)) as fecha_est
          from locations_hist where snapshot_date = '{latest}'
        )
        select e.evse_uid, e.location_id, e.speed, e.region, e.codigo_region, e.comuna, e.codigo_comuna,
               e.operador, b.fecha_est, year(b.fecha_est) as anio
        from evses e join base b using (location_id)
        """
    )

    con.execute(
        f"""
        create table metadatos as
        select '{latest}'::date as ultima_foto,
               (select min(fecha) from fotos) as primera_foto,
               (select count(*) from fotos) as n_fotos
        """
    )
    _normalize_types(con)
    con.close()
    tmp.replace(out)
    print(f"Base construida en {out} (última foto {latest}, {len(files['evses'])} fotos)")


def _normalize_types(con: duckdb.DuckDBPyConnection) -> None:
    """Evidence no maneja bien HUGEINT ni DECIMAL (salen de sum()); los pasamos a BIGINT/DOUBLE."""
    cols = con.execute(
        """
        select table_name, column_name, data_type from information_schema.columns
        where data_type = 'HUGEINT' or data_type like 'DECIMAL%'
        """
    ).fetchall()
    for table, column, dtype in cols:
        target = "BIGINT" if dtype == "HUGEINT" else "DOUBLE"
        con.execute(f'alter table {table} alter column "{column}" type {target}')


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--snapshots", required=True, type=Path)
    p.add_argument("--out", type=Path, default=DB_PATH)
    args = p.parse_args(argv)
    build(args.snapshots, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
