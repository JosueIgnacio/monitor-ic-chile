---
title: Tarifas
description: Precio por kWh declarado, por operador y tipo de corriente.
sidebar_position: 7
---

{@partial "filtros.md"}

```sql t
select * from monitor.tarifas
where codigo_region like '${inputs.region.value}'
  and coalesce(codigo_comuna, '-') like '${inputs.comuna.value}'
```

```sql kpi
select
  median(precio_kwh) filter (where corriente = 'AC') as ac,
  median(precio_kwh) filter (where corriente = 'DC') as dc,
  count(*) as conectores
from ${t}
```

```sql por_op
select operador, corriente,
       min(precio_kwh) as minimo,
       quantile_cont(precio_kwh, 0.25) as p25,
       median(precio_kwh) as mediana,
       quantile_cont(precio_kwh, 0.75) as p75,
       max(precio_kwh) as maximo,
       count(*) as conectores
from ${t}
group by all
having count(*) >= 3
order by corriente, mediana
```

## Precio de la energía

<Grid cols=3>
<BigValue data={kpi} value=ac title="Mediana AC ($/kWh)" fmt="$#,##0"/>
<BigValue data={kpi} value=dc title="Mediana DC ($/kWh)" fmt="$#,##0"/>
<BigValue data={kpi} value=conectores title="Conectores con tarifa informada" fmt="#,##0"/>
</Grid>

<BarChart
  data={por_op}
  x=operador
  y=mediana
  series=corriente
  type=grouped
  swapXY=true
  yFmt="$#,##0"
  labels=true
  title="Precio mediano por kWh, por operador"
  subtitle="Pesos chilenos, IVA según lo declarado por el operador"
  seriesColors={{"AC": "#0f4c5c", "DC": "#e76f51"}}
/>

<DataTable data={por_op} rows=all>
  <Column id=operador title="Operador"/>
  <Column id=corriente title="Corriente"/>
  <Column id=minimo title="Mínimo" fmt="$#,##0"/>
  <Column id=mediana title="Mediana" fmt="$#,##0"/>
  <Column id=maximo title="Máximo" fmt="$#,##0"/>
  <Column id=conectores title="Conectores" fmt="#,##0"/>
</DataTable>

<p class="text-sm text-base-content-muted">Se considera el componente de energía ($/kWh) de la primera tarifa de cada conector. Algunos operadores agregan cargos fijos o por tiempo que no se muestran aquí. Solo operadores con 3 o más conectores con tarifa.</p>
