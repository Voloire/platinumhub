# -*- coding: utf-8 -*-
"""Le pagine della modalita' streamer: overlay, episodi, sessione, diagnostica."""

import json
import re

from .config import CUR_PORT
from .hotkeys import HOTKEYS_DEFAULT, HOTKEY_STATE
from .i18n import T, L
from .routes import ROUTES
from .store import (get_pref, lang, open_session, session_row,
                    sessions_of)
from .ui import esc, fmt_tc, page_head, video_link


OBS_JS = r"""
var OBS = {ws:null, ok:false, rec:false, recTc:0, str:false, strTc:0, prefer:'auto', err:'', svc:''};
function sha256b64(str){
  return crypto.subtle.digest('SHA-256', new TextEncoder().encode(str)).then(function(buf){
    var b = new Uint8Array(buf), s = '';
    for(var i=0;i<b.length;i++) s += String.fromCharCode(b[i]);
    return btoa(s);
  });
}
function tcToSec(tc){
  if(!tc) return 0;
  var p = tc.split(':'); if(p.length < 3) return 0;
  return (+p[0])*3600 + (+p[1])*60 + parseFloat(p[2]);
}
function obsSend(type){
  if(!OBS.ok || !OBS.ws) return;
  try{ OBS.ws.send(JSON.stringify({op:6, d:{requestType:type, requestId:type}})); }catch(e){}
}
function obsPoll(){
  if(OBS._t) return;
  OBS._t = setInterval(function(){ obsSend('GetRecordStatus'); obsSend('GetStreamStatus'); }, 1000);
  obsSend('GetRecordStatus'); obsSend('GetStreamStatus'); obsSend('GetStreamServiceSettings');
}
function obsConnect(url, pass, cb){
  try{ if(OBS.ws) OBS.ws.close(); }catch(e){}
  if(OBS._t){ clearInterval(OBS._t); OBS._t = null; }
  var ws;
  try{ ws = new WebSocket(url); }catch(e){ if(cb) cb(false, 'URL?'); return; }
  OBS.ws = ws; OBS.ok = false; OBS.err = '';
  var done = false;
  var timer = setTimeout(function(){
    if(!OBS.ok && !done){ done = true; try{ ws.close(); }catch(e){}
      OBS.err = 'nessuna risposta (password?)'; if(cb) cb(false, OBS.err); }
  }, 4000);
  ws.onmessage = function(ev){
    var msg; try{ msg = JSON.parse(ev.data); }catch(e){ return; }
    if(msg.op === 0){
      var d = msg.d;
      var ident = function(a){
        ws.send(JSON.stringify({op:1, d:{rpcVersion:1, authentication:a, eventSubscriptions:0}}));
      };
      if(d && d.authentication){
        sha256b64((pass||'') + d.authentication.salt)
          .then(function(s1){ return sha256b64(s1 + d.authentication.challenge); })
          .then(ident)
          .catch(function(){ if(cb && !done){ done=true; OBS.err='password'; cb(false, OBS.err); } });
      } else { ident(undefined); }
    } else if(msg.op === 2){
      OBS.ok = true; OBS.err = ''; clearTimeout(timer);
      if(cb && !done){ done = true; cb(true, 'rpc v' + (msg.d ? msg.d.negotiatedRpcVersion : '?')); }
      obsPoll();
    } else if(msg.op === 7 && msg.d && msg.d.responseData){
      var r = msg.d, x = r.responseData;
      if(r.requestType === 'GetRecordStatus'){ OBS.rec = !!x.outputActive; OBS.recTc = tcToSec(x.outputTimecode); }
      if(r.requestType === 'GetStreamStatus'){ OBS.str = !!x.outputActive; OBS.strTc = tcToSec(x.outputTimecode); }
      if(r.requestType === 'GetStreamServiceSettings'){
        var ss = x.streamServiceSettings || {};
        var srv = ss.service || ss.server || x.streamServiceType || '';
        srv = String(srv);
        if(/youtube|ytb/i.test(srv)) srv = 'YouTube';
        else if(/twitch/i.test(srv)) srv = 'Twitch';
        else if(srv === 'rtmp_custom') srv = 'RTMP';
        OBS.svc = srv.slice(0, 22);
      }
    }
  };
  ws.onerror = function(){ clearTimeout(timer); OBS.ok = false;
    if(cb && !done){ done = true; OBS.err = 'non raggiungibile'; cb(false, OBS.err); } };
  ws.onclose = function(ev){ if(OBS.ok) OBS.err = 'connessione chiusa';
    else if(!OBS.err) OBS.err = 'password o handshake rifiutati';
    OBS.ok = false; if(OBS._t){ clearInterval(OBS._t); OBS._t = null; } };
}
/* which timecode counts, and is anything actually running */
function obsTime(){
  if(!OBS.ok) return null;
  var p = OBS.prefer;
  if(p === 'stream') return OBS.str ? {tc:OBS.strTc, kind:'stream'} : null;
  if(p === 'rec')    return OBS.rec ? {tc:OBS.recTc, kind:'rec'} : null;
  if(OBS.str) return {tc:OBS.strTc, kind:'stream'};
  if(OBS.rec) return {tc:OBS.recTc, kind:'rec'};
  return null;
}
"""


OVERLAY_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:transparent;font-family:'Roboto','Segoe UI',system-ui,Arial,sans-serif;
color:#fff;overflow:hidden}
#box{position:fixed;transition:opacity .6s ease;left:var(--pad,24px);bottom:var(--pad,24px);max-width:var(--maxw,44vw);min-width:340px;
background:linear-gradient(90deg,rgba(13,15,20,.93),rgba(13,15,20,.78));
border-left:4px solid #c8a24a;border-radius:6px;padding:13px 20px 14px;
box-shadow:0 6px 26px rgba(0,0,0,.55)}
body.pos-top #box{top:var(--pad,24px);bottom:auto}
body.pos-tr #box{top:var(--pad,24px);bottom:auto;left:auto;right:var(--pad,24px)}
body.pos-br #box{bottom:var(--pad,24px);top:auto;left:auto;right:var(--pad,24px)}
#box.hide{opacity:0}
.k{font-size:13px;letter-spacing:3px;color:#8a8878;text-transform:uppercase;margin-bottom:5px}
.k b{color:#c8a24a;font-weight:500;letter-spacing:2px}
.t{font-size:26px;line-height:1.28;font-weight:500;text-shadow:0 2px 6px rgba(0,0,0,.9)}
.t .cap{color:#7fd8d0}
.l{font-size:15px;color:#9c9a8a;margin-top:5px}
.row{display:flex;gap:10px;align-items:center;margin-top:9px;flex-wrap:wrap}
.pill{font-size:12px;letter-spacing:1px;padding:2px 9px;border-radius:4px}
.pill.tro{background:#2a2413;color:#c8a24a;border:1px solid #8a7134}
.pill.miss{background:#2a1a14;color:#c86a4a;border:1px solid #4a2a1e}
.pill.nxt{background:#141d2a;color:#7fa8d9;border:1px solid #4a6a94}
.prog{font-size:13px;color:#8a8878;font-variant-numeric:tabular-nums;letter-spacing:1px}
body.size-s .t{font-size:20px} body.size-s .k{font-size:11px} body.size-s .l{font-size:13px}
body.size-l .t{font-size:33px} body.size-l .k{font-size:15px} body.size-l .l{font-size:17px}
#box.flash{animation:fl 1.6s ease-out 1}
#toast{position:fixed;left:50%;transform:translateX(-50%);bottom:6vh;opacity:0;
transition:opacity .25s ease;background:rgba(13,15,20,.94);border:1px solid #c8a24a;
border-radius:6px;padding:9px 20px;font-size:19px;letter-spacing:.5px;
box-shadow:0 6px 26px rgba(0,0,0,.6);pointer-events:none;max-width:70vw}
#toast.on{opacity:1}
@keyframes fl{0%{border-left-color:#fff;background:linear-gradient(90deg,rgba(60,48,16,.96),rgba(13,15,20,.8))}
100%{border-left-color:#c8a24a}}
"""


def render_overlay(run_id, q):
    lg = lang()
    pos = (q.get("pos") or ["bl"])[0]
    size = (q.get("size") or ["m"])[0]
    shownext = (q.get("next") or ["1"])[0] != "0"
    try:
        pad = max(0, min(1200, int((q.get("pad") or ["24"])[0])))
    except ValueError:
        pad = 24
    wq = (q.get("w") or [""])[0]
    if wq:
        try:
            maxw = "%dpx" % max(240, min(3000, int(wq)))
        except ValueError:
            maxw = "44vw"
    else:
        maxw = "44vw"      # si adatta da solo a qualsiasi canvas
    showprog = (q.get("progress") or ["1"])[0] != "0"
    try:
        hold = max(0, min(600, int((q.get("hold") or ["10"])[0])))
    except ValueError:
        hold = 10
    cls = {"bl": "", "top": "pos-top", "tr": "pos-tr", "br": "pos-br"}.get(pos, "")
    cls += " size-" + (size if size in ("s", "m", "l") else "m")
    lab = "ORA" if lg == "it" else "NOW"
    labn = "POI" if lg == "it" else "NEXT"
    return f"""<!DOCTYPE html><html lang="{lg}"><head><meta charset="UTF-8">
<title>overlay</title><style>{OVERLAY_CSS}</style></head>
<body class="{cls}" style="--pad:{pad}px;--maxw:{maxw}">
<div id="box" style="opacity:0">
  <div class="k"><b id="ph">—</b></div>
  <div class="t" id="txt">—</div>
  <div class="l" id="loc"></div>
  <div class="row" id="row"></div>
</div>
<div id="toast"></div>
<script>
var RUN = {json.dumps(run_id)}, SHOWNEXT = {str(shownext).lower()}, SHOWPROG = {str(showprog).lower()};
var HOLD = {hold};
var LAB = {json.dumps(lab)}, LABN = {json.dumps(labn)};
var lastKey = null, hideT = null, lastToast = '', toastT = null;
function esc(s){{ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;'); }}
var CAPRE = null;
try{{ CAPRE = new RegExp("(?<![\\w'\u2019])([A-Z\u00C0-\u00DE][A-Z\u00C0-\u00DE0-9'\u2019+\\-]{{1,}}(?:[ ][A-Z\u00C0-\u00DE][A-Z\u00C0-\u00DE0-9'\u2019+\\-]{{1,}})*)(?![\\w'\u2019])", "g"); }}
catch(e){{ CAPRE = null; }}
function caps(s){{
  var t = esc(s);
  if(!CAPRE) return t;
  try{{ return t.replace(CAPRE, '<span class="cap">$1</span>'); }}catch(e){{ return t; }}
}}
function tick(){{
  fetch('/api/current?run='+RUN).then(function(r){{return r.json();}}).then(function(j){{
    var box = document.getElementById('box'), c = j.current;
    if(!c){{ box.style.opacity = 0; return; }}
    var key = c.i;
    document.getElementById('ph').textContent = LAB + ' \u00b7 ' + c.phase;
    document.getElementById('txt').innerHTML = caps(c.text);
    document.getElementById('loc').textContent = c.loc || '';
    var row = [];
    if(c.trophy && c.trophy_label) row.push('<span class="pill tro">'+esc(c.trophy_label)+'</span>');
    if(c.missable) row.push('<span class="pill miss">\u26a0 MISSABILE</span>');
    if(SHOWNEXT && j.next) row.push('<span class="pill nxt">'+LABN+': '+esc(j.next.text.slice(0,58))+'\u2026</span>');
    if(SHOWPROG) row.push('<span class="prog">🏆 '+j.tdone+'/'+j.ttotal+' \u00b7 📋 '+j.done+'/'+j.total+'</span>');
    document.getElementById('row').innerHTML = row.join('');
    if(lastKey === null || key !== lastKey){{
      /* nuovo task: mostra, lampeggia, e se HOLD > 0 sparisce da solo */
      box.style.opacity = 1;
      box.classList.remove('flash'); void box.offsetWidth;
      if(lastKey !== null) box.classList.add('flash');
      if(hideT) clearTimeout(hideT);
      if(HOLD > 0) hideT = setTimeout(function(){{ box.style.opacity = 0; }}, HOLD * 1000);
    }} else if(HOLD === 0){{
      box.style.opacity = 1;
    }}
    lastKey = key;
    if(j.toast && j.toast !== lastToast){{
      lastToast = j.toast;
      var tb = document.getElementById('toast');
      tb.textContent = j.toast; tb.classList.add('on');
      if(toastT) clearTimeout(toastT);
      toastT = setTimeout(function(){{ tb.classList.remove('on'); }}, 2600);
    }}
  }}).catch(function(){{}});
}}
tick(); setInterval(tick, 700);
</script></body></html>"""


def render_episodes(run_id):
    lg, t = lang(), T[lang()]
    d = ROUTES[run_id]
    # Un marker il cui sid non e' piu' nella route (orfano) non deve rompere
    # la pagina: si salta e basta. E' il vecchio IndexError del 2.10, che coi
    # sid non puo' piu' nemmeno presentarsi come indice fuori scala.
    by_sid = {s["sid"]: s for p in d["phases"] for s in p["steps"]}
    eps = sessions_of(run_id)
    p = [page_head(lg, d["game"], run_id, "eps", t["eps_title"])]
    if not eps:
        p.append(f'<div class="hubnote">{t["no_eps"]}</div>')
    for e in eps:
        marks = [m for m in e["markers"]]
        ntask = len({m["sid"] for m in marks if m["kind"] == "done"})
        ntro = len({m["sid"] for m in marks if m["kind"] == "done"
                    and m["sid"] in by_sid and by_sid[m["sid"]].get("trophy")})
        dur = max([m["tc"] for m in marks] or [0])
        state = (f'<a class="chip ok" href="{esc(e["video_url"])}" target="_blank">▶ {esc(e["video_url"])[:44]} · {t["linked"]}</a>'
                 if e["video_url"] else f'<span class="chip bad">⚠ {t["no_video"]}</span>')
        live = "" if e["ended_at"] else f' <span class="chip ep">● {t["rec"]}</span>'
        p.append('<div class="epcard"><div class="h">'
                 f'<h3>{t["ep"].upper()}ISODIO {e["number"]}' if lg == "it" else
                 '<div class="epcard"><div class="h">' f'<h3>EPISODE {e["number"]}')
        p.append(f'{" — " + esc(e["title"]) if e["title"] else ""}</h3>'
                 f'<span class="meta">{fmt_tc(dur)} · {ntask} task · {ntro} 🏆 · {esc(e["started_at"][:16])}{live}</span>'
                 f'<span class="spacer"></span>{state}</div><div class="b">')
        p.append('<div class="tl">')
        for m in marks:
            if m["kind"] == "session_start":
                lab = "Inizio sessione" if lg == "it" else "Session start"
                p.append(f'<div class="t">{fmt_tc(0)}</div><div class="d">{lab}</div>')
                continue
            if m["kind"] != "done" and m["kind"] != "free":
                continue
            secs = max(0, int(round(m["tc"] - e["video_offset"] - e["lead"])))
            shown = fmt_tc(secs)
            if e["video_url"]:
                shown = f'<a href="{video_link(e["video_url"], secs)}" target="_blank">{shown}</a>'
            if m["kind"] == "free":
                p.append(f'<div class="t">{shown}</div><div class="d">📍 {esc(m["note"] or "—")}</div>')
            else:
                st = by_sid.get(m["sid"])
                if not st:
                    continue
                txt = L(st, "text", lg)
                tro = next((L(x, "label", lg) for x in st.get("tags", []) if x["type"] == "trophy"), "")
                cls = " tro" if st.get("trophy") else ""
                p.append(f'<div class="t">{shown}</div><div class="d{cls}">'
                         f'{esc(tro if tro else txt[:96])}</div>')
        p.append("</div>")
        p.append(f'<div class="setrow">'
                 f'<button onclick="chapters({e["id"]},1)">📋 {t["chapters"]}</button>'
                 f'<button onclick="chapters({e["id"]},0)">📄 {t["copy_tasks"]}</button>'
                 f'<button class="danger" onclick="delEp({e["id"]})">🗑 {t["del_ep"]}</button>'
                 f'<span id="cp{e["id"]}" style="color:var(--ok)"></span></div>')
        p.append(f'<textarea class="mono" id="ta{e["id"]}" readonly></textarea>')
        p.append("</div></div>")
    p.append(f'<div class="setrow" style="margin:20px 0 4px"><a class="chip ok" style="padding:9px 15px;'
             f'font-size:.9em;text-decoration:none" href="/export/{run_id}">📤 {t["publish"]}</a>'
             f'<span style="max-width:560px">{t["publish_note"]}</span></div>')
    p.append(f'<footer>{t["footer_run"]}</footer></div>')
    p.append("""<script>
var RUN = %s, EPS = %s;
function fmt(s){ s=Math.max(0,Math.round(s)); var h=Math.floor(s/3600),m=Math.floor(s%%3600/60),x=s%%60;
  return (h? h+':'+String(m).padStart(2,'0') : String(m).padStart(2,'0'))+':'+String(x).padStart(2,'0'); }
function chapters(id, onlyTro){
  var e = EPS[id]; if(!e) return;
  var out = ['00:00 Intro'], last = 0;
  e.marks.forEach(function(m){
    if(m.kind !== 'done' && m.kind !== 'free') return;
    if(onlyTro && m.kind === 'done' && !m.trophy) return;
    var s = Math.max(0, Math.round(m.tc - e.off - e.lead));
    if(s <= last) s = last + 1;
    last = s;
    out.push(fmt(s) + ' ' + (m.label || ''));
  });
  var txt = out.join('\\n');
  var ta = document.getElementById('ta'+id); ta.value = txt; ta.select();
  try{ document.execCommand('copy'); }catch(err){}
  if(navigator.clipboard) navigator.clipboard.writeText(txt).catch(function(){});
  document.getElementById('cp'+id).textContent = %s;
  setTimeout(function(){ document.getElementById('cp'+id).textContent=''; }, 2000);
}
function delEp(id){
  if(!confirm('?')) return;
  fetch('/api/session/delete', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({id: id})}).then(function(){ location.reload(); });
}
</script></body></html>""" % (json.dumps(run_id), json.dumps(episodes_js(run_id)), json.dumps(t["copied"])))
    return "\n".join(p)


def episodes_js(run_id):
    lg = lang()
    d = ROUTES[run_id]
    by_sid = {s["sid"]: s for p in d["phases"] for s in p["steps"]}
    out = {}
    for e in sessions_of(run_id):
        marks = []
        for m in e["markers"]:
            if m["kind"] == "free":
                marks.append({"kind": "free", "tc": m["tc"], "label": "📍 " + (m["note"] or ""),
                              "trophy": True})
            elif m["kind"] == "done" and m["sid"] in by_sid:
                st = by_sid[m["sid"]]
                tro = next((L(x, "label", lg) for x in st.get("tags", []) if x["type"] == "trophy"), "")
                lab = (tro or L(st, "text", lg))
                lab = re.sub(r"^🏆\s*", "", lab)[:80]
                marks.append({"kind": "done", "tc": m["tc"], "label": lab,
                              "trophy": bool(st.get("trophy"))})
        out[e["id"]] = {"off": e["video_offset"], "lead": e["lead"], "marks": marks}
    return out


# -------------------------------------------------------------- session page
def render_session(run_id):
    lg, t = lang(), T[lang()]
    d = ROUTES[run_id]
    ses = session_row(open_session(run_id)[0]) if open_session(run_id) else None
    p = [page_head(lg, d["game"], run_id, "ses", t["session_cfg"])]
    p.append('<div class="epcard"><div class="b">')
    p.append(f'<div class="setrow"><span>{t["obs_addr"]}</span>'
             f'<input type="text" id="obsUrl" value="{esc(get_pref("obs_url", "ws://127.0.0.1:4455"))}">'
             f'<span>{t["obs_pw"]}</span><input type="password" id="obsPw" value="{esc(get_pref("obs_pass", ""))}">'
             f'<button onclick="testObs()">{t["obs_test"]}</button>'
             f'<span id="obsState" class="chip bad">{t["obs_off"]}</span></div>')
    pref = get_pref("obs_prefer", "auto")
    opts = "".join(f'<option value="{k}"{" selected" if pref == k else ""}>{t["pref_" + k]}</option>'
                   for k in ("auto", "stream", "rec"))
    p.append(f'<div class="setrow"><span>{t["prefer"]}</span>'
             f'<select id="obsPrefer" onchange="savePrefs()" style="background:#0a0c10;border:1px solid var(--line);'
             f'border-radius:6px;color:var(--text);padding:6px 10px;font-family:inherit">{opts}</select></div>')
    p.append("</div></div>")

    p.append(f'<h2 style="font-size:.85em;color:var(--gold);letter-spacing:2px;margin:24px 0 4px;'
             f'text-transform:uppercase;font-weight:500">{t["ep_cfg"]}</h2>')
    p.append('<div class="epcard"><div class="b">')
    if ses:
        p.append(f'<div class="setrow"><span>{t["ep"]} {ses["number"]}</span>'
                 f'<span>{t["ep_title"]}</span><input type="text" id="epTitle" value="{esc(ses["title"])}"></div>')
        p.append(f'<div class="setrow"><span>{t["ep_url"]}</span>'
                 f'<input type="text" id="epUrl" style="min-width:300px" value="{esc(ses["video_url"])}"></div>')
        p.append(f'<div class="setrow"><span>{t["ep_off"]}</span>'
                 f'<input type="number" id="epOff" value="{ses["video_offset"]}"><span>{t["ep_off_u"]}</span></div>')
        p.append(f'<div class="setrow"><span>{t["ep_lead"]}</span>'
                 f'<input type="number" id="epLead" value="{ses["lead"]}"><span>{t["ep_lead_u"]}</span></div>')
        p.append(f'<div class="setrow"><button onclick="saveSes({ses["id"]})">💾 {t["obs_save"]}</button>'
                 f'<span id="sesState" style="color:var(--ok)"></span></div>')
    else:
        p.append(f'<div class="setrow">{t["no_eps"]}</div>')
    p.append("</div></div>")

    # ---- scorciatoie globali -------------------------------------------------
    hk_spec = get_pref("hotkeys", HOTKEYS_DEFAULT)
    hk_on = get_pref("hotkeys_on", "1") == "1"
    p.append(f'<h2 style="font-size:.85em;color:var(--gold);letter-spacing:2px;margin:24px 0 4px;'
             f'text-transform:uppercase;font-weight:500">⌨ {t["hk_sec"]}</h2>')
    p.append('<div class="epcard"><div class="b">')
    if HOTKEY_STATE["active"]:
        rows = " · ".join("<code>%s</code> %s" % (esc(lb), esc(ac)) for lb, ac in HOTKEY_STATE["active"])
        p.append(f'<div class="setrow"><span class="chip ok">● {t["hk_state_on"]}</span><span>{rows}</span></div>')
    else:
        why = HOTKEY_STATE["why"] or "-"
        p.append(f'<div class="setrow"><span class="chip bad">{t["hk_state_off"]}</span>'
                 f'<span>{esc(why)}</span></div>')
    for lb, ac in HOTKEY_STATE["failed"]:
        p.append(f'<div class="setrow"><span class="chip bad">⚠</span>'
                 f'<span><code>{esc(lb)}</code> → {esc(ac)}: combinazione già occupata da un altro programma</span></div>')
    p.append(f'<div class="setrow"><input type="text" id="hkSpec" style="min-width:420px" value="{esc(hk_spec)}">'
             f'<label style="display:flex;gap:6px;align-items:center"><input type="checkbox" id="hkOn"'
             f'{" checked" if hk_on else ""}> on</label>'
             f'<button onclick="saveHk()">💾 {t["hk_save"]}</button>'
             f'<span id="hkState" style="color:var(--ok)"></span></div>')
    p.append(f'<div class="setrow" style="max-width:660px;color:var(--muted)">{t["hk_hint"]}</div>')
    p.append('</div></div>')

    ov = f"http://127.0.0.1:{CUR_PORT[0]}/overlay/{run_id}"
    p.append(f'<h2 style="font-size:.85em;color:var(--gold);letter-spacing:2px;margin:24px 0 4px;'
             f'text-transform:uppercase;font-weight:500">{t["ov_title"]}</h2>')
    p.append('<div class="epcard"><div class="b">')
    p.append(f'<div class="setrow"><input type="text" id="ovUrl" style="min-width:340px" readonly value="{ov}">'
             f'<button onclick="copyOv()">📋 {t["ov_copy"]}</button>'
             f'<a class="chip ep" href="{ov}" target="_blank">anteprima</a></div>')
    p.append(f'<div class="setrow" style="max-width:640px">{t["ov_note"]}</div>')
    p.append(f'<div class="setrow"><a class="btn" style="background:var(--panel2);border:1px solid var(--line);'
             f'border-radius:6px;padding:7px 13px;color:var(--text)" href="/selftest/{run_id}">🩺 {t["diag"]}</a>'
             f'<span>{t["diag_note"][:60]}…</span></div>')
    p.append(f'<div class="setrow"><span>?pos=</span><code>bl</code> / <code>br</code> / <code>top</code> / <code>tr</code>'
             f' · <span>&amp;size=</span><code>s</code>/<code>m</code>/<code>l</code>'
             f' · <span>&amp;pad=</span>margine dai bordi · <span>&amp;w=</span>larghezza max'
             f' · <span>&amp;hold=</span>secondi visibile (<code>0</code> = sempre)'
             f' · <span>&amp;next=0</span> · <span>&amp;progress=0</span></div>')
    p.append(f'<div class="setrow" style="max-width:680px;color:var(--muted);display:block;line-height:1.6">'
             f'<b style="color:var(--gold);font-weight:500">Regola unica: larghezza e altezza della sorgente '
             f'Browser identiche al canvas di OBS</b> (Impostazioni → Video → Risoluzione di base). '
             f'Vale per qualsiasi risoluzione — 1920×1080, 2560×1080, 3440×1440. Non ridimensionare il '
             f'riquadro nella scena: il posizionamento lo fa la pagina, e stirarlo sfoca il testo. '
             f'La larghezza del pannello è il 44% del canvas, quindi si adatta da sola.<br>'
             f'<code>&amp;pad=</code> serve solo se un gioco gira in 16:9 dentro un canvas più largo: '
             f'alza il margine fino a far partire il pannello dove inizia l&#39;immagine '
             f'(su 2560×1080 con gioco 16:9 sono 320&nbsp;px di banda per lato).</div>')
    p.append("</div></div>")
    p.append(f'<footer>{t["footer_run"]}</footer></div>')
    p.append("""<script>
function savePrefs(){
  fetch('/api/pref', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({obs_url: document.getElementById('obsUrl').value,
      obs_pass: document.getElementById('obsPw').value,
      obs_prefer: document.getElementById('obsPrefer').value})});
}
function copyOv(){ var e=document.getElementById('ovUrl'); e.select();
  try{document.execCommand('copy');}catch(x){}
  if(navigator.clipboard) navigator.clipboard.writeText(e.value).catch(function(){}); }
function saveSes(id){
  fetch('/api/session/update', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({id:id, title:document.getElementById('epTitle').value,
      video_url:document.getElementById('epUrl').value,
      video_offset:parseInt(document.getElementById('epOff').value||'0',10),
      lead:parseInt(document.getElementById('epLead').value||'15',10)})})
   .then(function(){ document.getElementById('sesState').textContent='ok ✓';
     setTimeout(function(){document.getElementById('sesState').textContent='';},1800); });
}
function saveHk(){
  var st = document.getElementById('hkState');
  st.style.color = 'var(--muted)'; st.textContent = '…';
  fetch('/api/hotkeys', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({spec: document.getElementById('hkSpec').value,
                          on: document.getElementById('hkOn').checked})})
    .then(function(r){ if(!r.ok) throw 0;
      st.style.color = 'var(--gold)'; st.textContent = 'salvato — riavvia l\\'app per applicarle'; })
    .catch(function(){ st.style.color = 'var(--warn)';
      st.textContent = 'combinazione non valida (serve almeno un modificatore: ctrl / alt / shift)'; });
}
""" + OBS_JS + """
function testObs(){
  savePrefs();
  var st = document.getElementById('obsState');
  st.textContent = '…'; st.className = 'chip';
  obsConnect(document.getElementById('obsUrl').value, document.getElementById('obsPw').value,
    function(ok, info){ st.textContent = ok ? ('● ' + info) : ('✕ ' + info);
                        st.className = ok ? 'chip ok' : 'chip bad'; });
}
</script></body></html>""")
    return "\n".join(p)


# ---------------------------------------------------------------- diagnostics
def render_selftest(run_id):
    lg, t = lang(), T[lang()]
    d = ROUTES[run_id]
    p = [page_head(lg, d["game"], run_id, "ses", t["diag"])]
    p.append('<div class="epcard"><div class="b">')
    p.append(f'<div class="setrow" style="max-width:700px">{t["diag_note"]}</div>')
    p.append(f'<div class="setrow"><button onclick="runDiag()">🩺 {t["diag_run"]}</button>'
             f'<button onclick="copyDiag()">📋 {t["diag_copy"]}</button>'
             f'<span id="dState" style="color:var(--ok)"></span></div>')
    p.append('<textarea class="mono" id="dOut" style="min-height:420px" readonly></textarea>')
    p.append('</div></div>')
    p.append(f'<footer>{t["footer_run"]}</footer></div>')
    cfg = {"run": run_id, "obs_url": get_pref("obs_url", "ws://127.0.0.1:4455"),
           "obs_pass": get_pref("obs_pass", ""), "prefer": get_pref("obs_prefer", "auto"),
           "port": CUR_PORT[0], "saved": t["diag_save"],
           "sids": d["_sids"][:2]}
    p.append("<script>\nvar D = " + json.dumps(cfg, ensure_ascii=False) + ";\n" + OBS_JS + DIAG_JS
             + "\n</script></body></html>")
    return "\n".join(p)


DIAG_JS = r"""
var LOG = [];
function say(ok, label, detail){
  var mark = ok === true ? '[ OK ]' : (ok === false ? '[FAIL]' : '[ .. ]');
  LOG.push(mark + '  ' + label + (detail ? '  ->  ' + detail : ''));
  document.getElementById('dOut').value = LOG.join('\n');
}
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }

async function runDiag(){
  LOG = []; document.getElementById('dState').textContent = '';
  var stamp = new Date().toISOString().replace('T',' ').slice(0,19);
  LOG.push('PLATINUM HUB - DIAGNOSTICA  ' + stamp);
  LOG.push('run: ' + D.run + '   porta: ' + D.port);
  LOG.push('browser: ' + navigator.userAgent.slice(0, 110));
  LOG.push(''.padEnd(66, '-'));

  /* 1 - server e dati */
  try{
    var sum = await (await fetch('/api/summary')).json();
    say(true, '1. Server e route', sum.length + ' run caricate');
    sum.forEach(function(r){
      LOG.push('        ' + r.game.padEnd(30) + r.steps_done + '/' + r.steps_total +
               ' passi, ' + r.trophies_done + '/' + r.trophies_total + ' trofei');
    });
  }catch(e){ say(false, '1. Server e route', String(e)); }

  /* 2 - font */
  try{ say(document.fonts.check('16px Roboto'), '2. Font Roboto', 'incorporato'); }
  catch(e){ say(false, '2. Font Roboto', String(e)); }

  /* 3 - OBS */
  OBS.prefer = D.prefer;
  var obsInfo = await new Promise(function(res){
    var done = false;
    obsConnect(D.obs_url, D.obs_pass, function(ok, info){ if(!done){ done = true; res({ok:ok, info:info}); } });
    setTimeout(function(){ if(!done){ done = true; res({ok:false, info:'nessuna risposta'}); } }, 6000);
  });
  say(obsInfo.ok, '3. Connessione OBS', D.obs_url + '  ' + obsInfo.info);
  if(!obsInfo.ok){
    LOG.push('        Controlla: OBS aperto, Strumenti > Impostazioni WebSocket abilitato,');
    LOG.push('        porta 4455, password corretta nella scheda Sessione.');
  }

  /* 4 - timecode che avanza */
  if(obsInfo.ok){
    await sleep(1400);
    var a = obsTime(); var aRec = OBS.rec, aStr = OBS.str;
    await sleep(2600);
    var b = obsTime();
    LOG.push('        registrazione attiva: ' + aRec + '   diretta attiva: ' + aStr);
    if(!a || !b){
      say(false, '4. Timecode', 'nessun output attivo: avvia una registrazione o una diretta di prova');
    } else {
      var dt = b.tc - a.tc;
      say(dt > 1.5 && dt < 6, '4. Timecode ' + b.kind,
          a.tc.toFixed(1) + 's -> ' + b.tc.toFixed(1) + 's  (avanzato di ' + dt.toFixed(1) + 's in ~2.6s)');
    }
  } else { say(null, '4. Timecode', 'saltato'); }

  /* 5 - giro completo sessione + marker sul database */
  var sid = null;
  try{
    var r = await (await fetch('/api/session/start', {method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({run: D.run, source: obsInfo.ok ? 'obs' : 'clock', title: '__DIAGNOSTICA__'})})).json();
    sid = r.session.id;
    var tc = (obsTime() ? obsTime().tc : 42);
    await fetch('/api/marker', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({run: D.run, session: sid, sid: D.sids[0], kind: 'done', tc: tc})});
    await fetch('/api/marker', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({run: D.run, session: sid, sid: D.sids[1], kind: 'start', tc: tc + 1})});
    var eps = await (await fetch('/api/episodes?run=' + D.run)).json();
    var mine = eps.filter(function(e){ return e.id === sid; })[0];
    var kinds = mine ? mine.markers.map(function(m){ return m.kind; }).join(',') : '';
    say(kinds === 'session_start,done,start', '5. Sessione e marker su SQLite', kinds || 'nessun marker');
    LOG.push('        tc scritto: ' + tc.toFixed(1) + 's   (' + (obsInfo.ok ? 'da OBS' : 'cronometro interno') + ')');
  }catch(e){ say(false, '5. Sessione e marker su SQLite', String(e)); }

  /* 6 - link al video */
  try{
    await fetch('/api/session/update', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({id: sid, video_url: 'https://youtu.be/TEST', video_offset: 0, lead: 5})});
    var html = await (await fetch('/run/' + D.run)).text();
    say(html.indexOf('youtu.be/TEST?t=') >= 0, '6. Link nella checklist',
        'targhetta EP con ?t= generata');
  }catch(e){ say(false, '6. Link nella checklist', String(e)); }

  /* 7 - overlay */
  try{
    var cur = await (await fetch('/api/current?run=' + D.run)).json();
    say(!!cur.current, '7. Overlay - task corrente',
        cur.current ? cur.current.text.slice(0, 62) : 'nessuno');
    var ov = await (await fetch('/overlay/' + D.run)).text();
    say(ov.indexOf('id="txt"') >= 0, '7b. Pagina overlay',
        'http://127.0.0.1:' + D.port + '/overlay/' + D.run + '  (' + ov.length + ' byte)');
  }catch(e){ say(false, '7. Overlay', String(e)); }

  /* pulizia */
  try{
    if(sid){ await fetch('/api/session/delete', {method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify({id: sid})}); }
    say(true, '8. Pulizia', 'sessione di prova eliminata');
  }catch(e){ say(false, '8. Pulizia', String(e)); }

  LOG.push(''.padEnd(66, '-'));
  var fails = LOG.filter(function(l){ return l.indexOf('[FAIL]') === 0; }).length;
  LOG.push(fails === 0 ? 'TUTTO OK - la catena funziona da cima a fondo.'
                       : fails + ' controllo/i falliti: vedi le righe [FAIL] qui sopra.');
  document.getElementById('dOut').value = LOG.join('\n');

  var res = await (await fetch('/api/selftest', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({text: LOG.join('\n')})})).json();
  document.getElementById('dState').textContent = res.ok ? D.saved : '';
}
function copyDiag(){
  var e = document.getElementById('dOut'); e.select();
  try{ document.execCommand('copy'); }catch(x){}
  if(navigator.clipboard) navigator.clipboard.writeText(e.value).catch(function(){});
}
"""
