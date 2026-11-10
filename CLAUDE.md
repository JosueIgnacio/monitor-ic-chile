# Monitor IC Chile: guía para mantener el proyecto con Claude

Dashboard público de la red de carga para vehículos eléctricos en Chile. Se actualiza solo cada noche con datos de https://cargadorespublicos.cl/api/data (JSON público, no documentado).

Idioma del proyecto: **español** (código comentado, textos del sitio, commits y PRs).

## Cómo está armado

```
API cargadorespublicos.cl
   │  (GitHub Actions, 00:00 hora de Chile: .github/workflows/etl.yml)
   ▼
etl/snapshot.py ──► rama `data`: snapshots/AAAA/AAAA-MM-DD/{locations,evses,connectors,tariffs}.parquet + manifest.csv
   │  (cada build: .github/workflows/dashboard.yml)
   ▼
etl/build_db.py ──► dashboard/sources/monitor/monitor.duckdb (no se versiona)
   ▼
dashboard/ (Evidence) ──► sitio estático ──► Cloudflare Pages
```

| Ruta | Qué es |
| --- | --- |
| `etl/clean.py` | Lista blanca de campos que se guardan de la API. Toda limpieza va aquí. |
| `etl/comunas.py` | Cruce de nombres de comuna con el código CUT. Alias para variantes nuevas. |
| `etl/snapshot.py` | Descarga, valida y escribe la foto diaria en Parquet. |
| `etl/build_db.py` | Toda la lógica de negocio en SQL: estado actual, series, rachas, altas/bajas, cobertura. |
| `reference/censo2024_comunas.csv` | Población por comuna, Censo 2024 (346 comunas). |
| `dashboard/pages/*.md` | Una página del sitio por archivo (Evidence, sintaxis clásica `<Componente/>`). |
| `dashboard/partials/filtros.md` | Filtros de región y comuna que comparten las páginas. |
| `dashboard/sources/monitor/*.sql` | Una tabla de `monitor.duckdb` expuesta a las páginas (`select * from tabla`). |
| `dashboard/patches/` | Parche a Evidence para formato numérico chileno (1.234,5). Se aplica en `npm ci`. |

## Reglas que no se rompen

1. **Nunca publicar datos de contacto.** Email, teléfonos, sitios web, RUT, direcciones de empresas, número de cliente: no se guardan. Si agregas un campo en `etl/clean.py`, confirma que no es de contacto y amplía `test_no_contact_data_leaks`.
2. **La rama `data` solo la escribe el workflow ETL.** No la edites a mano ni la reescribas: es la historia del proyecto y no se puede reconstruir.
3. **Todo cambio entra por PR a `main`**, con capturas (el workflow las comenta solo) y aprobación del dueño.
4. **La lógica va en `etl/build_db.py`, no en las páginas.** Las páginas solo filtran y grafican. Si necesitas una métrica nueva, créala como tabla en `build_db.py` y agrega su `.sql` en `dashboard/sources/monitor/`.
5. **Los filtros usan códigos, no nombres** (`codigo_region like '${inputs.region.value}'`), porque nombres como O'Higgins rompen el SQL.
6. Evidence falla si una tabla de fuente queda vacía; `build_db.py` le agrega una fila de NULL. En las páginas filtra con `where <columna> is not null` las tablas que pueden estar vacías (como `altas_bajas_detalle`).
7. Evidence no maneja `HUGEINT` ni `DECIMAL`; `build_db.py` los convierte al final. Usa `sum(...)` sin miedo.

## Definiciones (deben coincidir con la página Metodología)

- **Punto de carga** = EVSE. **Lento** < 50 kW, **rápido** ≥ 50 kW (potencia máxima del EVSE).
- **Operativo** = estado DISPONIBLE u OCUPADO en la foto de las 00:00.
- **Tramos de potencia de conectores**: 0–10, 11–22, 23–49, 50–150, más de 150 kW.

## Comandos

```bash
# ETL y pruebas (Python 3.12)
pip install -r requirements.txt
python -m pytest -q etl
git fetch origin data && git worktree add ../data origin/data      # fotos diarias
python -m etl.build_db --snapshots ../data/snapshots

# Dashboard
cd dashboard && npm ci
npm run sources && npm run dev        # servidor local en http://localhost:3000
npm run build:strict                  # lo mismo que corre CI
```

`npm run sources` necesita descargar la extensión parquet de DuckDB desde `extensions.duckdb.org`. Si tu entorno bloquea ese dominio (por ejemplo, Claude Code en la nube), no podrás compilar localmente: sube el cambio a un PR y revisa las capturas que deja el workflow `Dashboard` en el PR (también quedan en la rama `capturas`).

## Flujo de un cambio

1. Crea una rama desde `main`.
2. Haz el cambio y corre `python -m pytest -q etl`.
3. Abre un PR usando la plantilla. El workflow `Dashboard` construye el sitio, comenta capturas de las 8 páginas y, si Cloudflare está configurado, publica una vista previa.
4. Revisa tú mismo las capturas antes de pedir revisión. Si alguna página falla, el workflow lo marca con ✗.
5. El dueño del repo aprueba y hace merge; producción se actualiza sola.

## Problemas conocidos

- La API no trae fecha de instalación: el crecimiento histórico es una estimación (`historia_estimada`) y se rotula así.
- Comunas sin calce con el Censo aparecen en el log del ETL ("Comunas sin calce"). Agrega el alias en `etl/comunas.py` y un caso en `etl/tests/test_etl.py`.
- GitHub puede atrasar el cron hasta ~30 min; el ETL acepta correr hasta las 02:59 de Chile.
