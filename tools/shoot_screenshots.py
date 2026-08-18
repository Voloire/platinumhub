# -*- coding: utf-8 -*-
"""Riscatta i tre screenshot pubblici (site/img e docs/img) dall'app VERA.

Perche' esiste: fino alla 5.1.0 le immagini pubblicate erano mockup della
fase di design -- una portava ancora il banner "MOCKUP NON FUNZIONANTE" e la
home era quella della v1.0 con sette giochi. Erano invecchiate perche'
rifarle era un lavoro manuale. Adesso e' un comando:

    .venv\\Scripts\\python tools/shoot_screenshots.py

Serve Playwright (dipendenza di SVILUPPO, requirements-dev.txt) piu'
`playwright install chromium`. L'app non acquisisce nessuna dipendenza.

Come funziona: avvia l'app in una sandbox usando lo stesso harness dei test
(il database reale non viene mai toccato), semina progressi, episodi e
marker passando dalle STESSE API che usa la pagina, poi fotografa.

L'unica finzione e' OBS: la modalita' streamer parla obs-websocket v5 dal
browser, e qui il partner e' simulato da Playwright. Il protocollo e' quello
vero, cosi' lo scatto mostra lo stato in cui l'app si trova davvero quando
OBS registra -- non un errore di connessione.
"""

import json
import os
import re
import sqlite3
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import harness  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:                                        # pragma: no cover
    sys.exit("Serve Playwright: pip install -r requirements-dev.txt "
             "&& playwright install chromium")

# Le due destinazioni tengono gli stessi file: il sito li serve da Pages,
# il README li mostra su GitHub.
DESTS = (os.path.join(ROOT, "site", "img"), os.path.join(ROOT, "docs", "img"))

# Quanti passi risultano spuntati per ciascuna run: uno stato di avanzamento
# credibile, con qualche run finita e qualche altra intatta.
SEED = {"er": 62, "dsr": 87, "ds3": 23, "lop": 40, "na": 67, "sek": 38, "hzd": 12}

REC_BASE = 4462.0          # 01:14:22 di registrazione gia' fatta
SHOTS = {"hub-home": (1400, 1000), "streamer": (1400, 1340), "guida": (1400, 896)}


def fake_obs(ws):
    """Partner obs-websocket v5 (nessuna autenticazione, registrazione attiva)."""
    t0 = time.time()

    def timecode():
        s = REC_BASE + (time.time() - t0)
        return "%02d:%02d:%06.3f" % (int(s // 3600), int(s % 3600 // 60), s % 60)

    ws.send(json.dumps({"op": 0, "d": {"obsWebSocketVersion": "5.5.2",
                                       "rpcVersion": 1}}))

    def on_message(raw):
        try:
            msg = json.loads(raw)
        except ValueError:
            return
        if msg.get("op") == 1:                             # Identify
            ws.send(json.dumps({"op": 2, "d": {"negotiatedRpcVersion": 1}}))
        elif msg.get("op") == 6:                           # Request
            d = msg.get("d") or {}
            kind = d.get("requestType")
            if kind == "GetRecordStatus":
                data = {"outputActive": True, "outputTimecode": timecode()}
            elif kind == "GetStreamStatus":
                data = {"outputActive": False, "outputTimecode": "00:00:00.000"}
            elif kind == "GetStreamServiceSettings":
                data = {"streamServiceType": "rtmp_common",
                        "streamServiceSettings": {"service": "YouTube - RTMPS"}}
            else:
                data = {}
            ws.send(json.dumps({"op": 7, "d": {
                "requestType": kind, "requestId": d.get("requestId"),
                "requestStatus": {"result": True, "code": 100},
                "responseData": data}}))

    ws.on_message(on_message)


def seed(srv):
    """Riempie la sandbox come una run vera a meta' strada."""
    srv.set_lang("it")
    for rid, done in SEED.items():
        srv.post_json("/api/progress", {"run": rid, "done": harness.sids_of(rid)[:done]})

    sids = harness.sids_of("er")

    # Episodio chiuso, con l'URL del video: e' quello che rende cliccabile la guida.
    first = srv.post_json("/api/session/start",
                          {"run": "er", "source": "clock", "lead": 15,
                           "title": "Sepolcride e Grantempesta"})[1]["session"]["id"]
    tc = 153
    for sid in sids[:10]:
        srv.post_json("/api/marker", {"run": "er", "session": first, "sid": sid,
                                      "kind": "done", "tc": tc})
        tc += 380 + (tc % 240)
    srv.post_json("/api/session/update",
                  {"id": first,
                   "video_url": "https://www.youtube.com/watch?v=xxxxxxxxxxx",
                   "video_offset": 0})
    srv.post_json("/api/session/stop", {"id": first})

    # Episodio in corso: la barra della sessione con un task iniziato.
    live = srv.post_json("/api/session/start",
                         {"run": "er", "source": "obs", "lead": 15,
                          "title": "Nokron e lo Spirito ancestrale"})[1]["session"]["id"]
    tc = 210
    for sid in sids[58:62]:
        srv.post_json("/api/marker", {"run": "er", "session": live, "sid": sid,
                                      "kind": "done", "tc": tc})
        tc += 520 + (tc % 300)
    srv.post_json("/api/marker", {"run": "er", "session": live, "sid": sids[62],
                                  "kind": "start", "tc": tc})
    srv.post_json("/api/current", {"run": "er", "sid": sids[62]})

    # Le date reali le scrive il server con datetime('now'): per avere un
    # episodio "di tre giorni fa" si tocca il database, non l'orologio.
    con = sqlite3.connect(srv.db_path())
    con.execute("UPDATE sessions SET started_at=datetime('now','-3 days','-2 hours'),"
                " ended_at=datetime('now','-3 days') WHERE id=?", (first,))
    con.execute("UPDATE sessions SET started_at=datetime('now','-47 minutes')"
                " WHERE id=?", (live,))
    con.execute("UPDATE markers SET wall=datetime('now','-3 days','-90 minutes')"
                " WHERE session_id=?", (first,))
    con.execute("UPDATE markers SET wall=datetime('now','-9 minutes')"
                " WHERE session_id=?", (live,))
    con.commit()
    con.close()

    srv.get("/mode/streamer")


def shoot(srv, out):
    """I tre scatti. La guida si apre da file://, com'e' per chi la esporta."""
    code, guide = srv.get_text("/export/er")
    if code != 200:
        raise SystemExit("export della guida fallito: HTTP %s" % code)
    guide_path = os.path.join(out, "_guida.html")
    with open(guide_path, "w", encoding="utf-8") as fh:
        fh.write(guide)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 1000},
                                device_scale_factor=1)
        page.route_web_socket(re.compile(r"^ws://127\.0\.0\.1:4455"), fake_obs)

        page.goto(srv.url("/"))
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)            # le thumbnail sono canvas
        page.screenshot(path=os.path.join(out, "hub-home.jpg"), type="jpeg",
                        quality=88, full_page=True)

        page.set_viewport_size({"width": 1400, "height": SHOTS["streamer"][1]})
        page.goto(srv.url("/run/er"))
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)            # handshake OBS e cronometro
        page.evaluate("window.scrollTo(0, 0)")  # la pagina salta a "dove ero rimasto"
        page.wait_for_timeout(400)
        page.screenshot(path=os.path.join(out, "streamer.jpg"), type="jpeg", quality=88)

        page.set_viewport_size({"width": 1400, "height": SHOTS["guida"][1]})
        page.goto("file:///" + guide_path.replace("\\", "/"))
        page.wait_for_timeout(800)
        anchor = page.locator("text=IL PERCORSO").first
        if anchor.count():
            anchor.scroll_into_view_if_needed()
            page.evaluate("window.scrollBy(0, -80)")
            page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(out, "guida.jpg"), type="jpeg", quality=88)

        browser.close()

    os.remove(guide_path)


def main():
    srv = harness.AppServer()
    srv.start()
    try:
        seed(srv)
        shoot(srv, DESTS[0])
    finally:
        srv.stop()

    for name in SHOTS:
        src = os.path.join(DESTS[0], name + ".jpg")
        size = os.path.getsize(src) // 1024
        with open(src, "rb") as fh:
            blob = fh.read()
        for dest in DESTS[1:]:
            with open(os.path.join(dest, name + ".jpg"), "wb") as fh:
                fh.write(blob)
        print("  %-12s %5d KB" % (name + ".jpg", size))

    print("\nScattati in site/img e copiati in docs/img.")
    print("Se l'altezza di hub-home e' cambiata, aggiorna width/height "
          "dell'immagine in site/index.html.")


if __name__ == "__main__":
    main()
