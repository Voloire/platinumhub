# -*- coding: utf-8 -*-
"""Le route: seed dal bundle, archivio in SQLite, caricamento in memoria.

Una route e' un file JSON autodescrittivo (blocco meta + fasi + passi con
sid). A runtime vive nella tabella `routes` del database: il bundle data/
e' solo il seme — al primo avvio (e a ogni avvio con una versione in bundle
piu' nuova) i file vengono importati nel database, e l'app legge SOLO da li'.
Cosi' una route scaricata dal catalogo e una route in bundle sono la stessa
cosa, e nessuna richiede una release dell'applicazione.
"""

import hashlib
import json
import os
import sqlite3

from .config import DATA, DB

# Il formato di route piu' alto che questa app sa leggere: una route con
# meta.format superiore viene rifiutata invece di essere importata e rompersi.
ROUTE_FORMAT = 1

ROUTES = {}


def structure_hash(route):
    """L'impronta dello scheletro: sid e flag trofeo, in ordine di pagina.

    Due versioni di una route con la stessa impronta differiscono solo nei
    testi. Lo stesso identico algoritmo vive in tools/build_index.py del
    repo del catalogo: se cambi uno, cambia anche l'altro.
    """
    skel = "|".join("%s:%s" % (s.get("sid"), "T" if s.get("trophy") else "F")
                    for p in route["phases"] for s in p["steps"])
    return hashlib.sha256(skel.encode("utf-8")).hexdigest()


def route_ok(d):
    """Controllo minimo di forma prima di importare: meta coerente e passi con sid.

    Non e' la validazione completa (quella la fanno i test e il catalogo):
    e' l'ultima rete che impedisce a un file rotto di entrare nel database.
    """
    meta = d.get("meta")
    if not isinstance(meta, dict):
        return False
    if not isinstance(meta.get("id"), str) or not meta["id"]:
        return False
    if not isinstance(meta.get("version"), int) or meta["version"] < 1:
        return False
    if not isinstance(meta.get("format"), int) or not (1 <= meta["format"] <= ROUTE_FORMAT):
        return False
    phases = d.get("phases")
    if not isinstance(phases, list) or not phases:
        return False
    for p in phases:
        steps = p.get("steps")
        if not isinstance(steps, list) or not steps:
            return False
        for s in steps:
            if not isinstance(s.get("sid"), str):
                return False
    return True


def _routes_table(con):
    con.execute("""CREATE TABLE IF NOT EXISTS routes(
        run_id TEXT PRIMARY KEY,
        json TEXT NOT NULL,
        version INTEGER NOT NULL,
        format INTEGER NOT NULL,
        structure_hash TEXT NOT NULL,
        source TEXT NOT NULL DEFAULT 'bundle',
        installed_at TEXT NOT NULL DEFAULT (datetime('now')))""")


def store_route(con, d, raw, source):
    """Scrive una route (gia' passata da route_ok) nella tabella."""
    meta = d["meta"]
    con.execute("""INSERT INTO routes(run_id,json,version,format,structure_hash,source,
                                      installed_at)
                   VALUES(?,?,?,?,?,?,datetime('now'))
                   ON CONFLICT(run_id) DO UPDATE SET
                       json=excluded.json, version=excluded.version,
                       format=excluded.format, structure_hash=excluded.structure_hash,
                       source=excluded.source, installed_at=excluded.installed_at""",
                (meta["id"], raw, meta["version"], meta["format"],
                 structure_hash(d), source))


def seed_bundle(con):
    """Importa nel database le route del bundle che mancano o sono piu' nuove.

    Una route installata dal catalogo con versione maggiore non viene mai
    retrocessa dal bundle: vince sempre il numero di versione piu' alto.
    """
    if not os.path.isdir(DATA):
        return
    for name in sorted(f for f in os.listdir(DATA) if f.endswith(".json")):
        path = os.path.join(DATA, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
            d = json.loads(raw)
        except Exception:
            print("  !! route in bundle illeggibile:", name)
            continue
        if not route_ok(d):
            print("  !! route in bundle non valida:", name)
            continue
        row = con.execute("SELECT version FROM routes WHERE run_id=?",
                          (d["meta"]["id"],)).fetchone()
        if row is None or d["meta"]["version"] > row[0]:
            store_route(con, d, raw, "bundle")
    con.commit()


def _prepare(d):
    """I precalcoli che tutta l'app da' per scontati su una route caricata."""
    d["_steps"] = sum(len(p["steps"]) for p in d["phases"])
    d["_tsteps"] = sum(1 for p in d["phases"] for s in p["steps"] if s.get("trophy"))
    # I sid in ordine di pagina: la chiave dei progressi e dei marker.
    d["_sids"] = [s.get("sid") for p in d["phases"] for s in p["steps"]]
    d["_sidset"] = set(d["_sids"])
    d["_trophy_sids"] = {s.get("sid") for p in d["phases"]
                         for s in p["steps"] if s.get("trophy")}
    return d


def load_routes():
    """Semina dal bundle, poi carica TUTTE le route dal database, in ordine di meta.order."""
    con = sqlite3.connect(DB)
    _routes_table(con)
    seed_bundle(con)
    rows = con.execute("SELECT run_id, json FROM routes").fetchall()
    con.close()
    loaded = []
    for rid, raw in rows:
        try:
            d = json.loads(raw)
        except Exception:
            print("  !! route corrotta nel database:", rid)
            continue
        if not route_ok(d) or d["meta"]["id"] != rid:
            print("  !! route non valida nel database:", rid)
            continue
        loaded.append(_prepare(d))
    loaded.sort(key=lambda d: (d["meta"].get("order", 10**6), d["meta"]["id"]))
    ROUTES.clear()
    for d in loaded:
        ROUTES[d["meta"]["id"]] = d
