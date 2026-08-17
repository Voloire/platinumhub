#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migrazione del database dallo schema v1 (progressi posizionali) al v2 (per sid).

Il contratto: un platinum.db scritto dalla 3.x o dalla 4.x viene convertito al
primo avvio SENZA perdere niente — le spunte finiscono in progress_steps con il
sid del passo che occupava quella posizione, i marker ricevono il sid, il
puntatore del passo corrente diventa un sid, e la tabella vecchia resta nel
file come progress_v1: e' la copia di sicurezza dell'utente.

La mappa posizione->sid e' legittima perche' i sid sono stati assegnati
nell'ordine dei passi dei JSON in bundle, cioe' nella stessa struttura che le
versioni vecchie usavano per la stringa di bit.
"""

import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: E402

RUN = "kz"
DONE_POSITIONS = (0, 2, 5)          # spunte nella stringa di bit del db vecchio
MARKER_STEP = 2                     # marker 'done' posizionale
CUR_STEP = 7                        # puntatore del passo corrente (indice)


def make_v1_db(path, n_steps):
    """Scrive un platinum.db con lo schema della 4.x: bits, markers.step, cur_ numerico."""
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE progress(
        run_id TEXT PRIMARY KEY, bits TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT (datetime('now')))""")
    con.execute("""CREATE TABLE notes(
        run_id TEXT PRIMARY KEY, body TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT (datetime('now')))""")
    con.execute("CREATE TABLE prefs(k TEXT PRIMARY KEY, v TEXT NOT NULL)")
    con.execute("""CREATE TABLE sessions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL, number INTEGER NOT NULL,
        title TEXT NOT NULL DEFAULT '',
        started_at TEXT NOT NULL, ended_at TEXT,
        source TEXT NOT NULL DEFAULT 'clock',
        video_url TEXT NOT NULL DEFAULT '',
        video_offset INTEGER NOT NULL DEFAULT 0,
        lead INTEGER NOT NULL DEFAULT 15)""")
    con.execute("""CREATE TABLE markers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL, run_id TEXT NOT NULL,
        step INTEGER, kind TEXT NOT NULL, tc REAL NOT NULL,
        wall TEXT NOT NULL, note TEXT NOT NULL DEFAULT '')""")
    bits = "".join("1" if i in DONE_POSITIONS else "0" for i in range(n_steps))
    con.execute("INSERT INTO progress(run_id,bits,updated_at) VALUES(?,?,?)",
                (RUN, bits, "2026-01-15 10:00:00"))
    con.execute("INSERT INTO notes(run_id,body) VALUES(?,?)", (RUN, "nota della 4.x"))
    con.execute("INSERT INTO prefs(k,v) VALUES(?,?)", ("cur_" + RUN, str(CUR_STEP)))
    con.execute("INSERT INTO prefs(k,v) VALUES('lang','it')")
    con.execute("""INSERT INTO sessions(run_id,number,title,started_at,ended_at,source)
                   VALUES(?,1,'ep vecchio','2026-01-15 09:00:00','2026-01-15 11:00:00','clock')""",
                (RUN,))
    ses = con.execute("SELECT id FROM sessions").fetchone()[0]
    con.execute("""INSERT INTO markers(session_id,run_id,step,kind,tc,wall)
                   VALUES(?,?,NULL,'session_start',0,'2026-01-15 09:00:00')""", (ses, RUN))
    con.execute("""INSERT INTO markers(session_id,run_id,step,kind,tc,wall)
                   VALUES(?,?,?,'done',120.5,'2026-01-15 09:02:00')""", (ses, RUN, MARKER_STEP))
    con.commit()
    con.close()


class V1MigrationTest(unittest.TestCase):
    """Un server avviato sopra un db 4.x deve convertirlo e non perdere nulla."""

    server = None

    @classmethod
    def setUpClass(cls):
        cls.sids = harness.sids_of(RUN)
        root, port = harness.make_sandbox()
        make_v1_db(os.path.join(root, "platinum.db"), len(cls.sids))
        cls.server = harness.AppServer().start(sandbox=root, port=port)

    @classmethod
    def tearDownClass(cls):
        if cls.server is not None:
            cls.server.stop()
            cls.server = None

    def _db(self):
        return sqlite3.connect(self.server.db_path())

    def test_progress_bits_became_sid_rows(self):
        code, res = self.server.get_json("/api/progress?run=%s" % RUN)
        self.assertEqual(code, 200)
        expected = sorted(self.sids[i] for i in DONE_POSITIONS)
        self.assertEqual(sorted(res["done"]), expected,
                         "le spunte migrate non corrispondono alle posizioni del db vecchio")

    def test_updated_at_of_the_old_save_is_preserved(self):
        code, res = self.server.get_json("/api/progress?run=%s" % RUN)
        self.assertEqual(res["updated_at"], "2026-01-15 10:00:00")

    def test_markers_received_their_sid(self):
        code, eps = self.server.get_json("/api/episodes?run=%s" % RUN)
        self.assertEqual(code, 200)
        done = [m for m in eps[0]["markers"] if m["kind"] == "done"]
        self.assertEqual(len(done), 1)
        self.assertEqual(done[0]["sid"], self.sids[MARKER_STEP])

    def test_current_pointer_became_a_sid(self):
        con = self._db()
        try:
            cur = con.execute("SELECT v FROM prefs WHERE k=?",
                              ("cur_" + RUN,)).fetchone()[0]
        finally:
            con.close()
        self.assertEqual(cur, self.sids[CUR_STEP])
        code, state = self.server.get_json("/api/current?run=%s" % RUN)
        self.assertEqual(state["current"]["i"], CUR_STEP)

    def test_the_old_table_is_kept_as_a_backup(self):
        con = self._db()
        try:
            tables = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            old = con.execute("SELECT bits FROM progress_v1 WHERE run_id=?",
                              (RUN,)).fetchone()
        finally:
            con.close()
        self.assertIn("progress_v1", tables, "la tabella vecchia e' stata cancellata")
        self.assertNotIn("progress", tables)
        self.assertTrue(old[0].startswith("101001"))

    def test_note_and_language_survive(self):
        code, note = self.server.get_json("/api/notes?run=%s" % RUN)
        self.assertEqual(note["body"], "nota della 4.x")

    def test_migration_is_marked_and_not_repeated(self):
        con = self._db()
        try:
            v = con.execute("SELECT v FROM prefs WHERE k='schema_v'").fetchone()
        finally:
            con.close()
        self.assertEqual(v[0], "2")


class V1MinimalDbTest(unittest.TestCase):
    """Un db 3.x minimale (solo progress/notes/prefs, niente sessioni) non deve rompere l'avvio."""

    server = None

    @classmethod
    def setUpClass(cls):
        cls.sids = harness.sids_of(RUN)
        root, port = harness.make_sandbox()
        con = sqlite3.connect(os.path.join(root, "platinum.db"))
        con.execute("""CREATE TABLE progress(
            run_id TEXT PRIMARY KEY, bits TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')))""")
        con.execute("INSERT INTO progress(run_id,bits) VALUES(?, '11')", (RUN,))
        con.commit()
        con.close()
        cls.server = harness.AppServer().start(sandbox=root, port=port)

    @classmethod
    def tearDownClass(cls):
        if cls.server is not None:
            cls.server.stop()
            cls.server = None

    def test_progress_is_migrated_and_server_answers(self):
        code, res = self.server.get_json("/api/progress?run=%s" % RUN)
        self.assertEqual(code, 200)
        self.assertEqual(sorted(res["done"]), sorted(self.sids[:2]))

    def test_no_traceback_reached_stderr(self):
        self.assertEqual(self.server.tracebacks(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
