---
title: Territorio
description: Distribución regional y comunal, cobertura y puntos de carga por habitante (Censo 2024).
sidebar_position: 3
---

```sql f_regiones
select codigo_region, region, orden from monitor.regiones order by orden
```

<Dropdown name=region data={f_regiones} value=codigo_region label=region order=orden title="Región" defaultValue="%">
  <DropdownOption value="%" valueLabel="Todas las regiones"/>
</Dropdown>

```sql com
select * from monitor.cobertura_comunal where codigo_region like '${inputs.region.value}'
```

```sql kpi
select count(*) filter (where con_infraestructura) as con,
       count(*) filter (where not con_infraestructura) as sin,
       count(*) filter (where con_infraestructura) / count(*) as share_con,
       sum(poblacion) filter (where not con_infraestructura) as poblacion_sin,
       sum(evses) * 100000.0 / sum(poblacion) as evses_100k
from ${com}
```

## Despliegue regional

<Grid cols=4>
<BigValue data={kpi} value=con title="Comunas CON infraestructura" fmt="#,##0" comparison=share_con comparisonFmt="0%" comparisonTitle="del total" comparisonDelta=false/>
<BigValue data={kpi} value=sin title="Comunas SIN infraestructura" fmt="#,##0"/>
<BigValue data={kpi} value=poblacion_sin title="Habitantes en comunas sin carga" fmt="#,##0"/>
<BigValue data={kpi} value=evses_100k title="Puntos por 100 mil habitantes" fmt="#,##0.0"/>
</Grid>

```sql reg
select region, orden_region, evses, evses_operativos, evses_100k, comunas, comunas_con, poblacion,
       comunas_con / comunas as share_comunas
from monitor.cobertura_regional
order by orden_region
```

<Grid cols=2>
<BarChart
  data={reg}
  title="Puntos de carga por región"
  subtitle="De norte a sur"
  x=region
  y=evses
  swapXY=true
  sort=false
  labels=true
  yFmt="#,##0"
/>
<BarChart
  data={reg}
  title="Puntos de carga por 100 mil habitantes"
  subtitle="Población: Censo 2024"
  x=region
  y=evses_100k
  swapXY=true
  sort=false
  labels=true
  yFmt="#,##0.0"
  fillColor="#2a9d8f"
/>
</Grid>

<DataTable data={reg} rows=all>
  <Column id=region title="Región"/>
  <Column id=evses title="Puntos" fmt="#,##0"/>
  <Column id=evses_operativos title="Operativos" fmt="#,##0"/>
  <Column id=evses_100k title="Por 100 mil hab." fmt="#,##0.0" contentType=colorscale colorScale=positive/>
  <Column id=comunas_con title="Comunas con carga" fmt="#,##0"/>
  <Column id=comunas title="Comunas" fmt="#,##0"/>
  <Column id=share_comunas title="% comunas cubiertas" fmt="0%" contentType=bar/>
  <Column id=poblacion title="Población" fmt="#,##0"/>
</DataTable>

## Comunas con y sin infraestructura de carga

```sql con
select comuna, region, ubicaciones, evses, evses_operativos, evses_100k, poblacion
from ${com} where con_infraestructura order by evses desc
```

```sql sin
select comuna, region, poblacion
from ${com} where not con_infraestructura order by poblacion desc
```

<Tabs>
<Tab label="Con infraestructura">
<DataTable data={con} search=true rows=15>
  <Column id=comuna title="Comuna"/>
  <Column id=region title="Región"/>
  <Column id=ubicaciones title="Ubicaciones" fmt="#,##0"/>
  <Column id=evses title="Puntos" fmt="#,##0"/>
  <Column id=evses_operativos title="Operativos" fmt="#,##0"/>
  <Column id=evses_100k title="Por 100 mil hab." fmt="#,##0.0"/>
  <Column id=poblacion title="Población" fmt="#,##0"/>
</DataTable>
</Tab>
<Tab label="Sin infraestructura">
<DataTable data={sin} search=true rows=15>
  <Column id=comuna title="Comuna"/>
  <Column id=region title="Región"/>
  <Column id=poblacion title="Población" fmt="#,##0"/>
</DataTable>
</Tab>
</Tabs>

## Rutas interurbanas

```sql ambito
select u.region, u.orden_region, u.ambito, sum(u.evses) as evses
from monitor.ubicaciones u
where u.codigo_region like '${inputs.region.value}'
group by all order by u.orden_region
```

<BarChart
  data={ambito}
  title="Puntos de carga urbanos e interurbanos"
  subtitle="Según el tipo de instalación declarado"
  x=region
  y=evses
  series=ambito
  swapXY=true
  sort=false
  type=stacked
  yFmt="#,##0"
/>
