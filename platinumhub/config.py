# -*- coding: utf-8 -*-
"""Costanti di configurazione: versione, percorsi, porta, registro delle run."""

import os
import sys


# ------------------------------------------------------------------- versione
# UNICA fonte di verita' del numero di versione: tutto il resto la interpola.
#
# Il workflow di release NON riscrive questa riga, di proposito: il binario
# pubblicato deve venire esattamente dal codice committato, che e' l'unica
# promessa verificabile che possiamo fare su un eseguibile non firmato.
# Va aggiornata A MANO prima di creare il tag -- e se te ne dimentichi il
# rilascio si ferma prima di compilare, perche' release.yml confronta questa
# costante con il tag e rifiuta di procedere se divergono.
VERSION = "5.0.0"
REPO = "Voloire/platinumhub"            # per il controllo aggiornamenti
RELEASES_API = "https://api.github.com/repos/%s/releases/latest" % REPO
RELEASES_PAGE = "https://github.com/%s/releases/latest" % REPO

# ------------------------------------------------------------------- percorsi
# Con PyInstaller i file del pacchetto stanno in sys._MEIPASS (sola lettura) e
# l'eseguibile puo' finire in C:\\Program Files, dove non si scrive: il database
# deve quindi stare nei dati utente, non accanto all'app.
if getattr(sys, "frozen", False):
    BASE = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    APP_DIR = os.path.dirname(sys.executable)
else:
    # questo file sta in platinumhub/: la radice dell'app e' un livello sopra
    BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    APP_DIR = BASE
DATA = os.path.join(BASE, "data")


def user_dir():
    """Cartella scrivibile dei dati utente, con ripiego se qualcosa va storto.

    PLATINUM_HUB_DATA la sovrascrive: serve ai test per essere isolati, e a chi
    vuole tenere i progressi su una chiavetta accanto all'app (modo portatile).
    """
    forced = os.environ.get("PLATINUM_HUB_DATA")
    if forced:
        try:
            os.makedirs(forced, exist_ok=True)
            return forced
        except Exception:
            pass
    if sys.platform == "win32":
        root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        root = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        root = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share")
    d = os.path.join(root, "PlatinumHub")
    try:
        os.makedirs(d, exist_ok=True)
        probe = os.path.join(d, ".write-test")
        with open(probe, "w") as fh:
            fh.write("ok")
        os.remove(probe)
        return d
    except Exception:
        return APP_DIR          # meglio accanto all'app che non partire


USER_DIR = user_dir()
DB = os.path.join(USER_DIR, "platinum.db")
LEGACY_DB = os.path.join(APP_DIR, "platinum.db")


def migrate_legacy_db():
    """Un database della v3.x accanto all'app viene spostato nei dati utente.

    Si copia (non si sposta) e si rinomina l'originale: se qualcosa va storto
    l'utente ha ancora i suoi progressi dov'erano."""
    if os.path.exists(DB) or not os.path.exists(LEGACY_DB) or LEGACY_DB == DB:
        return None
    try:
        import shutil
        shutil.copy2(LEGACY_DB, DB)
        os.replace(LEGACY_DB, LEGACY_DB + ".migrated")
        return LEGACY_DB
    except Exception:
        return None


PORT_START = 8787
CUR_PORT = [PORT_START]
UPDATE = {"checked": False, "latest": "", "url": RELEASES_PAGE, "notes": ""}
