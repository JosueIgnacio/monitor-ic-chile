---
title: Operadores
description: Participación de mercado, disponibilidad y medios de pago por operador.
sidebar_position: 5
---

{@partial "filtros.md"}

```sql ev
select * from monitor.evses
where codigo_region like '${inputs.region.value}'
  and coalesce(codigo_comuna, '-') like '${inputs.comuna.value}'
```

```sql ops
select operador,
       count(distinct location_id) as ubicaciones,
       count(*) as puntos,
       count(*) filter (where speed = 'Rápido') as rapidos,
       count(*) filter (where operativo) as operativos,
       count(*) filter (where operativo) / count(*) as disponibilidad,
       count(*) / sum(count(*)) over () as participacion
from ${ev}
group by 1
order by puntos desc
```

## Participación por operador

<BarChart
  data={ops}
  x=operador
  y=puntos
  swapXY=true
  labels=true
  yFmt="#,##0"
  title="Puntos de carga por operador"
/>

<DataTable data={ops} rows=all>
  <Column id=operador title="Operador"/>
  <Column id=ubicaciones title="Ubicaciones" fmt="#,##0"/>
  <Column id=puntos title="Puntos" fmt="#,##0"/>
  <Column id=participacion title="Participación" fmt="0.0%" contentType=bar/>
  <Column id=rapidos title="Rápidos" fmt="#,##0"/>
  <Column id=disponibilidad title="Operativos hoy" fmt="0%" contentType=colorscale colorScale=positive/>
</DataTable>

<p class="text-sm text-base-content-muted">"Sin operador informado" agrupa las ubicaciones declaradas sin un operador de carga asignado. La evolución histórica por operador está en la página Disponibilidad.</p>

## Cómo se paga y cómo se activa

```sql pagos
select medio, count(*) as puntos
from (select unnest(string_split(medios_pago, ',')) as medio from ${ev} where medios_pago <> '')
group by 1 order by puntos desc
```

```sql activacion
select medio, count(*) as puntos
from (select unnest(string_split(medios_activacion, ',')) as medio from ${ev} where medios_activacion <> '')
group by 1 order by puntos desc
```

<Grid cols=2>
<BarChart data={pagos} x=medio y=puntos swapXY=true labels=true yFmt="#,##0" title="Medios de pago aceptados" subtitle="Un punto puede aceptar varios"/>
<BarChart data={activacion} x=medio y=puntos swapXY=true labels=true yFmt="#,##0" title="Formas de iniciar la carga" subtitle="Un punto puede ofrecer varias" fillColor="#2a9d8f"/>
</Grid>

## Fabricantes

```sql marcas
select coalesce(marca, 'No informada') as marca, count(*) as puntos
from ${ev} group by 1 order by puntos desc limit 12
```

<BarChart data={marcas} x=marca y=puntos swapXY=true labels=true yFmt="#,##0" title="Marcas de cargadores más comunes" fillColor="#6d597a"/>
