---
title: Mapa
description: Ubicaciones de carga pública, coloreadas por estado o potencia.
sidebar_position: 2
---

{@partial "filtros.md"}

```sql ubic
select location_id, ubicacion, direccion, comuna, region, operador, lat, lon, evses, evses_operativos,
       potencia_max_kw, carga as velocidad, estado_ubicacion as estado, tipo_instalacion
from monitor.ubicaciones
where lat is not null and lon is not null
  and codigo_region like '${inputs.region.value}'
  and coalesce(codigo_comuna, '-') like '${inputs.comuna.value}'
order by case estado_ubicacion when 'Todo operativo' then 1 when 'Parcial' then 2 when 'Nada operativo' then 3 else 4 end
```

<ButtonGroup name=color_por title="Colorear por">
  <ButtonGroupItem valueLabel="Estado" value="estado" default/>
  <ButtonGroupItem valueLabel="Velocidad" value="velocidad"/>
</ButtonGroup>

{#if inputs.color_por === 'velocidad'}

<PointMap
  data={ubic}
  lat=lat
  long=lon
  value=velocidad
  pointName=ubicacion
  height=640
  basemap={'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'}
  attribution="Mapa base © Esri"
  colorPalette={['#0f4c5c', '#e76f51']}
  tooltipType=click
  tooltip={[
    {id: 'ubicacion', showColumnName: false, valueClass: 'text-lg font-semibold'},
    {id: 'operador', title: 'Operador'},
    {id: 'direccion', title: 'Dirección'},
    {id: 'comuna', title: 'Comuna'},
    {id: 'evses', title: 'Puntos de carga', fmt: '#,##0'},
    {id: 'evses_operativos', title: 'Operativos ahora', fmt: '#,##0'},
    {id: 'potencia_max_kw', title: 'Potencia máxima (kW)', fmt: '#,##0.0'}
  ]}
/>

{:else}

<PointMap
  data={ubic}
  lat=lat
  long=lon
  value=estado
  pointName=ubicacion
  height=640
  basemap={'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'}
  attribution="Mapa base © Esri"
  colorPalette={['#2a9d8f', '#e9a23b', '#d1495b', '#9ca3af']}
  tooltipType=click
  tooltip={[
    {id: 'ubicacion', showColumnName: false, valueClass: 'text-lg font-semibold'},
    {id: 'operador', title: 'Operador'},
    {id: 'direccion', title: 'Dirección'},
    {id: 'comuna', title: 'Comuna'},
    {id: 'evses', title: 'Puntos de carga', fmt: '#,##0'},
    {id: 'evses_operativos', title: 'Operativos ahora', fmt: '#,##0'},
    {id: 'potencia_max_kw', title: 'Potencia máxima (kW)', fmt: '#,##0.0'}
  ]}
/>

{/if}

<p class="text-sm text-base-content-muted">Haz clic en un punto para ver su ficha. "Todo operativo" significa que todos sus puntos estaban disponibles u ocupados a las 00:00.</p>
