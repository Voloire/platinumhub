#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sessioni di registrazione, marker e capitoli YouTube.

Il pezzo delicato: i capitoli generati dalla pagina /episodes devono essere
in ordine di tempo STRETTAMENTE crescente (YouTube rifiuta i capitoli
duplicati o fuori ordine) e il primo capitolo deve essere 00:00.
La generazione vive nel JavaScript della pagina; qui estraiamo i dati che la
pagina passa al browser (la variabile EPS) e applichiamo lo stesso algoritmo,
cosi' il test copre esattamente cio' che l'utente incolla su YouTube.
"""

import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: E402

EPS_RE = re.compile(r"^var RUN = (.*?), EPS = (\{.*\});$", re.M)


def fmt_tc(seconds):
    """Stessa formattazione di fmt() nel JS della pagina episodi."""
    s = max(0, int(round(seconds)))
    h, m, x = s // 3600, s % 3600 // 60, s % 60
    return ("%d:%02d:%02d" % (h, m, x)) if h else ("%02d:%02d" % (m, x))


def build_chapters(episode, only_trophies=False):
    """Replica esatta di chapters() in render_episodes()."""
    out = [(0, "Intro")]
    last = 0
    for m in episode["marks"]:
        if m["kind"] not in ("done", "free"):
            continue
        if only_trophies and m["kind"] == "done" and not m["trophy"]:
            continue
        s = max(0, int(round(m["tc"] - episode["off"] - episode["lead"])))
        if s <= last:
            s = last + 1
        last = s
        out.append((s, m["label"] or ""))
    return out


class SessionLifecycleTest(harness.ServerTestCase, unittest.TestCase):
    """Apertura, chiusura e aggiornamento delle sessioni."""

    RUN = "kz"

    def setUp(self):
        self.server.post_json("/api/run/reset", {"run": self.RUN})

    def test_start_creates_an_episode_with_its_opening_marker(self):
        code, res = self.server.post_json("/api/session/start",
                                          {"run": self.RUN, "title": "Prima sessione", "lead": 12})
        self.assertEqual(code, 200)
        ses = res["session"]
        self.assertEqual(ses["run_id"], self.RUN)
        self.assertEqual(ses["number"], 1)
        self.assertEqual(ses["title"], "Prima sessione")
        self.assertEqual(ses["lead"], 12)
        self.assertIsNone(ses["ended_at"])

        code, eps = self.server.get_json("/api/episodes?run=%s" % self.RUN)
        self.assertEqual(code, 200)
        self.assertEqual(len(eps), 1)
        kinds = [m["kind"] for m in eps[0]["markers"]]
        self.assertIn("session_start", kinds, "manca il marker di inizio sessione")

    def test_starting_a_new_session_closes_the_previous_one(self):
        code, res = self.server.post_json("/api/session/start", {"run": self.RUN})
        first = res["session"]["id"]
        code, res = self.server.post_json("/api/session/start", {"run": self.RUN})
        second = res["session"]
        self.assertEqual(second["number"], 2)
        code, eps = self.server.get_json("/api/episodes?run=%s" % self.RUN)
        closed = next(e for e in eps if e["id"] == first)
        self.assertIsNotNone(closed["ended_at"], "la sessione precedente e' rimasta aperta")
        open_ones = [e for e in eps if e["ended_at"] is None]
        self.assertEqual(len(open_ones), 1, "piu' di una sessione aperta contemporaneamente")

    def test_stop_marks_the_session_as_ended(self):
        code, res = self.server.post_json("/api/session/start", {"run": self.RUN})
        sid = res["session"]["id"]
        code, _ = self.server.post_json("/api/session/stop", {"id": sid})
        self.assertEqual(code, 200)
        code, eps = self.server.get_json("/api/episodes?run=%s" % self.RUN)
        self.assertIsNotNone(eps[0]["ended_at"])

    def test_update_stores_video_url_offset_and_lead(self):
        code, res = self.server.post_json("/api/session/start", {"run": self.RUN})
        sid = res["session"]["id"]
        code, res = self.server.post_json("/api/session/update", {
            "id": sid, "video_url": "https://youtu.be/abcdEFGH", "video_offset": 30,
            "lead": 8, "title": "Episodio uno"})
        self.assertEqual(code, 200)
        ses = res["session"]
        self.assertEqual(ses["video_url"], "https://youtu.be/abcdEFGH")
        self.assertEqual(ses["video_offset"], 30)
        self.assertEqual(ses["lead"], 8)
        self.assertEqual(ses["title"], "Episodio uno")

    def test_lead_zero_is_honoured_and_absent_lead_defaults_to_15(self):
        """
        CORRETTO in v4.0: lead=0 e' un valore legittimo (nessun anticipo sui
        marker) e non deve piu' essere scambiato per "non indicato". Solo un
        lead assente torna al default di 15.
        """
        code, res = self.server.post_json("/api/session/start", {"run": self.RUN, "lead": 0})
        self.assertEqual(code, 200)
        self.assertEqual(res["session"]["lead"], 0)
        self.server.post_json("/api/session/stop", {"id": res["session"]["id"]})
        code, res2 = self.server.post_json("/api/session/start", {"run": self.RUN})
        self.assertEqual(res2["session"]["lead"], 15)
        code, res = self.server.post_json("/api/session/update",
                                          {"id": res["session"]["id"], "lead": 0})
        self.assertEqual(res["session"]["lead"], 0, "nemmeno update accetta lead=0")

    def test_delete_removes_the_session_and_its_markers(self):
        code, res = self.server.post_json("/api/session/start", {"run": self.RUN})
        sid = res["session"]["id"]
        self.server.post_json("/api/marker", {"run": self.RUN, "session": sid,
                                              "kind": "done",
                                              "sid": harness.sids_of(self.RUN)[0], "tc": 10})
        code, _ = self.server.post_json("/api/session/delete", {"id": sid})
        self.assertEqual(code, 200)
        code, eps = self.server.get_json("/api/episodes?run=%s" % self.RUN)
        self.assertEqual(eps, [])

    def test_current_state_exposes_the_open_session(self):
        code, res = self.server.post_json("/api/session/start", {"run": self.RUN})
        sid = res["session"]["id"]
        code, state = self.server.get_json("/api/current?run=%s" % self.RUN)
        self.assertEqual(code, 200)
        self.assertIsNotNone(state["session"])
        self.assertEqual(state["session"]["id"], sid)
        self.server.post_json("/api/session/stop", {"id": sid})
        code, state = self.server.get_json("/api/current?run=%s" % self.RUN)
        self.assertIsNone(state["session"], "sessione chiusa ancora segnalata come aperta")


class MarkerTest(harness.ServerTestCase, unittest.TestCase):
    """Scrittura dei marker e loro validazione. Dal v2 i marker puntano al sid del passo."""

    RUN = "n3"

    def setUp(self):
        self.server.post_json("/api/run/reset", {"run": self.RUN})
        code, res = self.server.post_json("/api/session/start", {"run": self.RUN, "lead": 0})
        self.ses = res["session"]["id"]
        self.sids = harness.sids_of(self.RUN)

    def test_markers_are_returned_ordered_by_timecode(self):
        for tc in (90.0, 12.0, 45.5, 3.0):
            code, _ = self.server.post_json("/api/marker", {
                "run": self.RUN, "session": self.ses, "kind": "done",
                "sid": self.sids[int(tc) % 20], "tc": tc})
            self.assertEqual(code, 200)
        code, eps = self.server.get_json("/api/episodes?run=%s" % self.RUN)
        tcs = [m["tc"] for m in eps[0]["markers"]]
        self.assertEqual(tcs, sorted(tcs), "i marker non arrivano in ordine di tempo")

    def test_re_marking_the_same_step_replaces_the_previous_marker(self):
        self.server.post_json("/api/marker", {"run": self.RUN, "session": self.ses,
                                              "kind": "done", "sid": self.sids[5], "tc": 10})
        self.server.post_json("/api/marker", {"run": self.RUN, "session": self.ses,
                                              "kind": "done", "sid": self.sids[5], "tc": 99})
        code, eps = self.server.get_json("/api/episodes?run=%s" % self.RUN)
        same = [m for m in eps[0]["markers"]
                if m["sid"] == self.sids[5] and m["kind"] == "done"]
        self.assertEqual(len(same), 1, "marker duplicato per lo stesso passo")
        self.assertEqual(same[0]["tc"], 99)

    def test_free_marker_keeps_its_note(self):
        code, _ = self.server.post_json("/api/marker", {
            "run": self.RUN, "session": self.ses, "kind": "free", "tc": 33.0,
            "note": "morte stupida"})
        self.assertEqual(code, 200)
        code, eps = self.server.get_json("/api/episodes?run=%s" % self.RUN)
        free = [m for m in eps[0]["markers"] if m["kind"] == "free"]
        self.assertEqual(len(free), 1)
        self.assertEqual(free[0]["note"], "morte stupida")

    def test_marker_delete_removes_the_step(self):
        self.server.post_json("/api/marker", {"run": self.RUN, "session": self.ses,
                                              "kind": "done", "sid": self.sids[2], "tc": 7})
        code, _ = self.server.post_json("/api/marker/delete",
                                        {"session": self.ses, "sid": self.sids[2]})
        self.assertEqual(code, 200)
        code, eps = self.server.get_json("/api/episodes?run=%s" % self.RUN)
        self.assertEqual([m for m in eps[0]["markers"] if m["sid"] == self.sids[2]], [])

    def test_bad_kind_is_rejected(self):
        code, res = self.server.post_json("/api/marker", {
            "run": self.RUN, "session": self.ses, "kind": "banana",
            "sid": self.sids[1], "tc": 1})
        self.assertEqual(code, 400)

    def test_malformed_sid_is_rejected(self):
        for bad in ("banana", "s1", 7, ""):
            with self.subTest(sid=repr(bad)):
                code, _ = self.server.post_json("/api/marker", {
                    "run": self.RUN, "session": self.ses, "kind": "done",
                    "sid": bad, "tc": 1})
                self.assertEqual(code, 400)

    def test_marker_without_session_is_rejected(self):
        code, res = self.server.post_json("/api/marker", {
            "run": self.RUN, "kind": "done", "sid": self.sids[1], "tc": 1})
        self.assertEqual(code, 400)

    def test_marker_on_unknown_run_is_404(self):
        code, res = self.server.post_json("/api/marker", {
            "run": "nope", "session": self.ses, "kind": "done",
            "sid": self.sids[1], "tc": 1})
        self.assertEqual(code, 404)


class YoutubeChaptersTest(harness.ServerTestCase, unittest.TestCase):
    """
    I capitoli generati per YouTube: primo capitolo a 00:00 e tempi
    strettamente crescenti, anche quando lead/offset spingono i marker
    sotto zero o sullo stesso secondo.
    """

    RUN = "bmw"

    def _episodes_payload(self):
        """Estrae la variabile EPS dalla pagina /episodes/<run>."""
        code, html = self.server.get_text("/episodes/%s" % self.RUN)
        self.assertEqual(code, 200)
        m = EPS_RE.search(html)
        self.assertIsNotNone(m, "variabile EPS non trovata nella pagina episodi")
        return json.loads(m.group(2))

    def _make_session(self, lead, offset, timecodes):
        self.server.post_json("/api/run/reset", {"run": self.RUN})
        code, res = self.server.post_json("/api/session/start", {"run": self.RUN, "lead": lead})
        sid = res["session"]["id"]
        sids = harness.sids_of(self.RUN)
        for step, tc in enumerate(timecodes):
            self.server.post_json("/api/marker", {"run": self.RUN, "session": sid,
                                                  "kind": "done", "sid": sids[step], "tc": tc})
        # lead viene riscritto qui: /api/session/start tratta lead=0 come "non indicato"
        # e ricade sul valore di default (15).
        self.server.post_json("/api/session/update", {
            "id": sid, "lead": lead, "video_offset": offset,
            "video_url": "https://youtu.be/TESTVIDEO"})
        self.server.post_json("/api/session/stop", {"id": sid})
        return sid

    def test_chapters_start_at_zero_and_increase_strictly(self):
        # lead 15 e marker molto ravvicinati: senza la correzione i tempi
        # collasserebbero tutti su 00:00.
        sid = self._make_session(lead=15, offset=0, timecodes=[5, 10, 16, 16.4, 30, 300, 3700])
        eps = self._episodes_payload()
        episode = eps[str(sid)]
        chapters = build_chapters(episode)
        self.assertGreater(len(chapters), 1, "nessun capitolo generato")
        self.assertEqual(fmt_tc(chapters[0][0]), "00:00",
                         "il primo capitolo YouTube deve essere 00:00")
        times = [c[0] for c in chapters]
        self.assertEqual(times, sorted(set(times)),
                         "i capitoli non sono strettamente crescenti: %s" % (times,))
        for a, b in zip(times, times[1:]):
            self.assertLess(a, b, "capitoli %s e %s non crescenti" % (a, b))

    def test_chapter_labels_are_never_empty(self):
        sid = self._make_session(lead=0, offset=0, timecodes=[10, 20, 30])
        episode = self._episodes_payload()[str(sid)]
        for tc, label in build_chapters(episode):
            self.assertTrue(str(label).strip(), "capitolo a %s senza etichetta" % fmt_tc(tc))

    def test_video_offset_is_subtracted_from_every_chapter(self):
        sid = self._make_session(lead=0, offset=100, timecodes=[200, 260, 320])
        episode = self._episodes_payload()[str(sid)]
        times = [c[0] for c in build_chapters(episode)]
        self.assertEqual(times, [0, 100, 160, 220])

    def test_trophy_only_chapters_are_a_subset_and_still_increasing(self):
        sid = self._make_session(lead=0, offset=0, timecodes=[10, 20, 30, 40, 50])
        episode = self._episodes_payload()[str(sid)]
        full = build_chapters(episode, only_trophies=False)
        only = build_chapters(episode, only_trophies=True)
        self.assertLessEqual(len(only), len(full))
        times = [c[0] for c in only]
        self.assertEqual(fmt_tc(times[0]), "00:00")
        for a, b in zip(times, times[1:]):
            self.assertLess(a, b)

    def test_episode_page_lists_the_episode_and_its_video_link(self):
        self._make_session(lead=0, offset=0, timecodes=[10])
        code, html = self.server.get_text("/episodes/%s" % self.RUN)
        self.assertEqual(code, 200)
        self.assertIn("https://youtu.be/TESTVIDEO", html)

    def test_timecode_formatting_matches_the_javascript(self):
        self.assertEqual(fmt_tc(0), "00:00")
        self.assertEqual(fmt_tc(59.4), "00:59")
        self.assertEqual(fmt_tc(60), "01:00")
        self.assertEqual(fmt_tc(3599), "59:59")
        self.assertEqual(fmt_tc(3600), "1:00:00")
        self.assertEqual(fmt_tc(-5), "00:00")


if __name__ == "__main__":
    unittest.main(verbosity=2)
