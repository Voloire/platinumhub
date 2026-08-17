#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility condivise da tutta la suite di test di Platinum Hub.

Regole rispettate qui dentro:
  * solo standard library (unittest, urllib, sqlite3, json, subprocess);
  * il database reale /home/claude/PlatinumHub/platinum.db non viene MAI toccato:
    ogni test lavora in una cartella temporanea in cui copiamo app.py, data/ e fonts/,
    cosi' BASE (e quindi DB) puntano alla sandbox;
  * ogni server avviato viene ucciso a fine test, anche se il test fallisce,
    perche' i processi orfani che tengono la porta hanno gia' causato bug fantasma.
"""

import atexit
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

# Cartella dell'applicazione da testare (sovrascrivibile per la CI).
APP_DIR = os.environ.get("PLATINUM_HUB_DIR",
                         os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(APP_DIR, "data")

# Identificativi delle run, ricavati dal registro RUNS di app.py.
RUN_IDS = ("er", "dsr", "ds3", "sb", "kz", "lop", "bor", "bmw", "n3", "na")

# Route di riferimento: la forma di questo file definisce lo schema atteso.
REFERENCE_ROUTE = "kz.json"

# Tempo massimo di attesa per l'avvio del server, in secondi.
BOOT_TIMEOUT = 25.0

_SANDBOXES = []
_LIVE_SERVERS = []


def _cleanup_everything():
    """
    Rete di sicurezza: alla chiusura del processo di test uccide i server ancora
    vivi e cancella le sandbox. Vale anche se un test esplode a meta',
    perche' i processi orfani che tengono la porta hanno gia' fatto perdere ore.
    """
    for server in list(_LIVE_SERVERS):
        try:
            server.stop()
        except Exception:
            pass
    del _LIVE_SERVERS[:]
    for path in list(_SANDBOXES):
        shutil.rmtree(path, ignore_errors=True)
    del _SANDBOXES[:]


atexit.register(_cleanup_everything)


def free_port():
    """Restituisce una porta TCP libera su 127.0.0.1."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def route_files():
    """Elenco ordinato dei file JSON delle route presenti in data/."""
    return sorted(f for f in os.listdir(DATA_DIR) if f.endswith(".json"))


def load_route(name):
    """Carica un file di route dalla cartella data/ dell'app reale (sola lettura)."""
    with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def route_step_count(route):
    """Numero di passi della route."""
    return sum(len(p["steps"]) for p in route["phases"])


def route_sids(route):
    """I sid dei passi in ordine di pagina: la chiave dei progressi dal v2."""
    return [s["sid"] for p in route["phases"] for s in p["steps"]]


def sids_of(rid):
    """Scorciatoia: i sid della run <rid> letti dal suo file JSON."""
    return route_sids(load_route(rid + ".json"))


def make_sandbox(port=None):
    """
    Crea una copia isolata dell'app in una cartella temporanea.

    Copiamo solo cio' che serve (app.py, data/, fonts/) e NON il database reale.
    PORT_START viene riscritto sulla porta indicata, cosi' i test non litigano
    ne' con l'istanza reale sulla 8787 ne' fra di loro.
    """
    if port is None:
        port = free_port()
    root = tempfile.mkdtemp(prefix="platinumhub-test-")
    _SANDBOXES.append(root)

    with open(os.path.join(APP_DIR, "app.py"), "r", encoding="utf-8") as f:
        src = f.read()
    patched, n = re.subn(r"^PORT_START = \d+$", "PORT_START = %d" % port, src, count=1,
                         flags=re.MULTILINE)
    if n != 1:
        raise RuntimeError("PORT_START non trovato in app.py: la sandbox non e' isolabile")
    with open(os.path.join(root, "app.py"), "w", encoding="utf-8") as f:
        f.write(patched)

    shutil.copytree(DATA_DIR, os.path.join(root, "data"))
    fonts = os.path.join(APP_DIR, "fonts")
    if os.path.isdir(fonts):
        shutil.copytree(fonts, os.path.join(root, "fonts"))
    return root, port


def drop_sandbox(root):
    """Cancella una sandbox e la toglie dalla lista di pulizia."""
    shutil.rmtree(root, ignore_errors=True)
    if root in _SANDBOXES:
        _SANDBOXES.remove(root)


def import_app_module(sandbox=None):
    """
    Importa app.py dalla sandbox come modulo, per testare le funzioni pure
    (parse_hotkeys, push_cmd/take_cmds, fmt_tc...) senza avviare il server.
    """
    if sandbox is None:
        sandbox, _ = make_sandbox()
    path = os.path.join(sandbox, "app.py")
    name = "platinumhub_under_test_%d" % (len(sys.modules),)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module, sandbox


class AppServer(object):
    """
    Avvia app.py in un sottoprocesso dentro la sandbox e offre helper HTTP.

    Usare sempre con stop() in tearDownClass/finally: il processo non deve
    mai sopravvivere al test.
    """

    def __init__(self):
        self.sandbox = None
        self.port = None
        self.proc = None
        self.stdout = []
        self.stderr = []
        self._threads = []
        # Nessun proxy: le richieste vanno dritte a 127.0.0.1.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    # ------------------------------------------------------------- ciclo di vita
    def start(self, sandbox=None, port=None):
        """Avvia il server. Passare una sandbox gia' pronta (da make_sandbox)
        permette di pre-seminare un platinum.db, p.es. con lo schema vecchio
        per collaudare la migrazione."""
        _LIVE_SERVERS.append(self)
        if sandbox is None:
            self.sandbox, self.port = make_sandbox()
        else:
            self.sandbox, self.port = sandbox, port
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["BROWSER"] = "/bin/true"        # niente browser aperto durante i test
        # Da v4.0 il database sta nella cartella dati utente: la forziamo dentro
        # la sandbox, altrimenti i test si scriverebbero addosso a vicenda e
        # toccherebbero i progressi veri dell'utente.
        env["PLATINUM_HUB_DATA"] = self.sandbox
        env["PLATINUM_HUB_NO_UPDATE"] = "1"   # nessuna chiamata di rete nei test
        env.pop("http_proxy", None)
        env.pop("https_proxy", None)
        env.pop("HTTP_PROXY", None)
        env.pop("HTTPS_PROXY", None)
        self.proc = subprocess.Popen(
            [sys.executable, "-u", os.path.join(self.sandbox, "app.py")],
            cwd=self.sandbox, env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._pump(self.proc.stdout, self.stdout)
        self._pump(self.proc.stderr, self.stderr)
        self._wait_ready()
        return self

    def _pump(self, stream, sink):
        """Svuota le pipe in un thread, altrimenti il processo si blocca sul buffer."""
        def run():
            for line in iter(stream.readline, b""):
                sink.append(line.decode("utf-8", "replace").rstrip("\n"))
            stream.close()
        t = threading.Thread(target=run, daemon=True)
        t.start()
        self._threads.append(t)

    def _wait_ready(self):
        deadline = time.time() + BOOT_TIMEOUT
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError("app.py e' morto durante l'avvio:\n%s\n%s"
                                   % ("\n".join(self.stdout), "\n".join(self.stderr)))
            try:
                code, _, body = self.request("GET", "/api/summary")
                if code == 200 and json.loads(body):
                    return
            except Exception:
                time.sleep(0.1)
        raise RuntimeError("app.py non risponde entro %.0fs sulla porta %s\n%s"
                           % (BOOT_TIMEOUT, self.port, "\n".join(self.stdout)))

    def stop(self):
        """Termina il processo. Nessun orfano: prima terminate, poi kill."""
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
        for t in self._threads:
            t.join(timeout=2)
        self._threads = []
        if self.sandbox:
            drop_sandbox(self.sandbox)
            self.sandbox = None
        if self in _LIVE_SERVERS:
            _LIVE_SERVERS.remove(self)

    # -------------------------------------------------------------------- HTTP
    def url(self, path):
        return "http://127.0.0.1:%d%s" % (self.port, path)

    def request(self, method, path, data=None, headers=None, follow=True):
        """Ritorna (status_code, headers, body_text). Non solleva su 4xx/5xx."""
        body = None
        hdrs = dict(headers or {})
        if data is not None:
            body = data if isinstance(data, bytes) else data.encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(self.url(path), data=body, headers=hdrs, method=method)
        opener = self._opener
        if not follow:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                                 _NoRedirect())
        try:
            resp = opener.open(req, timeout=20)
            with resp:
                return resp.getcode(), dict(resp.headers), resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            with e:
                return e.code, dict(e.headers), e.read().decode("utf-8", "replace")

    def get(self, path, follow=True):
        return self.request("GET", path, follow=follow)

    def get_text(self, path):
        code, _, body = self.get(path)
        return code, body

    def post_json(self, path, obj):
        code, _, body = self.request("POST", path, json.dumps(obj))
        try:
            return code, json.loads(body)
        except ValueError:
            return code, body

    def get_json(self, path):
        code, _, body = self.get(path)
        try:
            return code, json.loads(body)
        except ValueError:
            return code, body

    def post_raw(self, path, raw, ctype="application/json"):
        return self.request("POST", path, raw, {"Content-Type": ctype})

    def set_lang(self, code):
        """Cambia lingua come farebbe l'utente, via /lang/<code>."""
        self.post_json("/api/pref", {"lang": code})

    # --------------------------------------------------------------- diagnostica
    def db_path(self):
        return os.path.join(self.sandbox, "platinum.db")

    def tracebacks(self):
        """Righe di traceback finite su stderr: devono restare zero."""
        return [l for l in self.stderr if "Traceback" in l or "Exception happened" in l]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Handler che non segue i redirect: serve per verificare i 303."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ServerTestCase(object):
    """
    Mixin: un solo server condiviso per classe di test.
    Le sottoclassi devono ereditare anche da unittest.TestCase.
    """

    server = None

    @classmethod
    def setUpClass(cls):
        cls.server = AppServer().start()

    @classmethod
    def tearDownClass(cls):
        if cls.server is not None:
            cls.server.stop()
            cls.server = None
