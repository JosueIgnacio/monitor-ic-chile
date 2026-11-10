---
title: Crecimiento
description: Evolución de la red, histórica estimada y medida día a día desde las fotos diarias.
sidebar_position: 4
---

{@partial "filtros.md"}

```sql hist
select anio::varchar as anio, anio as anio_num, speed as velocidad, count(*) as nuevos
from monitor.historia_estimada
where anio is not null
  and codigo_region like '${inputs.region.value}'
  and coalesce(codigo_comuna, '-') like '${inputs.comuna.value}'
group by all
```

```sql acumulado
select anio, velocidad,
       sum(nuevos) over (partition by velocidad order by anio_num) as acumulado
from ${hist}
order by anio_num
```

```sql anual
with t as (
  select anio_num, sum(nuevos) as nuevos from ${hist} group by 1
),
a as (
  select anio_num, sum(nuevos) over (order by anio_num) as acumulado from t
)
select anio_num::varchar as anio, acumulado,
       acumulado / lag(acumulado) over (order by anio_num) - 1 as crecimiento
from a order by anio_num
```

```sql crec
select
  max(case when anio = '2023' then crecimiento end) as c2023,
  max(case when anio = '2024' then crecimiento end) as c2024,
  max(case when anio = '2025' then crecimiento end) as c2025
from ${anual}
```

## Cantidad acumulada de puntos de carga

<Grid cols=3>
<BigValue data={crec} value=c2023 title="Crecimiento 2023 vs 2022" fmt="+0%"/>
<BigValue data={crec} value=c2024 title="Crecimiento 2024 vs 2023" fmt="+0%"/>
<BigValue data={crec} value=c2025 title="Crecimiento 2025 vs 2024" fmt="+0%"/>
</Grid>

<BarChart
  data={acumulado}
  x=anio
  y=acumulado
  series=velocidad
  type=stacked
  yFmt="#,##0"
  labels=true
  seriesColors={{"Lento": "#0f4c5c", "Rápido": "#e76f51"}}
  xType=category
/>

<Alert status=warning>
<b>Estimación.</b> La fuente no publica la fecha de instalación. Usamos la fecha más antigua entre la fecha de conexión y la de revisión de la declaración, y contamos solo los puntos que siguen activos hoy. Sirve para ver la tendencia, no como cifra oficial. Lentos: menos de 50 kW; rápidos: 50 kW o más.
</Alert>

## Medido día a día

```sql serie
select fecha, velocidad, sum(evses) as puntos
from monitor.serie_diaria
where codigo_region like '${inputs.region.value}'
  and coalesce(codigo_comuna, '-') like '${inputs.comuna.value}'
group by all
order by fecha
```

<AreaChart
  data={serie}
  x=fecha
  y=puntos
  series=velocidad
  yFmt="#,##0"
  xFmt="dd-mm-yyyy"
  seriesColors={{"Lento": "#0f4c5c", "Rápido": "#e76f51"}}
  emptySet=pass
/>

<p class="text-sm text-base-content-muted">Esta serie se construye con la foto de cada medianoche desde el 10-11-2026 y se vuelve más útil con cada día que pasa.</p>
