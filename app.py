#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLATINUM HUB - by Voloirex
Local checklist hub for platinum runs, with progress saved in SQLite.
Bilingual IT/EN: the language switch changes both the interface and the
route content (game asset names use the official Italian localisation;
anything that could not be verified stays in English on purpose).

Zero dependencies: Python 3 standard library only (http.server + sqlite3).
Run:  double-click run.bat  (Windows)  /  python3 app.py  (anything else)

Questo file e' solo la porta d'ingresso: l'applicazione vive nel package
platinumhub/ (config, store, routes, i18n, ui, pagine, server). Il numero
di versione sta in platinumhub/config.py, ed e' l'unica fonte di verita'.
"""

from platinumhub.server import main

if __name__ == "__main__":
    main()
