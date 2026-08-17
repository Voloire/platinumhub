#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Esegue tutta la suite di test di Platinum Hub.

    python3 tests/run_all.py            # tutto
    python3 tests/run_all.py -v         # con il nome di ogni test
    python3 tests/run_all.py data api   # solo i file che contengono 'data' o 'api'

Exit code 0 se tutto passa, diverso da zero se anche un solo test fallisce:
e' la convenzione a cui si allinea la pipeline di CI.

I test che richiedono Playwright NON sono qui dentro: stanno in
optional_playwright_ui.py e vanno lanciati a mano (vedi il file). La CI di base
gira con la sola libreria standard di Python 3.
"""

import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Ordine di esecuzione: prima i controlli sui dati (velocissimi e senza server),
# poi tutto quello che richiede di avviare l'app.
MODULES = [
    "test_data_integrity",
    "test_hotkeys",
    "test_api",
    "test_sessions",
    "test_render",
    "test_robustness",
]


def main(argv):
    verbosity = 2 if ("-v" in argv or "--verbose" in argv) else 1
    filters = [a for a in argv if not a.startswith("-")]
    modules = [m for m in MODULES if not filters or any(f in m for f in filters)]
    if not filters:
        # Prende anche eventuali test_*.py aggiunti dopo, senza toccare questo file.
        for name in sorted(os.listdir(HERE)):
            if name.startswith("test_") and name.endswith(".py"):
                mod = name[:-3]
                if mod not in modules:
                    modules.append(mod)

    loader = unittest.TestLoader()
    runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
    started = time.time()
    report = []
    failed = False

    for mod in modules:
        suite = loader.loadTestsFromName(mod)
        count = suite.countTestCases()
        print()
        print("=" * 72)
        print("  %s  (%d test)" % (mod, count))
        print("=" * 72)
        t0 = time.time()
        result = runner.run(suite)
        elapsed = time.time() - t0
        report.append((mod, count, len(result.failures), len(result.errors),
                       len(result.skipped), len(result.expectedFailures),
                       len(result.unexpectedSuccesses), elapsed))
        if not result.wasSuccessful():
            failed = True

    total = time.time() - started
    print()
    print("=" * 72)
    print("  RIEPILOGO")
    print("=" * 72)
    print("  %-24s %6s %6s %6s %6s %6s %8s" %
          ("file", "test", "fail", "err", "skip", "xfail", "tempo"))
    tot_tests = tot_xfail = 0
    for mod, count, nf, ne, ns, nx, nu, elapsed in report:
        tot_tests += count
        tot_xfail += nx
        print("  %-24s %6d %6d %6d %6d %6d %7.2fs"
              % (mod, count, nf, ne, ns, nx, elapsed))
        if nu:
            failed = True
            print("      !! %d test marcati come fallimenti attesi ora passano: "
                  "il difetto e' stato corretto, togliere @unittest.expectedFailure" % nu)
    print("  " + "-" * 68)
    print("  %-24s %6d %31s %7.2fs" % ("TOTALE", tot_tests, "", total))
    if tot_xfail:
        print()
        print("  Nota: %d test sono fallimenti attesi (difetti noti di app.py, "
              "documentati nel file test_robustness.py)." % tot_xfail)
    print()
    print("  ESITO: %s" % ("FALLITO" if failed else "TUTTO OK"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
