#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Le route vivono in SQLite: il bundle data/ e' solo il seme.

Il contratto: al primo avvio le route del bundle finiscono nella tabella
`routes` e l'app legge SOLO da li'; una route installata (dal catalogo, un
domani) con versione piu' alta non viene mai retrocessa dal bundle; l'ordine
delle card e' meta.order; una route con formato sconosciuto si rifiuta.
"""

import json
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: E402


class RoutesFromDbTest(harness.ServerTestCase, unittest.TestCase):
    """Il server serve le route dalla tabella, seminata dal bundle."""

    def _db(self):
        return sqlite3.connect(self.server.db_path())

    def test_bundle_routes_are_seeded_into_the_table(self):
        con = self._db()
        try:
            rows = {r[0]: (r[1], r[2]) for r in con.execute(
                "SELECT run_id, version, source FROM routes")}
        finally:
            con.close()
        expected = {os.path.splitext(f)[0] for f in harness.route_files()}
        self.assertEqual(set(rows), expected, "la tabella routes non riflette il bundle")
        for rid, (version, source) in rows.items():
            self.assertGreaterEqual(version, 1)
            self.assertEqual(source, "bundle")

    def test_structure_hash_is_stored_and_matches_the_algorithm(self):
        routes_mod, sandbox = harness.import_app_module("routes")
        try:
            con = self._db()
            try:
                stored = dict(con.execute("SELECT run_id, structure_hash FROM routes"))
            finally:
                con.close()
            for name in harness.route_files():
                rid = os.path.splitext(name)[0]
                with self.subTest(run=rid):
                    self.assertEqual(stored[rid],
                                     routes_mod.structure_hash(harness.load_route(name)))
        finally:
            harness.drop_sandbox(sandbox)

    def test_home_cards_follow_meta_order(self):
        code, html = self.server.get_text("/")
        self.assertEqual(code, 200)
        by_order = sorted(
            ((harness.load_route(f)["meta"]["order"], os.path.splitext(f)[0])
             for f in harness.route_files()))
        positions = [html.index('href="/run/%s"' % rid) for _, rid in by_order]
        self.assertEqual(positions, sorted(positions),
                         "le card della home non seguono meta.order")


class RouteVersioningTest(unittest.TestCase):
    """Una route del database con versione piu' alta vince sul bundle."""

    server = None

    @classmethod
    def setUpClass(cls):
        root, port = harness.make_sandbox()
        # Prepara nel db una kz "installata dal catalogo": versione 99,
        # titolo modificato, stessa struttura.
        route = harness.load_route("kz.json")
        route["game"] = "Khazan CATALOGO v99"
        route["meta"]["version"] = 99
        raw = json.dumps(route, ensure_ascii=False)
        con = sqlite3.connect(os.path.join(root, "platinum.db"))
        con.execute("""CREATE TABLE routes(
            run_id TEXT PRIMARY KEY, json TEXT NOT NULL,
            version INTEGER NOT NULL, format INTEGER NOT NULL,
            structure_hash TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'bundle',
            installed_at TEXT NOT NULL DEFAULT (datetime('now')))""")
        con.execute("INSERT INTO routes(run_id,json,version,format,structure_hash,source) "
                    "VALUES('kz',?,99,1,'x','catalog')", (raw,))
        con.commit()
        con.close()
        cls.server = harness.AppServer().start(sandbox=root, port=port)

    @classmethod
    def tearDownClass(cls):
        if cls.server is not None:
            cls.server.stop()
            cls.server = None

    def test_the_newer_installed_route_is_not_downgraded_by_the_bundle(self):
        code, summary = self.server.get_json("/api/summary")
        self.assertEqual(code, 200)
        kz = next(r for r in summary if r["run"] == "kz")
        self.assertEqual(kz["game"], "Khazan CATALOGO v99",
                         "il seed del bundle ha retrocesso una route piu' nuova")

    def test_the_other_routes_still_come_from_the_bundle(self):
        code, summary = self.server.get_json("/api/summary")
        self.assertEqual(len(summary), len(harness.route_files()))


class RouteFormatGuardTest(unittest.TestCase):
    """Una route in bundle con formato superiore al supportato non si importa."""

    def test_unknown_format_is_skipped_not_crashed(self):
        root, port = harness.make_sandbox()
        try:
            # kz nel bundle dichiara un formato futuro
            path = os.path.join(root, "data", "kz.json")
            with open(path, "r", encoding="utf-8") as f:
                route = json.load(f)
            route["meta"]["format"] = 999
            route["meta"]["version"] = 100
            with open(path, "w", encoding="utf-8") as f:
                json.dump(route, f, ensure_ascii=False)
            server = harness.AppServer().start(sandbox=root, port=port)
            try:
                code, summary = self.server_summary(server)
                self.assertEqual(code, 200)
                runs = {r["run"] for r in summary}
                self.assertNotIn("kz", runs, "una route di formato sconosciuto e' stata importata")
                self.assertEqual(len(runs), len(harness.route_files()) - 1)
            finally:
                server.stop()
        finally:
            harness.drop_sandbox(root)

    @staticmethod
    def server_summary(server):
        return server.get_json("/api/summary")


if __name__ == "__main__":
    unittest.main(verbosity=2)
