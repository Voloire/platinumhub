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
"""

import re
import sys
import time
import http.server
import socketserver
import sqlite3
import json
import os
import html
import webbrowser
import threading
import datetime
import urllib.parse
import urllib.request

# ------------------------------------------------------------------- versione
# UNICA fonte di verita' del numero di versione: tutto il resto la interpola.
# In release il workflow la riscrive partendo dal tag git, cosi' non puo'
# divergere da quello che e' stato pubblicato.
VERSION = "4.0.0"
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
    BASE = os.path.dirname(os.path.abspath(__file__))
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

# ------------------------------------------------------------------ UI strings
T = {
    "en": {
        "hub_title": "PLATINUM HUB",
        "hub_sub": "Pick a run - progress saves itself",
        "hub_meta": "Progress is stored locally in <code>platinum.db</code>, in your user folder — updates never touch it",
        "by": "by Voloirex",
        "trophies": "trophies",
        "trophy_steps": "Trophy steps",
        "steps": "Steps",
        "total_steps": "Total steps",
        "back": "back to the hub",
        "lang_label": "Language",
        "checklist": "PLATINUM CHECKLIST",
        "sub_run": "Step-by-step platinum route",
        "rules": "GOLDEN RULES OF THE RUN",
        "build": "BUILD",
        "legend": ('Tag legend: <span class="tag trophy">🏆 solid gold</span> = a trophy pops on this step · '
                   '<span class="tag coll">🏆 dashed gold</span> = counts toward a collection/cumulative trophy · '
                   '<span class="tag build">BUILD</span> = build item · <span class="tag quest">quest</span> = '
                   'questline &amp; lore · <span class="tag miss">⚠ MISSABLE</span> = can be lost.'),
        "expand": "Expand all",
        "collapse": "Collapse all",
        "resume": "Where I left off",
        "reset": "Reset run",
        "filter_ph": "filter steps… (press / to jump here)",
        "hide_done": "hide completed",
        "only_miss": "only missable",
        "no_match": "No step matches the filter.",
        "stats_ref": "Build Progression Reference",
        "notes_title": "My notes for this run",
        "notes_note": ("Free text, saved in the database with your progress. Where you stopped, what to remember "
                       "next session, the boss that keeps killing you."),
        "notes_ph": "write anything…",
        "gloss_title": "Glossary EN ⇄ IT",
        "gloss_note": "",
        "plat_done": "🏆 Platinum complete. Well fought.",
        "loading": "loading…",
        "saving": "saving…",
        "saved": "saved ✓",
        "new_run": "new run",
        "loaded": "loaded",
        "save_failed": "SAVE FAILED - is the app still running?",
        "offline": "offline - not saving",
        "confirm_reset": ("Reset this run completely?\n\nThis deletes, for this game only:\n"
                          "· every ticked step\n· every recorded episode, with its video URL\n"
                          "· every timestamp marker\n· your notes for this run\n\n"
                          "The other games are untouched. This cannot be undone."),
        "confirm_import": "Importing REPLACES all progress for every run with the contents of the backup file. Continue?",
        "backup_title": "Backup",
        "backup_note": ("Everything already lives in platinum.db in this folder - copying that file is a complete "
                        "backup. These buttons are for when you want a dated copy or need to move progress to "
                        "another PC."),
        "download_backup": "Download backup",
        "restore_backup": "Restore backup…",
        "import_ok": "Backup restored.",
        "import_bad": "That file is not a valid Platinum Hub backup.",
        "footer": ('Platinum Hub v%s - by Voloirex' % VERSION + '  · routes verified against PowerPyx, Fextralife, Game8, '
                   'PSNProfiles and community sources, cross-checked by independent fact-checks'),
        "footer_run": ('Checklist v%s - by Voloirex' % VERSION + '  · route verified against PowerPyx, Fextralife, Game8, '
                       'PSNProfiles and community sources, cross-checked by independent fact-checks'),
        "hubnote": ("<b>How saving works.</b> Every checkbox you tick is written straight into a SQLite database "
                    "(<code>platinum.db</code>) in this folder - no cloud, no account, nothing to click. Close the "
                    "browser, close the app, reboot: come back and everything is exactly where you left it."),
        "notfound": "Nothing here.",
        "publish": "Publish the clickable guide",
        "publish_note": "Downloads a single HTML file: a snapshot of the run right now, with every step, its state and the ▶ links to the exact moment in your videos. Plain HTML — edit it by hand if you need to.",
        "url_ph": "paste the YouTube link (any format)",
        "ask_url": "Episode finished. Paste the video URL now, if you already have it — you can also add it later in the Session tab.",
        "lq_title": "{n} episode(s) still without a video link — paste it here when the video is online",
        "upd_title": "Version {v} is available",
        "upd_body": "You are running {cur}. The download is a zip: unpack it over the old folder, keeping it — your progress lives in your user folder, not next to the app, so nothing is lost.",
        "upd_get": "Download from GitHub",
        "upd_notes": "what changed",
        "upd_off": "stop checking",
        "chlog_title": "What changed",
        "chlog_back": "back to the hub",
        "chlog_none": "No changelog shipped with this copy.",
        "lq_tasks": "task",
        "hk_all_done": "checklist finished",
        "hk_nothing": "nothing to undo",
        "hk_no_ses": "no session open",
        "hk_start": "recording + episode started",
        "hk_stop": "episode closed",
        "hk_sec": "Global shortcuts (work while the game has focus)",
        "hk_hint": "Windows only. One per line: combo:action — actions: rec, next, undo, mark. Restart the app to apply.",
        "hk_state_on": "active",
        "hk_state_off": "not active",
        "hk_save": "Save shortcuts",
        "hk_btn": "Shortcuts",
        "hk_panel_title": "Keyboard shortcuts",
        "hk_panel_intro": ("These work <b>while the game has focus</b>: you do not need to alt+tab. "
                           "Windows only. Press <kbd>?</kbd> to open this panel again."),
        "hk_col_key": "Key",
        "hk_col_what": "What it does",
        "hk_act_rec": "Start or stop the OBS recording",
        "hk_act_next": "Tick the current step and move to the next one",
        "hk_act_undo": "Undo the step you ticked last",
        "hk_act_mark": "Drop a bookmark at this exact moment",
        "hk_ok": "registered",
        "hk_taken": "taken by another program",
        "hk_thieves": ("A combination that will not register is almost always held by the GeForce Experience "
                       "overlay, Discord or the Xbox Game Bar. Turn its shortcut off there, or pick another key."),
        "hk_off_note": "Shortcuts are off. Turn them on and choose your own combinations in",
        "hk_settings": "the session settings",
        "hk_restart": "Changing them needs an app restart.",
        "hk_close": "Close",
        "hk_loading": "reading the state…",
        "diag": "Diagnostics",
        "diag_run": "Run the checks",
        "diag_note": "Runs the whole chain on this PC and writes a report to diagnostica.txt next to app.py. Start OBS (and a test stream or recording) before pressing.",
        "diag_save": "Report saved to diagnostica.txt",
        "diag_copy": "Copy report",
        "mode": "Mode",
        "gamer": "GAMER",
        "streamer": "STREAMER",
        "tab_check": "Checklist",
        "tab_eps": "Episodes",
        "tab_ses": "Session",
        "obs_on": "OBS connected",
        "obs_off": "OBS not connected",
        "obs_try": "connecting…",
        "clock_mode": "internal stopwatch",
        "rec": "REC",
        "idle": "no session",
        "start_ses": "Start episode",
        "stop_ses": "End episode",
        "mark": "Mark moment",
        "doing": "NOW",
        "started_at": "started at",
        "since": "for",
        "eps_title": "Recorded episodes",
        "ep": "EP",
        "no_video": "no video linked",
        "linked": "linked",
        "chapters": "Copy YouTube chapters",
        "copy_tasks": "Copy task list",
        "del_ep": "Delete episode",
        "ch_only_tro": "only trophy steps",
        "ch_all": "all tasks",
        "ch_free": "hand-marked moments",
        "session_cfg": "OBS connection",
        "obs_addr": "Address",
        "obs_pw": "Password",
        "obs_test": "Test",
        "obs_save": "Save",
        "ep_cfg": "Current episode",
        "ep_title": "Title",
        "ep_url": "Video URL",
        "ep_off": "Video starts at",
        "ep_off_u": "seconds into the recording (the trimmed intro)",
        "ep_lead": "Marker lead",
        "ep_lead_u": "seconds — links land just before the moment, not after",
        "ov_title": "Overlay for OBS",
        "ov_note": "Add a Browser Source in OBS with this address, 1920×1080, transparent background. It follows the checklist by itself.",
        "ov_copy": "Copy address",
        "no_eps": "No episode recorded yet. Hit “Start episode” when you go live.",
        "prefer": "Use the time of",
        "pref_auto": "automatic",
        "pref_stream": "stream",
        "pref_rec": "recording",
        "no_session_warn": "No session open: ticking works, but no timestamps are recorded.",
        "started": "started",
        "copied": "copied ✓",
        "notes_sec": "RUN NOTES &amp; WARNINGS",
        "notes_sec_sub": "read once before you start · {r} rules · {b} build notes",
        "rules_h": "Golden rules — the mistakes that cost you a trophy",
        "build_h": "The build, in short",
        "legend_h": "Tag legend",
    },
    "it": {
        "hub_title": "PLATINUM HUB",
        "hub_sub": "Scegli una run - i progressi si salvano da soli",
        "hub_meta": "I progressi stanno in locale in <code>platinum.db</code>, nella tua cartella utente — gli aggiornamenti non lo toccano",
        "by": "di Voloirex",
        "trophies": "trofei",
        "trophy_steps": "Passi con trofeo",
        "steps": "Passi",
        "total_steps": "Passi totali",
        "back": "torna all'hub",
        "lang_label": "Lingua",
        "checklist": "CHECKLIST PLATINO",
        "sub_run": "Percorso platino passo per passo",
        "rules": "REGOLE D'ORO DELLA RUN",
        "build": "BUILD",
        "legend": ('Legenda dei tag: <span class="tag trophy">🏆 oro pieno</span> = il trofeo scatta su questo passo · '
                   '<span class="tag coll">🏆 oro tratteggiato</span> = conta per un trofeo collezione · '
                   '<span class="tag build">BUILD</span> = roba di build · <span class="tag quest">quest</span> = '
                   'questline e lore · <span class="tag miss">⚠ MISSABILE</span> = lo puoi perdere.'),
        "expand": "Apri tutto",
        "collapse": "Chiudi tutto",
        "resume": "Dove ero rimasto",
        "reset": "Azzera la run",
        "filter_ph": "filtra i passi… (premi / per venire qui)",
        "hide_done": "nascondi i fatti",
        "only_miss": "solo missabili",
        "no_match": "Nessun passo corrisponde al filtro.",
        "stats_ref": "Progressione della build",
        "notes_title": "Le mie note per questa run",
        "notes_note": ("Testo libero, salvato nel database insieme ai progressi. Dove ti sei fermato, cosa ricordare "
                       "la prossima sessione, il boss che continua ad ammazzarti."),
        "notes_ph": "scrivi quello che vuoi…",
        "gloss_title": "Glossario EN ⇄ IT",
        "gloss_note": ("I nomi in italiano qui sotto sono quelli ufficiali del gioco. Dove non è stato possibile "
                       "verificare il nome italiano, nella checklist è rimasto quello inglese: meglio un nome inglese "
                       "giusto che un nome italiano inventato."),
        "plat_done": "🏆 Platino completato. Ben combattuto.",
        "loading": "carico…",
        "saving": "salvo…",
        "saved": "salvato ✓",
        "new_run": "run nuova",
        "loaded": "caricata",
        "save_failed": "SALVATAGGIO FALLITO - l'app è ancora aperta?",
        "offline": "offline - non sto salvando",
        "confirm_reset": ("Azzerare completamente questa run?\n\nVengono cancellati, solo per questo gioco:\n"
                          "· tutte le spunte\n· tutti gli episodi registrati, con i loro URL video\n"
                          "· tutti i marker con i timestamp\n· le tue note per questa run\n\n"
                          "Gli altri giochi non vengono toccati. Non si torna indietro."),
        "confirm_import": "Il ripristino SOSTITUISCE i progressi di tutte le run con quelli del file di backup. Procedo?",
        "backup_title": "Backup",
        "backup_note": ("Tutto sta già in platinum.db dentro questa cartella: copiare quel file è un backup completo. "
                        "Questi pulsanti servono quando vuoi una copia datata o devi spostare i progressi su un altro PC."),
        "download_backup": "Scarica backup",
        "restore_backup": "Ripristina backup…",
        "import_ok": "Backup ripristinato.",
        "import_bad": "Quel file non è un backup valido di Platinum Hub.",
        "footer": ('Platinum Hub v%s - di Voloirex' % VERSION + '  · percorsi verificati su PowerPyx, Fextralife, Game8, PSNProfiles '
                   'e fonti della community, ricontrollati da fact-check indipendenti'),
        "footer_run": ('Checklist v%s - di Voloirex' % VERSION + '  · percorso verificato su PowerPyx, Fextralife, Game8, PSNProfiles '
                       'e fonti della community, ricontrollato da fact-check indipendenti'),
        "hubnote": ("<b>Come funziona il salvataggio.</b> Ogni casella che spunti finisce dritta in un database SQLite "
                    "(<code>platinum.db</code>) in questa cartella - niente cloud, niente account, niente da cliccare. "
                    "Chiudi il browser, chiudi l'app, riavvia: torni e trovi tutto dov'era."),
        "notfound": "Qui non c'è niente.",
        "publish": "Pubblica la guida cliccabile",
        "publish_note": "Scarica un unico file HTML: una fotografia della run in questo momento, con tutti i passi, il loro stato e i link ▶ al minuto esatto nei tuoi video. È HTML semplice, se serve lo modifichi a mano.",
        "url_ph": "incolla il link YouTube (qualsiasi formato)",
        "ask_url": "Episodio chiuso. Incolla l'URL del video ora, se ce l'hai già — puoi anche metterlo dopo nella scheda Sessione.",
        "lq_title": "{n} episodio/i ancora senza link al video — incollalo qui quando il video è online",
        "upd_title": "È disponibile la versione {v}",
        "upd_body": "Tu stai usando la {cur}. Il download è uno zip: scompattalo sopra la cartella vecchia, tenendola — i progressi stanno nella tua cartella utente, non accanto all'app, quindi non si perde niente.",
        "upd_get": "Scarica da GitHub",
        "upd_notes": "cosa è cambiato",
        "upd_off": "non controllare più",
        "chlog_title": "Cosa è cambiato",
        "chlog_back": "torna all'hub",
        "chlog_none": "Nessun changelog incluso in questa copia.",
        "lq_tasks": "task",
        "hk_all_done": "checklist finita",
        "hk_nothing": "niente da annullare",
        "hk_no_ses": "nessuna sessione aperta",
        "hk_start": "registrazione + episodio avviati",
        "hk_stop": "episodio chiuso",
        "hk_sec": "Scorciatoie globali (funzionano con il gioco in primo piano)",
        "hk_hint": "Solo Windows. Una per riga: combinazione:azione — azioni: rec, next, undo, mark. Riavvia l'app per applicarle.",
        "hk_state_on": "attive",
        "hk_state_off": "non attive",
        "hk_save": "Salva scorciatoie",
        "hk_btn": "Scorciatoie",
        "hk_panel_title": "Scorciatoie da tastiera",
        "hk_panel_intro": ("Funzionano <b>con il gioco in primo piano</b>: non serve fare alt+tab. "
                           "Solo Windows. Premi <kbd>?</kbd> per riaprire questo pannello."),
        "hk_col_key": "Tasti",
        "hk_col_what": "Cosa fa",
        "hk_act_rec": "Avvia o ferma la registrazione di OBS",
        "hk_act_next": "Spunta il passo corrente e passa al successivo",
        "hk_act_undo": "Annulla l'ultimo passo che hai spuntato",
        "hk_act_mark": "Metti un segnaposto in questo preciso momento",
        "hk_ok": "registrata",
        "hk_taken": "occupata da un altro programma",
        "hk_thieves": ("Una combinazione che non si registra è quasi sempre tenuta dall'overlay di GeForce "
                       "Experience, da Discord o dalla Xbox Game Bar. Disattivala là, o scegline un'altra."),
        "hk_off_note": "Le scorciatoie sono spente. Puoi accenderle e scegliere le tue combinazioni in",
        "hk_settings": "impostazioni della sessione",
        "hk_restart": "Per cambiarle serve riavviare l'app.",
        "hk_close": "Chiudi",
        "hk_loading": "leggo lo stato…",
        "diag": "Diagnostica",
        "diag_run": "Esegui i controlli",
        "diag_note": "Prova tutta la catena su questo PC e scrive un referto in diagnostica.txt, accanto ad app.py. Avvia OBS (con una diretta o registrazione di prova) prima di premere.",
        "diag_save": "Referto salvato in diagnostica.txt",
        "diag_copy": "Copia il referto",
        "mode": "Modalità",
        "gamer": "GAMER",
        "streamer": "STREAMER",
        "tab_check": "Checklist",
        "tab_eps": "Episodi",
        "tab_ses": "Sessione",
        "obs_on": "OBS collegato",
        "obs_off": "OBS non collegato",
        "obs_try": "connessione…",
        "clock_mode": "cronometro interno",
        "rec": "REC",
        "idle": "nessuna sessione",
        "start_ses": "Avvia episodio",
        "stop_ses": "Chiudi episodio",
        "mark": "Segna momento",
        "doing": "IN CORSO",
        "started_at": "iniziato a",
        "since": "da",
        "eps_title": "Episodi registrati",
        "ep": "EP",
        "no_video": "nessun video collegato",
        "linked": "collegato",
        "chapters": "Copia capitoli YouTube",
        "copy_tasks": "Copia elenco task",
        "del_ep": "Elimina episodio",
        "ch_only_tro": "solo passi con trofeo",
        "ch_all": "tutti i task",
        "ch_free": "momenti segnati a mano",
        "session_cfg": "Collegamento a OBS",
        "obs_addr": "Indirizzo",
        "obs_pw": "Password",
        "obs_test": "Verifica",
        "obs_save": "Salva",
        "ep_cfg": "Episodio corrente",
        "ep_title": "Titolo",
        "ep_url": "URL del video",
        "ep_off": "Il video parte da",
        "ep_off_u": "secondi di registrazione (l'intro tagliata)",
        "ep_lead": "Anticipo sui marker",
        "ep_lead_u": "secondi — il link punta poco prima del momento, non dopo",
        "ov_title": "Overlay per OBS",
        "ov_note": "Aggiungi in OBS una sorgente Browser con questo indirizzo, 1920×1080, sfondo trasparente. Segue la checklist da sola.",
        "ov_copy": "Copia indirizzo",
        "no_eps": "Nessun episodio registrato. Premi “Avvia episodio” quando vai in diretta.",
        "prefer": "Usa il tempo di",
        "pref_auto": "automatico",
        "pref_stream": "diretta",
        "pref_rec": "registrazione",
        "no_session_warn": "Nessuna sessione aperta: le spunte funzionano, ma non registrano timestamp.",
        "started": "avviato",
        "copied": "copiato ✓",
        "notes_sec": "NOTE PER LA RUN E AVVERTENZE",
        "notes_sec_sub": "da leggere una volta prima di partire · {r} regole · {b} note di build",
        "rules_h": "Regole d'oro — gli errori che ti costano un trofeo",
        "build_h": "La build, in breve",
        "legend_h": "Legenda dei tag",
    },
}


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
        ROUTES[r["id"]] = d


# ---------------------------------------------------------------------- SQLite
def db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS progress(
        run_id TEXT PRIMARY KEY, bits TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT (datetime('now')))""")
    con.execute("""CREATE TABLE IF NOT EXISTS notes(
        run_id TEXT PRIMARY KEY, body TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT (datetime('now')))""")
    con.execute("""CREATE TABLE IF NOT EXISTS prefs(
        k TEXT PRIMARY KEY, v TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS sessions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        number INTEGER NOT NULL,
        title TEXT NOT NULL DEFAULT '',
        started_at TEXT NOT NULL,
        ended_at TEXT,
        source TEXT NOT NULL DEFAULT 'clock',
        video_url TEXT NOT NULL DEFAULT '',
        video_offset INTEGER NOT NULL DEFAULT 0,
        lead INTEGER NOT NULL DEFAULT 15)""")
    con.execute("""CREATE TABLE IF NOT EXISTS markers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        run_id TEXT NOT NULL,
        step INTEGER,
        kind TEXT NOT NULL,
        tc REAL NOT NULL,
        wall TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT '')""")
    con.execute("CREATE INDEX IF NOT EXISTS ix_mark ON markers(session_id, step, kind)")
    con.commit()
    return con


# --------------------------------------------------------------- sessions
def open_session(run_id):
    con = db()
    row = con.execute("SELECT * FROM sessions WHERE run_id=? AND ended_at IS NULL "
                      "ORDER BY id DESC LIMIT 1", (run_id,)).fetchone()
    con.close()
    return row


def session_row(sid):
    con = db()
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    con.close()
    return dict(row) if row else None


def sessions_of(run_id):
    con = db()
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT * FROM sessions WHERE run_id=? ORDER BY number DESC", (run_id,))]
    for r in rows:
        r["markers"] = [dict(m) for m in con.execute(
            "SELECT * FROM markers WHERE session_id=? ORDER BY tc", (r["id"],))]
    con.close()
    return rows


def step_stamps(run_id):
    """{step_index: {'done': {...}, 'start': {...}}} with episode + link data."""
    con = db()
    con.row_factory = sqlite3.Row
    rows = con.execute("""SELECT m.step, m.kind, m.tc, s.number, s.video_url, s.video_offset, s.lead
                          FROM markers m JOIN sessions s ON s.id = m.session_id
                          WHERE m.run_id=? AND m.step IS NOT NULL
                          ORDER BY m.id""", (run_id,)).fetchall()
    con.close()
    out = {}
    for r in rows:
        d = out.setdefault(r["step"], {})
        secs = max(0, int(round(r["tc"] - r["video_offset"] - r["lead"])))
        d[r["kind"]] = {"ep": r["number"], "tc": r["tc"], "url": r["video_url"], "t": secs}
    return out


def fmt_tc(sec):
    sec = max(0, int(round(sec)))
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return (f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}")


def video_link(url, t):
    if not url:
        return ""
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}t={int(t)}"


def get_pref(k, default=""):
    con = db()
    row = con.execute("SELECT v FROM prefs WHERE k=?", (k,)).fetchone()
    con.close()
    return row[0] if row else default


def set_pref(k, v):
    con = db()
    con.execute("INSERT INTO prefs(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))
    con.commit()
    con.close()


def lang():
    l = get_pref("lang", "it")
    return l if l in ("it", "en") else "it"


def get_bits(run_id, length):
    con = db()
    row = con.execute("SELECT bits FROM progress WHERE run_id=?", (run_id,)).fetchone()
    con.close()
    bits = row[0] if row else ""
    if len(bits) < length:
        bits += "0" * (length - len(bits))
    return bits[:length]


def set_bits(run_id, bits):
    con = db()
    con.execute("""INSERT INTO progress(run_id,bits,updated_at) VALUES(?,?,datetime('now'))
                   ON CONFLICT(run_id) DO UPDATE SET bits=excluded.bits, updated_at=datetime('now')""",
                (run_id, bits))
    con.commit()
    con.close()


def get_note(run_id):
    con = db()
    row = con.execute("SELECT body FROM notes WHERE run_id=?", (run_id,)).fetchone()
    con.close()
    return row[0] if row else ""


def set_note(run_id, body):
    con = db()
    con.execute("""INSERT INTO notes(run_id,body,updated_at) VALUES(?,?,datetime('now'))
                   ON CONFLICT(run_id) DO UPDATE SET body=excluded.body, updated_at=datetime('now')""",
                (run_id, body))
    con.commit()
    con.close()


def stats(run_id):
    d = ROUTES.get(run_id)
    if not d:
        return (0, 0, 0, 0, None)
    con = db()
    row = con.execute("SELECT updated_at FROM progress WHERE run_id=?", (run_id,)).fetchone()
    con.close()
    bits = get_bits(run_id, d["_steps"])
    flags = [bool(s.get("trophy")) for p in d["phases"] for s in p["steps"]]
    done = sum(1 for c in bits if c == "1")
    tdone = sum(1 for i, c in enumerate(bits) if c == "1" and flags[i])
    return (done, d["_steps"], tdone, d["_tsteps"], row[0] if row else None)


# ------------------------------------------------------------------------- CSS
CSS = """
@font-face{font-family:'Roboto';src:url('/fonts/roboto-400.woff2') format('woff2');
font-weight:400;font-style:normal;font-display:swap}
@font-face{font-family:'Roboto';src:url('/fonts/roboto-400i.woff2') format('woff2');
font-weight:400;font-style:italic;font-display:swap}
@font-face{font-family:'Roboto';src:url('/fonts/roboto-700.woff2') format('woff2');
font-weight:700;font-style:normal;font-display:swap}
:root{--bg:#0d0f14;--panel:#151823;--panel2:#1a1e2c;--line:#2a2f42;--gold:#c8a24a;
--gold-dim:#8a7134;--moon:#7fa8d9;--moon-dim:#4a6a94;--text:#d8d5c8;--muted:#8a8878;
--warn:#c86a4a;--warn-bg:#2a1a14;--ok:#7fc98a;--item:#7fd8d0;--rec:#e05252}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);
font-family:'Roboto','Segoe UI',system-ui,-apple-system,Arial,sans-serif;
line-height:1.55;padding-bottom:80px;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
header{padding:30px 20px 18px;text-align:center;
background:linear-gradient(180deg,#131625 0%,var(--bg) 100%);border-bottom:1px solid var(--line);position:relative}
header h1{font-size:1.5em;color:var(--gold);letter-spacing:3px;font-weight:500}
header p.sub{color:var(--muted);margin-top:6px;font-style:italic}
header p.sub .by{color:var(--gold)}
header p.meta{color:var(--moon);margin-top:8px;font-size:.85em}
.langsel{display:inline-flex;align-items:center;gap:6px;font-size:.82em;letter-spacing:1px;
background:var(--panel);border:1px solid var(--gold-dim);border-radius:8px;padding:5px 8px 5px 11px}
.langsel .lbl{color:var(--muted);font-size:.86em;margin-right:2px}
.langsel a{padding:4px 11px;border:1px solid var(--line);border-radius:5px;color:var(--muted);
font-weight:bold;letter-spacing:1px}
.langsel a:hover{border-color:var(--gold);color:var(--gold);background:var(--panel2)}
.langsel a.on{background:var(--gold-dim);border-color:var(--gold);color:#12141c}
.langsel-top{position:absolute;top:14px;right:16px;z-index:30}
@media(max-width:700px){.langsel-top{position:static;margin:0 auto 10px;display:inline-flex}}
.wrap{max-width:900px;margin:0 auto;padding:0 16px}
.back{display:inline-block;margin:16px 0 0;font-size:.85em;color:var(--muted)}
.back:hover{color:var(--gold)}
/* ---- hub cards ---- */
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(390px,1fr));gap:16px;margin:24px 0}
@media(max-width:840px){.cards{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 20px;
display:block;transition:border-color .18s,transform .18s;position:relative;overflow:hidden}
.card:hover{border-color:var(--gold-dim);transform:translateY(-2px)}
.card .stripe{position:absolute;left:0;top:0;bottom:0;width:4px}
.card h2{font-size:1.05em;font-weight:500;color:var(--gold);letter-spacing:1px;margin-bottom:4px}
.card .tag2{font-size:.84em;color:var(--muted);font-style:italic;margin-bottom:12px;display:block}
.card .facts{font-size:.78em;color:var(--moon);margin-bottom:12px}
.card .prow{display:flex;align-items:center;gap:10px;margin-top:7px}
.card .prow .lb{font-size:.74em;color:var(--muted);min-width:100px}
.card .when{font-size:.7em;color:#5f5d50;margin-top:9px;font-style:italic}
.bar{flex:1;height:10px;background:#0a0c10;border-radius:6px;overflow:hidden;
border:1px solid var(--line);min-width:110px}
.bar>div{height:100%;width:0%;background:linear-gradient(90deg,var(--gold-dim),var(--gold));transition:width .3s}
.bar.moonbar>div{background:linear-gradient(90deg,var(--moon-dim),var(--moon))}
.count{font-size:.8em;color:var(--gold);min-width:66px;text-align:right;font-variant-numeric:tabular-nums}
.count.mooncount{color:var(--moon)}
.hubnote{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:14px 18px;font-size:.85em;color:var(--muted);margin:8px 0 18px}
.hubnote b{color:var(--gold);font-weight:normal}
.hubnote h3{color:var(--gold);font-weight:normal;font-size:1em;letter-spacing:1px;margin-bottom:6px}
.hubnote .btns{margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
/* ---- checklist ---- */
.progress-panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:14px 18px;margin:18px auto;position:sticky;top:0;z-index:20;box-shadow:0 4px 18px rgba(0,0,0,.6)}
.progress-row{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.progress-row .label{font-size:.85em;color:var(--muted);min-width:120px}
.toolbar{display:flex;gap:8px;margin-top:11px;flex-wrap:wrap;align-items:center}
button,.btn{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:6px;
padding:6px 12px;cursor:pointer;font-family:inherit;font-size:.8em}
button:hover,.btn:hover{border-color:var(--gold-dim);color:var(--gold)}
button.danger:hover{border-color:var(--warn);color:var(--warn)}
#filterBox{flex:1;min-width:190px;background:#0a0c10;border:1px solid var(--line);border-radius:6px;
color:var(--text);padding:6px 10px;font-size:.82em;font-family:inherit}
#filterBox:focus{outline:none;border-color:var(--gold-dim)}
.chk{display:inline-flex;align-items:center;gap:6px;font-size:.78em;color:var(--muted);cursor:pointer;
padding:5px 9px;border:1px solid var(--line);border-radius:6px;user-select:none}
.chk:hover{border-color:var(--gold-dim);color:var(--gold)}
.chk input{accent-color:var(--gold);width:14px;height:14px}
#saveState{font-size:.75em;color:var(--ok);min-width:92px;font-style:italic}
#saveState.pending{color:var(--muted)}
#saveState.err{color:var(--warn)}
section.notes-sec{background:var(--warn-bg);border:1px solid #4a2a1e;border-radius:10px;margin:18px auto;overflow:hidden}
section.notes-sec .phase-head{background:#33201a}
section.notes-sec .phase-head:hover{background:#3d271f}
section.notes-sec .phase-head h2{color:var(--warn)}
section.notes-sec .phase-head .num{color:var(--warn)}
.rules{padding:4px 2px 2px}
.rules h3{color:var(--warn);font-size:.82em;letter-spacing:2px;text-transform:uppercase;
margin:14px 0 8px;font-weight:500}
.rules h3:first-child{margin-top:6px}
.rules ul{list-style:none}
.rules li{position:relative;padding:6px 0 6px 18px;font-size:.9em;line-height:1.5}
.rules li::before{content:"▸";position:absolute;left:0;color:var(--warn);opacity:.8}
.buildbox li::before{color:var(--ok)}
.buildbox li{color:var(--ok)}
.buildbox .bh{color:#a8e6b4;font-weight:700;letter-spacing:.4px}
.buildbox .bh::after{content:" — ";color:var(--muted);font-weight:400}
.cap{color:var(--item);font-weight:500}
.legend{margin-top:14px;padding-top:10px;border-top:1px solid #4a2a1e;font-size:.8em;color:#8a8878}
section.phase{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:16px auto;overflow:hidden}
.phase-head{display:flex;align-items:center;gap:12px;padding:14px 18px;cursor:pointer;background:var(--panel2);
user-select:none}
.phase-head:hover{background:#20253a}
.phase-head .num{color:var(--moon);font-size:.8em;letter-spacing:2px;white-space:nowrap}
.phase-head h2{font-size:1em;color:var(--gold);font-weight:500;flex:1}
.phase-head .mini{font-size:.8em;color:var(--muted);font-variant-numeric:tabular-nums}
.phase-head .chev{color:var(--muted);transition:transform .2s}
section.phase.open .chev{transform:rotate(90deg)}
.phase-body{display:none;padding:6px 18px 16px}
section.phase.open .phase-body{display:block}
.phase-note{font-size:.85em;color:var(--muted);font-style:italic;padding:8px 2px 10px;
border-bottom:1px dashed var(--line);margin-bottom:6px}
label.item{display:flex;gap:12px;padding:11px 8px;border-bottom:1px solid #1d2130;cursor:pointer;
align-items:flex-start;min-height:44px;border-radius:6px;scroll-margin-top:calc(var(--stick,0px) + 64px)}
label.item:last-child{border-bottom:none}
label.item:hover{background:#181c2a}
label.item input{margin-top:3px;accent-color:var(--gold);width:20px;height:20px;flex-shrink:0;cursor:pointer}
label.item .txt{flex:1;font-size:.92em}
label.item .txt .loc{display:block;font-size:.82em;color:var(--muted)}
label.item.checked .txt{color:#5a5848;text-decoration:line-through}
label.item.checked .txt .loc{text-decoration:line-through}
label.item.hit{outline:1px solid var(--gold-dim);background:#1d2032}
label.item.here{animation:pulse 1.4s ease-out 1;background:#20263c}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(200,162,74,.55)}100%{box-shadow:0 0 0 16px rgba(200,162,74,0)}}
body.hidedone label.item.checked{display:none}
label.item.filtered{display:none}
section.phase.filtered{display:none}
#noMatch{display:none;color:var(--muted);font-style:italic;text-align:center;padding:24px}
#noMatch.show{display:block}
.tag{display:inline-block;font-size:.68em;letter-spacing:1px;padding:1px 7px;border-radius:4px;
margin-left:6px;vertical-align:1px;text-decoration:none !important}
.tag.trophy{background:#2a2413;color:var(--gold);border:1px solid var(--gold-dim)}
.tag.coll{background:#221d10;color:#c8a24a;border:1px dashed var(--gold-dim)}
.tag.quest{background:#141d2a;color:var(--moon);border:1px solid var(--moon-dim)}
.tag.miss{background:var(--warn-bg);color:var(--warn);border:1px solid #4a2a1e}
.tag.build{background:#14241a;color:var(--ok);border:1px solid #2e5a3a}
table.stats{width:100%;border-collapse:collapse;font-size:.85em;margin:10px 0}
table.stats th{background:var(--panel2);color:var(--gold);padding:7px 6px;text-align:center;
border:1px solid var(--line);font-weight:normal;letter-spacing:1px}
table.stats td{padding:6px;text-align:center;border:1px solid #1d2130;color:var(--text);font-variant-numeric:tabular-nums}
table.stats td:first-child{color:var(--moon);font-weight:bold}
table.stats td:last-child{text-align:left;font-size:.92em;color:var(--muted)}
table.stats tr:hover td{background:#181c2a}
table.gloss{width:100%;border-collapse:collapse;font-size:.85em;margin:8px 0}
table.gloss td{padding:5px 8px;border-bottom:1px solid #1d2130}
table.gloss td:first-child{color:var(--muted);width:48%}
table.gloss td:last-child{color:var(--gold)}
textarea.notes{width:100%;min-height:130px;background:#0a0c10;border:1px solid var(--line);border-radius:8px;
color:var(--text);padding:10px;font-family:inherit;font-size:.9em;resize:vertical}
footer{text-align:center;color:var(--muted);font-size:.8em;padding:30px 16px;font-style:italic}
.plat{background:linear-gradient(135deg,#1a1e2c,#232a44);border:1px solid var(--moon-dim);border-radius:10px;
padding:20px;text-align:center;margin:18px auto;display:none}
.plat.show{display:block}
.plat h2{color:var(--moon);font-weight:normal;letter-spacing:2px}

/* ---- mode + tabs ---- */
.modesel{display:inline-flex;align-items:center;gap:6px;font-size:.8em;letter-spacing:1px;
background:var(--panel);border:1px solid var(--gold-dim);border-radius:8px;padding:5px 8px 5px 11px}
.modesel .lbl{color:var(--muted);font-size:.86em}
.modesel a{padding:4px 11px;border:1px solid var(--line);border-radius:5px;color:var(--muted);font-weight:bold}
.modesel a:hover{border-color:var(--gold);color:var(--gold)}
.modesel a.on{background:var(--gold-dim);border-color:var(--gold);color:#12141c}
.topright{position:absolute;top:14px;right:16px;z-index:30;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
@media(max-width:820px){.topright{position:static;justify-content:center;margin-bottom:10px}}
/* pannello delle scorciatoie: si apre da un pulsante o col tasto ? */
.hkbtn{font-size:.8em;letter-spacing:1px;padding:5px 11px;background:var(--panel);
border:1px solid var(--gold-dim);border-radius:8px;color:var(--muted);cursor:pointer}
.hkbtn:hover{border-color:var(--gold);color:var(--gold)}
.hkmodal{position:fixed;inset:0;z-index:200;display:none;align-items:center;justify-content:center;
background:rgba(6,8,12,.72);padding:20px}
.hkmodal.open{display:flex}
.hkbox{background:var(--panel);border:1px solid var(--gold-dim);border-radius:12px;
max-width:680px;width:100%;max-height:86vh;overflow:auto;padding:22px 24px}
.hkbox h2{margin:0 0 10px;font-size:1.05em;color:var(--gold);letter-spacing:2px;text-transform:uppercase;
font-weight:500}
.hkbox .intro{color:var(--muted);font-size:.9em;line-height:1.6;margin-bottom:16px}
.hkrow{display:flex;gap:14px;align-items:baseline;padding:9px 0;border-top:1px solid var(--line);
flex-wrap:wrap}
.hkrow .what{flex:1;min-width:220px}
kbd,.hkkey{font-family:inherit;font-size:.82em;letter-spacing:1px;background:var(--panel2);
border:1px solid var(--line);border-bottom-width:2px;border-radius:5px;padding:3px 8px;color:var(--text);
white-space:nowrap}
.hkfoot{margin-top:18px;padding-top:14px;border-top:1px solid var(--line);display:flex;gap:12px;
align-items:center;flex-wrap:wrap;font-size:.88em;color:var(--muted)}
.hkwarn{color:var(--warn);font-size:.88em;line-height:1.6;margin-top:12px;background:var(--warn-bg);
border:1px solid var(--warn);border-radius:8px;padding:10px 13px}
.tabs{display:flex;gap:8px;margin:16px 0 0}
.tabs a{background:var(--panel2);border:1px solid var(--line);color:var(--muted);
border-radius:7px 7px 0 0;padding:7px 15px;font-size:.85em}
.tabs a.on{background:var(--panel);color:var(--gold);border-color:var(--gold-dim);border-bottom-color:var(--panel)}
.tabs a:hover{color:var(--gold)}
/* ---- session bar ---- */
.sessionbar{background:linear-gradient(180deg,#1b1420,#151823);border:1px solid #4a2a3a;
border-radius:10px;padding:12px 16px;margin:14px auto}
.sessionbar .row1{display:flex;align-items:center;gap:13px;flex-wrap:wrap}
.recdot{width:9px;height:9px;border-radius:50%;background:var(--rec);display:inline-block;
box-shadow:0 0 0 0 rgba(224,82,82,.6);animation:recpulse 1.8s infinite}
@keyframes recpulse{70%{box-shadow:0 0 0 9px rgba(224,82,82,0)}100%{box-shadow:0 0 0 0 rgba(224,82,82,0)}}
.recdot.off{background:#555;animation:none}
.reclab{color:var(--rec);font-weight:700;letter-spacing:1px;font-size:.85em}
.reclab.off{color:var(--muted)}
.tc{font-variant-numeric:tabular-nums;font-size:1.12em;letter-spacing:1px}
.chip{font-size:.76em;border-radius:5px;padding:2px 9px;letter-spacing:1px}
.chip.ok{color:var(--ok);border:1px solid #2e5a3a;background:#14241a}
.chip.bad{color:var(--warn);border:1px solid #4a2a1e;background:var(--warn-bg)}
.chip.ep{color:var(--moon);border:1px solid var(--moon-dim);background:#141d2a}
.sessionbar .spacer{flex:1}
.doing{margin-top:10px;padding-top:9px;border-top:1px solid #33203a;font-size:.86em;
display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.doing .lab{color:var(--muted);letter-spacing:1px;font-size:.9em}
.doing .task{color:var(--gold)}
.doing .since{color:var(--muted);font-variant-numeric:tabular-nums}
/* ---- avviso di aggiornamento ---- */
.updbox{border:1px solid var(--gold-dim);background:linear-gradient(90deg,#1a1608,#12141c);
border-radius:9px;padding:14px 18px;margin:0 0 18px}
.updbox .uh{color:var(--gold);letter-spacing:1px;font-size:.95em;margin-bottom:5px}
.updbox .ub{color:var(--muted);font-size:.88em;line-height:1.55}
.updbox .ur{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-top:11px}
.updbox .updbtn{background:var(--gold);color:#14100a;border-radius:6px;padding:7px 15px;
text-decoration:none;font-size:.9em;letter-spacing:.5px}
.updbox .updlnk{color:var(--muted);font-size:.85em;text-decoration:none;border-bottom:1px dotted var(--line)}
.chlog{max-width:820px;margin:0 auto;line-height:1.65}
.chlog h2{color:var(--gold);font-size:1.05em;margin:26px 0 6px;letter-spacing:.5px}
.chlog h3{color:var(--moon);font-size:.9em;margin:16px 0 4px;letter-spacing:1px;text-transform:uppercase}
.chlog li{margin:4px 0}
.chlog code{background:var(--panel2);padding:1px 6px;border-radius:4px;font-size:.9em}
/* ---- coda dei link video mancanti ---- */
.linkq{margin-top:10px;padding-top:10px;border-top:1px solid #33203a}
.linkq .lqh{color:var(--warn);font-size:.86em;letter-spacing:.5px;margin-bottom:8px}
.linkq .lqrow{display:flex;align-items:center;gap:9px;flex-wrap:wrap;padding:5px 0}
.linkq .lqep{color:var(--moon);font-size:.8em;letter-spacing:1px;min-width:56px}
.linkq .lqmeta{color:var(--muted);font-size:.8em;min-width:150px}
.linkq .lqin{flex:1;min-width:210px;background:#0a0c10;border:1px solid var(--line);
border-radius:6px;color:var(--text);padding:5px 9px;font-size:.9em;font-family:inherit}
.linkq .lqst{font-size:.9em;min-width:14px}
/* ---- step stamps ---- */
.stamp{display:inline-block;font-size:.72em;letter-spacing:.5px;padding:2px 8px;border-radius:5px;
margin-left:8px;white-space:nowrap;vertical-align:1px;background:#161d2c;border:1px solid var(--moon-dim);
color:var(--moon);text-decoration:none !important}
.stamp:hover{background:#1d2740;border-color:var(--moon);color:#a8c8e8}
.stamp .ep{color:var(--gold);font-weight:700}
.stamp.two{border-style:dashed}
.stamp.live{border-color:var(--rec);color:var(--rec);background:#241416}
label.item.checked .stamp{text-decoration:none;color:var(--moon)}
label.item.current{background:#1c2436;outline:1px solid var(--moon-dim)}
.doingtag{display:inline-block;font-size:.7em;letter-spacing:1px;color:var(--rec);
border:1px solid var(--rec);border-radius:5px;padding:1px 7px;margin-left:8px;vertical-align:1px}
/* ---- episodes ---- */
.epcard{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:14px 0;overflow:hidden}
.epcard .h{display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--panel2);flex-wrap:wrap}
.epcard .h h3{font-size:1em;color:var(--gold);font-weight:500;letter-spacing:1px}
.epcard .h .meta{font-size:.8em;color:var(--muted)}
.epcard .h .spacer{flex:1}
.epcard .b{padding:6px 16px 14px}
.tl{display:grid;grid-template-columns:84px 1fr;gap:1px 14px;font-size:.88em;margin:6px 0}
.tl .t{color:var(--moon);font-variant-numeric:tabular-nums;padding:5px 0;text-align:right}
.tl .t a{color:var(--moon)} .tl .t a:hover{color:var(--gold)}
.tl .d{padding:5px 0;border-bottom:1px solid #1a1e2b}
.tl .d.tro{color:var(--gold)}
.setrow{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:10px;font-size:.84em;color:var(--muted)}
.setrow input[type=text],.setrow input[type=password]{background:#0a0c10;border:1px solid var(--line);
border-radius:6px;color:var(--text);padding:6px 10px;font-family:inherit;font-size:.95em;min-width:210px}
.setrow input[type=number]{background:#0a0c10;border:1px solid var(--line);border-radius:6px;
color:var(--text);padding:6px 8px;font-family:inherit;width:78px;font-size:.95em}
textarea.mono{width:100%;min-height:110px;background:#0a0c10;border:1px solid var(--line);border-radius:8px;
color:var(--text);padding:10px;font-family:ui-monospace,Consolas,monospace;font-size:.82em;
resize:vertical;margin-top:10px;line-height:1.7}
@media print{header,.progress-panel,.toolbar,.langsel,.back,footer,.hubnote,.sessionbar,.tabs,.topright{display:none}
section.phase .phase-body{display:block !important}body{background:#fff;color:#000}}
"""


# words that are capitalised for emphasis, not because they name a thing
_STOP = {
    "NON", "MAI", "NIENTE", "SOLO", "TUTTI", "TUTTO", "TUTTE", "PRIMA", "DOPO", "SEMPRE", "OGNI",
    "QUI", "ORA", "POI", "SE", "MA", "E", "O", "UNA", "UNO", "DUE", "TRE", "QUATTRO", "VOLTA",
    "VOLTE", "SUBITO", "ANCHE", "ADESSO", "QUANDO", "PERCHE", "PERCHÉ", "COSA", "FASE",
    "NOT", "NEVER", "ONLY", "ALL", "EVERY", "ALWAYS", "FIRST", "THEN", "BEFORE", "AFTER", "NOW",
    "ONE", "TWO", "THREE", "FOUR", "ONCE", "TWICE", "MUST", "DO", "DON'T", "AND", "OR", "IF",
    "THIS", "THAT", "HERE", "YES", "NO", "PHASE", "STEP", "OK",
    "CIASCUNA", "CIASCUNO", "ENTRAMBI", "ENTRAMBE", "SOLTANTO", "QUALSIASI", "QUALUNQUE",
    "NESSUNO", "NESSUNA", "MENO", "PIU", "PIÙ", "MOLTO", "TROPPO", "ASSOLUTAMENTE",
    "EACH", "BOTH", "ANY", "ANYTHING", "NOTHING", "MORE", "LESS", "VERY", "ABSOLUTELY", "JUST",
}
_CAPS = re.compile(r"(?<![\w'’])([A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9'’+\-]{1,}(?:[  ][A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9'’+\-]{1,})*)(?![\w'’])")


def esc(s):
    return html.escape(str(s), quote=False)


def hl(s):
    """Escape, then paint ALL-CAPS in-game nouns in the item colour."""
    out = html.escape(str(s), quote=False)

    def repl(m):
        tok = m.group(1)
        if all(w in _STOP for w in tok.split()):
            return tok
        if len(tok.replace(" ", "")) < 2:
            return tok
        return '<span class="cap">%s</span>' % tok

    return _CAPS.sub(repl, out)


def short(s, n):
    s = str(s).strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    if "(" in cut and ")" not in cut[cut.index("("):]:
        trimmed = cut[:cut.index("(")].rstrip()
        if len(trimmed) >= 12:
            cut = trimmed
    cut = cut.rsplit(" ", 1)[0].rstrip(" ,;:-—·(")
    return cut + "…"


def L(d, key, lg):
    """Localised field: key_it when lang is it and it exists, else key."""
    if lg == "it":
        v = d.get(key + "_it")
        if v:
            return v
    return d.get(key, "")


def langsel(lg, path, top=False):
    q = urllib.parse.quote(path, safe="/")
    a = lambda code, txt: (f'<a class="{"on" if lg == code else ""}" href="/lang/{code}?next={q}">{txt}</a>')
    cls = "langsel langsel-top" if top else "langsel"
    return (f'<div class="{cls}"><span class="lbl">🌐 {T[lg]["lang_label"]}</span>'
            f'{a("it", "ITA")}{a("en", "ENG")}</div>')


# ------------------------------------------------------------------- home page
def md_lite(text):
    """Markdown minimo per il changelog: titoli, elenchi, grassetto, codice.

    Non serve una libreria: il file lo scrivo io e conosco la forma che ha."""
    out, in_ul = [], False
    for raw in str(text).splitlines():
        line = html.escape(raw.rstrip(), quote=False)
        line = re.sub(r"`([^`]+)`", r"<code>\1</code>", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line)
        line = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
                      r'<a href="\2" target="_blank" rel="noopener">\1</a>', line)
        stripped = line.strip()
        is_li = stripped.startswith(("- ", "* "))
        if is_li and not in_ul:
            out.append("<ul>")
            in_ul = True
        elif not is_li and in_ul:
            out.append("</ul>")
            in_ul = False
        if is_li:
            out.append("<li>%s</li>" % stripped[2:])
        elif stripped.startswith("### "):
            out.append("<h3>%s</h3>" % stripped[4:])
        elif stripped.startswith("## "):
            out.append("<h2>%s</h2>" % stripped[3:])
        elif stripped.startswith("# "):
            continue                       # il titolo del file lo mettiamo noi
        elif stripped.startswith("---"):
            out.append('<hr style="border:0;border-top:1px solid var(--line);margin:18px 0">')
        elif stripped:
            out.append("<p>%s</p>" % stripped)
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


def render_changelog():
    lg = lang()
    t = T[lg]
    body = ""
    for name in ("CHANGELOG.md", os.path.join("docs", "CHANGELOG.md")):
        fp = os.path.join(BASE, name)
        if os.path.exists(fp):
            try:
                with open(fp, encoding="utf-8") as fh:
                    body = md_lite(fh.read()[:60000])
            except Exception:
                body = ""
            break
    if not body:
        body = '<p>%s <a href="%s" target="_blank" rel="noopener">GitHub</a>.</p>' % (
            t["chlog_none"], RELEASES_PAGE)
    p = ['<!DOCTYPE html><html lang="%s"><head><meta charset="UTF-8">' % lg,
         '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
         "<title>%s - Platinum Hub</title>" % t["chlog_title"],
         "<style>" + CSS + "</style></head><body>",
         f'<header><h1>{t["chlog_title"]}</h1>'
         f'<p class="sub">Platinum Hub v{VERSION} · <span class="by">by Voloirex</span></p></header>',
         '<div class="wrap"><p><a href="/">&larr; %s</a></p>' % t["chlog_back"],
         '<div class="chlog">', body, "</div>",
         f'<p style="margin-top:26px"><a href="{RELEASES_PAGE}" target="_blank" rel="noopener">'
         f'{RELEASES_PAGE}</a></p>',
         f'</div><footer>{t["footer"]}</footer></body></html>']
    return "\n".join(p)


def render_home():
    lg = lang()
    t = T[lg]
    p = ['<!DOCTYPE html><html lang="%s"><head><meta charset="UTF-8">' % lg,
         '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
         "<title>Platinum Hub - by Voloirex</title>", "<style>" + CSS + "</style></head><body>",
         hk_panel(lg)]
    p.append(f'<header><div class="topright">{hk_button(lg)}{langsel(lg, "/")}</div>'
             f'<h1>{t["hub_title"]}</h1>'
             f'<p class="sub">{t["hub_sub"]} · <span class="by">{t["by"]}</span></p>'
             f'<p class="meta">{t["hub_meta"]}</p></header>')
    p.append('<div class="wrap">')
    if UPDATE["latest"]:
        p.append(f'<div class="updbox"><div class="uh">⬆ {t["upd_title"].format(v=esc(UPDATE["latest"]))}</div>'
                 f'<div class="ub">{t["upd_body"].format(cur=VERSION)}</div>'
                 f'<div class="ur"><a class="updbtn" href="{esc(UPDATE["url"])}" target="_blank" '
                 f'rel="noopener">{t["upd_get"]}</a>'
                 f'<a class="updlnk" href="/changelog">{t["upd_notes"]}</a>'
                 f'<a class="updlnk" href="/update/off">{t["upd_off"]}</a></div></div>')
    p.append('<div class="cards">')
    for r in RUNS:
        d = ROUTES.get(r["id"])
        if not d:
            continue
        done, total, tdone, ttotal, when = stats(r["id"])
        pct = (done / total * 100) if total else 0
        tpct = (tdone / ttotal * 100) if ttotal else 0
        p.append(f'<a class="card" href="/run/{r["id"]}">')
        p.append(f'<span class="stripe" style="background:{r["accent"]}"></span>')
        p.append(f'<h2>{esc(d["game"])}{" &nbsp;🏆" if total and done == total else ""}</h2>')
        p.append(f'<span class="tag2">{esc(r["tagline"][lg])}</span>')
        p.append(f'<div class="facts">🏆 {d["trophy_total"]} {t["trophies"]} · ⏱ {esc(short(L(d, "hours", lg), 34))}<br>'
                 f'<span style="color:var(--muted)">{esc(short(L(d, "playthroughs", lg), 78))}</span></div>')
        p.append(f'<div class="prow"><span class="lb">🏆 {t["trophy_steps"]}</span><div class="bar">'
                 f'<div style="width:{tpct:.1f}%"></div></div><span class="count">{tdone} / {ttotal}</span></div>')
        p.append(f'<div class="prow"><span class="lb">📋 {t["steps"]}</span><div class="bar moonbar">'
                 f'<div style="width:{pct:.1f}%"></div></div>'
                 f'<span class="count mooncount">{done} / {total}</span></div>')
        if when:
            p.append(f'<div class="when">↻ {esc(when)}</div>')
        p.append("</a>")
    p.append("</div>")
    p.append(f'<div class="hubnote">{t["hubnote"]}</div>')
    p.append(f'<div class="hubnote"><h3>💾 {t["backup_title"]}</h3>{t["backup_note"]}'
             f'<div class="btns"><a class="btn" href="/api/export">⬇ {t["download_backup"]}</a>'
             f'<button onclick="document.getElementById(\'impf\').click()">⬆ {t["restore_backup"]}</button>'
             f'<input type="file" id="impf" accept="application/json,.json" style="display:none">'
             f'<span id="impState" style="font-size:.8em;color:var(--muted)"></span></div></div>')
    p.append("</div>")
    p.append(f'<footer>{t["footer"]}</footer>')
    p.append("""<script>
document.getElementById('impf').addEventListener('change', function(){
  var f = this.files[0]; if(!f) return;
  if(!confirm(%s)) { this.value=''; return; }
  var fr = new FileReader();
  fr.onload = function(){
    fetch('/api/import', {method:'POST', headers:{'Content-Type':'application/json'}, body: fr.result})
      .then(function(r){ if(!r.ok) throw 0; return r.json(); })
      .then(function(){ document.getElementById('impState').textContent = %s; setTimeout(function(){location.reload();}, 700); })
      .catch(function(){ document.getElementById('impState').textContent = %s; });
  };
  fr.readAsText(f);
});
</script></body></html>""" % (json.dumps(T[lg]["confirm_import"]), json.dumps(T[lg]["import_ok"]),
                              json.dumps(T[lg]["import_bad"])))
    return "\n".join(p)


# -------------------------------------------------------------- checklist page
CHECKLIST_JS = r"""
var RUN = __RUN__, S = __STR__;
var items = Array.prototype.slice.call(document.querySelectorAll('label.item input'));
var ids = items.map(function(i){return i.id;});
var stateEl = document.getElementById('saveState');
var saveTimer = null, firstLoad = true;

function bitstring(){ return ids.map(function(id){ return document.getElementById(id).checked ? '1':'0'; }).join(''); }
function flag(txt, cls){ stateEl.textContent = txt; stateEl.className = cls || ''; }

function refresh(){
  var all = items.length, done = 0, tAll = 0, tDone = 0;
  items.forEach(function(cb){
    var lab = cb.closest('label');
    var isT = lab.getAttribute('data-t') === '1';
    if(isT) tAll++;
    if(cb.checked){ done++; if(isT) tDone++; lab.classList.add('checked'); }
    else lab.classList.remove('checked');
  });
  document.getElementById('barAll').style.width = (all? done/all*100:0)+'%';
  document.getElementById('cntAll').textContent = done+' / '+all;
  document.getElementById('barTrophy').style.width = (tAll? tDone/tAll*100:0)+'%';
  document.getElementById('cntTrophy').textContent = tDone+' / '+tAll;
  document.querySelectorAll('section.phase').forEach(function(sec){
    var cbs = sec.querySelectorAll('input[type=checkbox]'), d = 0;
    cbs.forEach(function(c){ if(c.checked) d++; });
    if(cbs.length) sec.querySelector('.mini').textContent = d+'/'+cbs.length;
  });
  document.getElementById('platBox').classList.toggle('show', all>0 && done === all);
}
function push(){
  flag(S.saving, 'pending');
  fetch('/api/progress', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({run: RUN, bits: bitstring()})})
    .then(function(r){ if(!r.ok) throw 0; flag(S.saved); })
    .catch(function(){ flag(S.save_failed, 'err'); });
}
function scheduleSave(){ if(saveTimer) clearTimeout(saveTimer); flag(S.saving,'pending'); saveTimer = setTimeout(push, 350); }
items.forEach(function(cb, idx){ cb.addEventListener('change', function(){
  refresh(); applyView(); scheduleSave();
  if(typeof onTickMarker === 'function') onTickMarker(idx, cb.checked);
}); });

/* the only sticky element is the progress panel: keep scroll targets clear of it */
function measureStick(){
  var panel = document.querySelector('.progress-panel');
  if(panel) document.documentElement.style.setProperty('--stick', panel.offsetHeight + 'px');
}
window.addEventListener('resize', measureStick);
measureStick();

function toggle(head){ head.parentElement.classList.toggle('open'); }
function expandAll(){ document.querySelectorAll('section.phase').forEach(function(s){ s.classList.add('open'); }); }
function collapseAll(){ document.querySelectorAll('section.phase').forEach(function(s){ s.classList.remove('open'); }); }

function resetRun(){
  if(!confirm(S.confirm_reset)) return;
  fetch('/api/run/reset', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({run: RUN})})
    .then(function(r){ if(!r.ok) throw 0; return r.json(); })
    .then(function(){ location.reload(); })
    .catch(function(){ flag(S.save_failed, 'err'); });
}

/* ---- view: filter + hide done + only missable ---- */
function applyView(){
  var q = document.getElementById('filterBox').value.trim().toLowerCase();
  var onlyMiss = document.getElementById('missOnly').checked;
  document.body.classList.toggle('hidedone', document.getElementById('hideDone').checked);
  var anyVisible = false;
  document.querySelectorAll('section.phase').forEach(function(sec){
    var shown = 0;
    sec.querySelectorAll('label.item').forEach(function(lab){
      var hideMiss = onlyMiss && lab.getAttribute('data-miss') !== '1';
      var hideQ = q && lab.textContent.toLowerCase().indexOf(q) < 0;
      lab.classList.toggle('filtered', hideMiss || hideQ);
      lab.classList.toggle('hit', !!q && !hideMiss && !hideQ);
      var visible = !(hideMiss || hideQ) &&
        !(document.body.classList.contains('hidedone') && lab.classList.contains('checked'));
      if(visible) shown++;
    });
    var empty = (q || onlyMiss) && shown === 0;
    sec.classList.toggle('filtered', empty);
    if(!empty) anyVisible = true;
    if((q || onlyMiss) && shown > 0) sec.classList.add('open');
  });
  document.getElementById('noMatch').classList.toggle('show', !anyVisible);
  if(!firstLoad) savePrefs();
}
function savePrefs(){
  fetch('/api/pref', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({hide_done: document.getElementById('hideDone').checked ? '1':'0',
                          only_miss: document.getElementById('missOnly').checked ? '1':'0'})}).catch(function(){});
}
document.getElementById('filterBox').addEventListener('input', applyView);
document.getElementById('hideDone').addEventListener('change', applyView);
document.getElementById('missOnly').addEventListener('change', applyView);
document.addEventListener('keydown', function(e){
  if(e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA'){
    e.preventDefault(); document.getElementById('filterBox').focus();
  }
});

/* ---- where I left off ---- */
function resume(){
  var next = items.find(function(cb){ return !cb.checked; });
  if(!next) return;
  var lab = next.closest('label');
  var sec = lab.closest('section.phase');
  if(sec) sec.classList.add('open');
  lab.classList.remove('filtered');
  lab.scrollIntoView({block:'center', behavior:'smooth'});
  lab.classList.remove('here'); void lab.offsetWidth; lab.classList.add('here');
}

/* ---- notes ---- */
var noteTimer = null, noteEl = document.getElementById('notesBox');
if(noteEl){
  noteEl.addEventListener('input', function(){
    if(noteTimer) clearTimeout(noteTimer);
    flag(S.saving, 'pending');
    noteTimer = setTimeout(function(){
      fetch('/api/notes', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({run: RUN, body: noteEl.value})})
        .then(function(r){ if(!r.ok) throw 0; flag(S.saved); })
        .catch(function(){ flag(S.save_failed, 'err'); });
    }, 600);
  });
}

/* ---- boot ---- */
fetch('/api/progress?run=' + RUN).then(function(r){ return r.json(); }).then(function(j){
  var bits = j.bits || '';
  ids.forEach(function(id, i){ document.getElementById(id).checked = bits.charAt(i) === '1'; });
  refresh(); applyView(); firstLoad = false;
  flag(j.updated_at ? S.loaded + ' (' + j.updated_at + ')' : S.new_run);
  if(bits.indexOf('1') >= 0) setTimeout(resume, 250);
}).catch(function(){ refresh(); applyView(); firstLoad = false; flag(S.offline, 'err'); });

/* ============================ sessioni e marker ============================ */
var CFG = __CFG__;
var SES = null;              /* sessione aperta */
var CUR = null;              /* indice del passo in corso */
var startedAt = null;        /* tc di inizio del passo in corso */

function nowTc(){
  var o = (typeof obsTime === 'function') ? obsTime() : null;
  if(o) return {tc: o.tc, kind: o.kind};
  if(SES && SES._t0) return {tc: (Date.now() - SES._t0)/1000, kind: 'clock'};
  return {tc: 0, kind: 'none'};
}
function fmtTc(sec){
  sec = Math.max(0, Math.round(sec));
  var h = Math.floor(sec/3600), m = Math.floor(sec%3600/60), x = sec%60;
  return (h ? h + ':' + String(m).padStart(2,'0') : String(m).padStart(2,'0')) + ':' + String(x).padStart(2,'0');
}
function firstUnchecked(from){
  for(var i = (from||0); i < items.length; i++){ if(!items[i].checked) return i; }
  return null;
}
function paintCurrent(){
  document.querySelectorAll('label.item.current').forEach(function(e){ e.classList.remove('current'); });
  if(CUR === null || CUR === undefined) return;
  var cb = document.getElementById('s' + (CUR+1));
  if(cb) cb.closest('label').classList.add('current');
}
function setCurrent(i, alsoMark){
  CUR = i;
  paintCurrent();
  fetch('/api/current', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({run: RUN, step: (i === null ? -1 : i)})}).catch(function(){});
  if(alsoMark && SES && i !== null){
    var n = nowTc();
    startedAt = n.tc;
    postMarker(i, 'start', n.tc);
  }
}
function postMarker(step, kind, tc, note){
  if(!SES) return;
  fetch('/api/marker', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({run: RUN, session: SES.id, step: step, kind: kind, tc: tc, note: note||''})})
    .catch(function(){});
}
function startSession(){
  var o = (typeof obsTime === 'function') ? obsTime() : null;
  fetch('/api/session/start', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({run: RUN, source: (o ? 'obs' : 'clock')})})
    .then(function(r){ return r.json(); })
    .then(function(j){ SES = j.session; SES._t0 = Date.now(); paintBar();
                       setCurrent(firstUnchecked(0), true); });
}
function stopSession(){
  if(!SES) return;
  var id = SES.id;
  fetch('/api/session/stop', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({id: id})})
    .then(function(){ SES = null; paintBar(); paintLinkQueue(); })
    .catch(function(){ SES = null; paintBar(); });
}
function markFree(){
  if(!SES) return;
  var note = prompt('📍', '');
  if(note === null) return;
  postMarker(null, 'free', nowTc().tc, note);
}
function ytNormalize(u){
  u = (u || '').trim();
  if(!u) return '';
  var m = u.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?(?:.*&)?v=|live\/|embed\/|shorts\/))([A-Za-z0-9_-]{6,})/);
  if(m) return 'https://youtu.be/' + m[1];
  if(/^[A-Za-z0-9_-]{11}$/.test(u)) return 'https://youtu.be/' + u;
  if(!/^https?:\/\//i.test(u)) return 'https://' + u;
  return u;
}
function saveUrl(){
  if(!SES) return;
  var el = document.getElementById('epUrlBar'), st = document.getElementById('urlState');
  var clean = ytNormalize(el.value);
  el.value = clean;
  fetch('/api/session/update', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({id: SES.id, video_url: clean})})
    .then(function(r){ return r.json(); })
    .then(function(j){ SES = j.session; st.style.color = 'var(--ok)';
      st.textContent = clean ? '✓' : '';
      setTimeout(function(){ st.textContent = ''; }, 2500); })
    .catch(function(){ st.style.color = 'var(--warn)'; st.textContent = '✕'; });
}
function paintBar(){
  var bar = document.getElementById('recDot');
  if(!bar) return;
  var o = (typeof obsTime === 'function') ? obsTime() : null;
  var chip = document.getElementById('obsChip');
  if(OBS.ok){ chip.className = 'chip ok'; chip.title = '';
    chip.textContent = '● ' + S.obs_on +
      (o ? ' · ' + (o.kind === 'stream' ? ('live' + (OBS.svc ? ' ' + OBS.svc : '')) : 'rec')
         : ' · nessun output attivo'); }
  else { chip.className = 'chip bad';
    chip.textContent = S.obs_off + (OBS.err ? ' · ' + OBS.err : '') + (SES ? ' · ' + S.clock_mode : '');
    chip.title = 'OBS: Strumenti > Impostazioni server WebSocket > abilita il server, poi incolla la password nella scheda Sessione.'; }
  var dot = document.getElementById('recDot'), lab = document.getElementById('recLab');
  var ep = document.getElementById('epChip');
  document.getElementById('btnStart').style.display = SES ? 'none' : '';
  document.getElementById('btnStop').style.display  = SES ? '' : 'none';
  document.getElementById('btnMark').style.display  = SES ? '' : 'none';
  if(SES){
    dot.className = 'recdot'; lab.className = 'reclab'; lab.textContent = S.rec;
    ep.style.display = ''; ep.textContent = S.ep.toUpperCase() + ' ' + SES.number;
    var ur = document.getElementById('urlRow');
    if(ur){ ur.style.display = '';
      var eu = document.getElementById('epUrlBar');
      if(document.activeElement !== eu && eu.value !== (SES.video_url || '')) eu.value = SES.video_url || ''; }
    document.getElementById('tcNow').textContent = fmtTc(nowTc().tc);
    var row = document.getElementById('doingRow');
    if(CUR !== null && CUR !== undefined && items[CUR]){
      row.style.display = '';
      var lb = items[CUR].closest('label').querySelector('.txt').firstChild;
      document.getElementById('doingTask').textContent =
        (items[CUR].closest('label').innerText || '').split('\n')[0].slice(0, 90);
      document.getElementById('doingSince').textContent =
        (startedAt !== null ? '— ' + S.started_at + ' ' + fmtTc(startedAt) : '');
    } else { row.style.display = 'none'; }
  } else {
    dot.className = 'recdot off'; lab.className = 'reclab off'; lab.textContent = S.idle;
    ep.style.display = 'none';
    var ur0 = document.getElementById('urlRow'); if(ur0) ur0.style.display = 'none';
    document.getElementById('tcNow').textContent = '--:--';
    document.getElementById('doingRow').style.display = 'none';
  }
}
function onTickMarker(idx, checked){
  if(!SES) return;
  var n = nowTc();
  if(checked){
    postMarker(idx, 'done', n.tc);
    var nx = firstUnchecked(0);
    setCurrent(nx, true);
  } else {
    fetch('/api/marker/delete', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({session: SES.id, step: idx})}).catch(function(){});
    setCurrent(firstUnchecked(0), false);
  }
}
/* boot della parte streamer */
if(CFG.mode === 'streamer'){
  OBS.prefer = CFG.obs_prefer || 'auto';
  obsConnect(CFG.obs_url, CFG.obs_pass, function(){ paintBar(); });
  setInterval(paintBar, 1000);
  /* riprova da sola ogni 15 s rileggendo le preferenze: cambi la password
     nella scheda Sessione e si riattacca senza ricaricare la pagina */
  setInterval(function(){
    if(OBS.ok) return;
    fetch('/api/prefs').then(function(r){ return r.json(); }).then(function(p){
      OBS.prefer = p.obs_prefer || 'auto';
      obsConnect(p.obs_url, p.obs_pass, function(){ paintBar(); });
    }).catch(function(){});
  }, 15000);
  fetch('/api/current?run=' + RUN).then(function(r){ return r.json(); }).then(function(j){
    if(j.session){ SES = j.session; SES._t0 = Date.now(); }
    CUR = j.current ? j.current.i : null;
    paintCurrent(); paintBar();
  }).catch(function(){});
  document.querySelectorAll('label.item').forEach(function(lab, i){
    lab.addEventListener('dblclick', function(ev){
      if(ev.target.tagName === 'INPUT') return;
      ev.preventDefault(); setCurrent(i, true);
    });
  });
  paintLinkQueue();
  setInterval(pollCmd, 700);
}

/* ===================== comandi dalle scorciatoie globali =====================
   Il tasto lo intercetta Python (che riceve anche a gioco in primo piano) e
   mette un comando in coda. Qui lo eseguiamo passando per le STESSE funzioni
   dei pulsanti: niente logica duplicata. */

function hkToast(txt){
  fetch('/api/toast', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({run: RUN, text: txt})}).catch(function(){});
  flag(txt);
}
function stepLabel(i){
  if(i === null || i === undefined || !items[i]) return '';
  return (items[i].closest('label').innerText || '').split('\n')[0].slice(0, 60);
}
function cmdNext(){
  var i = (CUR !== null && CUR !== undefined && items[CUR] && !items[CUR].checked)
            ? CUR : firstUnchecked(0);
  if(i === null){ hkToast(S.hk_all_done); return; }
  var lb = stepLabel(i);
  items[i].checked = true;
  items[i].dispatchEvent(new Event('change'));     /* stesso percorso del click */
  hkToast('✓ ' + lb);
}
function cmdUndo(){
  var last = null;
  for(var i = 0; i < items.length; i++){ if(items[i].checked) last = i; }
  if(last === null){ hkToast(S.hk_nothing); return; }
  var lb = stepLabel(last);
  items[last].checked = false;
  items[last].dispatchEvent(new Event('change'));
  hkToast('↶ ' + lb);
}
function cmdMark(){
  if(!SES){ hkToast(S.hk_no_ses); return; }
  postMarker(null, 'free', nowTc().tc, '📍');
  hkToast('📍 ' + fmtTc(nowTc().tc));
}
function cmdRec(){
  if(SES){
    if(OBS.ok) obsSend('StopRecord');
    hkToast(S.hk_stop);
    stopSession();
  } else {
    if(OBS.ok) obsSend('StartRecord');
    hkToast(S.hk_start);
    /* diamo a OBS un secondo per far partire l'output, cosi' il timecode
       della sessione nasce gia' allineato al video */
    setTimeout(startSession, 1200);
  }
}
function runCmd(c){
  if(c.a === 'next') return cmdNext();
  if(c.a === 'undo') return cmdUndo();
  if(c.a === 'mark') return cmdMark();
  if(c.a === 'rec')  return cmdRec();
}
function pollCmd(){
  fetch('/api/pending?run=' + RUN).then(function(r){ return r.json(); })
    .then(function(j){ (j.cmds || []).forEach(runCmd); })
    .catch(function(){});
}

/* ======================= episodi in attesa del link video ===================
   Il link non esiste quando chiudi la registrazione: esiste dopo, quando il
   video e' online. Quindi non lo chiediamo in quel momento — lo teniamo in
   una lista visibile finche' non lo incolli. */

function paintLinkQueue(){
  var box = document.getElementById('linkQueue');
  if(!box) return;
  fetch('/api/episodes?run=' + RUN).then(function(r){ return r.json(); }).then(function(eps){
    var miss = (eps || []).filter(function(e){ return !e.video_url && e.ended_at; });
    if(!miss.length){ box.style.display = 'none'; box.innerHTML = ''; return; }
    var h = '<div class="lqh">▶ ' + S.lq_title.replace('{n}', miss.length) + '</div>';
    miss.forEach(function(e){
      var n = (e.markers || []).filter(function(m){ return m.kind === 'done'; }).length;
      h += '<div class="lqrow" data-id="' + e.id + '">' +
           '<span class="lqep">' + S.ep.toUpperCase() + ' ' + e.number + '</span>' +
           '<span class="lqmeta">' + (e.started_at || '').slice(0, 16) + ' · ' +
              n + ' ' + S.lq_tasks + '</span>' +
           '<input type="text" class="lqin" placeholder="' + S.url_ph + '">' +
           '<button class="lqok">💾</button>' +
           '<span class="lqst"></span></div>';
    });
    box.innerHTML = h;
    box.style.display = '';
    box.querySelectorAll('.lqrow').forEach(function(row){
      var inp = row.querySelector('.lqin'), st = row.querySelector('.lqst');
      var send = function(){
        var clean = ytNormalize(inp.value);
        if(!clean){ st.textContent = '✕'; st.style.color = 'var(--warn)'; return; }
        st.textContent = '…'; st.style.color = 'var(--muted)';
        fetch('/api/session/update', {method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({id: parseInt(row.getAttribute('data-id'), 10), video_url: clean})})
          .then(function(r){ if(!r.ok) throw 0; st.textContent = '✓';
                             st.style.color = 'var(--ok)'; setTimeout(paintLinkQueue, 700); })
          .catch(function(){ st.textContent = '✕'; st.style.color = 'var(--warn)'; });
      };
      row.querySelector('.lqok').addEventListener('click', send);
      inp.addEventListener('keydown', function(ev){ if(ev.key === 'Enter') send(); });
    });
  }).catch(function(){});
}
"""


def render_run(run_id):
    lg = lang()
    t = T[lg]
    d = ROUTES[run_id]
    hide_done = get_pref("hide_done", "0") == "1"
    only_miss = get_pref("only_miss", "0") == "1"
    note_body = get_note(run_id)
    p = ['<!DOCTYPE html><html lang="%s"><head><meta charset="UTF-8">' % lg,
         '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
         f"<title>{esc(d['game'])} - {t['checklist']} - Voloirex</title>",
         "<style>" + CSS + "</style></head><body>", hk_panel(lg, run_id)]
    p.append(f'<header><div class="topright">{hk_button(lg)}{modesel(lg, "/run/" + run_id)}'
             f'{langsel(lg, "/run/" + run_id)}</div><h1>{esc(d["game"]).upper()} · {t["checklist"]}</h1>'
             f'<p class="sub">{t["sub_run"]} · <span class="by">{t["by"]}</span></p>'
             f'<p class="meta">🏆 {d["trophy_total"]} {t["trophies"]} · {esc(L(d, "playthroughs", lg))} · '
             f'⏱ {esc(L(d, "hours", lg))}</p></header>')
    p.append('<div class="wrap">')
    p.append(f'<a class="back" href="/">← {t["back"]}</a>')
    p.append(tabs(lg, run_id, "check"))
    p.append(f'''<div class="progress-panel">
    <div class="progress-row"><span class="label">🏆 {t["trophy_steps"]}</span><div class="bar"><div id="barTrophy"></div></div><span class="count" id="cntTrophy">0 / 0</span></div>
    <div class="progress-row" style="margin-top:7px"><span class="label">📋 {t["total_steps"]}</span><div class="bar moonbar"><div id="barAll"></div></div><span class="count mooncount" id="cntAll">0 / 0</span></div>
    <div class="toolbar">
      <input id="filterBox" placeholder="{t["filter_ph"]}">
      <label class="chk"><input type="checkbox" id="hideDone"{" checked" if hide_done else ""}>{t["hide_done"]}</label>
      <label class="chk"><input type="checkbox" id="missOnly"{" checked" if only_miss else ""}>{t["only_miss"]}</label>
      <button onclick="resume()">📍 {t["resume"]}</button>
      <button onclick="expandAll()">⤵ {t["expand"]}</button>
      <button onclick="collapseAll()">⤴ {t["collapse"]}</button>
      <button class="danger" onclick="resetRun()">🗑 {t["reset"]}</button>
      {langsel(lg, "/run/" + run_id)}
      <span id="saveState">{t["loading"]}</span>
    </div>
  </div>''')
    if mode() == "streamer":
        p.append(f'''<div class="sessionbar">
      <div class="row1">
        <span class="recdot off" id="recDot"></span><span class="reclab off" id="recLab">{t["idle"]}</span>
        <span class="tc" id="tcNow">--:--</span>
        <span class="chip bad" id="obsChip">{t["obs_off"]}</span>
        <span class="chip ep" id="epChip" style="display:none"></span>
        <span class="spacer"></span>
        <button id="btnStart" onclick="startSession()">🔴 {t["start_ses"]}</button>
        <button id="btnMark" onclick="markFree()" style="display:none">📍 {t["mark"]}</button>
        <button id="btnStop" class="danger" onclick="stopSession()" style="display:none">⏹ {t["stop_ses"]}</button>
      </div>
      <div class="doing" id="doingRow" style="display:none">
        <span class="lab">{t["doing"]}</span><span class="task" id="doingTask">—</span>
        <span class="since" id="doingSince"></span>
      </div>
      <div class="doing" id="urlRow" style="display:none">
        <span class="lab">▶ {t["ep_url"]}</span>
        <input type="text" id="epUrlBar" placeholder="{t["url_ph"]}"
               style="flex:1;min-width:200px;background:#0a0c10;border:1px solid var(--line);border-radius:6px;color:var(--text);padding:5px 9px;font-size:.9em;font-family:inherit">
        <button onclick="saveUrl()">💾</button>
        <span id="urlState" style="font-size:.9em"></span>
      </div>
      <div id="linkQueue" class="linkq" style="display:none"></div>
    </div>''')

    rules = L(d, "golden_rules", lg) or d["golden_rules"]
    bullets = (d.get("build_bullets_it") if lg == "it" else None) or d.get("build_bullets") or []
    p.append('<section class="phase notes-sec">')
    p.append(f'<div class="phase-head" onclick="toggle(this)"><span class="num">⚠️</span>'
             f'<h2>{t["notes_sec"]}</h2>'
             f'<span class="mini">{t["notes_sec_sub"].format(r=len(rules), b=len(bullets))}</span>'
             f'<span class="chev">▶</span></div>')
    p.append('<div class="phase-body"><div class="rules">')
    p.append(f'<h3>{t["rules_h"]}</h3><ul>')
    for r in rules:
        p.append(f"<li>{hl(r)}</li>")
    p.append("</ul>")
    if bullets:
        p.append(f'<h3>🛡 {t["build_h"]}</h3><ul class="buildbox">')
        for bl in bullets:
            p.append(f'<li><span class="bh">{esc(bl["h"])}</span>{hl(bl["t"])}</li>')
        p.append("</ul>")
    else:
        p.append(f'<h3>🛡 {t["build_h"]}</h3><ul class="buildbox">'
                 f'<li>{hl(L(d, "build_summary", lg))}</li></ul>')
    p.append(f'<h3>{t["legend_h"]}</h3><p class="legend">{t["legend"]}</p>')
    p.append("</div></div></section>")

    stamps = step_stamps(run_id) if mode() == "streamer" or True else {}
    n = 0
    for pi, ph in enumerate(d["phases"]):
        opencls = " open" if pi == 0 else ""
        p.append(f'<section class="phase{opencls}">')
        p.append(f'<div class="phase-head" onclick="toggle(this)"><span class="num">P{pi+1}</span>'
                 f'<h2>{esc(L(ph, "title", lg))}</h2><span class="mini"></span><span class="chev">▶</span></div>')
        p.append('<div class="phase-body">')
        note = L(ph, "note", lg)
        if note:
            p.append(f'<div class="phase-note">{hl(note)}</div>')
        for st in ph["steps"]:
            n += 1
            tags = st.get("tags", [])
            dt = ' data-t="1"' if st.get("trophy") else ""
            dm = ' data-miss="1"' if any(x["type"] == "miss" for x in tags) else ""
            tg = "".join(f'<span class="tag {x["type"]}">{esc(L(x, "label", lg))}</span>' for x in tags)
            if tg:
                tg = " " + tg
            sh = stamp_html(stamps.get(n - 1, {}), lg) if stamps.get(n - 1) else ""
            p.append(f'<label class="item"{dt}{dm}><input type="checkbox" id="s{n}">'
                     f'<span class="txt">{hl(L(st, "text", lg))}{tg}{sh}'
                     f'<span class="loc">{esc(L(st, "loc", lg))}</span></span></label>')
        p.append("</div></section>")

    p.append(f'<div id="noMatch">{t["no_match"]}</div>')

    stt = (d.get("stat_table_it") if lg == "it" else None) or d["stat_table"]
    p.append(f'<section class="phase"><div class="phase-head" onclick="toggle(this)">'
             f'<span class="num">📊 REF</span><h2>{t["stats_ref"]}</h2>'
             f'<span class="mini"></span><span class="chev">▶</span></div><div class="phase-body">')
    p.append(f'<div class="phase-note">{esc(stt["note"])}</div><table class="stats">')
    p.append("<tr>" + "".join(f"<th>{esc(c)}</th>" for c in stt["columns"]) + "</tr>")
    for row in stt["rows"]:
        p.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>")
    p.append("</table></div></section>")

    gloss = d.get("glossary_it") or {}
    if lg == "it" and gloss:
        p.append(f'<section class="phase"><div class="phase-head" onclick="toggle(this)">'
                 f'<span class="num">📖 GLOS</span><h2>{t["gloss_title"]}</h2>'
                 f'<span class="mini">{len(gloss)}</span><span class="chev">▶</span></div><div class="phase-body">')
        p.append(f'<div class="phase-note">{t["gloss_note"]}</div><table class="gloss">')
        for k, v in sorted(gloss.items(), key=lambda kv: kv[0].lower()):
            p.append(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>")
        p.append("</table></div></section>")

    p.append(f'<section class="phase"><div class="phase-head" onclick="toggle(this)">'
             f'<span class="num">📝 {"NOTE" if lg == "it" else "NOTES"}</span><h2>{t["notes_title"]}</h2>'
             f'<span class="mini"></span><span class="chev">▶</span></div><div class="phase-body">'
             f'<div class="phase-note">{t["notes_note"]}</div>'
             f'<textarea class="notes" id="notesBox" placeholder="{t["notes_ph"]}">{esc(note_body)}</textarea>'
             "</div></section>")

    p.append(f'<div class="plat" id="platBox"><h2>{t["plat_done"]}</h2></div></div>')
    p.append(f'<footer>{t["footer_run"]}</footer>')
    strings = {k: t[k] for k in ("saving", "saved", "save_failed", "offline", "loaded", "new_run",
                                 "confirm_reset", "obs_on", "obs_off", "clock_mode", "rec", "idle",
                                 "ep", "doing", "started_at", "since", "mark", "no_session_warn",
                                 "ask_url", "url_ph", "lq_title", "lq_tasks", "hk_all_done",
                                 "hk_nothing", "hk_no_ses", "hk_start", "hk_stop")}
    cfg = {"mode": mode(),
           "obs_url": get_pref("obs_url", "ws://127.0.0.1:4455"),
           "obs_pass": get_pref("obs_pass", ""),
           "obs_prefer": get_pref("obs_prefer", "auto")}
    js = (OBS_JS + CHECKLIST_JS).replace("__RUN__", json.dumps(run_id)) \
        .replace("__STR__", json.dumps(strings, ensure_ascii=False)) \
        .replace("__CFG__", json.dumps(cfg, ensure_ascii=False))
    p.append("<script>" + js + "</script></body></html>")
    return "\n".join(p)




def mode():
    m = get_pref("mode", "gamer")
    return m if m in ("gamer", "streamer") else "gamer"


def modesel(lg, path):
    q = urllib.parse.quote(path, safe="/")
    t = T[lg]
    m = mode()
    a = lambda code, txt: f'<a class="{"on" if m == code else ""}" href="/mode/{code}?next={q}">{txt}</a>'
    return (f'<div class="modesel"><span class="lbl">🎮 {t["mode"]}</span>'
            f'{a("gamer", t["gamer"])}{a("streamer", t["streamer"])}</div>')


def tabs(lg, run_id, active):
    t = T[lg]
    if mode() != "streamer":
        return ""
    def a(key, href, label):
        return f'<a class="{"on" if active == key else ""}" href="{href}">{label}</a>'
    return ('<div class="tabs">'
            + a("check", f"/run/{run_id}", "📋 " + t["tab_check"])
            + a("eps", f"/episodes/{run_id}", "🎬 " + t["tab_eps"])
            + a("ses", f"/session/{run_id}", "⚙️ " + t["tab_ses"])
            + "</div>")


def stamp_html(st, lg):
    """The EP · mm:ss ▶ badge for one step."""
    done, start = st.get("done"), st.get("start")
    t = T[lg]
    if done and done["url"]:
        main = f'<span class="ep">{t["ep"]} {done["ep"]}</span> · {fmt_tc(done["t"])} ▶'
        cls = "stamp"
        extra = ""
        if start and start["ep"] != done["ep"]:
            cls += " two"
            if start["url"]:
                extra = (f' · <a class="stamp" style="border:none;padding:0;margin:0;background:none" '
                         f'href="{video_link(start["url"], start["t"])}" target="_blank">'
                         f'{t["ep"]} {start["ep"]} · {fmt_tc(start["t"])}</a>')
            else:
                extra = f' · {t["ep"]} {start["ep"]}'
        return (f'<a class="{cls}" href="{video_link(done["url"], done["t"])}" target="_blank">'
                f'{main}{extra}</a>')
    if done:
        return (f'<span class="stamp" title="{t["no_video"]}">'
                f'<span class="ep">{t["ep"]} {done["ep"]}</span> · {fmt_tc(done["tc"])}</span>')
    if start:
        return (f'<span class="stamp live"><span class="ep">{t["ep"]} {start["ep"]}</span> · '
                f'{fmt_tc(start["tc"])}</span>')
    return ""


# ============================================================ scorciatoie da
# tastiera globali (Windows) + coda comandi
#
# Il browser non riceve tasti quando il gioco ha il fuoco: le scorciatoie le
# registra il processo Python con RegisterHotKey (user32, via ctypes: nessuna
# dipendenza in piu'). Il thread non esegue nulla di suo, si limita a mettere
# un comando in coda; a eseguirlo e' la pagina gia' aperta, che e' l'unica ad
# avere il WebSocket di OBS e lo stato della checklist. Cosi' i tasti passano
# esattamente per lo stesso codice dei pulsanti, e non esiste una seconda
# implementazione da tenere allineata.

# ==================================================== controllo aggiornamenti
# Una sola chiamata all'avvio, in un thread, con timeout corto. Se non c'e'
# rete non succede niente: l'app non deve MAI dipendere da GitHub per partire.
# Nessun download automatico e nessuna installazione silenziosa: si avvisa e
# basta, il file lo scarica l'utente. Su un'app non firmata, un aggiornamento
# che si installa da solo e' esattamente quello che fa un malware.

def _vtuple(v):
    """'v4.1.2' -> (4, 1, 2). Le parti non numeriche (rc, beta) si ignorano."""
    nums = re.findall(r"\d+", str(v or ""))
    return tuple(int(x) for x in nums[:3]) + (0,) * (3 - len(nums[:3]))


def check_update():
    if os.environ.get("PLATINUM_HUB_NO_UPDATE") == "1":
        UPDATE["checked"] = True
        return
    if get_pref("update_check", "1") != "1":
        UPDATE["checked"] = True
        UPDATE["latest"] = ""
        return
    try:
        req = urllib.request.Request(RELEASES_API, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "PlatinumHub/" + VERSION})
        with urllib.request.urlopen(req, timeout=6) as r:
            j = json.loads(r.read().decode("utf-8"))
        tag = str(j.get("tag_name") or "")
        if tag and _vtuple(tag) > _vtuple(VERSION):
            UPDATE["latest"] = tag.lstrip("vV")
            UPDATE["url"] = j.get("html_url") or RELEASES_PAGE
            UPDATE["notes"] = (j.get("body") or "")[:1500]
    except Exception:
        pass                     # nessuna rete, GitHub giu', limite di richieste: pazienza
    finally:
        UPDATE["checked"] = True


HOTKEYS_DEFAULT = "ctrl+alt+F9:rec, ctrl+alt+F10:next, ctrl+alt+F8:undo, ctrl+alt+F11:mark"
HOTKEY_ACTIONS = ("rec", "next", "undo", "mark")

CMDQ = []                      # comandi in attesa che la pagina li esegua
CMDLOCK = threading.Lock()
TOASTS = {}                    # run_id -> (testo, timestamp) per l'overlay
HOTKEY_STATE = {"active": [], "failed": [], "why": ""}


def push_cmd(action, run=None):
    if action not in HOTKEY_ACTIONS:
        return False
    with CMDLOCK:
        CMDQ.append({"a": action, "run": run, "ts": time.time()})
        del CMDQ[:-20]
    return True


def take_cmds():
    now = time.time()
    with CMDLOCK:
        out = [c for c in CMDQ if now - c["ts"] < 10]
        del CMDQ[:]
    return out


def set_toast(run_id, text):
    TOASTS[run_id] = (str(text)[:90], time.time())


def get_toast(run_id):
    v = TOASTS.get(run_id)
    if not v or time.time() - v[1] > 4:
        return ""
    return v[0]


def parse_hotkeys(spec):
    """'ctrl+alt+F9:rec, ...' -> [(mods, vk, action, testo)] — nessuna eccezione."""
    mods = {"alt": 0x0001, "ctrl": 0x0002, "control": 0x0002,
            "shift": 0x0004, "win": 0x0008}
    out = []
    for chunk in str(spec or "").split(","):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        combo, action = chunk.rsplit(":", 1)
        action = action.strip().lower()
        if action not in HOTKEY_ACTIONS:
            continue
        m, vk = 0, None
        for part in combo.split("+"):
            part = part.strip().lower()
            if part in mods:
                m |= mods[part]
            elif re.fullmatch(r"f([1-9]|1[0-9]|2[0-4])", part):
                vk = 0x6F + int(part[1:])          # F1 = 0x70 ... F24 = 0x87
            elif len(part) == 1 and part.isalnum():
                vk = ord(part.upper())
        if vk and m:                                # senza modificatori non si registra
            out.append((m, vk, action, combo.strip()))
    return out


def _fire(action, port):
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:%d/api/cmd" % port,
            data=json.dumps({"action": action}).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=2).read()
    except Exception:
        pass


def hotkey_worker(spec, port):
    """Registra le scorciatoie e resta in ascolto. Solo Windows."""
    try:
        import ctypes
        from ctypes import wintypes
    except Exception as e:                                   # pragma: no cover
        HOTKEY_STATE["why"] = "ctypes non disponibile (%s)" % e
        return
    u32 = ctypes.windll.user32
    MOD_NOREPEAT = 0x4000
    WM_HOTKEY = 0x0312
    idmap = {}
    for i, (m, vk, action, label) in enumerate(parse_hotkeys(spec), start=1):
        if u32.RegisterHotKey(None, i, m | MOD_NOREPEAT, vk):
            idmap[i] = action
            HOTKEY_STATE["active"].append((label, action))
        else:
            HOTKEY_STATE["failed"].append((label, action))
    if not idmap:
        HOTKEY_STATE["why"] = "nessuna combinazione registrata (gia' occupate?)"
        return
    msg = wintypes.MSG()
    while u32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == WM_HOTKEY:
            action = idmap.get(msg.wParam)
            if action:
                threading.Thread(target=_fire, args=(action, port), daemon=True).start()


def start_hotkeys(port):
    spec = get_pref("hotkeys", HOTKEYS_DEFAULT)
    if get_pref("hotkeys_on", "1") != "1":
        HOTKEY_STATE["why"] = "disattivate"
        return
    if sys.platform != "win32":
        HOTKEY_STATE["why"] = "solo su Windows"
        return
    threading.Thread(target=hotkey_worker, args=(spec, port), daemon=True).start()
    time.sleep(0.3)


OBS_JS = r"""
var OBS = {ws:null, ok:false, rec:false, recTc:0, str:false, strTc:0, prefer:'auto', err:'', svc:''};
function sha256b64(str){
  return crypto.subtle.digest('SHA-256', new TextEncoder().encode(str)).then(function(buf){
    var b = new Uint8Array(buf), s = '';
    for(var i=0;i<b.length;i++) s += String.fromCharCode(b[i]);
    return btoa(s);
  });
}
function tcToSec(tc){
  if(!tc) return 0;
  var p = tc.split(':'); if(p.length < 3) return 0;
  return (+p[0])*3600 + (+p[1])*60 + parseFloat(p[2]);
}
function obsSend(type){
  if(!OBS.ok || !OBS.ws) return;
  try{ OBS.ws.send(JSON.stringify({op:6, d:{requestType:type, requestId:type}})); }catch(e){}
}
function obsPoll(){
  if(OBS._t) return;
  OBS._t = setInterval(function(){ obsSend('GetRecordStatus'); obsSend('GetStreamStatus'); }, 1000);
  obsSend('GetRecordStatus'); obsSend('GetStreamStatus'); obsSend('GetStreamServiceSettings');
}
function obsConnect(url, pass, cb){
  try{ if(OBS.ws) OBS.ws.close(); }catch(e){}
  if(OBS._t){ clearInterval(OBS._t); OBS._t = null; }
  var ws;
  try{ ws = new WebSocket(url); }catch(e){ if(cb) cb(false, 'URL?'); return; }
  OBS.ws = ws; OBS.ok = false; OBS.err = '';
  var done = false;
  var timer = setTimeout(function(){
    if(!OBS.ok && !done){ done = true; try{ ws.close(); }catch(e){}
      OBS.err = 'nessuna risposta (password?)'; if(cb) cb(false, OBS.err); }
  }, 4000);
  ws.onmessage = function(ev){
    var msg; try{ msg = JSON.parse(ev.data); }catch(e){ return; }
    if(msg.op === 0){
      var d = msg.d;
      var ident = function(a){
        ws.send(JSON.stringify({op:1, d:{rpcVersion:1, authentication:a, eventSubscriptions:0}}));
      };
      if(d && d.authentication){
        sha256b64((pass||'') + d.authentication.salt)
          .then(function(s1){ return sha256b64(s1 + d.authentication.challenge); })
          .then(ident)
          .catch(function(){ if(cb && !done){ done=true; OBS.err='password'; cb(false, OBS.err); } });
      } else { ident(undefined); }
    } else if(msg.op === 2){
      OBS.ok = true; OBS.err = ''; clearTimeout(timer);
      if(cb && !done){ done = true; cb(true, 'rpc v' + (msg.d ? msg.d.negotiatedRpcVersion : '?')); }
      obsPoll();
    } else if(msg.op === 7 && msg.d && msg.d.responseData){
      var r = msg.d, x = r.responseData;
      if(r.requestType === 'GetRecordStatus'){ OBS.rec = !!x.outputActive; OBS.recTc = tcToSec(x.outputTimecode); }
      if(r.requestType === 'GetStreamStatus'){ OBS.str = !!x.outputActive; OBS.strTc = tcToSec(x.outputTimecode); }
      if(r.requestType === 'GetStreamServiceSettings'){
        var ss = x.streamServiceSettings || {};
        var srv = ss.service || ss.server || x.streamServiceType || '';
        srv = String(srv);
        if(/youtube|ytb/i.test(srv)) srv = 'YouTube';
        else if(/twitch/i.test(srv)) srv = 'Twitch';
        else if(srv === 'rtmp_custom') srv = 'RTMP';
        OBS.svc = srv.slice(0, 22);
      }
    }
  };
  ws.onerror = function(){ clearTimeout(timer); OBS.ok = false;
    if(cb && !done){ done = true; OBS.err = 'non raggiungibile'; cb(false, OBS.err); } };
  ws.onclose = function(ev){ if(OBS.ok) OBS.err = 'connessione chiusa';
    else if(!OBS.err) OBS.err = 'password o handshake rifiutati';
    OBS.ok = false; if(OBS._t){ clearInterval(OBS._t); OBS._t = null; } };
}
/* which timecode counts, and is anything actually running */
function obsTime(){
  if(!OBS.ok) return null;
  var p = OBS.prefer;
  if(p === 'stream') return OBS.str ? {tc:OBS.strTc, kind:'stream'} : null;
  if(p === 'rec')    return OBS.rec ? {tc:OBS.recTc, kind:'rec'} : null;
  if(OBS.str) return {tc:OBS.strTc, kind:'stream'};
  if(OBS.rec) return {tc:OBS.recTc, kind:'rec'};
  return null;
}
"""


# ------------------------------------------------------------------- overlay
def current_state(run_id):
    """What the overlay and the session bar need: current step, next step, progress."""
    d = ROUTES[run_id]
    lg = lang()
    steps = []
    for pi, ph in enumerate(d["phases"]):
        for st in ph["steps"]:
            steps.append((pi, ph, st))
    bits = get_bits(run_id, d["_steps"])
    try:
        cur = int(get_pref("cur_" + run_id, "-1"))
    except ValueError:
        cur = -1
    if cur < 0 or cur >= len(steps) or bits[cur] == "1":
        cur = bits.find("0")
    done = sum(1 for c in bits if c == "1")
    flags = [bool(s.get("trophy")) for _, _, s in steps]
    tdone = sum(1 for i, c in enumerate(bits) if c == "1" and flags[i])

    def pack(i):
        if i is None or i < 0 or i >= len(steps):
            return None
        pi, ph, st = steps[i]
        tags = st.get("tags", [])
        return {"i": i, "text": L(st, "text", lg), "loc": L(st, "loc", lg),
                "phase": L(ph, "title", lg), "phase_n": pi + 1,
                "trophy": bool(st.get("trophy")),
                "trophy_label": next((L(t, "label", lg) for t in tags if t["type"] == "trophy"), ""),
                "missable": any(t["type"] == "miss" for t in tags)}

    nxt = None
    if cur is not None and cur >= 0:
        j = bits.find("0", cur + 1)
        nxt = j if j >= 0 else None
    ses = open_session(run_id)
    return {"run": run_id, "game": d["game"], "lang": lg,
            "current": pack(cur if cur >= 0 else None), "next": pack(nxt),
            "done": done, "total": d["_steps"], "tdone": tdone, "ttotal": d["_tsteps"],
            "session": session_row(ses[0]) if ses else None}


OVERLAY_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:transparent;font-family:'Roboto','Segoe UI',system-ui,Arial,sans-serif;
color:#fff;overflow:hidden}
#box{position:fixed;transition:opacity .6s ease;left:var(--pad,24px);bottom:var(--pad,24px);max-width:var(--maxw,44vw);min-width:340px;
background:linear-gradient(90deg,rgba(13,15,20,.93),rgba(13,15,20,.78));
border-left:4px solid #c8a24a;border-radius:6px;padding:13px 20px 14px;
box-shadow:0 6px 26px rgba(0,0,0,.55)}
body.pos-top #box{top:var(--pad,24px);bottom:auto}
body.pos-tr #box{top:var(--pad,24px);bottom:auto;left:auto;right:var(--pad,24px)}
body.pos-br #box{bottom:var(--pad,24px);top:auto;left:auto;right:var(--pad,24px)}
#box.hide{opacity:0}
.k{font-size:13px;letter-spacing:3px;color:#8a8878;text-transform:uppercase;margin-bottom:5px}
.k b{color:#c8a24a;font-weight:500;letter-spacing:2px}
.t{font-size:26px;line-height:1.28;font-weight:500;text-shadow:0 2px 6px rgba(0,0,0,.9)}
.t .cap{color:#7fd8d0}
.l{font-size:15px;color:#9c9a8a;margin-top:5px}
.row{display:flex;gap:10px;align-items:center;margin-top:9px;flex-wrap:wrap}
.pill{font-size:12px;letter-spacing:1px;padding:2px 9px;border-radius:4px}
.pill.tro{background:#2a2413;color:#c8a24a;border:1px solid #8a7134}
.pill.miss{background:#2a1a14;color:#c86a4a;border:1px solid #4a2a1e}
.pill.nxt{background:#141d2a;color:#7fa8d9;border:1px solid #4a6a94}
.prog{font-size:13px;color:#8a8878;font-variant-numeric:tabular-nums;letter-spacing:1px}
body.size-s .t{font-size:20px} body.size-s .k{font-size:11px} body.size-s .l{font-size:13px}
body.size-l .t{font-size:33px} body.size-l .k{font-size:15px} body.size-l .l{font-size:17px}
#box.flash{animation:fl 1.6s ease-out 1}
#toast{position:fixed;left:50%;transform:translateX(-50%);bottom:6vh;opacity:0;
transition:opacity .25s ease;background:rgba(13,15,20,.94);border:1px solid #c8a24a;
border-radius:6px;padding:9px 20px;font-size:19px;letter-spacing:.5px;
box-shadow:0 6px 26px rgba(0,0,0,.6);pointer-events:none;max-width:70vw}
#toast.on{opacity:1}
@keyframes fl{0%{border-left-color:#fff;background:linear-gradient(90deg,rgba(60,48,16,.96),rgba(13,15,20,.8))}
100%{border-left-color:#c8a24a}}
"""


def render_overlay(run_id, q):
    lg = lang()
    pos = (q.get("pos") or ["bl"])[0]
    size = (q.get("size") or ["m"])[0]
    shownext = (q.get("next") or ["1"])[0] != "0"
    try:
        pad = max(0, min(1200, int((q.get("pad") or ["24"])[0])))
    except ValueError:
        pad = 24
    wq = (q.get("w") or [""])[0]
    if wq:
        try:
            maxw = "%dpx" % max(240, min(3000, int(wq)))
        except ValueError:
            maxw = "44vw"
    else:
        maxw = "44vw"      # si adatta da solo a qualsiasi canvas
    showprog = (q.get("progress") or ["1"])[0] != "0"
    try:
        hold = max(0, min(600, int((q.get("hold") or ["10"])[0])))
    except ValueError:
        hold = 10
    cls = {"bl": "", "top": "pos-top", "tr": "pos-tr", "br": "pos-br"}.get(pos, "")
    cls += " size-" + (size if size in ("s", "m", "l") else "m")
    lab = "ORA" if lg == "it" else "NOW"
    labn = "POI" if lg == "it" else "NEXT"
    return f"""<!DOCTYPE html><html lang="{lg}"><head><meta charset="UTF-8">
<title>overlay</title><style>{OVERLAY_CSS}</style></head>
<body class="{cls}" style="--pad:{pad}px;--maxw:{maxw}">
<div id="box" style="opacity:0">
  <div class="k"><b id="ph">—</b></div>
  <div class="t" id="txt">—</div>
  <div class="l" id="loc"></div>
  <div class="row" id="row"></div>
</div>
<div id="toast"></div>
<script>
var RUN = {json.dumps(run_id)}, SHOWNEXT = {str(shownext).lower()}, SHOWPROG = {str(showprog).lower()};
var HOLD = {hold};
var LAB = {json.dumps(lab)}, LABN = {json.dumps(labn)};
var lastKey = null, hideT = null, lastToast = '', toastT = null;
function esc(s){{ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;'); }}
var CAPRE = null;
try{{ CAPRE = new RegExp("(?<![\\w'\u2019])([A-Z\u00C0-\u00DE][A-Z\u00C0-\u00DE0-9'\u2019+\\-]{{1,}}(?:[ ][A-Z\u00C0-\u00DE][A-Z\u00C0-\u00DE0-9'\u2019+\\-]{{1,}})*)(?![\\w'\u2019])", "g"); }}
catch(e){{ CAPRE = null; }}
function caps(s){{
  var t = esc(s);
  if(!CAPRE) return t;
  try{{ return t.replace(CAPRE, '<span class="cap">$1</span>'); }}catch(e){{ return t; }}
}}
function tick(){{
  fetch('/api/current?run='+RUN).then(function(r){{return r.json();}}).then(function(j){{
    var box = document.getElementById('box'), c = j.current;
    if(!c){{ box.style.opacity = 0; return; }}
    var key = c.i;
    document.getElementById('ph').textContent = LAB + ' \u00b7 ' + c.phase;
    document.getElementById('txt').innerHTML = caps(c.text);
    document.getElementById('loc').textContent = c.loc || '';
    var row = [];
    if(c.trophy && c.trophy_label) row.push('<span class="pill tro">'+esc(c.trophy_label)+'</span>');
    if(c.missable) row.push('<span class="pill miss">\u26a0 MISSABILE</span>');
    if(SHOWNEXT && j.next) row.push('<span class="pill nxt">'+LABN+': '+esc(j.next.text.slice(0,58))+'\u2026</span>');
    if(SHOWPROG) row.push('<span class="prog">🏆 '+j.tdone+'/'+j.ttotal+' \u00b7 📋 '+j.done+'/'+j.total+'</span>');
    document.getElementById('row').innerHTML = row.join('');
    if(lastKey === null || key !== lastKey){{
      /* nuovo task: mostra, lampeggia, e se HOLD > 0 sparisce da solo */
      box.style.opacity = 1;
      box.classList.remove('flash'); void box.offsetWidth;
      if(lastKey !== null) box.classList.add('flash');
      if(hideT) clearTimeout(hideT);
      if(HOLD > 0) hideT = setTimeout(function(){{ box.style.opacity = 0; }}, HOLD * 1000);
    }} else if(HOLD === 0){{
      box.style.opacity = 1;
    }}
    lastKey = key;
    if(j.toast && j.toast !== lastToast){{
      lastToast = j.toast;
      var tb = document.getElementById('toast');
      tb.textContent = j.toast; tb.classList.add('on');
      if(toastT) clearTimeout(toastT);
      toastT = setTimeout(function(){{ tb.classList.remove('on'); }}, 2600);
    }}
  }}).catch(function(){{}});
}}
tick(); setInterval(tick, 700);
</script></body></html>"""



# ------------------------------------------------------------- episodes page
def hk_button(lg):
    """Il pulsante che apre il pannello delle scorciatoie."""
    t = T[lg]
    return ('<button class="hkbtn" onclick="hkOpen()" title="%s  (?)">⌨ %s</button>'
            % (esc(t["hk_panel_title"]), esc(t["hk_btn"])))


# Le combinazioni arrivano dalle preferenze, cioe' sono testo scritto dall'utente:
# passano tutte da hkEsc() prima di finire in innerHTML.
HK_PANEL_JS = """
function hkEsc(s){ var d=document.createElement('div'); d.textContent=(s==null?'':s); return d.innerHTML; }
function hkPretty(s){
  return String(s).split('+').map(function(x){
    x = x.trim();
    return x.length > 1 ? x.charAt(0).toUpperCase() + x.slice(1) : x.toUpperCase();
  }).join(' + ');
}
function hkRow(key, action, state, cls){
  return '<div class="hkrow"><span class="hkkey">' + hkEsc(hkPretty(key)) + '</span>' +
         '<span class="what">' + hkEsc(HK_DESC[action] || action) + '</span>' +
         '<span class="chip ' + cls + '">' + hkEsc(state) + '</span></div>';
}
function hkClose(){ var m = document.getElementById('hkModal'); if(m) m.classList.remove('open'); }
function hkOpen(){
  var m = document.getElementById('hkModal'); if(!m) return;
  m.classList.add('open');
  var box = document.getElementById('hkRows');
  fetch('/api/hotkeys').then(function(r){ return r.json(); }).then(function(d){
    var act = {}, fail = {};
    (d.active || []).forEach(function(p){ act[p[0]] = 1; });
    (d.failed || []).forEach(function(p){ fail[p[0]] = 1; });
    var rows = (d.configured || []).map(function(p){
      if(act[p[0]])  return hkRow(p[0], p[1], HK_TXT.ok, 'ok');
      if(fail[p[0]]) return hkRow(p[0], p[1], HK_TXT.taken, 'bad');
      return hkRow(p[0], p[1], d.why || HK_TXT.off, '');
    });
    box.innerHTML = rows.length ? rows.join('')
      : '<div class="hkrow"><span class="what">' + HK_TXT.offnote + ' ' + HK_TXT.where + '</span></div>';
    document.getElementById('hkWarn').innerHTML =
      (d.failed && d.failed.length) ? '<div class="hkwarn">' + HK_TXT.thieves + '</div>' : '';
  }).catch(function(){ box.textContent = '\\u2014'; });
}
document.addEventListener('keydown', function(e){
  var tag = ((e.target && e.target.tagName) || '').toLowerCase();
  if(tag === 'input' || tag === 'textarea' || tag === 'select') return;
  if(e.key === '?'){ e.preventDefault(); hkOpen(); }
  else if(e.key === 'Escape'){ hkClose(); }
});
"""


def hk_panel(lg, run_id=None):
    """Il pannello delle scorciatoie, identico su ogni pagina.

    Non e' documentazione incollata: legge /api/hotkeys e dice quali
    combinazioni Windows ha davvero registrato e quali gli ha rubato un altro
    programma. Quel dato non sta in nessun file di testo, e in un file di testo
    non potrebbe starci."""
    t = T[lg]
    where = ('<a href="/session/%s">%s</a>' % (esc(str(run_id)), esc(t["hk_settings"]))
             if run_id else esc(t["hk_settings"]))
    txt = {"ok": t["hk_ok"], "taken": t["hk_taken"], "off": t["hk_state_off"],
           "thieves": t["hk_thieves"], "offnote": t["hk_off_note"], "where": where}
    desc = {a: t["hk_act_" + a] for a in HOTKEY_ACTIONS}
    return ('<div class="hkmodal" id="hkModal" onclick="if(event.target===this)hkClose()">'
            '<div class="hkbox" role="dialog" aria-modal="true" aria-label="%s">'
            '<h2>⌨ %s</h2><div class="intro">%s</div>'
            '<div id="hkRows">%s</div><div id="hkWarn"></div>'
            '<div class="hkfoot"><button onclick="hkClose()">%s</button><span>%s</span></div>'
            '</div></div><script>var HK_DESC=%s;var HK_TXT=%s;%s</script>'
            % (esc(t["hk_panel_title"]), esc(t["hk_panel_title"]), t["hk_panel_intro"],
               esc(t["hk_loading"]), esc(t["hk_close"]), esc(t["hk_restart"]),
               json.dumps(desc, ensure_ascii=False), json.dumps(txt, ensure_ascii=False),
               HK_PANEL_JS))


def page_head(lg, title, run_id, active, subtitle=""):
    t = T[lg]
    return ('<!DOCTYPE html><html lang="%s"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            '<title>%s</title><style>%s</style></head><body>%s'
            '<header><div class="topright">%s%s%s</div><h1>%s</h1>'
            '<p class="sub">%s · <span class="by">%s</span></p></header>'
            '<div class="wrap"><a class="back" href="/">← %s</a>%s'
            % (lg, esc(title), CSS, hk_panel(lg, run_id),
               hk_button(lg),
               modesel(lg, "/%s/%s" % (active_path(active), run_id)),
               langsel(lg, "/%s/%s" % (active_path(active), run_id)),
               esc(title), esc(subtitle), t["by"], t["back"],
               tabs(lg, run_id, active)))


def active_path(active):
    return {"check": "run", "eps": "episodes", "ses": "session"}[active]


def render_episodes(run_id):
    lg, t = lang(), T[lang()]
    d = ROUTES[run_id]
    steps = [s for p in d["phases"] for s in p["steps"]]
    eps = sessions_of(run_id)
    p = [page_head(lg, d["game"], run_id, "eps", t["eps_title"])]
    if not eps:
        p.append(f'<div class="hubnote">{t["no_eps"]}</div>')
    for e in eps:
        marks = [m for m in e["markers"]]
        ntask = len({m["step"] for m in marks if m["kind"] == "done"})
        ntro = len({m["step"] for m in marks if m["kind"] == "done"
                    and m["step"] is not None and 0 <= m["step"] < len(steps)
                    and steps[m["step"]].get("trophy")})
        dur = max([m["tc"] for m in marks] or [0])
        state = (f'<a class="chip ok" href="{esc(e["video_url"])}" target="_blank">▶ {esc(e["video_url"])[:44]} · {t["linked"]}</a>'
                 if e["video_url"] else f'<span class="chip bad">⚠ {t["no_video"]}</span>')
        live = "" if e["ended_at"] else f' <span class="chip ep">● {t["rec"]}</span>'
        p.append('<div class="epcard"><div class="h">'
                 f'<h3>{t["ep"].upper()}ISODIO {e["number"]}' if lg == "it" else
                 '<div class="epcard"><div class="h">' f'<h3>EPISODE {e["number"]}')
        p.append(f'{" — " + esc(e["title"]) if e["title"] else ""}</h3>'
                 f'<span class="meta">{fmt_tc(dur)} · {ntask} task · {ntro} 🏆 · {esc(e["started_at"][:16])}{live}</span>'
                 f'<span class="spacer"></span>{state}</div><div class="b">')
        p.append('<div class="tl">')
        for m in marks:
            if m["kind"] == "session_start":
                lab = "Inizio sessione" if lg == "it" else "Session start"
                p.append(f'<div class="t">{fmt_tc(0)}</div><div class="d">{lab}</div>')
                continue
            if m["kind"] != "done" and m["kind"] != "free":
                continue
            secs = max(0, int(round(m["tc"] - e["video_offset"] - e["lead"])))
            shown = fmt_tc(secs)
            if e["video_url"]:
                shown = f'<a href="{video_link(e["video_url"], secs)}" target="_blank">{shown}</a>'
            if m["kind"] == "free":
                p.append(f'<div class="t">{shown}</div><div class="d">📍 {esc(m["note"] or "—")}</div>')
            else:
                st = steps[m["step"]] if m["step"] is not None and m["step"] < len(steps) else None
                if not st:
                    continue
                txt = L(st, "text", lg)
                tro = next((L(x, "label", lg) for x in st.get("tags", []) if x["type"] == "trophy"), "")
                cls = " tro" if st.get("trophy") else ""
                p.append(f'<div class="t">{shown}</div><div class="d{cls}">'
                         f'{esc(tro if tro else txt[:96])}</div>')
        p.append("</div>")
        p.append(f'<div class="setrow">'
                 f'<button onclick="chapters({e["id"]},1)">📋 {t["chapters"]}</button>'
                 f'<button onclick="chapters({e["id"]},0)">📄 {t["copy_tasks"]}</button>'
                 f'<button class="danger" onclick="delEp({e["id"]})">🗑 {t["del_ep"]}</button>'
                 f'<span id="cp{e["id"]}" style="color:var(--ok)"></span></div>')
        p.append(f'<textarea class="mono" id="ta{e["id"]}" readonly></textarea>')
        p.append("</div></div>")
    p.append(f'<div class="setrow" style="margin:20px 0 4px"><a class="chip ok" style="padding:9px 15px;'
             f'font-size:.9em;text-decoration:none" href="/export/{run_id}">📤 {t["publish"]}</a>'
             f'<span style="max-width:560px">{t["publish_note"]}</span></div>')
    p.append(f'<footer>{t["footer_run"]}</footer></div>')
    p.append("""<script>
var RUN = %s, EPS = %s;
function fmt(s){ s=Math.max(0,Math.round(s)); var h=Math.floor(s/3600),m=Math.floor(s%%3600/60),x=s%%60;
  return (h? h+':'+String(m).padStart(2,'0') : String(m).padStart(2,'0'))+':'+String(x).padStart(2,'0'); }
function chapters(id, onlyTro){
  var e = EPS[id]; if(!e) return;
  var out = ['00:00 Intro'], last = 0;
  e.marks.forEach(function(m){
    if(m.kind !== 'done' && m.kind !== 'free') return;
    if(onlyTro && m.kind === 'done' && !m.trophy) return;
    var s = Math.max(0, Math.round(m.tc - e.off - e.lead));
    if(s <= last) s = last + 1;
    last = s;
    out.push(fmt(s) + ' ' + (m.label || ''));
  });
  var txt = out.join('\\n');
  var ta = document.getElementById('ta'+id); ta.value = txt; ta.select();
  try{ document.execCommand('copy'); }catch(err){}
  if(navigator.clipboard) navigator.clipboard.writeText(txt).catch(function(){});
  document.getElementById('cp'+id).textContent = %s;
  setTimeout(function(){ document.getElementById('cp'+id).textContent=''; }, 2000);
}
function delEp(id){
  if(!confirm('?')) return;
  fetch('/api/session/delete', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({id: id})}).then(function(){ location.reload(); });
}
</script></body></html>""" % (json.dumps(run_id), json.dumps(episodes_js(run_id)), json.dumps(t["copied"])))
    return "\n".join(p)


def episodes_js(run_id):
    lg = lang()
    d = ROUTES[run_id]
    steps = [s for p in d["phases"] for s in p["steps"]]
    out = {}
    for e in sessions_of(run_id):
        marks = []
        for m in e["markers"]:
            if m["kind"] == "free":
                marks.append({"kind": "free", "tc": m["tc"], "label": "📍 " + (m["note"] or ""),
                              "trophy": True})
            elif m["kind"] == "done" and m["step"] is not None and m["step"] < len(steps):
                st = steps[m["step"]]
                tro = next((L(x, "label", lg) for x in st.get("tags", []) if x["type"] == "trophy"), "")
                lab = (tro or L(st, "text", lg))
                lab = re.sub(r"^🏆\s*", "", lab)[:80]
                marks.append({"kind": "done", "tc": m["tc"], "label": lab,
                              "trophy": bool(st.get("trophy"))})
        out[e["id"]] = {"off": e["video_offset"], "lead": e["lead"], "marks": marks}
    return out


# -------------------------------------------------------------- session page
def render_session(run_id):
    lg, t = lang(), T[lang()]
    d = ROUTES[run_id]
    ses = session_row(open_session(run_id)[0]) if open_session(run_id) else None
    p = [page_head(lg, d["game"], run_id, "ses", t["session_cfg"])]
    p.append('<div class="epcard"><div class="b">')
    p.append(f'<div class="setrow"><span>{t["obs_addr"]}</span>'
             f'<input type="text" id="obsUrl" value="{esc(get_pref("obs_url", "ws://127.0.0.1:4455"))}">'
             f'<span>{t["obs_pw"]}</span><input type="password" id="obsPw" value="{esc(get_pref("obs_pass", ""))}">'
             f'<button onclick="testObs()">{t["obs_test"]}</button>'
             f'<span id="obsState" class="chip bad">{t["obs_off"]}</span></div>')
    pref = get_pref("obs_prefer", "auto")
    opts = "".join(f'<option value="{k}"{" selected" if pref == k else ""}>{t["pref_" + k]}</option>'
                   for k in ("auto", "stream", "rec"))
    p.append(f'<div class="setrow"><span>{t["prefer"]}</span>'
             f'<select id="obsPrefer" onchange="savePrefs()" style="background:#0a0c10;border:1px solid var(--line);'
             f'border-radius:6px;color:var(--text);padding:6px 10px;font-family:inherit">{opts}</select></div>')
    p.append("</div></div>")

    p.append(f'<h2 style="font-size:.85em;color:var(--gold);letter-spacing:2px;margin:24px 0 4px;'
             f'text-transform:uppercase;font-weight:500">{t["ep_cfg"]}</h2>')
    p.append('<div class="epcard"><div class="b">')
    if ses:
        p.append(f'<div class="setrow"><span>{t["ep"]} {ses["number"]}</span>'
                 f'<span>{t["ep_title"]}</span><input type="text" id="epTitle" value="{esc(ses["title"])}"></div>')
        p.append(f'<div class="setrow"><span>{t["ep_url"]}</span>'
                 f'<input type="text" id="epUrl" style="min-width:300px" value="{esc(ses["video_url"])}"></div>')
        p.append(f'<div class="setrow"><span>{t["ep_off"]}</span>'
                 f'<input type="number" id="epOff" value="{ses["video_offset"]}"><span>{t["ep_off_u"]}</span></div>')
        p.append(f'<div class="setrow"><span>{t["ep_lead"]}</span>'
                 f'<input type="number" id="epLead" value="{ses["lead"]}"><span>{t["ep_lead_u"]}</span></div>')
        p.append(f'<div class="setrow"><button onclick="saveSes({ses["id"]})">💾 {t["obs_save"]}</button>'
                 f'<span id="sesState" style="color:var(--ok)"></span></div>')
    else:
        p.append(f'<div class="setrow">{t["no_eps"]}</div>')
    p.append("</div></div>")

    # ---- scorciatoie globali -------------------------------------------------
    hk_spec = get_pref("hotkeys", HOTKEYS_DEFAULT)
    hk_on = get_pref("hotkeys_on", "1") == "1"
    p.append(f'<h2 style="font-size:.85em;color:var(--gold);letter-spacing:2px;margin:24px 0 4px;'
             f'text-transform:uppercase;font-weight:500">⌨ {t["hk_sec"]}</h2>')
    p.append('<div class="epcard"><div class="b">')
    if HOTKEY_STATE["active"]:
        rows = " · ".join("<code>%s</code> %s" % (esc(lb), esc(ac)) for lb, ac in HOTKEY_STATE["active"])
        p.append(f'<div class="setrow"><span class="chip ok">● {t["hk_state_on"]}</span><span>{rows}</span></div>')
    else:
        why = HOTKEY_STATE["why"] or "-"
        p.append(f'<div class="setrow"><span class="chip bad">{t["hk_state_off"]}</span>'
                 f'<span>{esc(why)}</span></div>')
    for lb, ac in HOTKEY_STATE["failed"]:
        p.append(f'<div class="setrow"><span class="chip bad">⚠</span>'
                 f'<span><code>{esc(lb)}</code> → {esc(ac)}: combinazione già occupata da un altro programma</span></div>')
    p.append(f'<div class="setrow"><input type="text" id="hkSpec" style="min-width:420px" value="{esc(hk_spec)}">'
             f'<label style="display:flex;gap:6px;align-items:center"><input type="checkbox" id="hkOn"'
             f'{" checked" if hk_on else ""}> on</label>'
             f'<button onclick="saveHk()">💾 {t["hk_save"]}</button>'
             f'<span id="hkState" style="color:var(--ok)"></span></div>')
    p.append(f'<div class="setrow" style="max-width:660px;color:var(--muted)">{t["hk_hint"]}</div>')
    p.append('</div></div>')

    ov = f"http://127.0.0.1:{CUR_PORT[0]}/overlay/{run_id}"
    p.append(f'<h2 style="font-size:.85em;color:var(--gold);letter-spacing:2px;margin:24px 0 4px;'
             f'text-transform:uppercase;font-weight:500">{t["ov_title"]}</h2>')
    p.append('<div class="epcard"><div class="b">')
    p.append(f'<div class="setrow"><input type="text" id="ovUrl" style="min-width:340px" readonly value="{ov}">'
             f'<button onclick="copyOv()">📋 {t["ov_copy"]}</button>'
             f'<a class="chip ep" href="{ov}" target="_blank">anteprima</a></div>')
    p.append(f'<div class="setrow" style="max-width:640px">{t["ov_note"]}</div>')
    p.append(f'<div class="setrow"><a class="btn" style="background:var(--panel2);border:1px solid var(--line);'
             f'border-radius:6px;padding:7px 13px;color:var(--text)" href="/selftest/{run_id}">🩺 {t["diag"]}</a>'
             f'<span>{t["diag_note"][:60]}…</span></div>')
    p.append(f'<div class="setrow"><span>?pos=</span><code>bl</code> / <code>br</code> / <code>top</code> / <code>tr</code>'
             f' · <span>&amp;size=</span><code>s</code>/<code>m</code>/<code>l</code>'
             f' · <span>&amp;pad=</span>margine dai bordi · <span>&amp;w=</span>larghezza max'
             f' · <span>&amp;hold=</span>secondi visibile (<code>0</code> = sempre)'
             f' · <span>&amp;next=0</span> · <span>&amp;progress=0</span></div>')
    p.append(f'<div class="setrow" style="max-width:680px;color:var(--muted);display:block;line-height:1.6">'
             f'<b style="color:var(--gold);font-weight:500">Regola unica: larghezza e altezza della sorgente '
             f'Browser identiche al canvas di OBS</b> (Impostazioni → Video → Risoluzione di base). '
             f'Vale per qualsiasi risoluzione — 1920×1080, 2560×1080, 3440×1440. Non ridimensionare il '
             f'riquadro nella scena: il posizionamento lo fa la pagina, e stirarlo sfoca il testo. '
             f'La larghezza del pannello è il 44% del canvas, quindi si adatta da sola.<br>'
             f'<code>&amp;pad=</code> serve solo se un gioco gira in 16:9 dentro un canvas più largo: '
             f'alza il margine fino a far partire il pannello dove inizia l&#39;immagine '
             f'(su 2560×1080 con gioco 16:9 sono 320&nbsp;px di banda per lato).</div>')
    p.append("</div></div>")
    p.append(f'<footer>{t["footer_run"]}</footer></div>')
    p.append("""<script>
function savePrefs(){
  fetch('/api/pref', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({obs_url: document.getElementById('obsUrl').value,
      obs_pass: document.getElementById('obsPw').value,
      obs_prefer: document.getElementById('obsPrefer').value})});
}
function copyOv(){ var e=document.getElementById('ovUrl'); e.select();
  try{document.execCommand('copy');}catch(x){}
  if(navigator.clipboard) navigator.clipboard.writeText(e.value).catch(function(){}); }
function saveSes(id){
  fetch('/api/session/update', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({id:id, title:document.getElementById('epTitle').value,
      video_url:document.getElementById('epUrl').value,
      video_offset:parseInt(document.getElementById('epOff').value||'0',10),
      lead:parseInt(document.getElementById('epLead').value||'15',10)})})
   .then(function(){ document.getElementById('sesState').textContent='ok ✓';
     setTimeout(function(){document.getElementById('sesState').textContent='';},1800); });
}
function saveHk(){
  var st = document.getElementById('hkState');
  st.style.color = 'var(--muted)'; st.textContent = '…';
  fetch('/api/hotkeys', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({spec: document.getElementById('hkSpec').value,
                          on: document.getElementById('hkOn').checked})})
    .then(function(r){ if(!r.ok) throw 0;
      st.style.color = 'var(--gold)'; st.textContent = 'salvato — riavvia l\\'app per applicarle'; })
    .catch(function(){ st.style.color = 'var(--warn)';
      st.textContent = 'combinazione non valida (serve almeno un modificatore: ctrl / alt / shift)'; });
}
""" + OBS_JS + """
function testObs(){
  savePrefs();
  var st = document.getElementById('obsState');
  st.textContent = '…'; st.className = 'chip';
  obsConnect(document.getElementById('obsUrl').value, document.getElementById('obsPw').value,
    function(ok, info){ st.textContent = ok ? ('● ' + info) : ('✕ ' + info);
                        st.className = ok ? 'chip ok' : 'chip bad'; });
}
</script></body></html>""")
    return "\n".join(p)




# ------------------------------------------------------- guida pubblicabile
EXPORT_CSS = """
:root{--bg:#0d0f14;--panel:#151823;--panel2:#1a1e2c;--line:#2a2f42;--gold:#c8a24a;
--gold-dim:#8a7134;--moon:#7fa8d9;--moon-dim:#4a6a94;--text:#d8d5c8;--muted:#8a8878;
--warn:#c86a4a;--warn-bg:#2a1a14;--ok:#7fc98a;--item:#7fd8d0}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);line-height:1.6;padding:0 0 60px;
font-family:'Roboto','Segoe UI',system-ui,-apple-system,Arial,sans-serif}
a{color:inherit}
.wrap{max-width:900px;margin:0 auto;padding:0 16px}
header{text-align:center;padding:34px 20px 22px;border-bottom:1px solid var(--line);
background:linear-gradient(180deg,#131625,var(--bg))}
header h1{font-size:1.5em;color:var(--gold);letter-spacing:3px;font-weight:500}
header .sub{color:var(--muted);font-style:italic;margin-top:6px}
header .meta{color:var(--moon);font-size:.85em;margin-top:9px}
.bar{display:flex;align-items:center;gap:12px;background:var(--panel);border:1px solid var(--line);
border-radius:10px;padding:14px 18px;margin:20px 0;flex-wrap:wrap}
.bar .n{font-size:1.5em;color:var(--gold);font-variant-numeric:tabular-nums}
.bar .l{font-size:.8em;color:var(--muted);text-transform:uppercase;letter-spacing:1px}
.bar .sep{width:1px;align-self:stretch;background:var(--line)}
h2.sec{font-size:.85em;color:var(--gold);letter-spacing:2px;text-transform:uppercase;
margin:28px 0 10px;font-weight:500;border-bottom:1px solid var(--line);padding-bottom:7px}
.eps{display:grid;gap:8px}
.ep{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 14px;
display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:.9em}
.ep b{color:var(--gold);font-weight:500}
.ep .m{color:var(--muted);font-size:.9em}
.ep a{color:var(--moon);text-decoration:none;border:1px solid var(--moon-dim);
border-radius:5px;padding:2px 9px;font-size:.85em}
.ep a:hover{color:var(--gold);border-color:var(--gold)}
section.phase{background:var(--panel);border:1px solid var(--line);border-radius:10px;
margin:14px 0;overflow:hidden}
.ph{display:flex;gap:12px;align-items:center;padding:12px 16px;background:var(--panel2)}
.ph .num{color:var(--moon);font-size:.78em;letter-spacing:2px}
.ph h3{font-size:1em;color:var(--gold);font-weight:500;flex:1}
.ph .mini{font-size:.8em;color:var(--muted)}
.body{padding:4px 16px 12px}
.note{font-size:.85em;color:var(--muted);font-style:italic;padding:8px 2px 10px;
border-bottom:1px dashed var(--line);margin-bottom:4px}
.step{display:flex;gap:11px;padding:9px 4px;border-bottom:1px solid #1d2130;align-items:flex-start}
.step:last-child{border-bottom:none}
.step .mk{flex-shrink:0;width:18px;text-align:center;color:var(--ok)}
.step.todo .mk{color:#3a3f52}
.step .tx{flex:1;font-size:.93em}
.step .loc{display:block;font-size:.83em;color:var(--muted)}
.step.done .tx{color:#8a8878}
.cap{color:var(--item);font-weight:500}
.tag{display:inline-block;font-size:.68em;letter-spacing:1px;padding:1px 7px;border-radius:4px;margin-left:6px}
.tag.trophy{background:#2a2413;color:var(--gold);border:1px solid var(--gold-dim)}
.tag.coll{background:#221d10;color:var(--gold);border:1px dashed var(--gold-dim)}
.tag.quest{background:#141d2a;color:var(--moon);border:1px solid var(--moon-dim)}
.tag.miss{background:var(--warn-bg);color:var(--warn);border:1px solid #4a2a1e}
.tag.build{background:#14241a;color:var(--ok);border:1px solid #2e5a3a}
.at{display:inline-block;font-size:.72em;letter-spacing:.5px;padding:2px 8px;border-radius:5px;
margin-left:8px;white-space:nowrap;background:#161d2c;border:1px solid var(--moon-dim);
color:var(--moon);text-decoration:none}
.at:hover{background:#1d2740;border-color:var(--moon);color:#a8c8e8}
.at .epn{color:var(--gold);font-weight:700}
.rules{background:var(--warn-bg);border:1px solid #4a2a1e;border-radius:10px;padding:14px 20px;margin:16px 0}
.rules h3{color:var(--warn);font-size:.82em;letter-spacing:2px;text-transform:uppercase;
margin:10px 0 8px;font-weight:500}
.rules ul{list-style:none}
.rules li{position:relative;padding:5px 0 5px 18px;font-size:.9em}
.rules li::before{content:"\\25b8";position:absolute;left:0;color:var(--warn);opacity:.8}
.rules .bx li{color:var(--ok)}
.rules .bx li::before{color:var(--ok)}
.rules .bx .bh{color:#a8e6b4;font-weight:700}
.rules .bx .bh::after{content:" \\2014 ";color:var(--muted);font-weight:400}
footer{text-align:center;color:var(--muted);font-size:.8em;padding:28px 16px;font-style:italic}
@media print{body{background:#fff;color:#111}header{background:none}}
"""


def render_export(run_id):
    lg, t = lang(), T[lang()]
    d = ROUTES[run_id]
    steps = [(pi, ph, st) for pi, ph in enumerate(d["phases"]) for st in ph["steps"]]
    bits = get_bits(run_id, d["_steps"])
    stamps = step_stamps(run_id)
    eps = sorted(sessions_of(run_id), key=lambda e: e["number"])
    done = sum(1 for c in bits if c == "1")
    flags = [bool(st.get("trophy")) for _, _, st in steps]
    tdone = sum(1 for i, c in enumerate(bits) if c == "1" and flags[i])
    when = datetime.datetime.now().strftime("%d/%m/%Y")
    IT = lg == "it"

    p = ['<!DOCTYPE html>', '<html lang="%s">' % lg, '<head><meta charset="UTF-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
         '<title>%s — %s</title>' % (esc(d["game"]), "Guida" if IT else "Guide"),
         '<style>%s</style></head>' % EXPORT_CSS,
         '<!--',
         '   Questa pagina e\' una FOTOGRAFIA della run al %s.' % when if IT
         else '   This page is a SNAPSHOT of the run taken on %s.' % when,
         '   E\' HTML semplice: puoi modificarla a mano con un editor di testo.' if IT
         else '   It is plain HTML: edit it by hand with any text editor.',
         '   I link ai video hanno la forma  https://youtu.be/ID?t=SECONDI' if IT
         else '   Video links look like  https://youtu.be/ID?t=SECONDS',
         '-->', '<body>']
    p.append('<header><h1>%s</h1>'
             '<p class="sub">%s · <span style="color:var(--gold)">%s</span></p>'
             '<p class="meta">%s %s</p></header>'
             % (esc(d["game"]).upper(),
                "Guida cliccabile della run" if IT else "Clickable run guide",
                t["by"], "Fotografia del" if IT else "Snapshot taken", when))
    p.append('<div class="wrap">')
    p.append('<div class="bar"><span class="n">%d/%d</span><span class="l">%s</span><span class="sep"></span>'
             '<span class="n">%d/%d</span><span class="l">%s</span><span class="sep"></span>'
             '<span class="n">%d</span><span class="l">%s</span></div>'
             % (tdone, d["_tsteps"], "trofei" if IT else "trophies",
                done, d["_steps"], "passi" if IT else "steps",
                len([e for e in eps if e["video_url"]]), "episodi" if IT else "episodes"))

    linked = [e for e in eps if e["video_url"]]
    if linked:
        p.append('<h2 class="sec">%s</h2><div class="eps">' % ("Gli episodi" if IT else "The episodes"))
        for e in linked:
            n_done = len({m["step"] for m in e["markers"] if m["kind"] == "done"})
            p.append('<div class="ep"><b>%s %d</b>%s<span class="m">%s %s</span>'
                     '<span style="flex:1"></span><a href="%s" target="_blank">%s</a></div>'
                     % ("EPISODIO" if IT else "EPISODE", e["number"],
                        (" — " + esc(e["title"])) if e["title"] else "",
                        n_done, "task", esc(e["video_url"]), "guarda ▶" if IT else "watch ▶"))
        p.append('</div>')

    rules = L(d, "golden_rules", lg) or d["golden_rules"]
    bullets = (d.get("build_bullets_it") if lg == "it" else None) or d.get("build_bullets") or []
    p.append('<h2 class="sec">%s</h2><div class="rules">'
             % (t["notes_sec"].replace("&amp;", "&")))
    p.append('<h3>%s</h3><ul>' % t["rules_h"])
    for r in rules:
        p.append("<li>%s</li>" % hl(r))
    p.append('</ul>')
    if bullets:
        p.append('<h3>%s</h3><ul class="bx">' % t["build_h"])
        for bl in bullets:
            p.append('<li><span class="bh">%s</span>%s</li>' % (esc(bl["h"]), hl(bl["t"])))
        p.append('</ul>')
    p.append('</div>')

    p.append('<h2 class="sec">%s</h2>' % ("Il percorso" if IT else "The route"))
    n = 0
    for pi, ph in enumerate(d["phases"]):
        cnt = len(ph["steps"])
        dn = sum(1 for j in range(n, n + cnt) if bits[j] == "1")
        p.append('<section class="phase"><div class="ph"><span class="num">P%d</span>'
                 '<h3>%s</h3><span class="mini">%d/%d</span></div><div class="body">'
                 % (pi + 1, esc(L(ph, "title", lg)), dn, cnt))
        note = L(ph, "note", lg)
        if note:
            p.append('<div class="note">%s</div>' % hl(note))
        for st in ph["steps"]:
            ok = bits[n] == "1"
            tags = "".join('<span class="tag %s">%s</span>' % (x["type"], esc(L(x, "label", lg)))
                           for x in st.get("tags", []))
            at = ""
            sm = stamps.get(n, {})
            dnm = sm.get("done")
            if dnm and dnm.get("url"):
                at = ('<a class="at" href="%s" target="_blank"><span class="epn">%s %d</span> · %s ▶</a>'
                      % (video_link(dnm["url"], dnm["t"]), t["ep"], dnm["ep"], fmt_tc(dnm["t"])))
            p.append('<div class="step %s"><span class="mk">%s</span><span class="tx">%s%s%s'
                     '<span class="loc">%s</span></span></div>'
                     % ("done" if ok else "todo", "&#10003;" if ok else "&#9675;",
                        hl(L(st, "text", lg)), tags, at, esc(L(st, "loc", lg))))
            n += 1
        p.append('</div></section>')

    p.append('</div><footer>%s · %s</footer></body></html>'
             % (esc(t["footer_run"]),
                "pagina generata da Platinum Hub" if IT else "page generated by Platinum Hub"))
    return "\n".join(p)


# ---------------------------------------------------------------- diagnostics
def render_selftest(run_id):
    lg, t = lang(), T[lang()]
    d = ROUTES[run_id]
    p = [page_head(lg, d["game"], run_id, "ses", t["diag"])]
    p.append('<div class="epcard"><div class="b">')
    p.append(f'<div class="setrow" style="max-width:700px">{t["diag_note"]}</div>')
    p.append(f'<div class="setrow"><button onclick="runDiag()">🩺 {t["diag_run"]}</button>'
             f'<button onclick="copyDiag()">📋 {t["diag_copy"]}</button>'
             f'<span id="dState" style="color:var(--ok)"></span></div>')
    p.append('<textarea class="mono" id="dOut" style="min-height:420px" readonly></textarea>')
    p.append('</div></div>')
    p.append(f'<footer>{t["footer_run"]}</footer></div>')
    cfg = {"run": run_id, "obs_url": get_pref("obs_url", "ws://127.0.0.1:4455"),
           "obs_pass": get_pref("obs_pass", ""), "prefer": get_pref("obs_prefer", "auto"),
           "port": CUR_PORT[0], "saved": t["diag_save"]}
    p.append("<script>\nvar D = " + json.dumps(cfg, ensure_ascii=False) + ";\n" + OBS_JS + DIAG_JS
             + "\n</script></body></html>")
    return "\n".join(p)


DIAG_JS = r"""
var LOG = [];
function say(ok, label, detail){
  var mark = ok === true ? '[ OK ]' : (ok === false ? '[FAIL]' : '[ .. ]');
  LOG.push(mark + '  ' + label + (detail ? '  ->  ' + detail : ''));
  document.getElementById('dOut').value = LOG.join('\n');
}
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }

async function runDiag(){
  LOG = []; document.getElementById('dState').textContent = '';
  var stamp = new Date().toISOString().replace('T',' ').slice(0,19);
  LOG.push('PLATINUM HUB - DIAGNOSTICA  ' + stamp);
  LOG.push('run: ' + D.run + '   porta: ' + D.port);
  LOG.push('browser: ' + navigator.userAgent.slice(0, 110));
  LOG.push(''.padEnd(66, '-'));

  /* 1 - server e dati */
  try{
    var sum = await (await fetch('/api/summary')).json();
    say(true, '1. Server e route', sum.length + ' run caricate');
    sum.forEach(function(r){
      LOG.push('        ' + r.game.padEnd(30) + r.steps_done + '/' + r.steps_total +
               ' passi, ' + r.trophies_done + '/' + r.trophies_total + ' trofei');
    });
  }catch(e){ say(false, '1. Server e route', String(e)); }

  /* 2 - font */
  try{ say(document.fonts.check('16px Roboto'), '2. Font Roboto', 'incorporato'); }
  catch(e){ say(false, '2. Font Roboto', String(e)); }

  /* 3 - OBS */
  OBS.prefer = D.prefer;
  var obsInfo = await new Promise(function(res){
    var done = false;
    obsConnect(D.obs_url, D.obs_pass, function(ok, info){ if(!done){ done = true; res({ok:ok, info:info}); } });
    setTimeout(function(){ if(!done){ done = true; res({ok:false, info:'nessuna risposta'}); } }, 6000);
  });
  say(obsInfo.ok, '3. Connessione OBS', D.obs_url + '  ' + obsInfo.info);
  if(!obsInfo.ok){
    LOG.push('        Controlla: OBS aperto, Strumenti > Impostazioni WebSocket abilitato,');
    LOG.push('        porta 4455, password corretta nella scheda Sessione.');
  }

  /* 4 - timecode che avanza */
  if(obsInfo.ok){
    await sleep(1400);
    var a = obsTime(); var aRec = OBS.rec, aStr = OBS.str;
    await sleep(2600);
    var b = obsTime();
    LOG.push('        registrazione attiva: ' + aRec + '   diretta attiva: ' + aStr);
    if(!a || !b){
      say(false, '4. Timecode', 'nessun output attivo: avvia una registrazione o una diretta di prova');
    } else {
      var dt = b.tc - a.tc;
      say(dt > 1.5 && dt < 6, '4. Timecode ' + b.kind,
          a.tc.toFixed(1) + 's -> ' + b.tc.toFixed(1) + 's  (avanzato di ' + dt.toFixed(1) + 's in ~2.6s)');
    }
  } else { say(null, '4. Timecode', 'saltato'); }

  /* 5 - giro completo sessione + marker sul database */
  var sid = null;
  try{
    var r = await (await fetch('/api/session/start', {method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({run: D.run, source: obsInfo.ok ? 'obs' : 'clock', title: '__DIAGNOSTICA__'})})).json();
    sid = r.session.id;
    var tc = (obsTime() ? obsTime().tc : 42);
    await fetch('/api/marker', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({run: D.run, session: sid, step: 0, kind: 'done', tc: tc})});
    await fetch('/api/marker', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({run: D.run, session: sid, step: 1, kind: 'start', tc: tc + 1})});
    var eps = await (await fetch('/api/episodes?run=' + D.run)).json();
    var mine = eps.filter(function(e){ return e.id === sid; })[0];
    var kinds = mine ? mine.markers.map(function(m){ return m.kind; }).join(',') : '';
    say(kinds === 'session_start,done,start', '5. Sessione e marker su SQLite', kinds || 'nessun marker');
    LOG.push('        tc scritto: ' + tc.toFixed(1) + 's   (' + (obsInfo.ok ? 'da OBS' : 'cronometro interno') + ')');
  }catch(e){ say(false, '5. Sessione e marker su SQLite', String(e)); }

  /* 6 - link al video */
  try{
    await fetch('/api/session/update', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({id: sid, video_url: 'https://youtu.be/TEST', video_offset: 0, lead: 5})});
    var html = await (await fetch('/run/' + D.run)).text();
    say(html.indexOf('youtu.be/TEST?t=') >= 0, '6. Link nella checklist',
        'targhetta EP con ?t= generata');
  }catch(e){ say(false, '6. Link nella checklist', String(e)); }

  /* 7 - overlay */
  try{
    var cur = await (await fetch('/api/current?run=' + D.run)).json();
    say(!!cur.current, '7. Overlay - task corrente',
        cur.current ? cur.current.text.slice(0, 62) : 'nessuno');
    var ov = await (await fetch('/overlay/' + D.run)).text();
    say(ov.indexOf('id="txt"') >= 0, '7b. Pagina overlay',
        'http://127.0.0.1:' + D.port + '/overlay/' + D.run + '  (' + ov.length + ' byte)');
  }catch(e){ say(false, '7. Overlay', String(e)); }

  /* pulizia */
  try{
    if(sid){ await fetch('/api/session/delete', {method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify({id: sid})}); }
    say(true, '8. Pulizia', 'sessione di prova eliminata');
  }catch(e){ say(false, '8. Pulizia', String(e)); }

  LOG.push(''.padEnd(66, '-'));
  var fails = LOG.filter(function(l){ return l.indexOf('[FAIL]') === 0; }).length;
  LOG.push(fails === 0 ? 'TUTTO OK - la catena funziona da cima a fondo.'
                       : fails + ' controllo/i falliti: vedi le righe [FAIL] qui sopra.');
  document.getElementById('dOut').value = LOG.join('\n');

  var res = await (await fetch('/api/selftest', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({text: LOG.join('\n')})})).json();
  document.getElementById('dState').textContent = res.ok ? D.saved : '';
}
function copyDiag(){
  var e = document.getElementById('dOut'); e.select();
  try{ document.execCommand('copy'); }catch(x){}
  if(navigator.clipboard) navigator.clipboard.writeText(e.value).catch(function(){});
}
"""

def render_404():
    lg = lang()
    return ('<!DOCTYPE html><html><head><meta charset="UTF-8"><title>404</title><style>' + CSS +
            f'</style></head><body><header><h1>404</h1><p class="sub">{T[lg]["notfound"]}</p></header>'
            f'<div class="wrap"><a class="back" href="/">← {T[lg]["back"]}</a></div></body></html>')


# ---------------------------------------------------------------------- server
class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "PlatinumHub/" + VERSION

    def log_message(self, fmt, *a):
        pass

    def _send(self, body, ctype="text/html; charset=utf-8", code=200, extra=None):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj, code=200):
        self._send(json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8", code)

    def _redirect(self, to):
        self.send_response(303)
        self.send_header("Location", to)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        path, q = u.path, urllib.parse.parse_qs(u.query)

        if path == "/":
            return self._send(render_home())

        if path.startswith("/lang/"):
            code = path[6:].strip("/")
            if code in ("it", "en"):
                set_pref("lang", code)
            nxt = (q.get("next") or ["/"])[0]
            if not nxt.startswith("/") or nxt.startswith("//"):
                nxt = "/"
            return self._redirect(nxt)

        if path.startswith("/run/"):
            rid = path[5:].strip("/")
            if rid in ROUTES:
                return self._send(render_run(rid))
            return self._send(render_404(), code=404)

        if path == "/api/progress":
            rid = (q.get("run") or [""])[0]
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            con = db()
            row = con.execute("SELECT updated_at FROM progress WHERE run_id=?", (rid,)).fetchone()
            con.close()
            return self._json({"run": rid, "bits": get_bits(rid, ROUTES[rid]["_steps"]),
                               "updated_at": row[0] if row else None, "total": ROUTES[rid]["_steps"]})

        if path == "/api/notes":
            rid = (q.get("run") or [""])[0]
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            return self._json({"run": rid, "body": get_note(rid)})

        if path.startswith("/mode/"):
            code = path[6:].strip("/")
            if code in ("gamer", "streamer"):
                set_pref("mode", code)
            nxt = (q.get("next") or ["/"])[0]
            return self._redirect(nxt if (nxt.startswith("/")
                                          and not nxt.startswith("//")) else "/")

        if path.startswith("/episodes/"):
            rid = path[10:].strip("/")
            if rid in ROUTES:
                return self._send(render_episodes(rid))
            return self._send(render_404(), code=404)

        if path.startswith("/session/"):
            rid = path[9:].strip("/")
            if rid in ROUTES:
                return self._send(render_session(rid))
            return self._send(render_404(), code=404)

        if path.startswith("/export/"):
            rid = path[8:].strip("/")
            if rid not in ROUTES:
                return self._send(render_404(), code=404)
            name = "%s - %s (by Voloirex).html" % (
                "Guida" if lang() == "it" else "Guide",
                re.sub(r"[^A-Za-z0-9 +.-]", "", ROUTES[rid]["game"]))
            return self._send(render_export(rid), extra={
                "Content-Disposition": 'attachment; filename="%s"' % name})

        if path.startswith("/selftest/"):
            rid = path[10:].strip("/")
            if rid in ROUTES:
                return self._send(render_selftest(rid))
            return self._send(render_404(), code=404)

        if path.startswith("/overlay/"):
            rid = path[9:].strip("/")
            if rid in ROUTES:
                return self._send(render_overlay(rid, q))
            return self._send(render_404(), code=404)

        if path == "/api/current":
            rid = (q.get("run") or [""])[0]
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            st = current_state(rid)
            st["toast"] = get_toast(rid)
            return self._json(st)

        if path == "/api/episodes":
            rid = (q.get("run") or [""])[0]
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            return self._json(sessions_of(rid))

        if path == "/api/pending":
            rid = (q.get("run") or [""])[0]
            return self._json({"cmds": take_cmds(), "run": rid})

        if path == "/api/version":
            return self._json({"version": VERSION, "latest": UPDATE["latest"],
                               "url": UPDATE["url"], "checked": UPDATE["checked"],
                               "check_on": get_pref("update_check", "1") == "1"})

        if path == "/update/off":
            set_pref("update_check", "0")
            UPDATE["latest"] = ""
            return self._redirect("/")

        if path == "/update/on":
            set_pref("update_check", "1")
            threading.Thread(target=check_update, daemon=True).start()
            return self._redirect("/")

        if path == "/changelog":
            return self._send(render_changelog())

        if path == "/api/hotkeys":
            spec = get_pref("hotkeys", HOTKEYS_DEFAULT)
            # "configured" e' la lista che l'utente ha impostato, indipendente da
            # quello che Windows ha poi accettato di registrare: serve al pannello
            # per mostrare le scorciatoie anche quando sono spente o siamo su Linux,
            # senza rifare in JavaScript il lavoro di parse_hotkeys().
            return self._json({"spec": spec,
                               "on": get_pref("hotkeys_on", "1") == "1",
                               "configured": [[label, action]
                                              for _m, _vk, action, label in parse_hotkeys(spec)],
                               "active": HOTKEY_STATE["active"],
                               "failed": HOTKEY_STATE["failed"],
                               "why": HOTKEY_STATE["why"],
                               "platform": sys.platform})

        if path == "/api/prefs":
            return self._json({"obs_url": get_pref("obs_url", "ws://127.0.0.1:4455"),
                               "obs_pass": get_pref("obs_pass", ""),
                               "obs_prefer": get_pref("obs_prefer", "auto"),
                               "mode": mode()})

        if path == "/api/summary":
            out = []
            for r in RUNS:
                if r["id"] in ROUTES:
                    done, total, td, tt, when = stats(r["id"])
                    out.append({"run": r["id"], "game": ROUTES[r["id"]]["game"], "steps_done": done,
                                "steps_total": total, "trophies_done": td, "trophies_total": tt,
                                "updated_at": when})
            return self._json(out)

        if path == "/api/export":
            con = db()
            payload = {
                "app": "PlatinumHub", "version": 2,
                "exported_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "progress": [{"run_id": a, "bits": b, "updated_at": c}
                             for a, b, c in con.execute("SELECT run_id,bits,updated_at FROM progress")],
                "notes": [{"run_id": a, "body": b, "updated_at": c}
                          for a, b, c in con.execute("SELECT run_id,body,updated_at FROM notes")],
                "prefs": {a: b for a, b in con.execute("SELECT k,v FROM prefs")},
            }
            con.close()
            fname = "platinum-backup-%s.json" % datetime.datetime.now().strftime("%Y%m%d-%H%M")
            return self._send(json.dumps(payload, ensure_ascii=False, indent=1),
                              "application/json; charset=utf-8",
                              extra={"Content-Disposition": 'attachment; filename="%s"' % fname})

        if path.startswith("/fonts/"):
            name = os.path.basename(path)
            fp = os.path.join(BASE, "fonts", name)
            if name.endswith(".woff2") and os.path.isfile(fp):
                with open(fp, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "font/woff2")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "public, max-age=604800")
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            return self._send(b"", "font/woff2", 404)

        if path == "/favicon.ico":
            return self._send(b"", "image/x-icon")
        return self._send(render_404(), code=404)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:
            return self._json({"error": "bad payload"}, 400)
        # Un JSON valido ma che non e' un oggetto ([1,2], "x", 42, null) non ha
        # .get(): senza questo controllo il gestore esplode a meta' strada e la
        # connessione si chiude senza risposta.
        if not isinstance(payload, dict):
            return self._json({"error": "body must be a JSON object"}, 400)
        try:
            return self._route_post(u, payload)
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            # campi presenti ma di tipo sbagliato ("lead": "molto", "step": {}):
            # e' un errore del chiamante, non del server. Meglio un 400 onesto
            # che un traceback e una connessione chiusa a meta'.
            return self._json({"error": "bad field: %s" % e.__class__.__name__}, 400)

    def _route_post(self, u, payload):

        if u.path == "/api/session/start":
            rid = payload.get("run")
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            con = db()
            con.execute("UPDATE sessions SET ended_at=datetime('now') "
                        "WHERE run_id=? AND ended_at IS NULL", (rid,))
            n = con.execute("SELECT COALESCE(MAX(number),0)+1 FROM sessions WHERE run_id=?",
                            (rid,)).fetchone()[0]
            cur = con.execute("""INSERT INTO sessions(run_id,number,title,started_at,source,lead)
                                 VALUES(?,?,?,datetime('now'),?,?)""",
                              (rid, n, str(payload.get("title") or "")[:120],
                               "obs" if payload.get("source") == "obs" else "clock",
                               int(15 if payload.get("lead") is None else payload.get("lead"))))
            sid = cur.lastrowid
            con.execute("""INSERT INTO markers(session_id,run_id,step,kind,tc,wall)
                           VALUES(?,?,NULL,'session_start',0,datetime('now'))""", (sid, rid))
            con.commit()
            con.close()
            return self._json({"ok": True, "session": session_row(sid)})

        if u.path == "/api/session/stop":
            con = db()
            con.execute("UPDATE sessions SET ended_at=datetime('now') WHERE id=?",
                        (int(payload.get("id") or 0),))
            con.commit()
            con.close()
            return self._json({"ok": True})

        if u.path == "/api/session/update":
            sid = int(payload.get("id") or 0)
            con = db()
            for k, col, cast in (("title", "title", str), ("video_url", "video_url", str),
                                 ("video_offset", "video_offset", int), ("lead", "lead", int)):
                if k in payload:
                    con.execute(f"UPDATE sessions SET {col}=? WHERE id=?",
                                (cast(payload[k]), sid))
            con.commit()
            con.close()
            return self._json({"ok": True, "session": session_row(sid)})

        if u.path == "/api/session/delete":
            sid = int(payload.get("id") or 0)
            con = db()
            con.execute("DELETE FROM markers WHERE session_id=?", (sid,))
            con.execute("DELETE FROM sessions WHERE id=?", (sid,))
            con.commit()
            con.close()
            return self._json({"ok": True})

        if u.path == "/api/cmd":
            action = str(payload.get("action") or "").lower()
            if not push_cmd(action, payload.get("run")):
                return self._json({"error": "bad action"}, 400)
            return self._json({"ok": True, "action": action})

        if u.path == "/api/toast":
            rid = payload.get("run")
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            set_toast(rid, payload.get("text") or "")
            return self._json({"ok": True})

        if u.path == "/api/hotkeys":
            spec = str(payload.get("spec") or HOTKEYS_DEFAULT)[:300]
            if not parse_hotkeys(spec):
                return self._json({"error": "no valid combo"}, 400)
            set_pref("hotkeys", spec)
            set_pref("hotkeys_on", "1" if payload.get("on", True) else "0")
            return self._json({"ok": True, "spec": spec, "restart": True})

        if u.path == "/api/marker":
            rid = payload.get("run")
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            sid = payload.get("session")
            if not sid:
                return self._json({"error": "no session"}, 400)
            kind = payload.get("kind")
            if kind not in ("start", "done", "free"):
                return self._json({"error": "bad kind"}, 400)
            step = payload.get("step")
            step = int(step) if step is not None else None
            con = db()
            if step is not None:
                con.execute("DELETE FROM markers WHERE session_id=? AND step=? AND kind=?",
                            (sid, step, kind))
            con.execute("""INSERT INTO markers(session_id,run_id,step,kind,tc,wall,note)
                           VALUES(?,?,?,?,?,datetime('now'),?)""",
                        (sid, rid, step, kind, float(payload.get("tc") or 0),
                         str(payload.get("note") or "")[:300]))
            con.commit()
            con.close()
            return self._json({"ok": True})

        if u.path == "/api/run/reset":
            rid = payload.get("run")
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            con = db()
            n_mark = con.execute("SELECT COUNT(*) FROM markers WHERE run_id=?", (rid,)).fetchone()[0]
            n_ses = con.execute("SELECT COUNT(*) FROM sessions WHERE run_id=?", (rid,)).fetchone()[0]
            n_note = con.execute("SELECT COUNT(*) FROM notes WHERE run_id=?", (rid,)).fetchone()[0]
            con.execute("DELETE FROM markers WHERE run_id=?", (rid,))
            con.execute("DELETE FROM sessions WHERE run_id=?", (rid,))
            con.execute("DELETE FROM notes WHERE run_id=?", (rid,))
            con.execute("DELETE FROM progress WHERE run_id=?", (rid,))
            con.execute("DELETE FROM prefs WHERE k=?", ("cur_" + rid,))
            con.commit()
            con.close()
            return self._json({"ok": True, "markers": n_mark, "sessions": n_ses, "notes": n_note})

        if u.path == "/api/marker/delete":
            con = db()
            con.execute("DELETE FROM markers WHERE session_id=? AND step=?",
                        (int(payload.get("session") or 0), int(payload.get("step") or -1)))
            con.commit()
            con.close()
            return self._json({"ok": True})

        if u.path == "/api/current":
            rid = payload.get("run")
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            set_pref("cur_" + rid, str(int(payload.get("step") or 0)))
            return self._json({"ok": True})

        if u.path == "/api/selftest":
            txt = str(payload.get("text") or "")[:60000]
            try:
                with open(os.path.join(BASE, "diagnostica.txt"), "w", encoding="utf-8",
                          newline="") as f:
                    f.write(txt.replace("\n", "\r\n"))
                return self._json({"ok": True, "path": os.path.join(BASE, "diagnostica.txt")})
            except Exception as e:
                return self._json({"ok": False, "error": str(e)}, 500)

        if u.path == "/api/pref":
            for k in ("hide_done", "only_miss", "lang", "mode", "obs_url", "obs_pass",
                      "obs_prefer", "overlay_style"):
                if k in payload:
                    set_pref(k, str(payload[k])[:200])
            return self._json({"ok": True})

        if u.path == "/api/import":
            if not isinstance(payload, dict) or payload.get("app") != "PlatinumHub":
                return self._json({"error": "not a Platinum Hub backup"}, 400)
            rows = payload.get("progress") or []
            for row in rows:
                rid = row.get("run_id")
                bits = str(row.get("bits") or "")
                if rid in ROUTES and all(c in "01" for c in bits):
                    total = ROUTES[rid]["_steps"]
                    set_bits(rid, (bits + "0" * total)[:total])
            for row in payload.get("notes") or []:
                if row.get("run_id") in ROUTES:
                    set_note(row["run_id"], str(row.get("body") or "")[:100000])
            prefs = payload.get("prefs") or {}
            if prefs.get("lang") in ("it", "en"):
                set_pref("lang", prefs["lang"])
            return self._json({"ok": True, "runs": len(rows)})

        rid = payload.get("run")
        if rid not in ROUTES:
            return self._json({"error": "unknown run"}, 404)

        if u.path == "/api/progress":
            bits = str(payload.get("bits") or "")
            if not all(c in "01" for c in bits):
                return self._json({"error": "bits must be 0/1"}, 400)
            total = ROUTES[rid]["_steps"]
            bits = (bits + "0" * total)[:total]
            set_bits(rid, bits)
            return self._json({"ok": True, "saved": sum(1 for c in bits if c == "1"), "total": total})

        if u.path == "/api/notes":
            set_note(rid, str(payload.get("body") or "")[:100000])
            return self._json({"ok": True})

        return self._json({"error": "unknown endpoint"}, 404)


class Server(socketserver.ThreadingTCPServer):
    # SO_REUSEADDR non vuol dire la stessa cosa sui due sistemi. Su Windows
    # permette a un secondo processo di legarsi a una porta GIA' in ascolto:
    # pick_port() non vedrebbe mai OSError, resterebbe sull'8787 e due istanze
    # si spartirebbero le richieste a caso -- si crede di provare la versione
    # nuova e si sta guardando la vecchia. Su POSIX serve invece a non farsi
    # rifiutare il bind dai TIME_WAIT dopo un riavvio, quindi la si tiene.
    allow_reuse_address = os.name != "nt"
    daemon_threads = True


def pick_port():
    for port in range(PORT_START, PORT_START + 25):
        try:
            return Server(("127.0.0.1", port), Handler), port
        except OSError:
            continue
    return None, None


def main():
    print()
    print("  =========================================")
    print("   PLATINUM HUB v%s  ·  by Voloirex" % VERSION)
    print("  =========================================")
    load_routes()
    if not ROUTES:
        print("  ERRORE / ERROR: nessun file route in", DATA)
        input("  Invio per chiudere / Enter to close...")
        return
    moved = migrate_legacy_db()
    db()
    for r in RUNS:
        if r["id"] in ROUTES:
            done, total, td, tt, _ = stats(r["id"])
            print(f"   · {ROUTES[r['id']]['game']:<30} {done:>3}/{total:<4} passi   {td:>2}/{tt:<3} trofei")
    srv, port = pick_port()
    if srv is None:
        print("  ERRORE: nessuna porta libera tra %d e %d." % (PORT_START, PORT_START + 24))
        input("  Invio per chiudere...")
        return
    CUR_PORT[0] = port
    url = "http://127.0.0.1:%d/" % port
    print()
    print("   Apri / Open:", url)
    print("   Database progressi:", DB)
    if moved:
        print("   (progressi della versione precedente importati da %s)" % moved)
    threading.Thread(target=check_update, daemon=True).start()
    start_hotkeys(port)
    if HOTKEY_STATE["active"]:
        print("   Scorciatoie globali attive (funzionano anche a gioco aperto):")
        for label, action in HOTKEY_STATE["active"]:
            print("      %-16s %s" % (label, {"rec": "avvia / chiudi registrazione + episodio",
                                              "next": "task fatto, passa al prossimo",
                                              "undo": "annulla l'ultima spunta",
                                              "mark": "segnaposto libero"}.get(action, action)))
        for label, action in HOTKEY_STATE["failed"]:
            print("      %-16s NON registrata (combinazione gia' occupata)" % label)
    elif HOTKEY_STATE["why"]:
        print("   Scorciatoie globali: %s" % HOTKEY_STATE["why"])
    print("   Lascia questa finestra aperta mentre usi l'hub.")
    print("   Chiudila (o Ctrl+C) quando hai finito.")
    print()
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n   Ciao. I progressi sono salvati.")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
