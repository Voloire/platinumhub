#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rendering di tutte le pagine, per tutte e 10 le route, in entrambe le lingue.

Il controllo che conta davvero: il numero di caselle di spunta nell'HTML deve
coincidere con il numero di passi della route, ed essere lo stesso in italiano
e in inglese. Se cambia, la stringa posizionale dei progressi non corrisponde
piu' alla checklist e le spunte finiscono sui passi sbagliati.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: E402

# Le caselle della checklist sono <input type="checkbox" id="s1" data-sid="s001">...
# il data-sid e' la chiave con cui la pagina dichiara i progressi al server.
CHECKBOX_RE = re.compile(r'<input type="checkbox" id="s(\d+)" data-sid="(s\d+)">')
# Nella guida esportata i passi diventano <div class="step done|todo">.
EXPORT_STEP_RE = re.compile(r'<div class="step (?:done|todo)">')

LANGS = ("it", "en")
PAGES = ("/run/%s", "/episodes/%s", "/session/%s", "/export/%s", "/selftest/%s", "/overlay/%s",
         "/thumb/%s")


class RenderTest(harness.ServerTestCase, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(RenderTest, cls).setUpClass()
        cls.steps = {os.path.splitext(f)[0]: harness.route_step_count(harness.load_route(f))
                     for f in harness.route_files()}

    def tearDown(self):
        self.server.set_lang("it")

    # ------------------------------------------------------------------ pagine
    def test_home_page_renders_in_both_languages(self):
        for lg in LANGS:
            self.server.set_lang(lg)
            with self.subTest(lang=lg):
                code, html = self.server.get_text("/")
                self.assertEqual(code, 200)
                self.assertIn('<html lang="%s"' % lg, html)
                self.assertIn("PLATINUM HUB", html)
                for rid in self.steps:
                    self.assertIn('href="/run/%s"' % rid, html,
                                  "la home non elenca la run %s" % rid)

    def test_every_page_answers_200_for_every_run_in_both_languages(self):
        for lg in LANGS:
            self.server.set_lang(lg)
            for rid in sorted(self.steps):
                for pattern in PAGES:
                    path = pattern % rid
                    with self.subTest(lang=lg, page=path):
                        code, html = self.server.get_text(path)
                        self.assertEqual(code, 200, "%s ha risposto %d" % (path, code))
                        self.assertGreater(len(html), 500, "%s ha restituito una pagina vuota" % path)
                        self.assertNotIn("Traceback (most recent call last)", html)

    def test_pages_declare_the_selected_language(self):
        for lg in LANGS:
            self.server.set_lang(lg)
            for rid in sorted(self.steps):
                for pattern in ("/run/%s", "/episodes/%s", "/session/%s", "/export/%s"):
                    with self.subTest(lang=lg, page=pattern % rid):
                        code, html = self.server.get_text(pattern % rid)
                        self.assertIn('lang="%s"' % lg, html)

    # ----------------------------------------------------- caselle di spunta
    def test_checkbox_count_matches_the_route_step_count(self):
        for lg in LANGS:
            self.server.set_lang(lg)
            for rid, expected in sorted(self.steps.items()):
                with self.subTest(lang=lg, run=rid):
                    code, html = self.server.get_text("/run/%s" % rid)
                    self.assertEqual(code, 200)
                    found = CHECKBOX_RE.findall(html)
                    self.assertEqual(len(found), expected,
                                     "%s in %s: %d caselle per %d passi"
                                     % (rid, lg, len(found), expected))
                    self.assertEqual([int(i) for i, _ in found], list(range(1, expected + 1)),
                                     "%s in %s: gli id delle caselle non sono consecutivi"
                                     % (rid, lg))
                    self.assertEqual([s for _, s in found], harness.sids_of(rid),
                                     "%s in %s: i data-sid della pagina non sono i sid "
                                     "della route, nell'ordine della route" % (rid, lg))

    def test_checkbox_count_is_identical_in_both_languages(self):
        """Il test che protegge dalla corruzione silenziosa dei salvataggi."""
        for rid in sorted(self.steps):
            counts = {}
            for lg in LANGS:
                self.server.set_lang(lg)
                code, html = self.server.get_text("/run/%s" % rid)
                counts[lg] = len(CHECKBOX_RE.findall(html))
            with self.subTest(run=rid):
                self.assertEqual(counts["it"], counts["en"],
                                 "%s: %d caselle in italiano, %d in inglese"
                                 % (rid, counts["it"], counts["en"]))

    def test_exported_guide_lists_every_step(self):
        for lg in LANGS:
            self.server.set_lang(lg)
            for rid, expected in sorted(self.steps.items()):
                with self.subTest(lang=lg, run=rid):
                    code, html = self.server.get_text("/export/%s" % rid)
                    self.assertEqual(code, 200)
                    self.assertEqual(len(EXPORT_STEP_RE.findall(html)), expected,
                                     "%s in %s: la guida esportata non ha tutti i passi" % (rid, lg))

    def test_export_is_downloaded_as_a_file(self):
        code, headers, _ = self.server.get("/export/kz")
        self.assertEqual(code, 200)
        self.assertIn("attachment", headers.get("Content-Disposition", ""))
        self.assertIn(".html", headers.get("Content-Disposition", ""))

    # -------------------------------------------------------------- contenuti
    def test_run_page_shows_the_localised_texts(self):
        route = harness.load_route("kz.json")
        first = route["phases"][0]["steps"][0]
        self.server.set_lang("en")
        code, html = self.server.get_text("/run/kz")
        self.assertIn(first["text"][:40].split("(")[0].strip()[:25], html)
        self.server.set_lang("it")
        code, html = self.server.get_text("/run/kz")
        self.assertIn(first["text_it"][:40].split("(")[0].strip()[:25], html)

    def test_glossary_is_rendered_only_in_italian(self):
        self.server.set_lang("it")
        code, html = self.server.get_text("/run/kz")
        self.assertIn("Glossario", html + "GLOS")
        self.assertIn("GLOS", html, "il glossario non compare nella versione italiana")
        self.server.set_lang("en")
        code, html = self.server.get_text("/run/kz")
        self.assertNotIn("📖 GLOS", html, "il glossario compare anche in inglese")

    def test_stat_table_has_the_expected_number_of_rows(self):
        for lg, key in (("en", "stat_table"), ("it", "stat_table_it")):
            self.server.set_lang(lg)
            for name in harness.route_files():
                rid = os.path.splitext(name)[0]
                table = harness.load_route(name)[key]
                with self.subTest(lang=lg, run=rid):
                    code, html = self.server.get_text("/run/%s" % rid)
                    body = html.split('<table class="stats">')[1].split("</table>")[0]
                    self.assertEqual(body.count("<tr>"), len(table["rows"]) + 1,
                                     "%s in %s: righe della tabella statistiche errate" % (rid, lg))

    def test_streamer_mode_adds_the_session_bar(self):
        self.server.post_json("/api/pref", {"mode": "gamer"})
        code, html = self.server.get_text("/run/kz")
        self.assertNotIn('class="sessionbar"', html)
        self.server.post_json("/api/pref", {"mode": "streamer"})
        code, html = self.server.get_text("/run/kz")
        self.assertIn('class="sessionbar"', html)
        self.server.post_json("/api/pref", {"mode": "gamer"})

    def test_progress_is_reflected_in_the_exported_guide(self):
        sids = harness.sids_of("kz")
        n = len(sids)
        self.server.post_json("/api/progress", {"run": "kz", "done": sids[:3]})
        code, html = self.server.get_text("/export/kz")
        self.assertEqual(html.count('<div class="step done">'), 3)
        self.assertEqual(html.count('<div class="step todo">'), n - 3)
        self.server.post_json("/api/run/reset", {"run": "kz"})

    def test_fonts_are_served(self):
        code, headers, body = self.server.get("/fonts/roboto-400.woff2")
        self.assertEqual(code, 200)
        self.assertEqual(headers.get("Content-Type"), "font/woff2")

    def test_zz_no_traceback_reached_stderr(self):
        self.assertEqual(self.server.tracebacks(), [],
                         "il server ha stampato un traceback durante il rendering")


class ThumbnailTest(harness.ServerTestCase, unittest.TestCase):
    """La pagina thumbnail e l'arte delle card in home.

    L'immagine la disegna il browser, quindi qui si verifica cio' che il server
    puo' garantire: che la pagina esista per ogni run, che porti il canvas e la
    configurazione, che il numero di trofei nel canvas venga dalla route (la
    thumbnail non deve poter mentire), e che ogni card della home abbia la sua
    tela con un run id valido.
    """

    @classmethod
    def setUpClass(cls):
        super(ThumbnailTest, cls).setUpClass()
        cls.routes = {os.path.splitext(f)[0]: harness.load_route(f)
                      for f in harness.route_files()}

    def tearDown(self):
        self.server.set_lang("it")

    def test_thumb_page_carries_canvas_and_config_for_every_run(self):
        for lg in LANGS:
            self.server.set_lang(lg)
            for rid, route in sorted(self.routes.items()):
                with self.subTest(lang=lg, run=rid):
                    code, html = self.server.get_text("/thumb/%s" % rid)
                    self.assertEqual(code, 200)
                    self.assertIn('id="thumbCanvas"', html)
                    self.assertIn("var CFG = ", html)
                    self.assertIn('"%s"' % route["trophy_total"], html.split("var CFG = ")[1][:400],
                                  "il numero di trofei nel canvas non viene dalla route")

    def test_thumb_page_of_unknown_run_is_404(self):
        code, _ = self.server.get_text("/thumb/questa-run-non-esiste")
        self.assertEqual(code, 404)

    def test_home_has_one_card_canvas_per_run(self):
        for lg in LANGS:
            self.server.set_lang(lg)
            with self.subTest(lang=lg):
                code, html = self.server.get_text("/")
                self.assertEqual(code, 200)
                found = set(re.findall(r'class="cardart" data-run="([a-z0-9]+)"', html))
                self.assertEqual(found, set(self.routes),
                                 "card della home e route non coincidono")
                self.assertIn("var ART = ", html)

    def test_every_design_icon_exists_in_the_art_js(self):
        """Un meta.thumb che nomina un'icona inesistente cadrebbe sul ripiego
        senza che nessuno se ne accorga: meglio un test rosso."""
        app, sandbox = harness.import_app_module("thumbs")
        try:
            for name in harness.route_files():
                icon = harness.load_route(name)["meta"]["thumb"]["icon"]
                with self.subTest(run=name):
                    self.assertIn("\n" + icon + ": function(", app.THUMB_ART_JS,
                                  "l'icona '%s' non esiste nel JS" % icon)
            self.assertIn("\ntrophy: function(", app.THUMB_ART_JS)
        finally:
            harness.drop_sandbox(sandbox)


if __name__ == "__main__":
    unittest.main(verbosity=2)
