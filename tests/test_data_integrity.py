#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IL TEST PIU' IMPORTANTE DELLA SUITE.

I progressi di Platinum Hub sono una stringa posizionale di '0' e '1' lunga
quanto la checklist della route. Non esiste nessun identificativo di passo:
la posizione E' il passo. Di conseguenza, se un file di data/ perde un campo,
cambia forma o presenta un numero di elementi diverso fra inglese e italiano,
i salvataggi si spostano di posizione e si corrompono in silenzio: nessun
errore a schermo, solo spunte sbagliate.

Questi test confrontano OGNI file di data/ con la forma della route di
riferimento (kz.json) e con gli invarianti che l'app da' per scontati.

Non serve nessun server: si leggono solo i file JSON (in sola lettura).
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: E402

# Tipi di tag ammessi dal CSS e dal rendering dell'app.
ALLOWED_TAG_TYPES = {"trophy", "miss", "coll", "build", "quest"}

# Campi obbligatori per ciascun livello della struttura.
STEP_FIELDS = ("text", "loc", "tags", "trophy", "text_it", "loc_it")
TAG_FIELDS = ("type", "label", "label_it")
PHASE_FIELDS = ("title", "note", "title_it", "note_it")

# Coppie di liste che devono avere la stessa lunghezza nelle due lingue.
PARALLEL_LISTS = (("golden_rules", "golden_rules_it"),
                  ("build_bullets", "build_bullets_it"))

# Segnaposto che non devono mai finire nei testi pubblicati.
PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|FIXME|XXX+|PLACEHOLDER|lorem ipsum)\b", re.I)


class RouteShapeTest(unittest.TestCase):
    """Ogni file di data/ deve avere la stessa forma di kz.json."""

    @classmethod
    def setUpClass(cls):
        cls.files = harness.route_files()
        cls.routes = {name: harness.load_route(name) for name in cls.files}
        cls.reference = cls.routes[harness.REFERENCE_ROUTE]

    # --------------------------------------------------------------- presenza
    def test_every_registered_run_has_its_data_file(self):
        """Il registro RUNS di app.py e data/ devono coincidere."""
        on_disk = {os.path.splitext(f)[0] for f in self.files}
        self.assertEqual(sorted(on_disk), sorted(harness.RUN_IDS),
                         "data/ e il registro RUNS non coincidono")

    def test_top_level_keys_match_the_reference_route(self):
        """Nessuna chiave di primo livello mancante o di troppo rispetto a kz.json."""
        expected = set(self.reference)
        for name, route in self.routes.items():
            with self.subTest(file=name):
                missing = sorted(expected - set(route))
                extra = sorted(set(route) - expected)
                self.assertEqual(missing, [], "chiavi mancanti in %s" % name)
                self.assertEqual(extra, [], "chiavi non previste in %s" % name)

    def test_top_level_field_types_match_the_reference_route(self):
        """Stesso tipo Python per ogni chiave di primo livello."""
        for name, route in self.routes.items():
            for key, ref_value in self.reference.items():
                with self.subTest(file=name, key=key):
                    # Confronto i nomi dei tipi: il messaggio d'errore resta leggibile
                    # anche quando il valore e' un glossario da 150 voci.
                    self.assertEqual(type(route[key]).__name__, type(ref_value).__name__,
                                     "%s.%s e' %s, dovrebbe essere %s (come in %s)"
                                     % (name, key, type(route[key]).__name__,
                                        type(ref_value).__name__, harness.REFERENCE_ROUTE))

    # ------------------------------------------------------------------ passi
    def test_every_step_has_all_required_fields(self):
        """
        Un passo senza text_it/loc_it manda l'italiano in fallback silenzioso,
        un passo senza 'trophy' falsa il conteggio dei trofei.
        """
        for name, route in self.routes.items():
            for pi, phase in enumerate(route["phases"]):
                for si, step in enumerate(phase["steps"]):
                    for field in STEP_FIELDS:
                        with self.subTest(file=name, phase=pi, step=si, field=field):
                            self.assertIn(field, step,
                                          "%s fase %d passo %d: manca '%s'"
                                          % (name, pi, si, field))
                    with self.subTest(file=name, phase=pi, step=si, field="types"):
                        self.assertIsInstance(step["tags"], list)
                        self.assertIsInstance(step["trophy"], bool)

    def test_every_tag_has_all_required_fields(self):
        for name, route in self.routes.items():
            for pi, phase in enumerate(route["phases"]):
                for si, step in enumerate(phase["steps"]):
                    for ti, tag in enumerate(step.get("tags", [])):
                        for field in TAG_FIELDS:
                            with self.subTest(file=name, phase=pi, step=si, tag=ti, field=field):
                                self.assertIn(field, tag,
                                              "%s fase %d passo %d tag %d: manca '%s'"
                                              % (name, pi, si, ti, field))

    def test_every_phase_has_all_required_fields(self):
        for name, route in self.routes.items():
            for pi, phase in enumerate(route["phases"]):
                for field in PHASE_FIELDS:
                    with self.subTest(file=name, phase=pi, field=field):
                        self.assertIn(field, phase,
                                      "%s fase %d: manca '%s'" % (name, pi, field))
                with self.subTest(file=name, phase=pi, field="steps"):
                    self.assertIsInstance(phase.get("steps"), list)
                    self.assertGreater(len(phase["steps"]), 0,
                                       "%s fase %d non ha passi" % (name, pi))

    def test_tag_types_are_from_the_known_set(self):
        """Un type sconosciuto produce una classe CSS inesistente: tag invisibile."""
        for name, route in self.routes.items():
            for pi, phase in enumerate(route["phases"]):
                for si, step in enumerate(phase["steps"]):
                    for tag in step.get("tags", []):
                        with self.subTest(file=name, phase=pi, step=si, type=tag.get("type")):
                            self.assertIn(tag.get("type"), ALLOWED_TAG_TYPES,
                                          "%s fase %d passo %d: tipo tag '%s' non ammesso"
                                          % (name, pi, si, tag.get("type")))

    # ------------------------------------------------------- parita' bilingue
    def test_parallel_lists_have_the_same_length_in_both_languages(self):
        """
        golden_rules / golden_rules_it e build_bullets / build_bullets_it:
        l'app sceglie la lista in base alla lingua, quindi lunghezze diverse
        significano contenuti che spariscono passando da EN a IT.
        """
        for name, route in self.routes.items():
            for en_key, it_key in PARALLEL_LISTS:
                with self.subTest(file=name, pair=(en_key, it_key)):
                    self.assertEqual(len(route.get(en_key) or []), len(route.get(it_key) or []),
                                     "%s: %s ha %d voci, %s ne ha %d"
                                     % (name, en_key, len(route.get(en_key) or []),
                                        it_key, len(route.get(it_key) or [])))

    def test_build_bullets_have_heading_and_text_in_both_languages(self):
        """render_run legge bl['h'] e bl['t']: una chiave mancante e' un KeyError a schermo."""
        for name, route in self.routes.items():
            for key in ("build_bullets", "build_bullets_it"):
                for bi, bullet in enumerate(route.get(key) or []):
                    with self.subTest(file=name, key=key, bullet=bi):
                        self.assertIsInstance(bullet, dict)
                        self.assertIn("h", bullet)
                        self.assertIn("t", bullet)

    def test_stat_tables_have_the_same_shape_in_both_languages(self):
        """Stesso numero di colonne e di righe, e ogni riga larga quanto l'intestazione."""
        for name, route in self.routes.items():
            en, it = route["stat_table"], route["stat_table_it"]
            with self.subTest(file=name, what="keys"):
                self.assertIn("columns", en)
                self.assertIn("rows", en)
                self.assertIn("note", en)
                self.assertIn("columns", it)
                self.assertIn("rows", it)
                self.assertIn("note", it)
            with self.subTest(file=name, what="columns"):
                self.assertEqual(len(en["columns"]), len(it["columns"]),
                                 "%s: colonne EN %d vs IT %d"
                                 % (name, len(en["columns"]), len(it["columns"])))
            with self.subTest(file=name, what="rows"):
                self.assertEqual(len(en["rows"]), len(it["rows"]),
                                 "%s: righe EN %d vs IT %d"
                                 % (name, len(en["rows"]), len(it["rows"])))
            for lang_key, table in (("stat_table", en), ("stat_table_it", it)):
                width = len(table["columns"])
                for ri, row in enumerate(table["rows"]):
                    with self.subTest(file=name, table=lang_key, row=ri):
                        self.assertEqual(len(row), width,
                                         "%s %s riga %d: %d celle su %d colonne"
                                         % (name, lang_key, ri, len(row), width))

    def test_glossary_is_a_dict_and_unverified_is_a_list(self):
        """
        glossary_it deve essere un dizionario: render_run fa gloss.items().
        Se qualcuno lo salva come lista di coppie, l'app risponde 500.
        E' gia' successo davvero.
        """
        for name, route in self.routes.items():
            with self.subTest(file=name, key="glossary_it"):
                self.assertEqual(type(route.get("glossary_it")).__name__, "dict",
                                 "%s: glossary_it e' %s, deve essere dict "
                                 "(una lista di coppie manda l'app in 500)"
                                 % (name, type(route.get("glossary_it")).__name__))
            with self.subTest(file=name, key="unverified_it"):
                self.assertEqual(type(route.get("unverified_it")).__name__, "list",
                                 "%s: unverified_it e' %s, deve essere list"
                                 % (name, type(route.get("unverified_it")).__name__))

    # -------------------------------------------------------------- conteggi
    def test_trophy_total_is_at_least_the_number_of_trophy_steps(self):
        """trophy_total e' l'intestazione della pagina: non puo' essere meno dei trofei reali."""
        for name, route in self.routes.items():
            trophy_steps = sum(1 for p in route["phases"] for s in p["steps"] if s.get("trophy"))
            with self.subTest(file=name):
                self.assertIsInstance(route["trophy_total"], int,
                                      "%s: trophy_total non e' un intero" % name)
                self.assertGreaterEqual(route["trophy_total"], trophy_steps,
                                        "%s: trophy_total=%s ma i passi con trophy sono %d"
                                        % (name, route["trophy_total"], trophy_steps))

    def test_step_count_is_positive_and_stable(self):
        """La lunghezza della stringa di bit dipende da questo numero."""
        for name, route in self.routes.items():
            with self.subTest(file=name):
                n = harness.route_step_count(route)
                self.assertGreater(n, 0, "%s non ha passi" % name)
                self.assertEqual(n, len([s for p in route["phases"] for s in p["steps"]]))

    def test_the_two_languages_expose_the_same_number_of_steps(self):
        """
        Il cuore del problema: la checklist italiana e quella inglese devono
        avere esattamente lo stesso numero di caselle, altrimenti la stringa
        posizionale dei progressi si sposta.
        """
        for name, route in self.routes.items():
            en = [s for p in route["phases"] for s in p["steps"] if str(s.get("text", "")).strip()]
            it = [s for p in route["phases"] for s in p["steps"]
                  if str(s.get("text_it") or s.get("text") or "").strip()]
            with self.subTest(file=name):
                self.assertEqual(len(en), len(it),
                                 "%s: %d passi in EN, %d in IT" % (name, len(en), len(it)))
                self.assertEqual(len(en), harness.route_step_count(route),
                                 "%s: passi con testo diversi dal totale" % name)

    # ------------------------------------------------------------ testi vuoti
    def test_no_text_field_is_empty(self):
        for name, route in self.routes.items():
            for pi, phase in enumerate(route["phases"]):
                for field in ("title", "title_it", "note", "note_it"):
                    with self.subTest(file=name, phase=pi, field=field):
                        self.assertTrue(str(phase.get(field, "")).strip(),
                                        "%s fase %d: campo '%s' vuoto" % (name, pi, field))
                for si, step in enumerate(phase["steps"]):
                    for field in ("text", "loc", "text_it", "loc_it"):
                        with self.subTest(file=name, phase=pi, step=si, field=field):
                            self.assertTrue(str(step.get(field, "")).strip(),
                                            "%s fase %d passo %d: campo '%s' vuoto"
                                            % (name, pi, si, field))
                    for ti, tag in enumerate(step.get("tags", [])):
                        for field in ("type", "label", "label_it"):
                            with self.subTest(file=name, phase=pi, step=si, tag=ti, field=field):
                                self.assertTrue(str(tag.get(field, "")).strip(),
                                                "%s fase %d passo %d tag %d: '%s' vuoto"
                                                % (name, pi, si, ti, field))

    def test_no_field_holds_the_placeholder_of_another_field(self):
        """
        Errore tipico del copia-incolla: la traduzione di 'text' finisce dentro
        'loc_it' (o viceversa). L'app non se ne accorge, l'utente si'.
        """
        for name, route in self.routes.items():
            for pi, phase in enumerate(route["phases"]):
                with self.subTest(file=name, phase=pi, what="phase"):
                    self.assertNotEqual(phase.get("title_it"), phase.get("note"),
                                        "%s fase %d: title_it e' la nota EN" % (name, pi))
                    self.assertNotEqual(phase.get("note_it"), phase.get("title"),
                                        "%s fase %d: note_it e' il titolo EN" % (name, pi))
                    self.assertNotEqual(phase.get("note_it"), phase.get("title_it"),
                                        "%s fase %d: note_it e' il titolo IT" % (name, pi))
                for si, step in enumerate(phase["steps"]):
                    with self.subTest(file=name, phase=pi, step=si, what="step"):
                        self.assertNotEqual(step.get("text_it"), step.get("loc"),
                                            "%s fase %d passo %d: text_it e' la loc EN"
                                            % (name, pi, si))
                        self.assertNotEqual(step.get("text_it"), step.get("loc_it"),
                                            "%s fase %d passo %d: text_it e' la loc IT"
                                            % (name, pi, si))
                        self.assertNotEqual(step.get("loc_it"), step.get("text"),
                                            "%s fase %d passo %d: loc_it e' il testo EN"
                                            % (name, pi, si))
                        self.assertNotEqual(step.get("loc_it"), step.get("text_it"),
                                            "%s fase %d passo %d: loc_it e' il testo IT"
                                            % (name, pi, si))

    def test_no_field_contains_a_leftover_marker(self):
        """Nessun TODO/TBD/FIXME sfuggito nei testi pubblicati."""
        for name in self.files:
            with open(os.path.join(harness.DATA_DIR, name), "r", encoding="utf-8") as f:
                raw = f.read()
            with self.subTest(file=name):
                found = PLACEHOLDER_RE.findall(raw)
                self.assertEqual(found, [], "%s contiene segnaposto: %s" % (name, found[:5]))

    def test_glossary_entries_are_non_empty_strings(self):
        for name, route in self.routes.items():
            gloss = route.get("glossary_it")
            if not isinstance(gloss, dict):
                continue        # gia' segnalato dal test sul tipo: qui non ha senso insistere
            for key, value in gloss.items():
                with self.subTest(file=name, term=key):
                    self.assertTrue(str(key).strip(), "%s: termine di glossario vuoto" % name)
                    self.assertTrue(str(value).strip(),
                                    "%s: traduzione vuota per '%s'" % (name, key))


if __name__ == "__main__":
    unittest.main(verbosity=2)
