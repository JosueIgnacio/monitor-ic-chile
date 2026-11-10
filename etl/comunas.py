"""Cruce de nombres de comuna/región de la API con los códigos CUT del Censo 2024.

La API escribe las comunas a mano y sin un código: a veces sin tildes
("Vina del Mar"), con variantes ("Llay-Llay") o con mayúsculas. Normalizamos el
texto y, si aun así no calza, usamos la tabla ALIASES.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .config import CENSO_CSV


def normalize(text: str | None) -> str:
    """'Viña del Mar' -> 'vina del mar'; 'O'Higgins' -> 'ohiggins'."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", str(text))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower().replace("'", "").replace("’", "")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# Nombre normalizado tal como viene en la API -> nombre normalizado del Censo.
# Agrega aquí las variantes nuevas que aparezcan en el log "Comunas sin calce".
ALIASES: dict[str, str] = {
    "llay llay": "llaillay",
    "til til": "tiltil",
    "marchigue": "marchihue",
    "paiguano": "paihuano",
    "cabo de hornos ex navarino": "cabo de hornos",
    "coihaique": "coyhaique",
    "puerto natales": "natales",
    "santiago centro": "santiago",
    "san vicente de tagua tagua": "san vicente",
    "san vicente tagua tagua": "san vicente",
    "trehuaco": "treguaco",
    "alto bio bio": "alto biobio",
    "la calera": "calera",
    "rapa nui": "isla de pascua",
}

# Región normalizada de la API -> código de región CUT.
REGION_ALIASES: dict[str, str] = {
    "metropolitana": "13",
    "region metropolitana": "13",
    "libertador bernardo ohiggins": "06",
    "ohiggins": "06",
    "aysen": "11",
    "aysen del general carlos ibanez del campo": "11",
    "magallanes": "12",
    "magallanes y de la antartica chilena": "12",
    "biobio": "08",
    "bio bio": "08",
    "nuble": "16",
}


@dataclass(frozen=True)
class Comuna:
    codigo_comuna: str
    nombre_comuna: str
    codigo_region: str
    nombre_region: str
    poblacion: int


@lru_cache(maxsize=1)
def load_censo(path: Path = CENSO_CSV) -> tuple[Comuna, ...]:
    with open(path, encoding="utf-8") as f:
        return tuple(
            Comuna(
                codigo_comuna=r["codigo_comuna"],
                nombre_comuna=r["nombre_comuna"],
                codigo_region=r["codigo_region"],
                nombre_region=r["nombre_region"],
                poblacion=int(r["poblacion_censada"]),
            )
            for r in csv.DictReader(f)
        )


@lru_cache(maxsize=1)
def _by_name() -> dict[str, Comuna]:
    return {normalize(c.nombre_comuna): c for c in load_censo()}


@lru_cache(maxsize=1)
def _regions() -> dict[str, str]:
    out = {normalize(c.nombre_region): c.codigo_region for c in load_censo()}
    out.update(REGION_ALIASES)
    return out


def match_comuna(name: str | None) -> Comuna | None:
    key = normalize(name)
    if not key:
        return None
    table = _by_name()
    if key in table:
        return table[key]
    alias = ALIASES.get(key)
    if alias and alias in table:
        return table[alias]
    return None


def match_region(name: str | None) -> str | None:
    """Devuelve el código CUT de la región (p. ej. '13') o None."""
    return _regions().get(normalize(name))


def region_name(code: str | None) -> str | None:
    for c in load_censo():
        if c.codigo_region == code:
            return c.nombre_region
    return None
