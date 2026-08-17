# -*- coding: utf-8 -*-
"""Registro delle run e caricamento delle route da data/."""

import json
import os

from .config import DATA


# ---------------------------------------------------------------- run registry
RUNS = [
    {"id": "er", "file": "er.json", "accent": "#c8a24a",
     "tagline": {"en": "Vagabond shield-knight - all 42 trophies, 3 endings via save backup",
                 "it": "Vagabondo con scudo - tutti e 42 i trofei, 3 finali col backup del salvataggio"}},
    {"id": "dsr", "file": "dsr.json", "accent": "#b8642e",
     "tagline": {"en": "Knight - the original grind, done in the right order",
                 "it": "Cavaliere - il grind originale, nell'ordine giusto"}},
    {"id": "ds3", "file": "ds3.json", "accent": "#8ea0c0",
     "tagline": {"en": "Knight - every ring, every boss soul, three endings",
                 "it": "Cavaliere - ogni anello, ogni anima di boss, tre finali"}},
    {"id": "sb", "file": "sb.json", "accent": "#d06a8a",
     "tagline": {"en": "Eve - the collectible run, nothing missed",
                 "it": "Eve - la run dei collezionabili, senza perdere niente"}},
    {"id": "kz", "file": "kz.json", "accent": "#6aa8a0",
     "tagline": {"en": "Greatsword Khazan - true ending gates handled",
                 "it": "Khazan con spadone - i gate del finale vero gestiti"}},
    {"id": "lop", "file": "lop.json", "accent": "#a06ad0",
     "tagline": {"en": "Motivity strength build - 42 base + 11 Overture achievements",
                 "it": "Build di forza (Motivity) - 42 achievement base + 11 della DLC Overture"}},
    {"id": "bor", "file": "bor.json", "accent": "#7fc98a",
     "tagline": {"en": "Emma & Koo - parry-tank, story mode, NG+ clear",
                 "it": "Emma e Kuu - parry-tank, story mode, clear in NG+"}},
    {"id": "bmw", "file": "bmw.json", "accent": "#c8483f",
     "tagline": {"en": "Smash-stance tank - 36 trophies, secret ending, one NG+ cycle",
                 "it": "Tank in posizione Smash - 36 trofei, finale segreto, un ciclo NG+"}},
    {"id": "n3", "file": "n3.json", "accent": "#8fae4e",
     "tagline": {"en": "Odachi samurai - 51 trophies, one playthrough, zero missables",
                 "it": "Samurai con odachi - 51 trofei, una sola run, nessun missabile"}},
    {"id": "na", "file": "na.json", "accent": "#7f86d8",
     "tagline": {"en": "2B, 9S, A2 - 48 trophies earned, never bought from the shop",
                 "it": "2B, 9S, A2 - 48 trofei guadagnati, mai comprati al negozio"}},
]

ROUTES = {}


def load_routes():
    for r in RUNS:
        path = os.path.join(DATA, r["file"])
        if not os.path.exists(path):
            print("  !! missing data file:", path)
            continue
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        d["_steps"] = sum(len(p["steps"]) for p in d["phases"])
        d["_tsteps"] = sum(1 for p in d["phases"] for s in p["steps"] if s.get("trophy"))
        # I sid in ordine di pagina: la chiave dei progressi e dei marker.
        d["_sids"] = [s.get("sid") for p in d["phases"] for s in p["steps"]]
        d["_sidset"] = set(d["_sids"])
        d["_trophy_sids"] = {s.get("sid") for p in d["phases"]
                             for s in p["steps"] if s.get("trophy")}
        ROUTES[r["id"]] = d
