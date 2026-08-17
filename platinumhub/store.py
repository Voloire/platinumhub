# -*- coding: utf-8 -*-
"""SQLite: schema, migrazione v1->v2, progressi per sid, sessioni, marker, preferenze."""

import re
import sqlite3

from .config import DB
from .i18n import L
from .routes import ROUTES


# ---------------------------------------------------------------------- SQLite
# I progressi si salvano PER SID, non per posizione: ogni spunta e' una riga
# (run_id, sid). Aggiornare una route non puo' piu' spostare le spunte di
# nessuno, e una riga il cui sid non esiste piu' nella route resta nel database
# (orfana ma intatta): un progresso non si cancella mai per effetto collaterale.
SID_OK = re.compile(r"^s\d{3,}$")


def db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS progress_steps(
        run_id TEXT NOT NULL, sid TEXT NOT NULL,
        done_at TEXT NOT NULL DEFAULT (datetime('now')),
        PRIMARY KEY(run_id, sid))""")
    con.execute("""CREATE TABLE IF NOT EXISTS progress_runs(
        run_id TEXT PRIMARY KEY,
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
        sid TEXT,
        kind TEXT NOT NULL,
        tc REAL NOT NULL,
        wall TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT '')""")
    con.commit()
    upgrade_v1_db(con)
    # DOPO la migrazione: in un database vecchio la colonna sid nasce solo li',
    # e creare l'indice prima farebbe morire l'avvio con "no such column".
    con.execute("CREATE INDEX IF NOT EXISTS ix_mark2 ON markers(session_id, sid, kind)")
    con.commit()
    return con


def upgrade_v1_db(con):
    """Converte in blocco un database 3.x/4.x (progressi posizionali) al formato per sid.

    La mappa posizione->sid e' deterministica: la struttura delle route 3.x/4.x
    e' quella dei JSON in bundle, e i sid sono stati assegnati proprio in
    quell'ordine. La tabella vecchia non si cancella: si rinomina in
    progress_v1 e resta li', e' la copia di sicurezza dell'utente.

    Se le route non sono ancora caricate si rimanda: la tabella 'progress'
    resta al suo posto e la conversione avverra' alla prima chiamata utile.
    """
    if get_pref_con(con, "schema_v") == "2":
        return
    tables = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    marker_cols = {r[1] for r in con.execute("PRAGMA table_info(markers)")}
    if "markers" in tables and "sid" not in marker_cols:
        # ALTER e' idempotente grazie al controllo sopra; le righe vecchie
        # tengono la colonna step, quelle nuove scrivono solo sid.
        con.execute("ALTER TABLE markers ADD COLUMN sid TEXT")
        con.execute("CREATE INDEX IF NOT EXISTS ix_mark2 ON markers(session_id, sid, kind)")
        con.commit()
        marker_cols.add("sid")
    # 'step' nelle colonne dei marker e' l'impronta di un database vecchio:
    # nei database nuovi la colonna non esiste proprio.
    if "progress" not in tables and "step" not in marker_cols:
        con.execute("INSERT OR REPLACE INTO prefs(k,v) VALUES('schema_v','2')")
        con.commit()
        return
    if not ROUTES:
        return          # niente flag: si riprova quando le route ci saranno
    for rid, d in ROUTES.items():
        sids = d["_sids"]
        if "progress" in tables:
            row = con.execute("SELECT bits, updated_at FROM progress WHERE run_id=?",
                              (rid,)).fetchone()
            if row:
                bits, when = row[0] or "", row[1]
                done = [(rid, sids[i], when) for i, c in enumerate(bits[:len(sids)]) if c == "1"]
                con.executemany("INSERT OR IGNORE INTO progress_steps(run_id,sid,done_at) "
                                "VALUES(?,?,?)", done)
                con.execute("INSERT OR IGNORE INTO progress_runs(run_id,updated_at) VALUES(?,?)",
                            (rid, when))
        if "step" in marker_cols:
            for i, s in enumerate(sids):
                con.execute("UPDATE markers SET sid=? WHERE run_id=? AND step=? AND sid IS NULL",
                            (s, rid, i))
        cur = get_pref_con(con, "cur_" + rid)
        if cur is not None and cur.lstrip("-").isdigit():
            i = int(cur)
            con.execute("UPDATE prefs SET v=? WHERE k=?",
                        (sids[i] if 0 <= i < len(sids) else "", "cur_" + rid))
    if "progress" in tables:
        con.execute("ALTER TABLE progress RENAME TO progress_v1")
    con.execute("INSERT OR REPLACE INTO prefs(k,v) VALUES('schema_v','2')")
    con.commit()


def get_pref_con(con, k):
    row = con.execute("SELECT v FROM prefs WHERE k=?", (k,)).fetchone()
    return row[0] if row else None


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
    """{sid: {'done': {...}, 'start': {...}}} with episode + link data."""
    con = db()
    con.row_factory = sqlite3.Row
    rows = con.execute("""SELECT m.sid, m.kind, m.tc, s.number, s.video_url, s.video_offset, s.lead
                          FROM markers m JOIN sessions s ON s.id = m.session_id
                          WHERE m.run_id=? AND m.sid IS NOT NULL
                          ORDER BY m.id""", (run_id,)).fetchall()
    con.close()
    out = {}
    for r in rows:
        d = out.setdefault(r["sid"], {})
        secs = max(0, int(round(r["tc"] - r["video_offset"] - r["lead"])))
        d[r["kind"]] = {"ep": r["number"], "tc": r["tc"], "url": r["video_url"], "t": secs}
    return out


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


def done_sids(run_id):
    """L'insieme dei sid spuntati per una run, orfani inclusi."""
    con = db()
    out = {r[0] for r in con.execute(
        "SELECT sid FROM progress_steps WHERE run_id=?", (run_id,))}
    con.close()
    return out


def progress_updated_at(run_id):
    con = db()
    row = con.execute("SELECT updated_at FROM progress_runs WHERE run_id=?",
                      (run_id,)).fetchone()
    con.close()
    return row[0] if row else None


def save_done(run_id, posted, route_sids):
    """Salva lo stato dichiarato dalla pagina.

    'posted' e' l'insieme completo dei sid spuntati secondo la pagina. Si
    tolgono SOLO le spunte dei sid che la route attuale conosce: una riga
    orfana (il suo passo non esiste piu') non viene mai toccata da un
    salvataggio, perche' la pagina non puo' dichiarare cio' che non mostra.
    Un sid dichiarato ma non piu' in route si conserva comunque: meglio un
    progresso in piu' che uno in meno.
    """
    posted = set(posted)
    con = db()
    to_clear = [(run_id, s) for s in route_sids - posted]
    con.executemany("DELETE FROM progress_steps WHERE run_id=? AND sid=?", to_clear)
    con.executemany("INSERT OR IGNORE INTO progress_steps(run_id,sid) VALUES(?,?)",
                    [(run_id, s) for s in posted])
    con.execute("""INSERT INTO progress_runs(run_id,updated_at) VALUES(?,datetime('now'))
                   ON CONFLICT(run_id) DO UPDATE SET updated_at=datetime('now')""",
                (run_id,))
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
    # I conteggi guardano solo i sid della route attuale: le righe orfane
    # restano nel database ma non falsano le percentuali.
    done_set = done_sids(run_id) & d["_sidset"]
    tdone = len(done_set & d["_trophy_sids"])
    return (len(done_set), d["_steps"], tdone, d["_tsteps"], progress_updated_at(run_id))


# ------------------------------------------------------------------- overlay
def current_state(run_id):
    """What the overlay and the session bar need: current step, next step, progress."""
    d = ROUTES[run_id]
    lg = lang()
    steps = []
    for pi, ph in enumerate(d["phases"]):
        for st in ph["steps"]:
            steps.append((pi, ph, st))
    done_set = done_sids(run_id) & d["_sidset"]
    undone = [i for i, s in enumerate(d["_sids"]) if s not in done_set]
    cur_sid = get_pref("cur_" + run_id, "")
    cur = d["_sids"].index(cur_sid) if cur_sid in d["_sidset"] else -1
    if cur < 0 or d["_sids"][cur] in done_set:
        cur = undone[0] if undone else -1
    done = len(done_set)
    tdone = len(done_set & d["_trophy_sids"])

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

    nxt = next((i for i in undone if i > cur), None) if cur >= 0 else None
    ses = open_session(run_id)
    return {"run": run_id, "game": d["game"], "lang": lg,
            "current": pack(cur if cur >= 0 else None), "next": pack(nxt),
            "done": done, "total": d["_steps"], "tdone": tdone, "ttotal": d["_tsteps"],
            "session": session_row(ses[0]) if ses else None}
