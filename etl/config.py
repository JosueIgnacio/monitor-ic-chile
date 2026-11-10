"""Configuración compartida del ETL."""
from pathlib import Path
from zoneinfo import ZoneInfo

API_URL = "https://cargadorespublicos.cl/api/data"
USER_AGENT = "monitor-ic-chile (+https://github.com/JosueIgnacio/monitor-ic-chile)"
TZ = ZoneInfo("America/Santiago")

REPO_ROOT = Path(__file__).resolve().parent.parent
CENSO_CSV = REPO_ROOT / "reference" / "censo2024_comunas.csv"
DB_PATH = REPO_ROOT / "dashboard" / "sources" / "monitor" / "monitor.duckdb"

# Tablas que componen una foto diaria. Cada una se guarda como <tabla>.parquet
# dentro de snapshots/AAAA/AAAA-MM-DD/ en la rama `data`.
SNAPSHOT_TABLES = ("locations", "evses", "connectors", "tariffs")

# Mínimos de cordura: si la API devuelve menos que esto, asumimos que está
# rota y no guardamos la foto (el job falla y GitHub avisa por correo).
MIN_LOCATIONS = 300
MIN_EVSES = 800

# Umbral de carga rápida (kW), igual que la referencia del Ministerio.
FAST_KW = 50
