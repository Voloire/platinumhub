#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assegna un sid (identificativo stabile di passo) a ogni passo che non ce l'ha.

Il sid e' la chiave con cui i progressi vengono salvati nel database: una volta
assegnato NON deve mai cambiare, per nessun motivo. Questo strumento quindi:

  * NON tocca i sid esistenti, mai;
  * assegna ai passi nuovi il primo numero libero (s001, s002, ...), che e'
    libero rispetto a TUTTA la storia del file, non alla posizione del passo:
    un sid che "sembra fuori ordine" e' normale e non e' un errore;
  * fallisce se trova sid duplicati, perche' un duplicato corrompe i progressi.

Uso:   python tools/assign_sids.py           # sistema tutti i file di data/
       python tools/assign_sids.py er.json   # un file solo
"""

import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

# Formato ammesso: 's' piu' cifre. Corto, opaco, impossibile da confondere
# con un indice di posizione.
SID_RE = re.compile(r"^s\d{3,}$")


def assign(path):
    """Assegna i sid mancanti in un file. Ritorna quanti ne ha aggiunti."""
    with open(path, "r", encoding="utf-8") as f:
        route = json.load(f)

    steps = [s for p in route["phases"] for s in p["steps"]]
    seen = {}
    for s in steps:
        sid = s.get("sid")
        if sid is None:
            continue
        if not SID_RE.match(str(sid)):
            raise SystemExit("%s: sid '%s' non rispetta il formato s<numero>"
                             % (os.path.basename(path), sid))
        if sid in seen:
            raise SystemExit("%s: sid '%s' duplicato — va corretto a mano, "
                             "questo strumento non decide quale dei due passi "
                             "tiene la storia dei progressi" % (os.path.basename(path), sid))
        seen[sid] = True

    next_n = max((int(sid[1:]) for sid in seen), default=0) + 1
    added = 0
    for s in steps:
        if s.get("sid") is None:
            s["sid"] = "s%03d" % next_n
            next_n += 1
            added += 1

    if added:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(route, f, ensure_ascii=False, indent=1)
            f.write("\n")
    return added


def main(argv):
    names = argv or sorted(f for f in os.listdir(DATA) if f.endswith(".json"))
    total = 0
    for name in names:
        path = os.path.join(DATA, name)
        if not os.path.exists(path):
            raise SystemExit("file non trovato: %s" % path)
        added = assign(path)
        total += added
        print("  %-12s %s" % (name, ("+%d sid" % added) if added else "gia' completo"))
    print("Totale sid assegnati: %d" % total)


if __name__ == "__main__":
    main(sys.argv[1:])
