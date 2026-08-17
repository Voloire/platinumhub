# -*- coding: utf-8 -*-
"""Il catalogo delle route su GitHub Pages: controllo silenzioso e installazione.

Filosofia identica al controllo aggiornamenti dell'app: si AVVISA e basta.
Il controllo all'avvio e' silenzioso — se manca la connettivita' non compare
nessun messaggio di errore, semplicemente non compare niente — e il download
avviene solo su click esplicito. Ogni file scaricato viene verificato contro
lo SHA256 dichiarato dal manifest e passato dalla validazione severa prima
di toccare il database.
"""

import hashlib
import json
import os
import re
import sqlite3
import urllib.request

from .config import DB, VERSION
from .routes import (ROUTE_FORMAT, load_routes, route_ok,
                     store_route, validate_route)

# La radice del catalogo. PLATINUM_HUB_CATALOG la sovrascrive: serve ai test
# per collaudare tutta la catena contro un server locale, senza rete vera.
CATALOG_BASE = os.environ.get("PLATINUM_HUB_CATALOG",
                              "https://voloire.github.io/platinumhub-routes/")

# Lo stato che la home legge: available e' la lista delle voci del manifest
# nuove o aggiornate rispetto a cio' che sta nel database.
CATALOG = {"checked": False, "available": []}

# Un limite largo ma esplicito: la route piu' grande del catalogo e' ~370 KB.
MAX_ROUTE_BYTES = 5 * 1024 * 1024

# Il manifest e' nostro e viaggia su HTTPS, ma i suoi valori si validano lo
# stesso: id e percorso del file hanno una forma sola.
_RID_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
_FILE_RE = re.compile(r"^routes/[a-z0-9_-]{1,32}\.json$")


def _get(url, limit):
    req = urllib.request.Request(url, headers={"User-Agent": "PlatinumHub/" + VERSION})
    with urllib.request.urlopen(req, timeout=8) as r:
        return r.read(limit + 1)


def installed_versions():
    con = sqlite3.connect(DB)
    try:
        rows = con.execute("SELECT run_id, version FROM routes").fetchall()
    except sqlite3.OperationalError:
        rows = []
    con.close()
    return dict(rows)


def check_catalog():
    """Confronta il manifest con il database. Silenzioso per contratto:
    qualunque errore di rete o di forma lascia solo available=[]."""
    if os.environ.get("PLATINUM_HUB_NO_UPDATE") == "1" and "PLATINUM_HUB_CATALOG" not in os.environ:
        CATALOG["checked"] = True
        return
    try:
        raw = _get(CATALOG_BASE + "index.json", 2 * 1024 * 1024)
        index = json.loads(raw.decode("utf-8"))
        have = installed_versions()
        found = []
        for e in index.get("routes") or []:
            rid, version = e.get("id"), e.get("version")
            if not isinstance(rid, str) or not _RID_RE.match(rid) \
                    or not isinstance(version, int):
                continue
            if not _FILE_RE.match(str(e.get("file") or "")):
                continue
            if not isinstance(e.get("format"), int) or e["format"] > ROUTE_FORMAT:
                continue        # route per un'app piu' nuova: non si offre
            if rid not in have or version > have[rid]:
                found.append({"id": rid, "version": version,
                              "installed": have.get(rid),
                              "game": str(e.get("game") or rid)[:80],
                              "tagline": e.get("tagline") or {},
                              "steps": e.get("steps"),
                              "trophy_total": e.get("trophy_total"),
                              "file": str(e.get("file") or ""),
                              "sha256": str(e.get("sha256") or ""),
                              "size": e.get("size")})
        CATALOG["available"] = found
    except Exception:
        CATALOG["available"] = []
    CATALOG["checked"] = True


def install_route(rid):
    """Scarica, verifica e installa una route dal catalogo. Ritorna (ok, msg)."""
    if not isinstance(rid, str) or not _RID_RE.match(rid):
        return False, "id non valido"
    entry = next((e for e in CATALOG["available"] if e["id"] == rid), None)
    if entry is None:
        return False, "route non nel catalogo"
    try:
        raw = _get(CATALOG_BASE + entry["file"], MAX_ROUTE_BYTES)
    except Exception:
        return False, "download fallito"
    if len(raw) > MAX_ROUTE_BYTES:
        return False, "file troppo grande"
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        return False, "SHA256 diverso dal manifest"
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception:
        return False, "JSON illeggibile"
    if not route_ok(d) or d["meta"]["id"] != rid or d["meta"]["version"] != entry["version"]:
        return False, "il file non corrisponde alla voce del manifest"
    problems = validate_route(d)
    if problems:
        return False, "route non valida: " + "; ".join(problems[:3])
    con = sqlite3.connect(DB)
    store_route(con, d, raw.decode("utf-8"), "catalog")
    con.commit()
    con.close()
    load_routes()
    CATALOG["available"] = [e for e in CATALOG["available"] if e["id"] != rid]
    return True, "installata"
