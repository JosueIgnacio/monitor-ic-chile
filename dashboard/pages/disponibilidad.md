---
title: Disponibilidad
description: Disponibilidad diaria de la red y puntos con más días seguidos fuera de servicio.
sidebar_position: 6
---

{@partial "filtros.md"}

```sql serie
select fecha, estado, orden_estado, sum(evses) as puntos
from monitor.serie_diaria
where codigo_region like '${inputs.region.value}'
  and coalesce(codigo_comuna, '-') like '${inputs.comuna.value}'
group by all
order by fecha, orden_estado
```

```sql disp
select fecha, sum(evses_operativos) / sum(evses) as disponibilidad
from monitor.serie_diaria
where codigo_region like '${inputs.region.value}'
  and coalesce(codigo_comuna, '-') like '${inputs.comuna.value}'
group by 1 order by 1
```

## Disponibilidad diaria de la red

<LineChart
  data={disp}
  x=fecha
  y=disponibilidad
  yFmt="0%"
  xFmt="dd-mm-yyyy"
  yMin=0
  yMax=1
  markers=true
  title="Porcentaje de puntos operativos a las 00:00"
  lineColor="#2a9d8f"
/>

<AreaChart
  data={serie}
  x=fecha
  y=puntos
  series=estado
  type=stacked
  yFmt="#,##0"
  xFmt="dd-mm-yyyy"
  title="Puntos de carga por estado"
  seriesColors={{"Disponible": "#2a9d8f", "Ocupado": "#457b9d", "No disponible": "#e9a23b", "Fuera de línea": "#d1495b", "Desconocido": "#9ca3af"}}
/>

## Disponibilidad por operador

```sql por_op
select operador, sum(evses_operativos) / sum(evses) as disponibilidad, sum(evses) / count(distinct fecha) as puntos_promedio
from monitor.serie_diaria
where codigo_region like '${inputs.region.value}'
  and coalesce(codigo_comuna, '-') like '${inputs.comuna.value}'
  and fecha >= (select max(fecha) - interval 30 day from monitor.serie_diaria)
group by 1
having puntos_promedio >= 5
order by disponibilidad desc
```

<BarChart
  data={por_op}
  x=operador
  y=disponibilidad
  swapXY=true
  yFmt="0%"
  labels=true
  yMax=1
  title="Puntos operativos, promedio de los últimos 30 días"
  subtitle="Operadores con al menos 5 puntos"
  fillColor="#0f4c5c"
/>

## Puntos con más días seguidos fuera de servicio

```sql rachas
select evse_id as punto, ubicacion, operador, region, comuna, estado, racha_fuera_dias, dias_fuera, dias_observados,
       disponibilidad
from monitor.disponibilidad_evse
where racha_fuera_dias > 0
  and codigo_region like '${inputs.region.value}'
  and coalesce(codigo_comuna, '-') like '${inputs.comuna.value}'
order by racha_fuera_dias desc, dias_fuera desc
```

<DataTable data={rachas} search=true rows=15>
  <Column id=punto title="Punto"/>
  <Column id=ubicacion title="Ubicación"/>
  <Column id=operador title="Operador"/>
  <Column id=comuna title="Comuna"/>
  <Column id=estado title="Estado hoy"/>
  <Column id=racha_fuera_dias title="Días seguidos fuera" fmt="#,##0" contentType=colorscale colorScale=negative/>
  <Column id=dias_fuera title="Días fuera (total)" fmt="#,##0"/>
  <Column id=disponibilidad title="Disponibilidad histórica" fmt="0%"/>
</DataTable>

<p class="text-sm text-base-content-muted">Un punto está "operativo" si a las 00:00 aparece disponible u ocupado. Los días se cuentan desde la primera foto diaria (10-11-2026), así que las rachas crecen a medida que se acumula historia.</p>
