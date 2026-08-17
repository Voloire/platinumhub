#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coda dei comandi (le scorciatoie da tastiera) e parser delle combinazioni.

La coda e' il ponte fra la scorciatoia globale premuta a gioco aperto e la
pagina del browser: POST /api/cmd accoda, GET /api/pending consuma. I comandi
piu' vecchi di 10 secondi devono scadere, altrimenti la pagina esegue azioni
premute mezz'ora prima.

parse_hotkeys() e take_cmds() sono funzioni pure e vengono provate in
processo, importando app.py dalla sandbox (mai dalla cartella reale, cosi'
BASE — e quindi il database — restano nella cartella temporanea).
"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: E402

# Bitmask dei modificatori usate da RegisterHotKey su Windows.
MOD_ALT, MOD_CTRL, MOD_SHIFT, MOD_WIN = 0x0001, 0x0002, 0x0004, 0x0008


class HotkeyParserTest(unittest.TestCase):
    """parse_hotkeys(): non deve mai sollevare eccezioni, qualunque sia l'input."""

    @classmethod
    def setUpClass(cls):
        cls.app, cls.sandbox = harness.import_app_module()

    @classmethod
    def tearDownClass(cls):
        harness.drop_sandbox(cls.sandbox)

    def parse(self, spec):
        return self.app.parse_hotkeys(spec)

    def test_default_spec_produces_one_entry_per_action(self):
        parsed = self.parse(self.app.HOTKEYS_DEFAULT)
        self.assertEqual(len(parsed), 4)
        self.assertEqual(sorted(a for _, _, a, _ in parsed), ["mark", "next", "rec", "undo"])

    def test_modifier_bitmask_is_built_correctly(self):
        (mods, vk, action, label), = self.parse("ctrl+alt+shift+win+F5:rec")
        self.assertEqual(mods, MOD_ALT | MOD_CTRL | MOD_SHIFT | MOD_WIN)
        self.assertEqual(action, "rec")
        self.assertEqual(label, "ctrl+alt+shift+win+F5")

    def test_control_is_an_alias_of_ctrl(self):
        (a_mods, a_vk, _, _), = self.parse("control+alt+F9:rec")
        (b_mods, b_vk, _, _), = self.parse("ctrl+alt+F9:rec")
        self.assertEqual(a_mods, b_mods)
        self.assertEqual(a_vk, b_vk)

    def test_function_key_codes_cover_f1_to_f24(self):
        """F1 = 0x70 e F24 = 0x87: se sbagliano, la scorciatoia registra il tasto sbagliato."""
        (_, vk1, _, _), = self.parse("ctrl+F1:rec")
        self.assertEqual(vk1, 0x70)
        (_, vk24, _, _), = self.parse("ctrl+F24:rec")
        self.assertEqual(vk24, 0x87)
        for n in range(1, 25):
            with self.subTest(key="F%d" % n):
                (_, vk, _, _), = self.parse("ctrl+F%d:rec" % n)
                self.assertEqual(vk, 0x6F + n)

    def test_f25_is_not_a_function_key(self):
        self.assertEqual(self.parse("ctrl+F25:rec"), [])

    def test_letters_and_digits_are_accepted_as_the_main_key(self):
        (_, vk, _, _), = self.parse("ctrl+alt+g:next")
        self.assertEqual(vk, ord("G"))
        (_, vk, _, _), = self.parse("ctrl+alt+7:next")
        self.assertEqual(vk, ord("7"))

    def test_combination_without_a_modifier_is_refused(self):
        """Senza modificatore la scorciatoia ruberebbe il tasto a tutto il sistema."""
        for spec in ("F9:rec", "g:next", "F9:rec, F10:next"):
            with self.subTest(spec=spec):
                self.assertEqual(self.parse(spec), [], "accettata combinazione senza modificatori")

    def test_modifier_without_a_key_is_refused(self):
        self.assertEqual(self.parse("ctrl+alt:rec"), [])

    def test_unknown_actions_are_dropped(self):
        self.assertEqual(self.parse("ctrl+alt+F9:selfdestruct"), [])
        parsed = self.parse("ctrl+alt+F9:rec, ctrl+alt+F10:selfdestruct, ctrl+alt+F11:mark")
        self.assertEqual([a for _, _, a, _ in parsed], ["rec", "mark"])

    def test_action_matching_is_case_insensitive(self):
        parsed = self.parse("CTRL+ALT+F9:REC")
        self.assertEqual([a for _, _, a, _ in parsed], ["rec"])

    def test_malformed_input_never_raises(self):
        for spec in ("", None, ",,,", ":::", "ctrl+alt+F9", "rec", "   ", "ctrl+alt+F9:",
                     "a" * 500, "ctrl+alt+F9:rec:extra", "+++:rec", "ctrl++F9:rec"):
            with self.subTest(spec=repr(spec)[:30]):
                out = self.parse(spec)
                self.assertIsInstance(out, list)

    def test_a_second_colon_invalidates_the_combo(self):
        """
        rsplit(':', 1) prende come azione l'ultimo pezzo: la parte prima resta
        'ctrl+alt+F9:rec', che non e' un tasto valido, quindi la riga viene scartata
        invece di registrare una scorciatoia a caso.
        """
        self.assertEqual(self.parse("ctrl+alt+F9:rec:mark"), [])


class CommandQueueUnitTest(unittest.TestCase):
    """push_cmd()/take_cmds() provate direttamente, compresa la scadenza a 10 secondi."""

    @classmethod
    def setUpClass(cls):
        cls.app, cls.sandbox = harness.import_app_module()

    @classmethod
    def tearDownClass(cls):
        harness.drop_sandbox(cls.sandbox)

    def setUp(self):
        del self.app.CMDQ[:]

    def test_only_known_actions_are_queued(self):
        for action in self.app.HOTKEY_ACTIONS:
            with self.subTest(action=action):
                self.assertTrue(self.app.push_cmd(action))
        self.assertEqual(len(self.app.CMDQ), len(self.app.HOTKEY_ACTIONS))

    def test_unknown_action_is_refused_and_not_queued(self):
        self.assertFalse(self.app.push_cmd("nuke"))
        self.assertFalse(self.app.push_cmd(""))
        self.assertFalse(self.app.push_cmd(None))
        self.assertEqual(self.app.CMDQ, [])

    def test_take_drains_the_queue(self):
        self.app.push_cmd("rec")
        self.app.push_cmd("next")
        first = self.app.take_cmds()
        self.assertEqual([c["a"] for c in first], ["rec", "next"])
        self.assertEqual(self.app.take_cmds(), [], "la coda non e' stata svuotata")

    def test_commands_older_than_ten_seconds_expire(self):
        self.app.push_cmd("rec")
        self.app.push_cmd("next")
        self.app.CMDQ[0]["ts"] = time.time() - 11        # vecchio: deve sparire
        self.app.CMDQ[1]["ts"] = time.time() - 9         # ancora valido
        out = self.app.take_cmds()
        self.assertEqual([c["a"] for c in out], ["next"],
                         "i comandi scaduti sono stati consegnati alla pagina")

    def test_queue_is_capped_at_twenty_entries(self):
        for _ in range(60):
            self.app.push_cmd("mark")
        self.assertLessEqual(len(self.app.CMDQ), 20)

    def test_toast_expires_after_four_seconds(self):
        self.app.set_toast("kz", "messaggio")
        self.assertEqual(self.app.get_toast("kz"), "messaggio")
        self.app.TOASTS["kz"] = ("messaggio", time.time() - 5)
        self.assertEqual(self.app.get_toast("kz"), "")


class CommandQueueApiTest(harness.ServerTestCase, unittest.TestCase):
    """Gli stessi comportamenti visti dal lato HTTP."""

    def setUp(self):
        self.server.get_json("/api/pending?run=kz")      # coda pulita a ogni test

    def test_valid_actions_are_accepted(self):
        for action in ("rec", "next", "undo", "mark"):
            with self.subTest(action=action):
                code, res = self.server.post_json("/api/cmd", {"action": action, "run": "kz"})
                self.assertEqual(code, 200)
                self.assertEqual(res["action"], action)

    def test_invalid_action_is_rejected_with_400(self):
        for action in ("", "banana", "REC ", "start", None, 12):
            with self.subTest(action=repr(action)):
                code, res = self.server.post_json("/api/cmd", {"action": action, "run": "kz"})
                self.assertEqual(code, 400, "azione non valida accettata: %r" % (action,))
                self.assertIn("error", res)

    def test_action_is_matched_case_insensitively(self):
        code, res = self.server.post_json("/api/cmd", {"action": "REC", "run": "kz"})
        self.assertEqual(code, 200)
        self.assertEqual(res["action"], "rec")

    def test_pending_returns_then_empties_the_queue(self):
        self.server.post_json("/api/cmd", {"action": "rec", "run": "kz"})
        self.server.post_json("/api/cmd", {"action": "undo", "run": "kz"})
        code, res = self.server.get_json("/api/pending?run=kz")
        self.assertEqual(code, 200)
        self.assertEqual([c["a"] for c in res["cmds"]], ["rec", "undo"])
        code, res = self.server.get_json("/api/pending?run=kz")
        self.assertEqual(res["cmds"], [], "/api/pending ha restituito due volte lo stesso comando")

    def test_pending_carries_the_run_it_was_asked_for(self):
        code, res = self.server.get_json("/api/pending?run=lop")
        self.assertEqual(res["run"], "lop")

    def test_hotkeys_endpoint_reports_the_current_spec(self):
        code, res = self.server.get_json("/api/hotkeys")
        self.assertEqual(code, 200)
        for key in ("spec", "on", "active", "failed", "why", "platform"):
            self.assertIn(key, res)

    def test_hotkeys_spec_without_a_valid_combo_is_rejected(self):
        code, res = self.server.post_json("/api/hotkeys", {"spec": "F9:rec", "on": True})
        self.assertEqual(code, 400)
        code, res = self.server.post_json("/api/hotkeys", {"spec": "ciao mamma", "on": True})
        self.assertEqual(code, 400)

    def test_valid_hotkeys_spec_is_stored(self):
        spec = "ctrl+shift+F7:rec, ctrl+shift+F8:next"
        code, res = self.server.post_json("/api/hotkeys", {"spec": spec, "on": True})
        self.assertEqual(code, 200)
        self.assertEqual(res["spec"], spec)
        code, res = self.server.get_json("/api/hotkeys")
        self.assertEqual(res["spec"], spec)
        self.assertTrue(res["on"])
        # ripristino il default per non lasciare stato sporco alle altre classi
        self.server.post_json("/api/hotkeys", {"spec": harness_default(self.server), "on": True})


def harness_default(server):
    """Riporta la specifica di default leggendola dall'app stessa."""
    return "ctrl+alt+F9:rec, ctrl+alt+F10:next, ctrl+alt+F8:undo, ctrl+alt+F11:mark"


if __name__ == "__main__":
    unittest.main(verbosity=2)
