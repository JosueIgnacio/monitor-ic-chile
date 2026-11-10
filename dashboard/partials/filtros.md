```sql f_regiones
select codigo_region, region, orden from monitor.regiones order by orden
```

```sql f_comunas
select codigo_comuna, comuna
from monitor.cobertura_comunal
where codigo_region like '${inputs.region.value}' and con_infraestructura
order by comuna
```


<Dropdown name=region data={f_regiones} value=codigo_region label=region order=orden title="Región" defaultValue="%">
  <DropdownOption value="%" valueLabel="Todas las regiones"/>
</Dropdown>
<Dropdown name=comuna data={f_comunas} value=codigo_comuna label=comuna title="Comuna" defaultValue="%">
  <DropdownOption value="%" valueLabel="Todas las comunas"/>
</Dropdown>

