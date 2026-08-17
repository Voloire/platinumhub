#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robustezza: payload malformati, run inesistenti, parametri fuori range.

Regola dell'app: qualunque cosa arrivi, il server deve rispondere con un codice
HTTP sensato e non deve mai stampare un traceback ne' chiudere la connessione
senza risposta.

La classe FixedInV4Test in fondo raccoglie i casi in cui questa regola una
volta NON era rispettata: erano segnati con @unittest.expectedFailure, i
difetti sono stati corretti e ora quei test passano davvero. Restano lì come
prova che non tornino indietro.

PortSelectionTest e' l'unico gruppo che dipende dal sistema operativo: su
Windows SO_REUSEADDR permetteva di legarsi a una porta gia' in ascolto, quindi
falliva solo la'. E' il motivo per cui la CI esegue questo file anche su Windows.
"""

import json
import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: E402

# Endpoint POST che accettano un campo "run".
RUN_POST_ENDPOINTS = ("/api/progress", "/api/notes", "/api/current", "/api/toast",
                      "/api/run/reset", "/api/session/start")


class RobustnessTest(harness.ServerTestCase, unittest.TestCase):

    # --------------------------------------------------------- payload rotti
    def test_malformed_json_body_is_rejected_with_400(self):
        for raw in (b"{not json", b"{", b'{"run": }', b"\x00\x01\x02", b'{"a":', b"<html>"):
            with self.subTest(body=raw[:12]):
                code, _, _ = self.server.post_raw("/api/progress", raw)
                self.assertEqual(code, 400, "payload rotto non respinto: %r" % raw)

    def test_empty_body_does_not_crash(self):
        for path in RUN_POST_ENDPOINTS:
            with self.subTest(path=path):
                code, _, _ = self.server.post_raw(path, b"")
                self.assertIn(code, (400, 404), "%s ha risposto %d al corpo vuoto" % (path, code))

    def test_body_with_wrong_content_type_is_still_parsed(self):
        code, _, _ = self.server.post_raw("/api/progress",
                                          json.dumps({"run": "kz", "done": []}),
                                          ctype="text/plain")
        self.assertEqual(code, 200)

    def test_unknown_run_never_returns_500(self):
        for path in RUN_POST_ENDPOINTS:
            for rid in ("", "nope", "../../etc/passwd", "kz ", "KZ", None, 5):
                with self.subTest(path=path, run=repr(rid)):
                    code, _ = self.server.post_json(path, {"run": rid, "done": [], "body": "x"})
                    self.assertEqual(code, 404, "%s con run=%r ha risposto %d" % (path, rid, code))

    def test_unknown_get_endpoints_are_404(self):
        for path in ("/api/nothing", "/run/nope", "/episodes/nope", "/session/nope",
                     "/export/nope", "/selftest/nope", "/overlay/nope", "/whatever",
                     "/run/", "/api/progress?run=", "/api/notes?run=nope"):
            with self.subTest(path=path):
                code, _ = self.server.get_text(path)
                self.assertEqual(code, 404, "%s ha risposto %d" % (path, code))

    def test_unknown_post_endpoint_is_404(self):
        code, res = self.server.post_json("/api/does-not-exist", {"run": "kz"})
        self.assertEqual(code, 404)

    # ------------------------------------------------------- overlay estremi
    def test_overlay_survives_every_out_of_range_parameter(self):
        cases = ["?pad=-999", "?pad=abc", "?pad=99999", "?pad=", "?pad=1e99",
                 "?w=1", "?w=abc", "?w=999999", "?w=-40",
                 "?hold=abc", "?hold=-5", "?hold=100000",
                 "?size=zzz", "?pos=zzz", "?next=0", "?next=banana", "?progress=0",
                 "?pad=24&w=800&hold=30&size=l&pos=tr&next=0&progress=0",
                 "?" + "x=1&" * 200]
        for q in cases:
            with self.subTest(query=q[:40]):
                code, html = self.server.get_text("/overlay/kz" + q)
                self.assertEqual(code, 200, "overlay%s ha risposto %d" % (q, code))
                self.assertIn("<html", html.lower())

    def test_overlay_clamps_padding_and_width(self):
        code, html = self.server.get_text("/overlay/kz?pad=-999")
        self.assertIn("--pad:0px", html.replace(" ", ""))
        code, html = self.server.get_text("/overlay/kz?pad=99999")
        self.assertIn("--pad:1200px", html.replace(" ", ""))
        code, html = self.server.get_text("/overlay/kz?w=1")
        self.assertIn("--maxw:240px", html.replace(" ", ""))

    # ------------------------------------------------------------- percorsi
    def test_font_path_traversal_is_blocked(self):
        for path in ("/fonts/../app.py", "/fonts/%2e%2e/app.py", "/fonts/../../etc/passwd",
                     "/fonts/../data/kz.json"):
            with self.subTest(path=path):
                code, body = self.server.get_text(path)
                self.assertEqual(code, 404)
                self.assertNotIn("PLATINUM HUB", body)
                self.assertNotIn("golden_rules", body)

    def test_language_switch_never_redirects_to_an_absolute_url(self):
        code, headers, _ = self.server.get("/lang/it?next=http://example.com/evil", follow=False)
        self.assertEqual(code, 303)
        self.assertEqual(headers.get("Location"), "/")
        code, headers, _ = self.server.get("/lang/zz?next=/run/kz", follow=False)
        self.assertEqual(code, 303, "una lingua sconosciuta deve comunque reindirizzare")

    def test_mode_switch_ignores_unknown_modes(self):
        self.server.post_json("/api/pref", {"mode": "gamer"})
        code, headers, _ = self.server.get("/mode/banana?next=/run/kz", follow=False)
        self.assertEqual(code, 303)
        code, prefs = self.server.get_json("/api/prefs")
        self.assertEqual(prefs["mode"], "gamer", "una modalita' inesistente e' stata salvata")

    # ------------------------------------------------------- dati esagerati
    def test_oversized_note_is_truncated_not_refused(self):
        code, _ = self.server.post_json("/api/notes", {"run": "kz", "body": "x" * 250000})
        self.assertEqual(code, 200)
        code, res = self.server.get_json("/api/notes?run=kz")
        self.assertLessEqual(len(res["body"]), 100000)

    def test_unicode_survives_the_round_trip(self):
        text = "日本語 · é à ü · ✓ 🏆 · <b>&amp;</b> · \"virgolette\" · 'apici'"
        self.server.post_json("/api/notes", {"run": "kz", "body": text})
        code, res = self.server.get_json("/api/notes?run=kz")
        self.assertEqual(res["body"], text)

    def test_html_in_a_note_is_escaped_in_the_page(self):
        self.server.post_json("/api/notes", {"run": "kz", "body": "<script>alert(1)</script>"})
        code, html = self.server.get_text("/run/kz")
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.server.post_json("/api/notes", {"run": "kz", "body": ""})

    def test_very_long_query_string_is_handled(self):
        code, _ = self.server.get_text("/api/progress?run=kz&" + "junk=1&" * 500)
        self.assertEqual(code, 200)

    # ------------------------------------------------------------ concorrenza
    def test_parallel_requests_do_not_break_the_server(self):
        """Il server e' ThreadingTCPServer: venti richieste insieme devono passare."""
        results = []
        lock = threading.Lock()

        def hit(i):
            try:
                code, _ = self.server.get_text("/api/summary" if i % 2 else "/run/kz")
            except Exception as e:
                code = "EXC:%s" % type(e).__name__
            with lock:
                results.append(code)

        threads = [threading.Thread(target=hit, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        self.assertEqual(len(results), 20)
        self.assertTrue(all(r == 200 for r in results), "risposte anomale: %s" % set(results))

    def test_parallel_progress_writes_leave_a_consistent_state(self):
        sids = harness.sids_of("sb")

        def write(i):
            try:
                self.server.post_json("/api/progress", {"run": "sb", "done": sids[:i + 1]})
            except Exception:
                pass

        threads = [threading.Thread(target=write, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        code, res = self.server.get_json("/api/progress?run=sb")
        self.assertEqual(code, 200)
        # lo stato finale e' quello di UNO dei writer, mai un ibrido corrotto:
        # l'insieme deve essere un prefisso della lista dei sid
        got = set(res["done"])
        self.assertIn(len(got), range(1, 11))
        self.assertEqual(got, set(sids[:len(got)]),
                         "lo stato salvato non corrisponde a nessuna delle scritture")

    # -------------------------------------------------------------- verifica
    def test_zz_no_traceback_reached_stderr(self):
        """Ultimo test della classe: nessuna delle richieste sopra deve aver alzato eccezioni."""
        time.sleep(0.3)
        tb = self.server.tracebacks()
        self.assertEqual(tb, [], "il server ha stampato un traceback: %s" % tb[:2])


class PortSelectionTest(unittest.TestCase):
    """
    pick_port(): se la porta di partenza e' occupata, l'app deve scivolare
    sulla successiva e stampare l'indirizzo giusto, non morire.
    """

    def test_app_falls_back_to_the_next_port_when_the_first_is_busy(self):
        import re as _re
        import socket
        import subprocess

        sandbox, port = harness.make_sandbox()
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        blocker.bind(("127.0.0.1", port))
        blocker.listen(1)
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        env["BROWSER"] = "/bin/true"
        # Senza questa riga l'app aprirebbe il database REALE dell'utente in
        # %LOCALAPPDATA%: e' gia' successo (la migrazione di schema e' partita
        # sul db vero durante i test). La sandbox e' obbligatoria, sempre.
        env["PLATINUM_HUB_DATA"] = sandbox
        env["PLATINUM_HUB_NO_UPDATE"] = "1"
        proc = subprocess.Popen([sys.executable, "-u", os.path.join(sandbox, "app.py")],
                                cwd=sandbox, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            chosen = None
            deadline = time.time() + harness.BOOT_TIMEOUT
            while time.time() < deadline and chosen is None:
                line = proc.stdout.readline().decode("utf-8", "replace")
                if not line:
                    break
                m = _re.search(r"http://127\.0\.0\.1:(\d+)/", line)
                if m:
                    chosen = int(m.group(1))
            self.assertIsNotNone(chosen, "l'app non ha stampato l'indirizzo su cui e' partita")
            self.assertNotEqual(chosen, port, "l'app dice di stare sulla porta gia' occupata")
            self.assertGreater(chosen, port)
            self.assertLess(chosen, port + 25, "pick_port ha superato la finestra di 25 porte")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
            proc.stdout.close()
            proc.stderr.close()
            blocker.close()
            harness.drop_sandbox(sandbox)


class FixedInV4Test(harness.ServerTestCase, unittest.TestCase):
    """
    Difetti reali gia' verificati sull'app. I test descrivono il comportamento
    CORRETTO e sono marcati come fallimenti attesi: quando app.py viene
    sistemata, unittest li segnala come "unexpected success" e basta togliere
    il decoratore.
    """

    def test_non_object_json_body_should_answer_400(self):
        """
        CORRETTO in v4.0 — app.py, do_POST (riga ~2678): il corpo viene deserializzato e
        usato subito con payload.get(...). Se il JSON e' valido ma non e' un
        oggetto (una lista, un numero, una stringa), parte un AttributeError:
        il server non risponde nulla e chiude la connessione, e su stderr
        compare il traceback. Atteso: 400.
        """
        for raw in (b"[1,2,3]", b'"stringa"', b"42", b"null", b"true"):
            code, _, _ = self.server.post_raw("/api/progress", raw)
            self.assertEqual(code, 400, "corpo %r non respinto correttamente" % raw)

    def test_non_numeric_fields_should_answer_400(self):
        """
        CORRETTO in v4.0 — app.py, do_POST: i campi numerici vengono convertiti con
        int()/float() senza protezione. Righe coinvolte:
          · /api/session/start   int(payload.get("lead") or 15)      (~2695)
          · /api/session/stop    int(payload.get("id") or 0)         (~2709)
          · /api/session/update  cast(payload[k]) per video_offset/lead (~2718)
          · /api/session/delete  int(payload.get("id") or 0)         (~2725)
          · /api/marker          int(step) e float(payload["tc"])    (~2765)
          · /api/marker/delete   int(session) e int(step)            (~2800)
          · /api/current (POST)  int(payload.get("step") or 0)       (~2812)
        Con un valore non numerico si ottiene ValueError, nessuna risposta HTTP
        e un traceback su stderr. Atteso: 400.
        """
        code, res = self.server.post_json("/api/session/start", {"run": "kz"})
        sid = res["session"]["id"]
        kz = harness.sids_of("kz")
        cases = [("/api/session/stop", {"id": "abc"}),
                 ("/api/session/update", {"id": sid, "video_offset": "abc"}),
                 ("/api/session/delete", {"id": "abc"}),
                 ("/api/marker", {"run": "kz", "session": sid, "kind": "done",
                                  "sid": 123, "tc": 1}),
                 ("/api/marker", {"run": "kz", "session": sid, "kind": "done",
                                  "sid": kz[1], "tc": "abc"}),
                 ("/api/marker/delete", {"session": "abc", "sid": kz[1]}),
                 ("/api/current", {"run": "kz", "sid": 42})]
        for path, payload in cases:
            code, _ = self.server.post_json(path, payload)
            self.assertEqual(code, 400, "%s con %r ha risposto %s" % (path, payload, code))

    def test_episodes_page_should_survive_an_out_of_range_marker(self):
        """
        CORRETTO in v4.0 — app.py, render_episodes() righe 1929-1930:

            ntro = len({m["step"] for m in marks if m["kind"] == "done"
                        and m["step"] is not None and steps[m["step"]].get("trophy")})

        qui manca il controllo  m["step"] < len(steps)  che invece c'e' poche
        righe piu' sotto. /api/marker accetta qualunque indice di passo, quindi
        basta un marker oltre la fine della checklist — cosa che succede da sola
        se una route perde dei passi in un aggiornamento — e la scheda Episodi
        smette di rispondere: IndexError, connessione chiusa senza risposta.
        Atteso: la pagina risponde 200 ignorando il marker orfano.
        """
        self.server.post_json("/api/run/reset", {"run": "bor"})
        code, res = self.server.post_json("/api/session/start", {"run": "bor"})
        sid = res["session"]["id"]
        # sid ben formato ma assente dalla route: e' l'orfano che nasce da solo
        # quando un aggiornamento toglie un passo
        self.server.post_json("/api/marker", {"run": "bor", "session": sid,
                                              "kind": "done", "sid": "s999999", "tc": 10})
        code, html = self.server.get_text("/episodes/bor")
        self.assertEqual(code, 200, "la pagina episodi non sopravvive a un marker orfano")


if __name__ == "__main__":
    unittest.main(verbosity=2)
