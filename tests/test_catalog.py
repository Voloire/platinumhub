#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Il catalogo delle route: check silenzioso, pulsante, installazione verificata.

Tutta la catena gira contro un catalogo di PROVA servito da un mini server
HTTP locale (PLATINUM_HUB_CATALOG): nessun test tocca la rete vera.

I contratti:
  * il check e' silenzioso: se il catalogo non risponde, available resta
    vuoto e nessuna pagina mostra errori;
  * l'installazione verifica lo SHA256 dichiarato dal manifest e la
    validazione severa PRIMA di toccare il database;
  * un aggiornamento di route non tocca i progressi (merge per sid);
  * una route ostile non si installa; e anche se finisse nel database,
    le pagine la renderizzano con l'escape, senza eseguire niente.
"""

import functools
import hashlib
import http.server
import json
import os
import socketserver
import sqlite3
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: E402


def make_zz_route(base_route, order=990):
    """Una route nuova di zecca ('zz') derivata da kz: id, sid e meta propri."""
    route = json.loads(json.dumps(base_route))
    route["game"] = "Zz Test Game"
    meta = route["meta"]
    meta.update({"id": "zz", "version": 1, "order": order})
    return route


def serve_catalog(root):
    """Mini server HTTP che serve la cartella del catalogo di prova."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, "http://127.0.0.1:%d/" % httpd.server_address[1]


def write_catalog(root, routes, sha_override=None):
    """Scrive routes/<id>.json e index.json come farebbe build_index.py."""
    os.makedirs(os.path.join(root, "routes"), exist_ok=True)
    entries = []
    for route in routes:
        meta = route["meta"]
        raw = json.dumps(route, ensure_ascii=False).encode("utf-8")
        with open(os.path.join(root, "routes", meta["id"] + ".json"), "wb") as f:
            f.write(raw)
        sha = hashlib.sha256(raw).hexdigest()
        if sha_override and meta["id"] in sha_override:
            sha = sha_override[meta["id"]]
        entries.append({"id": meta["id"], "file": "routes/%s.json" % meta["id"],
                        "version": meta["version"], "format": meta["format"],
                        "order": meta["order"], "game": route["game"],
                        "tagline": meta["tagline"],
                        "steps": sum(len(p["steps"]) for p in route["phases"]),
                        "trophy_total": route["trophy_total"],
                        "structure_hash": "n/a", "sha256": sha, "size": len(raw)})
    with open(os.path.join(root, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"catalog": "test", "format": 1, "routes": entries}, f, ensure_ascii=False)


class CatalogInstallTest(unittest.TestCase):
    """Nuova route e aggiornamento: la catena intera contro il catalogo di prova."""

    server = None
    httpd = None

    @classmethod
    def setUpClass(cls):
        kz = harness.load_route("kz.json")
        # una route nuova (zz) e un aggiornamento SOLO testuale di kz (v2)
        kz2 = json.loads(json.dumps(kz))
        kz2["meta"]["version"] = 2
        kz2["phases"][0]["steps"][0]["text"] = "TESTO CORRETTO DALLA V2 DEL CATALOGO"
        kz2["phases"][0]["steps"][0]["text_it"] = "TESTO CORRETTO DALLA V2 DEL CATALOGO"
        cls.cat_root = harness.make_sandbox()[0]      # solo per avere una temp dir pulita
        write_catalog(cls.cat_root, [make_zz_route(kz), kz2])
        cls.httpd, base = serve_catalog(cls.cat_root)
        root, port = harness.make_sandbox()
        cls.server = harness.AppServer().start(sandbox=root, port=port,
                                               env={"PLATINUM_HUB_CATALOG": base})

    @classmethod
    def tearDownClass(cls):
        if cls.server is not None:
            cls.server.stop()
            cls.server = None
        if cls.httpd is not None:
            cls.httpd.shutdown()
            cls.httpd.server_close()

    def _check(self):
        code, res = self.server.post_json("/api/routes/check", {})
        self.assertEqual(code, 200)
        return res

    def test_01_check_lists_the_new_and_updated_routes(self):
        res = self._check()
        found = {e["id"]: e for e in res["available"]}
        self.assertIn("zz", found, "la route nuova non e' stata offerta")
        self.assertIn("kz", found, "l'aggiornamento di kz non e' stato offerto")
        self.assertIsNone(found["zz"]["installed"])
        self.assertEqual(found["kz"]["installed"], 1)

    def test_02_installing_a_new_route_makes_it_playable(self):
        self._check()
        code, res = self.server.post_json("/api/routes/install", {"id": "zz"})
        self.assertEqual(code, 200, res)
        code, summary = self.server.get_json("/api/summary")
        self.assertIn("zz", {r["run"] for r in summary})
        code, html = self.server.get_text("/run/zz")
        self.assertEqual(code, 200)
        # e i progressi si salvano subito, come per qualunque run
        sids = harness.sids_of("kz")     # zz ha gli stessi sid di kz
        code, res = self.server.post_json("/api/progress", {"run": "zz", "done": sids[:2]})
        self.assertEqual(code, 200)

    def test_03_updating_a_route_keeps_the_progress(self):
        kz_sids = harness.sids_of("kz")
        done = sorted(kz_sids[:7])
        self.server.post_json("/api/progress", {"run": "kz", "done": done})
        self._check()
        code, res = self.server.post_json("/api/routes/install", {"id": "kz"})
        self.assertEqual(code, 200, res)
        code, back = self.server.get_json("/api/progress?run=kz")
        self.assertEqual(sorted(back["done"]), done,
                         "l'aggiornamento della route ha toccato i progressi")
        code, html = self.server.get_text("/run/kz")
        self.assertIn("TESTO CORRETTO DALLA V2 DEL CATALOGO", html,
                      "il testo aggiornato non e' arrivato")

    def test_04_after_install_nothing_more_is_offered(self):
        res = self._check()
        self.assertEqual(res["available"], [],
                         "il catalogo offre ancora route gia' installate")

    def test_05_no_tracebacks_in_the_whole_chain(self):
        self.assertEqual(self.server.tracebacks(), [])


class CatalogRejectsTest(unittest.TestCase):
    """SHA sbagliato e route ostile: l'installazione deve rifiutare."""

    server = None
    httpd = None

    @classmethod
    def setUpClass(cls):
        kz = harness.load_route("kz.json")
        bad_sha = make_zz_route(kz, order=991)
        hostile = make_zz_route(kz, order=992)
        hostile["meta"]["id"] = "evil"
        # tipo di tag fuori whitelist: finirebbe in un attributo class
        hostile["phases"][0]["steps"][0]["tags"] = [
            {"type": 'x"><script>alert(1)</script>', "label": "x", "label_it": "x"}]
        cls.cat_root = harness.make_sandbox()[0]
        write_catalog(cls.cat_root, [bad_sha, hostile],
                      sha_override={"zz": "0" * 64})
        cls.httpd, base = serve_catalog(cls.cat_root)
        root, port = harness.make_sandbox()
        cls.server = harness.AppServer().start(sandbox=root, port=port,
                                               env={"PLATINUM_HUB_CATALOG": base})

    @classmethod
    def tearDownClass(cls):
        if cls.server is not None:
            cls.server.stop()
            cls.server = None
        if cls.httpd is not None:
            cls.httpd.shutdown()
            cls.httpd.server_close()

    def test_wrong_sha256_is_refused(self):
        self.server.post_json("/api/routes/check", {})
        code, res = self.server.post_json("/api/routes/install", {"id": "zz"})
        self.assertEqual(code, 400)
        self.assertIn("SHA256", res["msg"])
        code, summary = self.server.get_json("/api/summary")
        self.assertNotIn("zz", {r["run"] for r in summary})

    def test_hostile_route_is_refused_by_validation(self):
        self.server.post_json("/api/routes/check", {})
        code, res = self.server.post_json("/api/routes/install", {"id": "evil"})
        self.assertEqual(code, 400)
        code, summary = self.server.get_json("/api/summary")
        self.assertNotIn("evil", {r["run"] for r in summary})

    def test_unknown_id_is_refused(self):
        for bad in ("nope", "../x", 42, None):
            code, _ = self.server.post_json("/api/routes/install", {"id": bad})
            self.assertEqual(code, 400)


class SilentOfflineTest(unittest.TestCase):
    """Catalogo irraggiungibile: nessun errore, nessun rumore. E' il contratto."""

    server = None

    @classmethod
    def setUpClass(cls):
        root, port = harness.make_sandbox()
        # una porta chiusa: il check deve fallire in silenzio
        cls.server = harness.AppServer().start(
            sandbox=root, port=port,
            env={"PLATINUM_HUB_CATALOG": "http://127.0.0.1:9/"})

    @classmethod
    def tearDownClass(cls):
        if cls.server is not None:
            cls.server.stop()
            cls.server = None

    def test_check_fails_silently_and_home_stays_clean(self):
        code, res = self.server.post_json("/api/routes/check", {})
        self.assertEqual(code, 200)
        self.assertEqual(res["available"], [])
        code, html = self.server.get_text("/")
        self.assertEqual(code, 200)
        self.assertNotIn("Traceback", html)
        self.assertEqual(self.server.tracebacks(), [],
                         "il catalogo offline ha prodotto rumore su stderr")


class HostileContentEscapeTest(unittest.TestCase):
    """
    Difesa in profondita': anche se una route ostile FINISSE nel database
    (bypassando la validazione), le pagine devono renderizzarla con l'escape.
    La si infila direttamente in SQLite, come farebbe solo un attaccante.
    """

    server = None
    PAYLOAD = "<script>alert('xss-1337')</script>"

    @classmethod
    def setUpClass(cls):
        route = make_zz_route(harness.load_route("kz.json"), order=993)
        route["meta"]["id"] = "hx"
        route["game"] = "Hostile " + cls.PAYLOAD
        step = route["phases"][0]["steps"][0]
        step["text"] = "testo " + cls.PAYLOAD
        step["text_it"] = "testo it " + cls.PAYLOAD
        step["loc"] = step["loc_it"] = "loc " + cls.PAYLOAD
        route["phases"][0]["title"] = route["phases"][0]["title_it"] = "fase " + cls.PAYLOAD
        route["golden_rules"] = route["golden_rules_it"] = ["regola " + cls.PAYLOAD]
        root, port = harness.make_sandbox()
        con = sqlite3.connect(os.path.join(root, "platinum.db"))
        con.execute("""CREATE TABLE routes(
            run_id TEXT PRIMARY KEY, json TEXT NOT NULL,
            version INTEGER NOT NULL, format INTEGER NOT NULL,
            structure_hash TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'bundle',
            installed_at TEXT NOT NULL DEFAULT (datetime('now')))""")
        con.execute("INSERT INTO routes(run_id,json,version,format,structure_hash,source) "
                    "VALUES('hx',?,1,1,'x','catalog')",
                    (json.dumps(route, ensure_ascii=False),))
        con.commit()
        con.close()
        cls.server = harness.AppServer().start(sandbox=root, port=port)

    @classmethod
    def tearDownClass(cls):
        if cls.server is not None:
            cls.server.stop()
            cls.server = None

    def test_no_page_lets_the_script_through(self):
        for path in ("/", "/run/hx", "/episodes/hx", "/session/hx",
                     "/export/hx", "/overlay/hx", "/thumb/hx", "/selftest/hx"):
            with self.subTest(page=path):
                code, html = self.server.get_text(path)
                self.assertEqual(code, 200, "%s ha risposto %d" % (path, code))
                self.assertNotIn(self.PAYLOAD, html,
                                 "%s ha emesso lo script senza escape" % path)
                self.assertNotIn("alert('xss-1337')</script>", html,
                                 "%s ha emesso lo script senza escape" % path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
