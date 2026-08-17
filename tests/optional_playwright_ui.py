#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  TEST OPZIONALI - RICHIEDONO PLAYWRIGHT - NON FANNO PARTE DELLA CI DI BASE
=============================================================================

Questo file NON viene raccolto da run_all.py: il nome non comincia per test_
proprio per tenerlo fuori dalla suite standard, che deve girare con la sola
libreria standard di Python 3.

Serve a provare le poche cose che vivono solo nel browser: la spunta che
salva davvero, i filtri della checklist e i capitoli YouTube generati dal
JavaScript della pagina episodi.

Per usarlo:

    pip install playwright
    playwright install chromium
    python3 tests/optional_playwright_ui.py

Senza Playwright installato i test vengono saltati, non falliti.
"""

import json
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
    HAVE_PLAYWRIGHT = True
except ImportError:                                          # pragma: no cover
    HAVE_PLAYWRIGHT = False


@unittest.skipUnless(HAVE_PLAYWRIGHT, "Playwright non installato: test di interfaccia saltati")
class ChecklistBrowserTest(harness.ServerTestCase, unittest.TestCase):
    """Interazioni reali sulla pagina della checklist."""

    @classmethod
    def setUpClass(cls):
        super(ChecklistBrowserTest, cls).setUpClass()
        cls._pw = sync_playwright().start()
        cls.browser = cls._pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.browser.close()
            cls._pw.stop()
        finally:
            super(ChecklistBrowserTest, cls).tearDownClass()

    def setUp(self):
        self.server.post_json("/api/run/reset", {"run": "kz"})
        self.page = self.browser.new_page()

    def tearDown(self):
        self.page.close()

    def test_ticking_a_box_is_saved_on_the_server(self):
        self.page.goto(self.server.url("/run/kz"))
        self.page.wait_for_selector("#s1")
        self.page.check("#s1")
        self.page.wait_for_timeout(1200)                     # il salvataggio e' differito
        code, res = self.server.get_json("/api/progress?run=kz")
        self.assertTrue(res["bits"].startswith("1"), "la spunta non e' arrivata al server")

    def test_progress_survives_a_reload(self):
        self.page.goto(self.server.url("/run/kz"))
        self.page.wait_for_selector("#s2")
        self.page.check("#s2")
        self.page.wait_for_timeout(1200)
        self.page.reload()
        self.page.wait_for_selector("#s2")
        self.page.wait_for_timeout(600)
        self.assertTrue(self.page.is_checked("#s2"), "la spunta non e' stata ricaricata")

    def test_filter_box_hides_the_steps_that_do_not_match(self):
        self.page.goto(self.server.url("/run/kz"))
        self.page.wait_for_selector("#filterBox")
        total = self.page.eval_on_selector_all("label.item", "els => els.length")
        self.page.fill("#filterBox", "zzzzzznessunrisultato")
        self.page.wait_for_timeout(400)
        visible = self.page.eval_on_selector_all(
            "label.item", "els => els.filter(e => e.offsetParent !== null).length")
        self.assertEqual(visible, 0, "il filtro non nasconde nulla")
        self.assertGreater(total, 0)

    def test_youtube_chapters_are_generated_in_strictly_increasing_order(self):
        """Esegue davvero chapters() nel browser e legge la textarea prodotta."""
        code, res = self.server.post_json("/api/session/start", {"run": "kz"})
        sid = res["session"]["id"]
        for step, tc in enumerate((5, 10, 16, 40, 3700)):
            self.server.post_json("/api/marker", {"run": "kz", "session": sid,
                                                  "kind": "done", "step": step, "tc": tc})
        self.server.post_json("/api/session/update",
                              {"id": sid, "video_url": "https://youtu.be/TEST"})
        self.server.post_json("/api/session/stop", {"id": sid})

        self.page.goto(self.server.url("/episodes/kz"))
        self.page.wait_for_selector("#ta%d" % sid)
        self.page.evaluate("id => chapters(id, 0)", sid)
        text = self.page.input_value("#ta%d" % sid)
        lines = [l for l in text.splitlines() if l.strip()]
        self.assertTrue(lines[0].startswith("00:00"), "il primo capitolo non e' 00:00")

        def to_seconds(stamp):
            parts = [int(x) for x in stamp.split(":")]
            return parts[0] * 60 + parts[1] if len(parts) == 2 else \
                parts[0] * 3600 + parts[1] * 60 + parts[2]

        times = [to_seconds(l.split(" ")[0]) for l in lines]
        for a, b in zip(times, times[1:]):
            self.assertLess(a, b, "capitoli non strettamente crescenti: %s" % times)

    def test_no_javascript_error_on_any_page(self):
        errors = []
        self.page.on("pageerror", lambda e: errors.append(str(e)))
        for path in ("/", "/run/kz", "/episodes/kz", "/session/kz", "/selftest/kz",
                     "/overlay/kz"):
            self.page.goto(self.server.url(path))
            self.page.wait_for_timeout(700)
        self.assertEqual(errors, [], "errori JavaScript: %s" % errors[:3])


if __name__ == "__main__":
    if not HAVE_PLAYWRIGHT:
        print("Playwright non e' installato. Questi test sono opzionali:")
        print("    pip install playwright && playwright install chromium")
    unittest.main(verbosity=2)
