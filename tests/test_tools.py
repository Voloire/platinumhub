#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gli strumenti di rilascio in tools/, provati come li lancia la pipeline.

Qui conta il MODO in cui vengono eseguiti, non solo cosa restituiscono:
changelog_extract.py viene lanciato come processo separato con lo stdout
rediretto in un file, ed e' esattamente in quel passaggio che si e' rotto il
rilascio della 4.1.0. Chiamare la funzione in processo non lo avrebbe scoperto,
perche' il difetto stava nella codifica di stdout, non nell'estrazione.

Questi test hanno senso soprattutto sul runner Windows: su Linux la codifica di
default e' UTF-8 e passano comunque.
"""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: E402

TOOL = os.path.join(harness.APP_DIR, "tools", "changelog_extract.py")

# U+2328 (tastiera) non esiste in cp1252, che e' la codifica che Windows usa per
# stdout quando nessuno dice il contrario. La lettera accentata invece in cp1252
# c'e': serve a distinguere "non sa scrivere UTF-8" da "non sa scrivere emoji".
CHANGELOG = """# Changelog

## [Non rilasciato]

## [9.9.9] - 2026-01-01

### Aggiunto
- Pannello ⌨ delle scorciatoie, con le combinazioni già attive.

## [9.9.8] - 2025-12-31

### Corretto
- Qualcosa d'altro.
"""


class ChangelogExtractCliTest(unittest.TestCase):
    """Lanciato come lo lancia release.yml: processo separato, stdout rediretto."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="platinumhub-tools-")
        cls.path = os.path.join(cls.dir, "CHANGELOG.md")
        with open(cls.path, "w", encoding="utf-8") as fh:
            fh.write(CHANGELOG)

    @classmethod
    def tearDownClass(cls):
        try:
            os.remove(cls.path)
            os.rmdir(cls.dir)
        except OSError:
            pass

    def run_tool(self, version):
        """Ambiente senza PYTHONIOENCODING e senza PYTHONUTF8.

        Entrambe forzerebbero UTF-8 e nasconderebbero il difetto: la pipeline
        non le imposta in quel passo, quindi il test non deve impostarle."""
        env = dict(os.environ)
        env.pop("PYTHONIOENCODING", None)
        env.pop("PYTHONUTF8", None)
        return subprocess.run([sys.executable, TOOL, version, "--file", self.path],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

    def test_a_section_with_an_emoji_is_written_without_dying(self):
        res = self.run_tool("9.9.9")
        self.assertEqual(res.returncode, 0,
                         "estrazione fallita: %s" % res.stderr.decode("utf-8", "replace"))
        out = res.stdout.decode("utf-8")
        self.assertIn("⌨", out, "il carattere fuori da cp1252 non e' arrivato nell'uscita")
        self.assertIn("già", out)

    def test_the_output_is_utf8_whatever_the_platform_default_is(self):
        res = self.run_tool("9.9.9")
        self.assertEqual(res.returncode, 0)
        # Deve decodificare come UTF-8 senza errori: e' cio' che si aspetta
        # `gh release create --notes-file`.
        res.stdout.decode("utf-8")

    def test_only_the_asked_section_comes_out(self):
        res = self.run_tool("9.9.9")
        out = res.stdout.decode("utf-8")
        self.assertIn("Pannello", out)
        self.assertNotIn("Qualcosa d'altro", out, "ha estratto anche la versione precedente")
        self.assertNotIn("Non rilasciato", out)

    def test_the_v_prefix_is_accepted(self):
        res = self.run_tool("v9.9.9")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Pannello", res.stdout.decode("utf-8"))

    def test_a_missing_section_fails_instead_of_publishing_nothing(self):
        res = self.run_tool("1.2.3")
        self.assertNotEqual(res.returncode, 0,
                            "una versione senza sezione deve fermare il rilascio")


if __name__ == "__main__":
    unittest.main(verbosity=2)
