# -*- coding: utf-8 -*-
"""Il server HTTP: routing, API, avvio."""

import datetime
import http.server
import json
import os
import re
import socketserver
import sys
import threading
import urllib.parse
import webbrowser

from .catalog import CATALOG, check_catalog, install_route
from .config import (BASE, CUR_PORT, DATA, DB, PORT_START, UPDATE, VERSION,
                     migrate_legacy_db)
from .hotkeys import (HOTKEYS_DEFAULT, HOTKEY_STATE, get_toast, parse_hotkeys,
                      push_cmd, set_toast, start_hotkeys, take_cmds)
from .page_export import render_export
from .page_home import render_changelog, render_home
from .page_run import render_run
from .page_streamer import (render_episodes, render_overlay, render_selftest,
                            render_session)
from .routes import ROUTES, load_routes
from .store import (SID_OK, current_state, db, done_sids, get_note, get_pref,
                    lang, progress_updated_at, save_done, sessions_of,
                    session_row, set_note, set_pref, stats)
from .thumbs import render_thumb
from .ui import mode, render_404
from .update import check_update


# ---------------------------------------------------------------------- server
class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "PlatinumHub/" + VERSION

    def log_message(self, fmt, *a):
        pass

    def _send(self, body, ctype="text/html; charset=utf-8", code=200, extra=None):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj, code=200):
        self._send(json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8", code)

    def _redirect(self, to):
        # niente caratteri di controllo nella Location: un %0d%0a decodificato
        # da parse_qs diventerebbe una riga di header scritta dal client.
        # quote() li ricodifica tutti, lasciando passare i percorsi normali.
        to = urllib.parse.quote(str(to), safe="/?&=%~")
        self.send_response(303)
        self.send_header("Location", to)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        path, q = u.path, urllib.parse.parse_qs(u.query)

        if path == "/":
            return self._send(render_home())

        if path.startswith("/lang/"):
            code = path[6:].strip("/")
            if code in ("it", "en"):
                set_pref("lang", code)
            nxt = (q.get("next") or ["/"])[0]
            if not nxt.startswith("/") or nxt.startswith("//"):
                nxt = "/"
            return self._redirect(nxt)

        if path.startswith("/run/"):
            rid = path[5:].strip("/")
            if rid in ROUTES:
                return self._send(render_run(rid))
            return self._send(render_404(), code=404)

        if path == "/api/progress":
            rid = (q.get("run") or [""])[0]
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            # si dichiarano solo i sid che la route attuale conosce: gli
            # orfani restano nel database ma non appartengono alla pagina
            done = sorted(done_sids(rid) & ROUTES[rid]["_sidset"])
            return self._json({"run": rid, "done": done,
                               "updated_at": progress_updated_at(rid),
                               "total": ROUTES[rid]["_steps"]})

        if path == "/api/notes":
            rid = (q.get("run") or [""])[0]
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            return self._json({"run": rid, "body": get_note(rid)})

        if path.startswith("/mode/"):
            code = path[6:].strip("/")
            if code in ("gamer", "streamer"):
                set_pref("mode", code)
            nxt = (q.get("next") or ["/"])[0]
            return self._redirect(nxt if (nxt.startswith("/")
                                          and not nxt.startswith("//")) else "/")

        if path.startswith("/episodes/"):
            rid = path[10:].strip("/")
            if rid in ROUTES:
                return self._send(render_episodes(rid))
            return self._send(render_404(), code=404)

        if path.startswith("/thumb/"):
            rid = path[7:].strip("/")
            if rid in ROUTES:
                return self._send(render_thumb(rid))
            return self._send(render_404(), code=404)

        if path.startswith("/session/"):
            rid = path[9:].strip("/")
            if rid in ROUTES:
                return self._send(render_session(rid))
            return self._send(render_404(), code=404)

        if path.startswith("/export/"):
            rid = path[8:].strip("/")
            if rid not in ROUTES:
                return self._send(render_404(), code=404)
            name = "%s - %s (by Voloirex).html" % (
                "Guida" if lang() == "it" else "Guide",
                re.sub(r"[^A-Za-z0-9 +.-]", "", ROUTES[rid]["game"]))
            return self._send(render_export(rid), extra={
                "Content-Disposition": 'attachment; filename="%s"' % name})

        if path.startswith("/selftest/"):
            rid = path[10:].strip("/")
            if rid in ROUTES:
                return self._send(render_selftest(rid))
            return self._send(render_404(), code=404)

        if path.startswith("/overlay/"):
            rid = path[9:].strip("/")
            if rid in ROUTES:
                return self._send(render_overlay(rid, q))
            return self._send(render_404(), code=404)

        if path == "/api/current":
            rid = (q.get("run") or [""])[0]
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            st = current_state(rid)
            st["toast"] = get_toast(rid)
            return self._json(st)

        if path == "/api/episodes":
            rid = (q.get("run") or [""])[0]
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            return self._json(sessions_of(rid))

        if path == "/api/pending":
            rid = (q.get("run") or [""])[0]
            return self._json({"cmds": take_cmds(), "run": rid})

        if path == "/api/routes/status":
            return self._json({"checked": CATALOG["checked"],
                               "available": CATALOG["available"]})

        if path == "/api/version":
            return self._json({"version": VERSION, "latest": UPDATE["latest"],
                               "url": UPDATE["url"], "checked": UPDATE["checked"],
                               "check_on": get_pref("update_check", "1") == "1"})

        if path == "/update/off":
            set_pref("update_check", "0")
            UPDATE["latest"] = ""
            return self._redirect("/")

        if path == "/update/on":
            set_pref("update_check", "1")
            threading.Thread(target=check_update, daemon=True).start()
            return self._redirect("/")

        if path == "/changelog":
            return self._send(render_changelog())

        if path == "/api/hotkeys":
            spec = get_pref("hotkeys", HOTKEYS_DEFAULT)
            # "configured" e' la lista che l'utente ha impostato, indipendente da
            # quello che Windows ha poi accettato di registrare: serve al pannello
            # per mostrare le scorciatoie anche quando sono spente o siamo su Linux,
            # senza rifare in JavaScript il lavoro di parse_hotkeys().
            return self._json({"spec": spec,
                               "on": get_pref("hotkeys_on", "1") == "1",
                               "configured": [[label, action]
                                              for _m, _vk, action, label in parse_hotkeys(spec)],
                               "active": HOTKEY_STATE["active"],
                               "failed": HOTKEY_STATE["failed"],
                               "why": HOTKEY_STATE["why"],
                               "platform": sys.platform})

        if path == "/api/prefs":
            return self._json({"obs_url": get_pref("obs_url", "ws://127.0.0.1:4455"),
                               "obs_pass": get_pref("obs_pass", ""),
                               "obs_prefer": get_pref("obs_prefer", "auto"),
                               "mode": mode()})

        if path == "/api/summary":
            out = []
            for rid, d in ROUTES.items():
                done, total, td, tt, when = stats(rid)
                out.append({"run": rid, "game": d["game"], "steps_done": done,
                            "steps_total": total, "trophies_done": td, "trophies_total": tt,
                            "updated_at": when})
            return self._json(out)

        if path == "/api/export":
            con = db()
            runs = [r[0] for r in con.execute(
                "SELECT DISTINCT run_id FROM progress_steps "
                "UNION SELECT run_id FROM progress_runs")]
            payload = {
                "app": "PlatinumHub", "version": 3,
                "exported_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                # per sid, orfani compresi: il backup e' una copia fedele,
                # non una vista filtrata
                "progress": [{"run_id": r,
                              "done": [s[0] for s in con.execute(
                                  "SELECT sid FROM progress_steps WHERE run_id=? ORDER BY sid",
                                  (r,))],
                              "updated_at": next((u[0] for u in con.execute(
                                  "SELECT updated_at FROM progress_runs WHERE run_id=?",
                                  (r,))), None)}
                             for r in runs],
                "notes": [{"run_id": a, "body": b, "updated_at": c}
                          for a, b, c in con.execute("SELECT run_id,body,updated_at FROM notes")],
                "prefs": {a: b for a, b in con.execute("SELECT k,v FROM prefs")},
            }
            con.close()
            fname = "platinum-backup-%s.json" % datetime.datetime.now().strftime("%Y%m%d-%H%M")
            return self._send(json.dumps(payload, ensure_ascii=False, indent=1),
                              "application/json; charset=utf-8",
                              extra={"Content-Disposition": 'attachment; filename="%s"' % fname})

        if path.startswith("/fonts/"):
            # whitelist stretta sul nome PIU' contenimento verificato del
            # percorso risolto: il file servito sta dentro fonts/, provato,
            # non dedotto dalla forma del nome
            name = os.path.basename(path)
            if not re.match(r"^[A-Za-z0-9_-]+\.woff2$", name):
                return self._send(b"", "font/woff2", 404)
            fonts_dir = os.path.realpath(os.path.join(BASE, "fonts"))
            fp = os.path.realpath(os.path.join(fonts_dir, name))
            if not fp.startswith(fonts_dir + os.sep):
                return self._send(b"", "font/woff2", 404)
            if os.path.isfile(fp):
                with open(fp, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "font/woff2")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "public, max-age=604800")
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            return self._send(b"", "font/woff2", 404)

        if path == "/favicon.ico":
            return self._send(b"", "image/x-icon")
        return self._send(render_404(), code=404)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:
            return self._json({"error": "bad payload"}, 400)
        # Un JSON valido ma che non e' un oggetto ([1,2], "x", 42, null) non ha
        # .get(): senza questo controllo il gestore esplode a meta' strada e la
        # connessione si chiude senza risposta.
        if not isinstance(payload, dict):
            return self._json({"error": "body must be a JSON object"}, 400)
        try:
            return self._route_post(u, payload)
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            # campi presenti ma di tipo sbagliato ("lead": "molto", "step": {}):
            # e' un errore del chiamante, non del server. Meglio un 400 onesto
            # che un traceback e una connessione chiusa a meta'.
            return self._json({"error": "bad field: %s" % e.__class__.__name__}, 400)

    def _route_post(self, u, payload):

        if u.path == "/api/session/start":
            rid = payload.get("run")
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            con = db()
            con.execute("UPDATE sessions SET ended_at=datetime('now') "
                        "WHERE run_id=? AND ended_at IS NULL", (rid,))
            n = con.execute("SELECT COALESCE(MAX(number),0)+1 FROM sessions WHERE run_id=?",
                            (rid,)).fetchone()[0]
            cur = con.execute("""INSERT INTO sessions(run_id,number,title,started_at,source,lead)
                                 VALUES(?,?,?,datetime('now'),?,?)""",
                              (rid, n, str(payload.get("title") or "")[:120],
                               "obs" if payload.get("source") == "obs" else "clock",
                               int(15 if payload.get("lead") is None else payload.get("lead"))))
            sid = cur.lastrowid
            con.execute("""INSERT INTO markers(session_id,run_id,sid,kind,tc,wall)
                           VALUES(?,?,NULL,'session_start',0,datetime('now'))""", (sid, rid))
            con.commit()
            con.close()
            return self._json({"ok": True, "session": session_row(sid)})

        if u.path == "/api/session/stop":
            con = db()
            con.execute("UPDATE sessions SET ended_at=datetime('now') WHERE id=?",
                        (int(payload.get("id") or 0),))
            con.commit()
            con.close()
            return self._json({"ok": True})

        if u.path == "/api/session/update":
            sid = int(payload.get("id") or 0)
            con = db()
            for k, col, cast in (("title", "title", str), ("video_url", "video_url", str),
                                 ("video_offset", "video_offset", int), ("lead", "lead", int)):
                if k in payload:
                    con.execute(f"UPDATE sessions SET {col}=? WHERE id=?",
                                (cast(payload[k]), sid))
            con.commit()
            con.close()
            return self._json({"ok": True, "session": session_row(sid)})

        if u.path == "/api/session/delete":
            sid = int(payload.get("id") or 0)
            con = db()
            con.execute("DELETE FROM markers WHERE session_id=?", (sid,))
            con.execute("DELETE FROM sessions WHERE id=?", (sid,))
            con.commit()
            con.close()
            return self._json({"ok": True})

        if u.path == "/api/routes/check":
            # il pulsante "Cerca nuove run": stessa strada del check silenzioso,
            # ma su richiesta esplicita e con la risposta in mano alla pagina
            check_catalog()
            return self._json({"checked": CATALOG["checked"],
                               "available": CATALOG["available"]})

        if u.path == "/api/routes/install":
            ok, msg = install_route(payload.get("id"))
            return self._json({"ok": ok, "msg": msg}, 200 if ok else 400)

        if u.path == "/api/cmd":
            action = str(payload.get("action") or "").lower()
            if not push_cmd(action, payload.get("run")):
                return self._json({"error": "bad action"}, 400)
            return self._json({"ok": True, "action": action})

        if u.path == "/api/toast":
            rid = payload.get("run")
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            set_toast(rid, payload.get("text") or "")
            return self._json({"ok": True})

        if u.path == "/api/hotkeys":
            spec = str(payload.get("spec") or HOTKEYS_DEFAULT)[:300]
            if not parse_hotkeys(spec):
                return self._json({"error": "no valid combo"}, 400)
            set_pref("hotkeys", spec)
            set_pref("hotkeys_on", "1" if payload.get("on", True) else "0")
            return self._json({"ok": True, "spec": spec, "restart": True})

        if u.path == "/api/marker":
            rid = payload.get("run")
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            ses = payload.get("session")
            if not ses:
                return self._json({"error": "no session"}, 400)
            kind = payload.get("kind")
            if kind not in ("start", "done", "free"):
                return self._json({"error": "bad kind"}, 400)
            msid = payload.get("sid")
            if msid is not None and not (isinstance(msid, str) and SID_OK.match(msid)):
                return self._json({"error": "bad sid"}, 400)
            con = db()
            if msid is not None:
                con.execute("DELETE FROM markers WHERE session_id=? AND sid=? AND kind=?",
                            (ses, msid, kind))
            con.execute("""INSERT INTO markers(session_id,run_id,sid,kind,tc,wall,note)
                           VALUES(?,?,?,?,?,datetime('now'),?)""",
                        (ses, rid, msid, kind, float(payload.get("tc") or 0),
                         str(payload.get("note") or "")[:300]))
            con.commit()
            con.close()
            return self._json({"ok": True})

        if u.path == "/api/run/reset":
            rid = payload.get("run")
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            con = db()
            n_mark = con.execute("SELECT COUNT(*) FROM markers WHERE run_id=?", (rid,)).fetchone()[0]
            n_ses = con.execute("SELECT COUNT(*) FROM sessions WHERE run_id=?", (rid,)).fetchone()[0]
            n_note = con.execute("SELECT COUNT(*) FROM notes WHERE run_id=?", (rid,)).fetchone()[0]
            con.execute("DELETE FROM markers WHERE run_id=?", (rid,))
            con.execute("DELETE FROM sessions WHERE run_id=?", (rid,))
            con.execute("DELETE FROM notes WHERE run_id=?", (rid,))
            con.execute("DELETE FROM progress_steps WHERE run_id=?", (rid,))
            con.execute("DELETE FROM progress_runs WHERE run_id=?", (rid,))
            con.execute("DELETE FROM prefs WHERE k=?", ("cur_" + rid,))
            con.commit()
            con.close()
            return self._json({"ok": True, "markers": n_mark, "sessions": n_ses, "notes": n_note})

        if u.path == "/api/marker/delete":
            msid = payload.get("sid")
            if not (isinstance(msid, str) and SID_OK.match(msid)):
                return self._json({"error": "bad sid"}, 400)
            con = db()
            con.execute("DELETE FROM markers WHERE session_id=? AND sid=?",
                        (int(payload.get("session") or 0), msid))
            con.commit()
            con.close()
            return self._json({"ok": True})

        if u.path == "/api/current":
            rid = payload.get("run")
            if rid not in ROUTES:
                return self._json({"error": "unknown run"}, 404)
            msid = payload.get("sid")
            if msid is not None and not (isinstance(msid, str) and SID_OK.match(msid)):
                return self._json({"error": "bad sid"}, 400)
            set_pref("cur_" + rid, msid or "")
            return self._json({"ok": True})

        if u.path == "/api/selftest":
            txt = str(payload.get("text") or "")[:60000]
            try:
                with open(os.path.join(BASE, "diagnostica.txt"), "w", encoding="utf-8",
                          newline="") as f:
                    f.write(txt.replace("\n", "\r\n"))
                return self._json({"ok": True, "path": os.path.join(BASE, "diagnostica.txt")})
            except Exception as e:
                return self._json({"ok": False, "error": str(e)}, 500)

        if u.path == "/api/pref":
            for k in ("hide_done", "only_miss", "lang", "mode", "obs_url", "obs_pass",
                      "obs_prefer", "overlay_style"):
                if k in payload:
                    set_pref(k, str(payload[k])[:200])
            return self._json({"ok": True})

        if u.path == "/api/import":
            if not isinstance(payload, dict) or payload.get("app") != "PlatinumHub":
                return self._json({"error": "not a Platinum Hub backup"}, 400)
            rows = payload.get("progress") or []
            for row in rows:
                rid = row.get("run_id")
                if rid not in ROUTES:
                    continue
                if isinstance(row.get("done"), list):
                    # backup v3: gia' per sid
                    done = [s for s in row["done"]
                            if isinstance(s, str) and SID_OK.match(s)]
                else:
                    # backup v2 (bits posizionali): la posizione si mappa al
                    # sid nell'ordine della route in bundle, come in migrazione
                    bits = str(row.get("bits") or "")
                    if not all(c in "01" for c in bits):
                        continue
                    sids = ROUTES[rid]["_sids"]
                    done = [sids[i] for i, c in enumerate(bits[:len(sids)]) if c == "1"]
                save_done(rid, done, ROUTES[rid]["_sidset"])
            for row in payload.get("notes") or []:
                if row.get("run_id") in ROUTES:
                    set_note(row["run_id"], str(row.get("body") or "")[:100000])
            prefs = payload.get("prefs") or {}
            if prefs.get("lang") in ("it", "en"):
                set_pref("lang", prefs["lang"])
            return self._json({"ok": True, "runs": len(rows)})

        rid = payload.get("run")
        if rid not in ROUTES:
            return self._json({"error": "unknown run"}, 404)

        if u.path == "/api/progress":
            done = payload.get("done")
            if not isinstance(done, list) or not all(
                    isinstance(s, str) and SID_OK.match(s) for s in done):
                return self._json({"error": "done must be a list of sids"}, 400)
            save_done(rid, done, ROUTES[rid]["_sidset"])
            saved = len(set(done) & ROUTES[rid]["_sidset"])
            return self._json({"ok": True, "saved": saved, "total": ROUTES[rid]["_steps"]})

        if u.path == "/api/notes":
            set_note(rid, str(payload.get("body") or "")[:100000])
            return self._json({"ok": True})

        return self._json({"error": "unknown endpoint"}, 404)


class Server(socketserver.ThreadingTCPServer):
    # SO_REUSEADDR non vuol dire la stessa cosa sui due sistemi. Su Windows
    # permette a un secondo processo di legarsi a una porta GIA' in ascolto:
    # pick_port() non vedrebbe mai OSError, resterebbe sull'8787 e due istanze
    # si spartirebbero le richieste a caso -- si crede di provare la versione
    # nuova e si sta guardando la vecchia. Su POSIX serve invece a non farsi
    # rifiutare il bind dai TIME_WAIT dopo un riavvio, quindi la si tiene.
    allow_reuse_address = os.name != "nt"
    daemon_threads = True


def pick_port():
    for port in range(PORT_START, PORT_START + 25):
        try:
            return Server(("127.0.0.1", port), Handler), port
        except OSError:
            continue
    return None, None


def main():
    print()
    print("  =========================================")
    print("   PLATINUM HUB v%s  ·  by Voloirex" % VERSION)
    print("  =========================================")
    # PRIMA delle route: load_routes() crea il file del database per la
    # tabella routes, e la migrazione del db 3.x accanto all'exe scatta solo
    # se il db utente non esiste ancora.
    moved = migrate_legacy_db()
    load_routes()
    if not ROUTES:
        print("  ERRORE / ERROR: nessun file route in", DATA)
        input("  Invio per chiudere / Enter to close...")
        return
    db()
    for rid in ROUTES:
        done, total, td, tt, _ = stats(rid)
        print(f"   · {ROUTES[rid]['game']:<30} {done:>3}/{total:<4} passi   {td:>2}/{tt:<3} trofei")
    srv, port = pick_port()
    if srv is None:
        print("  ERRORE: nessuna porta libera tra %d e %d." % (PORT_START, PORT_START + 24))
        input("  Invio per chiudere...")
        return
    CUR_PORT[0] = port
    url = "http://127.0.0.1:%d/" % port
    print()
    print("   Apri / Open:", url)
    print("   Database progressi:", DB)
    if moved:
        print("   (progressi della versione precedente importati da %s)" % moved)
    threading.Thread(target=check_update, daemon=True).start()
    # Anche il catalogo delle route si controlla all'avvio, in silenzio:
    # se non c'e' rete non compare niente, per contratto.
    threading.Thread(target=check_catalog, daemon=True).start()
    start_hotkeys(port)
    if HOTKEY_STATE["active"]:
        print("   Scorciatoie globali attive (funzionano anche a gioco aperto):")
        for label, action in HOTKEY_STATE["active"]:
            print("      %-16s %s" % (label, {"rec": "avvia / chiudi registrazione + episodio",
                                              "next": "task fatto, passa al prossimo",
                                              "undo": "annulla l'ultima spunta",
                                              "mark": "segnaposto libero"}.get(action, action)))
        for label, action in HOTKEY_STATE["failed"]:
            print("      %-16s NON registrata (combinazione gia' occupata)" % label)
    elif HOTKEY_STATE["why"]:
        print("   Scorciatoie globali: %s" % HOTKEY_STATE["why"])
    print("   Lascia questa finestra aperta mentre usi l'hub.")
    print("   Chiudila (o Ctrl+C) quando hai finito.")
    print()
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n   Ciao. I progressi sono salvati.")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
