#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Round-trip delle API di Platinum Hub: progressi, note, preferenze,
backup (export/import) e azzeramento della singola run.

Il server gira in una sandbox temporanea con il proprio platinum.db:
il database reale non viene mai aperto.
"""

import json
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: E402


class ProgressApiTest(harness.ServerTestCase, unittest.TestCase):
    """/api/progress: la stringa di bit va salvata e riletta identica."""

    def setUp(self):
        # Ogni test riparte da progressi azzerati sulle run che tocca.
        for rid in ("kz", "er"):
            self.server.post_json("/api/run/reset", {"run": rid})

    def test_saved_bits_come_back_identical(self):
        code, total = self.server.get_json("/api/progress?run=kz")
        self.assertEqual(code, 200)
        n = total["total"]
        bits = "".join("1" if i % 3 == 0 else "0" for i in range(n))
        code, res = self.server.post_json("/api/progress", {"run": "kz", "bits": bits})
        self.assertEqual(code, 200)
        self.assertEqual(res["saved"], bits.count("1"))
        self.assertEqual(res["total"], n)
        code, back = self.server.get_json("/api/progress?run=kz")
        self.assertEqual(code, 200)
        self.assertEqual(back["bits"], bits, "la stringa riletta non coincide con quella salvata")
        self.assertEqual(len(back["bits"]), n)
        self.assertIsNotNone(back["updated_at"])

    def test_bit_string_length_matches_the_route_steps(self):
        """La lunghezza deve combaciare col numero di passi del file JSON."""
        for name in harness.route_files():
            rid = os.path.splitext(name)[0]
            expected = harness.route_step_count(harness.load_route(name))
            with self.subTest(run=rid):
                code, res = self.server.get_json("/api/progress?run=%s" % rid)
                self.assertEqual(code, 200)
                self.assertEqual(res["total"], expected)
                self.assertEqual(len(res["bits"]), expected)

    def test_short_payload_is_padded_and_long_one_truncated(self):
        code, res = self.server.get_json("/api/progress?run=kz")
        n = res["total"]
        code, res = self.server.post_json("/api/progress", {"run": "kz", "bits": "111"})
        self.assertEqual(code, 200)
        code, back = self.server.get_json("/api/progress?run=kz")
        self.assertEqual(len(back["bits"]), n)
        self.assertEqual(back["bits"], "111" + "0" * (n - 3))
        code, res = self.server.post_json("/api/progress", {"run": "kz", "bits": "1" * (n + 50)})
        self.assertEqual(code, 200)
        code, back = self.server.get_json("/api/progress?run=kz")
        self.assertEqual(len(back["bits"]), n)

    def test_non_binary_payload_is_rejected(self):
        code, res = self.server.post_json("/api/progress", {"run": "kz", "bits": "1012"})
        self.assertEqual(code, 400)
        self.assertIn("error", res)

    def test_unknown_run_is_a_404(self):
        code, res = self.server.get_json("/api/progress?run=nope")
        self.assertEqual(code, 404)
        code, res = self.server.post_json("/api/progress", {"run": "nope", "bits": "1"})
        self.assertEqual(code, 404)

    def test_summary_reflects_what_was_saved(self):
        code, res = self.server.get_json("/api/progress?run=er")
        n = res["total"]
        self.server.post_json("/api/progress", {"run": "er", "bits": "1" * 10 + "0" * (n - 10)})
        code, summary = self.server.get_json("/api/summary")
        self.assertEqual(code, 200)
        row = next(r for r in summary if r["run"] == "er")
        self.assertEqual(row["steps_done"], 10)
        self.assertEqual(row["steps_total"], n)
        self.assertGreaterEqual(row["trophies_total"], row["trophies_done"])

    def test_progress_is_actually_persisted_in_sqlite(self):
        """Controllo diretto sul file .db della sandbox."""
        self.server.post_json("/api/progress", {"run": "kz", "bits": "101"})
        con = sqlite3.connect(self.server.db_path())
        try:
            row = con.execute("SELECT bits FROM progress WHERE run_id='kz'").fetchone()
        finally:
            con.close()
        self.assertIsNotNone(row)
        self.assertTrue(row[0].startswith("101"))


class NotesApiTest(harness.ServerTestCase, unittest.TestCase):
    """/api/notes: testo libero per run."""

    def test_note_round_trip(self):
        body = "Boss che mi ammazza: Malenia.\nRiprendere dal passo 12 — attenzione al missabile."
        code, res = self.server.post_json("/api/notes", {"run": "ds3", "body": body})
        self.assertEqual(code, 200)
        code, back = self.server.get_json("/api/notes?run=ds3")
        self.assertEqual(code, 200)
        self.assertEqual(back["body"], body)
        self.assertEqual(back["run"], "ds3")

    def test_note_is_overwritten_not_appended(self):
        self.server.post_json("/api/notes", {"run": "sb", "body": "primo"})
        self.server.post_json("/api/notes", {"run": "sb", "body": "secondo"})
        code, back = self.server.get_json("/api/notes?run=sb")
        self.assertEqual(back["body"], "secondo")

    def test_note_on_unknown_run_is_404(self):
        code, _ = self.server.get_json("/api/notes?run=nope")
        self.assertEqual(code, 404)
        code, _ = self.server.post_json("/api/notes", {"run": "nope", "body": "x"})
        self.assertEqual(code, 404)

    def test_note_survives_in_the_backup(self):
        self.server.post_json("/api/notes", {"run": "bmw", "body": "nota da esportare"})
        code, _, raw = self.server.get("/api/export")
        payload = json.loads(raw)
        rows = {r["run_id"]: r["body"] for r in payload["notes"]}
        self.assertEqual(rows.get("bmw"), "nota da esportare")


class PrefsApiTest(harness.ServerTestCase, unittest.TestCase):
    """/api/pref e /lang/<code>: le preferenze devono restare fra una richiesta e l'altra."""

    def test_language_preference_changes_the_rendered_page(self):
        self.server.post_json("/api/pref", {"lang": "en"})
        code, html = self.server.get_text("/run/kz")
        self.assertEqual(code, 200)
        self.assertIn('<html lang="en"', html)
        self.server.post_json("/api/pref", {"lang": "it"})
        code, html = self.server.get_text("/run/kz")
        self.assertIn('<html lang="it"', html)

    def test_language_switch_url_redirects_and_sticks(self):
        code, headers, _ = self.server.get("/lang/en?next=/run/kz", follow=False)
        self.assertEqual(code, 303)
        self.assertEqual(headers.get("Location"), "/run/kz")
        code, html = self.server.get_text("/run/kz")
        self.assertIn('<html lang="en"', html)
        self.server.post_json("/api/pref", {"lang": "it"})

    def test_mode_preference_round_trip(self):
        self.server.post_json("/api/pref", {"mode": "streamer"})
        code, prefs = self.server.get_json("/api/prefs")
        self.assertEqual(code, 200)
        self.assertEqual(prefs["mode"], "streamer")
        self.server.post_json("/api/pref", {"mode": "gamer"})
        code, prefs = self.server.get_json("/api/prefs")
        self.assertEqual(prefs["mode"], "gamer")

    def test_obs_preferences_round_trip(self):
        self.server.post_json("/api/pref", {"obs_url": "ws://127.0.0.1:9999",
                                            "obs_prefer": "record"})
        code, prefs = self.server.get_json("/api/prefs")
        self.assertEqual(prefs["obs_url"], "ws://127.0.0.1:9999")
        self.assertEqual(prefs["obs_prefer"], "record")

    def test_current_step_pointer_round_trip(self):
        self.server.post_json("/api/progress", {"run": "n3", "bits": "000"})
        code, res = self.server.post_json("/api/current", {"run": "n3", "step": 7})
        self.assertEqual(code, 200)
        code, state = self.server.get_json("/api/current?run=n3")
        self.assertEqual(code, 200)
        self.assertEqual(state["current"]["i"], 7)
        self.assertEqual(state["run"], "n3")

    def test_toast_is_returned_once_it_is_set(self):
        code, res = self.server.post_json("/api/toast", {"run": "n3", "text": "ciao"})
        self.assertEqual(code, 200)
        code, state = self.server.get_json("/api/current?run=n3")
        self.assertEqual(state["toast"], "ciao")


class BackupApiTest(harness.ServerTestCase, unittest.TestCase):
    """/api/export e /api/import: il backup deve essere un round-trip completo."""

    def test_export_has_the_expected_envelope(self):
        code, headers, raw = self.server.get("/api/export")
        self.assertEqual(code, 200)
        self.assertIn("attachment", headers.get("Content-Disposition", ""))
        payload = json.loads(raw)
        self.assertEqual(payload["app"], "PlatinumHub")
        for key in ("version", "exported_at", "progress", "notes", "prefs"):
            self.assertIn(key, payload)

    def test_backup_restores_progress_and_notes(self):
        code, res = self.server.get_json("/api/progress?run=lop")
        n = res["total"]
        bits = ("1" * 20).ljust(n, "0")
        self.server.post_json("/api/progress", {"run": "lop", "bits": bits})
        self.server.post_json("/api/notes", {"run": "lop", "body": "nota originale"})
        code, _, raw = self.server.get("/api/export")
        backup = json.loads(raw)

        # Sporchiamo lo stato, poi ripristiniamo.
        self.server.post_json("/api/progress", {"run": "lop", "bits": "0" * n})
        self.server.post_json("/api/notes", {"run": "lop", "body": "nota sbagliata"})
        code, res = self.server.post_json("/api/import", backup)
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])

        code, back = self.server.get_json("/api/progress?run=lop")
        self.assertEqual(back["bits"], bits, "l'import non ha ripristinato i progressi")
        code, note = self.server.get_json("/api/notes?run=lop")
        self.assertEqual(note["body"], "nota originale")

    def test_import_pads_a_short_bit_string_to_the_route_length(self):
        code, res = self.server.get_json("/api/progress?run=bor")
        n = res["total"]
        code, res = self.server.post_json("/api/import", {
            "app": "PlatinumHub", "version": 2,
            "progress": [{"run_id": "bor", "bits": "11", "updated_at": None}],
            "notes": [], "prefs": {}})
        self.assertEqual(code, 200)
        code, back = self.server.get_json("/api/progress?run=bor")
        self.assertEqual(len(back["bits"]), n)
        self.assertTrue(back["bits"].startswith("11"))

    def test_import_ignores_unknown_runs_without_failing(self):
        code, res = self.server.post_json("/api/import", {
            "app": "PlatinumHub", "version": 2,
            "progress": [{"run_id": "does-not-exist", "bits": "111"}],
            "notes": [{"run_id": "does-not-exist", "body": "x"}], "prefs": {}})
        self.assertEqual(code, 200)

    def test_garbage_file_is_rejected_with_400(self):
        """Un file qualunque non deve poter sovrascrivere i progressi."""
        for payload in ({"hello": "world"},
                        {"app": "SomethingElse", "progress": []},
                        [1, 2, 3],
                        "just a string",
                        42):
            with self.subTest(payload=repr(payload)[:40]):
                code, res = self.server.post_json("/api/import", payload)
                self.assertEqual(code, 400, "payload spazzatura accettato: %r" % (payload,))

    def test_truncated_json_file_is_rejected_with_400(self):
        code, _, body = self.server.post_raw("/api/import", b'{"app": "PlatinumHub", "progr')
        self.assertEqual(code, 400)


class RunResetTest(harness.ServerTestCase, unittest.TestCase):
    """
    /api/run/reset deve cancellare progressi, marker, sessioni e note
    SOLO della run indicata. Le altre run non si devono toccare:
    e' gia' stato un bug vero.
    """

    def _populate(self, rid, marker_step):
        code, res = self.server.get_json("/api/progress?run=%s" % rid)
        n = res["total"]
        bits = ("1" * 5).ljust(n, "0")
        self.server.post_json("/api/progress", {"run": rid, "bits": bits})
        self.server.post_json("/api/notes", {"run": rid, "body": "note di %s" % rid})
        self.server.post_json("/api/current", {"run": rid, "step": 3})
        code, res = self.server.post_json("/api/session/start", {"run": rid, "title": "ep " + rid})
        self.assertEqual(code, 200)
        sid = res["session"]["id"]
        self.server.post_json("/api/marker", {"run": rid, "session": sid, "kind": "done",
                                              "step": marker_step, "tc": 42.0})
        self.server.post_json("/api/session/stop", {"id": sid})
        return bits

    def _counts(self, rid):
        con = sqlite3.connect(self.server.db_path())
        try:
            q = lambda sql: con.execute(sql, (rid,)).fetchone()[0]
            return {
                "progress": q("SELECT COUNT(*) FROM progress WHERE run_id=?"),
                "notes": q("SELECT COUNT(*) FROM notes WHERE run_id=?"),
                "sessions": q("SELECT COUNT(*) FROM sessions WHERE run_id=?"),
                "markers": q("SELECT COUNT(*) FROM markers WHERE run_id=?"),
            }
        finally:
            con.close()

    def test_reset_wipes_only_the_requested_run(self):
        victim, bystander = "kz", "sb"
        self.server.post_json("/api/run/reset", {"run": victim})
        self.server.post_json("/api/run/reset", {"run": bystander})
        self._populate(victim, 2)
        keep_bits = self._populate(bystander, 4)

        before = self._counts(bystander)
        self.assertEqual(before, {"progress": 1, "notes": 1, "sessions": 1, "markers": 2},
                         "il popolamento della run testimone non e' andato a buon fine")

        code, res = self.server.post_json("/api/run/reset", {"run": victim})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])

        wiped = self._counts(victim)
        self.assertEqual(wiped, {"progress": 0, "notes": 0, "sessions": 0, "markers": 0},
                         "il reset non ha ripulito tutto per la run indicata")

        after = self._counts(bystander)
        self.assertEqual(after, before,
                         "il reset di '%s' ha toccato i dati di '%s'" % (victim, bystander))
        code, back = self.server.get_json("/api/progress?run=%s" % bystander)
        self.assertEqual(back["bits"], keep_bits, "i progressi della run testimone sono cambiati")
        code, note = self.server.get_json("/api/notes?run=%s" % bystander)
        self.assertEqual(note["body"], "note di %s" % bystander)
        code, eps = self.server.get_json("/api/episodes?run=%s" % bystander)
        self.assertEqual(len(eps), 1, "gli episodi della run testimone sono spariti")

    def test_reset_clears_the_current_step_pointer_of_that_run_only(self):
        self.server.post_json("/api/run/reset", {"run": "na"})
        self.server.post_json("/api/run/reset", {"run": "n3"})
        self.server.post_json("/api/current", {"run": "na", "step": 9})
        self.server.post_json("/api/current", {"run": "n3", "step": 11})
        self.server.post_json("/api/run/reset", {"run": "na"})
        con = sqlite3.connect(self.server.db_path())
        try:
            keys = {k for (k,) in con.execute("SELECT k FROM prefs")}
        finally:
            con.close()
        self.assertNotIn("cur_na", keys)
        self.assertIn("cur_n3", keys, "il reset ha cancellato il puntatore di un'altra run")

    def test_reset_reports_how_much_it_deleted(self):
        self.server.post_json("/api/run/reset", {"run": "bor"})
        self._populate("bor", 1)
        code, res = self.server.post_json("/api/run/reset", {"run": "bor"})
        self.assertEqual(code, 200)
        self.assertEqual(res["sessions"], 1)
        self.assertEqual(res["notes"], 1)
        self.assertGreaterEqual(res["markers"], 1)

    def test_reset_of_unknown_run_is_404(self):
        code, _ = self.server.post_json("/api/run/reset", {"run": "nope"})
        self.assertEqual(code, 404)


class SandboxIsolationTest(harness.ServerTestCase, unittest.TestCase):
    """
    Guardia sulla regola piu' importante della suite: i test non devono
    scrivere niente nella cartella reale dell'applicazione.

    I confronti fra percorsi passano tutti da _norm(). Su Windows la cartella
    temporanea puo' arrivare in forma 8.3 (C:\\Users\\RUNNER~1\\...) mentre
    realpath() restituisce la forma lunga (C:\\Users\\runneradmin\\...): due
    nomi dello stesso posto, che uno startswith fra stringhe grezze giudica
    diversi. E' cosi' che questi test fallivano solo sul runner Windows.
    """

    @staticmethod
    def _norm(path):
        return os.path.normcase(os.path.realpath(path))

    def test_the_database_lives_in_the_sandbox(self):
        self.server.post_json("/api/progress", {"run": "kz", "bits": "1"})
        self.assertTrue(os.path.isfile(self.server.db_path()),
                        "il database della sandbox non e' stato creato")
        db = self._norm(self.server.db_path())
        self.assertTrue(db.startswith(self._norm(self.server.sandbox)),
                        "il database e' fuori dalla sandbox: %s" % db)
        self.assertFalse(db.startswith(self._norm(harness.APP_DIR)),
                         "il database e' dentro la cartella reale dell'app: %s" % db)

    def test_the_real_database_is_never_created_or_touched(self):
        real_db = os.path.join(harness.APP_DIR, "platinum.db")
        before = os.path.getmtime(real_db) if os.path.exists(real_db) else None
        self.server.post_json("/api/progress", {"run": "er", "bits": "111"})
        self.server.post_json("/api/notes", {"run": "er", "body": "test"})
        after = os.path.getmtime(real_db) if os.path.exists(real_db) else None
        self.assertEqual(before, after,
                         "i test hanno toccato il database reale in %s" % harness.APP_DIR)

    def test_selftest_report_is_written_inside_the_sandbox(self):
        code, res = self.server.post_json("/api/selftest", {"text": "riga di prova"})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])
        self.assertTrue(self._norm(res["path"]).startswith(self._norm(self.server.sandbox)),
                        "diagnostica.txt scritta fuori dalla sandbox: %s" % res["path"])
        self.assertFalse(os.path.exists(os.path.join(harness.APP_DIR, "diagnostica.txt")),
                         "diagnostica.txt e' finita nella cartella reale dell'app")


if __name__ == "__main__":
    unittest.main(verbosity=2)
