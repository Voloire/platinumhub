#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test: start Platinum Hub and check that it answers.

Used by .github/workflows/ci.yml (on ubuntu-latest and windows-latest) and by
.github/workflows/release.yml (against the PyInstaller executable, before the
GitHub Release is published).

    python tools/smoke_check.py
    python tools/smoke_check.py --exe dist/PlatinumHub/PlatinumHub.exe

Zero third-party imports on purpose: this script also proves that the
application runs on a bare Python 3 installation.

The test suite can reuse the launcher:

    from tools.smoke_check import start_app
    with start_app() as base_url:
        ...
"""

from __future__ import annotations

import argparse
import contextlib
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# app.py starts at PORT_START and walks forward until it finds a free port.
PORT_START = 8787
PORT_RANGE = 25

# How long we wait for the server to come up (PyInstaller one-folder is slow
# to boot the first time on a cold Windows runner).
BOOT_TIMEOUT_S = 90.0


def _no_browser_env() -> dict:
    """Environment that stops webbrowser.open() from launching anything.

    A no-op command is used rather than an invalid one: webbrowser.open()
    walks the whole browser list until one of them succeeds, so the no-op
    has to actually succeed.
    """
    env = dict(os.environ)
    env["BROWSER"] = "cmd /c rem" if os.name == "nt" else "true"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _http_get(url: str, timeout: float = 10.0):
    """Return (status, body_bytes, content_type). Raises on transport errors."""
    req = urllib.request.Request(url, headers={"User-Agent": "platinum-hub-smoke/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - localhost only
            return resp.status, resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), exc.headers.get("Content-Type", "")


def _ports_in_use() -> set:
    """Ports of app.py's range that are already taken before we start.

    Without this, a leftover Platinum Hub from a previous run would answer our
    probes and the smoke test would happily pass against the wrong process.
    """
    busy = set()
    for port in range(PORT_START, PORT_START + PORT_RANGE):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.3)
        try:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                busy.add(port)
        finally:
            sock.close()
    return busy


def _discover_port(proc: subprocess.Popen, deadline: float, skip: set) -> int:
    """Find the port the app bound to, by probing the range it uses.

    Reading the port from stdout would be nicer, but a frozen executable does
    not reliably give us an unbuffered stream, so probing is the portable way.
    """
    candidates = [p for p in range(PORT_START, PORT_START + PORT_RANGE) if p not in skip]
    if not candidates:
        raise RuntimeError(
            "tutte le porte da %d a %d sono gia' occupate: chiudi le istanze precedenti"
            % (PORT_START, PORT_START + PORT_RANGE - 1)
        )
    last_error = "nessun tentativo"
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(
                "l'applicazione e' uscita subito con codice %s" % proc.returncode
            )
        for port in candidates:
            try:
                status, body, _ = _http_get("http://127.0.0.1:%d/" % port, timeout=3.0)
            except Exception as exc:  # connection refused while still booting
                last_error = "%s: %s" % (type(exc).__name__, exc)
                continue
            if status == 200 and b"Platinum Hub" in body:
                return port
            last_error = "porta %d ha risposto %s ma senza il marcatore atteso" % (port, status)
        time.sleep(0.5)
    raise TimeoutError("server non raggiungibile entro %ds (%s)" % (BOOT_TIMEOUT_S, last_error))


def _drain(stream, sink: list) -> None:
    for raw in iter(stream.readline, b""):
        sink.append(raw.decode("utf-8", "replace").rstrip())
    with contextlib.suppress(Exception):
        stream.close()


@contextlib.contextmanager
def start_app(exe: str | None = None, cwd: str | None = None):
    """Start the app, yield its base URL, always terminate it afterwards."""
    cwd = cwd or REPO_ROOT
    if exe:
        cmd = [os.path.abspath(exe)]
        run_cwd = os.path.dirname(os.path.abspath(exe)) or cwd
    else:
        cmd = [sys.executable, "-u", os.path.join(cwd, "app.py")]
        run_cwd = cwd

    already_busy = _ports_in_use()
    proc = subprocess.Popen(
        cmd,
        cwd=run_cwd,
        env=_no_browser_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output: list = []
    reader = threading.Thread(target=_drain, args=(proc.stdout, output), daemon=True)
    reader.start()
    try:
        try:
            port = _discover_port(proc, time.time() + BOOT_TIMEOUT_S, already_busy)
        except BaseException:
            print("--- output dell'applicazione ---")
            for line in output[-60:]:
                print("   " + line)
            print("--------------------------------")
            raise
        yield "http://127.0.0.1:%d" % port
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=15)
        reader.join(timeout=5)


# --------------------------------------------------------------------- checks
# (path, expected status, marker that must appear in the body)
CHECKS = [
    ("/", 200, b"Platinum Hub"),
    ("/run/er", 200, b"<html"),
    ("/api/summary", 200, b'"run"'),
    ("/api/prefs", 200, b"{"),
    ("/episodes/er", 200, b"<html"),
    ("/overlay/er", 200, b"<html"),
    ("/selftest/er", 200, b"<html"),
    ("/fonts/roboto-400.woff2", 200, b"wOF2"),
    ("/run/questa-run-non-esiste", 404, b""),
]


def run_checks(base_url: str) -> int:
    failures = 0
    for path, want_status, marker in CHECKS:
        label = "%-32s" % path
        try:
            status, body, ctype = _http_get(base_url + path)
        except Exception as exc:
            print("  [FAIL] %s  errore di trasporto: %s" % (label, exc))
            failures += 1
            continue
        problems = []
        if status != want_status:
            problems.append("status %s invece di %s" % (status, want_status))
        if marker and marker not in body:
            problems.append("manca il marcatore %r" % marker)
        if problems:
            print("  [FAIL] %s  %s" % (label, "; ".join(problems)))
            failures += 1
        else:
            print("  [ OK ] %s  %s, %d byte, %s" % (label, status, len(body), ctype.split(";")[0]))
    return failures


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test di Platinum Hub")
    parser.add_argument(
        "--exe",
        default=None,
        help="percorso dell'eseguibile PyInstaller da collaudare al posto di app.py",
    )
    args = parser.parse_args(argv)

    target = args.exe or os.path.join(REPO_ROOT, "app.py")
    print("Platinum Hub - smoke test")
    print("  target   : %s" % target)
    print("  python   : %s" % sys.version.split()[0])
    print("  piattaforma: %s" % sys.platform)
    print()

    if args.exe and not os.path.isfile(args.exe):
        print("ERRORE: eseguibile non trovato: %s" % args.exe)
        return 2
    if not args.exe and not os.path.isfile(target):
        print("ERRORE: app.py non trovato in %s" % REPO_ROOT)
        return 2

    started = time.time()
    with start_app(exe=args.exe) as base_url:
        print("Server attivo su %s (avvio in %.1fs)" % (base_url, time.time() - started))
        print()
        failures = run_checks(base_url)

    print()
    if failures:
        print("SMOKE TEST FALLITO: %d controlli su %d non sono passati." % (failures, len(CHECKS)))
        return 1
    print("SMOKE TEST OK: %d controlli su %d." % (len(CHECKS), len(CHECKS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
