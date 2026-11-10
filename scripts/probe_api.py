"""Sonda de la API de cargadorespublicos.cl: descarga y describe el esquema.

Imprime estructura, tipos, conteos y valores frecuentes. No imprime campos de
contacto (email, teléfono, web) para no exponerlos en los logs.
"""
import collections
import json
import sys
import urllib.request

URL = "https://cargadorespublicos.cl/api/data"
SENSITIVE = ("mail", "phone", "telefono", "fono", "contact", "website", "url", "web")


def is_sensitive(key: str) -> bool:
    k = key.lower()
    return any(s in k for s in SENSITIVE)


def walk(obj, path, stats, values):
    t = type(obj).__name__
    stats[path][t] += 1
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk(v, f"{path}.{k}", stats, values)
    elif isinstance(obj, list):
        for item in obj:
            walk(item, f"{path}[]", stats, values)
    else:
        last = path.rsplit(".", 1)[-1]
        if is_sensitive(last):
            values[path]["<redactado>"] += 1
        else:
            values[path][str(obj)[:60]] += 1


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "monitor-ic-chile/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        status = r.status
        headers = dict(r.headers)
        raw = r.read()
    print(f"HTTP {status} | {len(raw)/1e6:.2f} MB | content-type={headers.get('Content-Type')}")
    data = json.loads(raw)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "wb") as f:
            f.write(raw)

    stats = collections.defaultdict(collections.Counter)
    values = collections.defaultdict(collections.Counter)
    walk(data, "$", stats, values)

    print("\n=== ESQUEMA (ruta | tipos | n) ===")
    for path in sorted(stats):
        print(f"{path} | {dict(stats[path])}")

    print("\n=== VALORES (n distintos | top 8) ===")
    for path in sorted(values):
        c = values[path]
        top = ", ".join(f"{v!r}:{n}" for v, n in c.most_common(8))
        print(f"{path} | distintos={len(c)} | {top}")


if __name__ == "__main__":
    main()
