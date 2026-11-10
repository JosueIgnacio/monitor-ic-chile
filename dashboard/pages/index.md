---
title: Monitor IC Chile
description: Infraestructura de carga pública para vehículos eléctricos en Chile, actualizada cada día.
sidebar_position: 1
---

```sql meta
select ultima_foto, n_fotos from monitor.metadatos
```

<p class="text-base-content-muted">
Red de carga pública para vehículos eléctricos según <a href="https://cargadorespublicos.cl" target="_blank">cargadorespublicos.cl</a>. Foto del <b><Value data={meta} column=ultima_foto fmt="dd-mm-yyyy"/></b> a las 00:00 (hora de Chile).
</p>

{@partial "filtros.md"}

```sql evses_f
select * from monitor.evses
where codigo_region like '${inputs.region.value}'
  and coalesce(codigo_comuna, '-') like '${inputs.comuna.value}'
```

```sql conectores_f
select * from monitor.conectores
where codigo_region like '${inputs.region.value}'
  and coalesce(codigo_comuna, '-') like '${inputs.comuna.value}'
```

```sql kpi
select
  count(distinct location_id) as ubicaciones,
  count(*) as puntos,
  count(*) filter (where speed = 'Lento') as lentos,
  count(*) filter (where speed = 'Rápido') as rapidos,
  count(*) filter (where current_type = 'AC') as puntos_ac,
  count(*) filter (where current_type = 'DC') as puntos_dc,
  count(*) filter (where operativo) as operativos,
  count(*) filter (where operativo) / nullif(count(*), 0) as disponibilidad
from ${evses_f}
```

```sql kpi_con
select
  count(*) as conectores,
  count(*) filter (where corriente = 'AC') as ac,
  count(*) filter (where corriente = 'DC') as dc,
  count(*) filter (where estandar = 'Tipo 1') as tipo1,
  count(*) filter (where estandar = 'Tipo 2') as tipo2,
  count(*) filter (where estandar = 'CHAdeMO') as chademo,
  count(*) filter (where estandar = 'CCS 1') as ccs1,
  count(*) filter (where estandar = 'CCS 2') as ccs2,
  count(*) filter (where estandar like 'GB/T%') as gbt
from ${conectores_f}
```

## La red hoy

<Grid cols=4>
<BigValue data={kpi} value=ubicaciones title="Ubicaciones" fmt="#,##0" description="Lugares con al menos un punto de carga declarado."/>
<BigValue data={kpi} value=puntos title="Puntos de carga" fmt="#,##0" description="Cada punto (EVSE) puede cargar un vehículo a la vez."/>
<BigValue data={kpi_con} value=conectores title="Conectores" fmt="#,##0" description="Un punto puede tener varios conectores de distinto estándar."/>
<BigValue data={kpi} value=disponibilidad title="Operativos ahora" fmt="0.0%" description="Puntos disponibles u ocupados en la foto de las 00:00."/>
</Grid>

<Grid cols=4>
<BigValue data={kpi} value=lentos title="Puntos lentos" fmt="#,##0" description="Potencia máxima menor a 50 kW."/>
<BigValue data={kpi} value=rapidos title="Puntos rápidos" fmt="#,##0" description="Potencia máxima de 50 kW o más."/>
<BigValue data={kpi} value=puntos_ac title="Puntos AC" fmt="#,##0" description="Corriente alterna."/>
<BigValue data={kpi} value=puntos_dc title="Puntos DC" fmt="#,##0" description="Corriente continua."/>
</Grid>

### Conectores por estándar

<Grid cols=5>
<BigValue data={kpi_con} value=tipo2 title="AC · Tipo 2" fmt="#,##0"/>
<BigValue data={kpi_con} value=tipo1 title="AC · Tipo 1" fmt="#,##0"/>
<BigValue data={kpi_con} value=ccs2 title="DC · CCS 2" fmt="#,##0"/>
<BigValue data={kpi_con} value=chademo title="DC · CHAdeMO" fmt="#,##0"/>
<BigValue data={kpi_con} value=gbt title="DC · GB/T" fmt="#,##0"/>
</Grid>

```sql por_tipo
select corriente, estandar, count(*) as conectores
from ${conectores_f}
group by all
order by conectores desc
```

```sql por_potencia
select tramo_potencia, orden_tramo, count(*) as conectores
from ${conectores_f}
where tramo_potencia <> 'Sin dato'
group by all
order by orden_tramo
```

<Grid cols=2>
<BarChart
  data={por_tipo}
  title="Conectores por tipo"
  x=estandar
  y=conectores
  series=corriente
  swapXY=true
  type=stacked
  yFmt="#,##0"
  labels=true
  seriesColors={{"AC": "#0f4c5c", "DC": "#e76f51"}}
/>
<BarChart
  data={por_potencia}
  fillColor="#2a9d8f"
  title="Conectores por potencia de carga"
  x=tramo_potencia
  y=conectores
  swapXY=true
  sort=false
  yFmt="#,##0"
  labels=true
/>
</Grid>

### Estado de los puntos de carga

```sql por_estado
select estado, orden_estado, count(*) as puntos, count(*) / sum(count(*)) over () as participacion
from ${evses_f}
group by all
order by orden_estado
```

<BarChart
  data={por_estado}
  x=estado
  y=puntos
  series=estado
  sort=false
  labels=true
  yFmt="#,##0"
  legend=false
  seriesColors={{"Disponible": "#2a9d8f", "Ocupado": "#457b9d", "No disponible": "#e9a23b", "Fuera de línea": "#d1495b", "Desconocido": "#9ca3af"}}
  chartAreaHeight=180
/>

<p class="text-sm text-base-content-muted">"Fuera de línea" significa que el punto no reporta su estado al sistema; "No disponible", que el operador lo marcó fuera de servicio.</p>

### Cambios desde la foto anterior

```sql cambios
select tipo, evse_id as punto, ubicacion, operador, region, comuna, max_power_kw as potencia_kw
from monitor.altas_bajas_detalle
where fecha is not null
  and fecha = (select max(fecha) from monitor.altas_bajas_detalle)
  and coalesce(codigo_region, '-') like '${inputs.region.value}'
  and coalesce(codigo_comuna, '-') like '${inputs.comuna.value}'
order by tipo, region, comuna
```

<DataTable data={cambios} rows=10 emptySet=pass emptyMessage="Sin altas ni bajas registradas aún: se calculan desde la segunda foto diaria.">
  <Column id=tipo title="Tipo"/>
  <Column id=punto title="Punto"/>
  <Column id=ubicacion title="Ubicación"/>
  <Column id=operador title="Operador"/>
  <Column id=region title="Región"/>
  <Column id=comuna title="Comuna"/>
  <Column id=potencia_kw title="Potencia (kW)" fmt="#,##0.0"/>
</DataTable>
