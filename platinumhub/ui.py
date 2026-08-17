# -*- coding: utf-8 -*-
"""Mattoni condivisi delle pagine: CSS, escape/evidenziazione, cornici, pannello scorciatoie."""

import html
import json
import re
import urllib.parse

from .hotkeys import HOTKEY_ACTIONS
from .i18n import T
from .store import get_pref, lang


def fmt_tc(sec):
    sec = max(0, int(round(sec)))
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return (f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}")


def video_link(url, t):
    if not url:
        return ""
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}t={int(t)}"


# ------------------------------------------------------------------------- CSS
CSS = """
@font-face{font-family:'Roboto';src:url('/fonts/roboto-400.woff2') format('woff2');
font-weight:400;font-style:normal;font-display:swap}
@font-face{font-family:'Roboto';src:url('/fonts/roboto-400i.woff2') format('woff2');
font-weight:400;font-style:italic;font-display:swap}
@font-face{font-family:'Roboto';src:url('/fonts/roboto-700.woff2') format('woff2');
font-weight:700;font-style:normal;font-display:swap}
:root{--bg:#0d0f14;--panel:#151823;--panel2:#1a1e2c;--line:#2a2f42;--gold:#c8a24a;
--gold-dim:#8a7134;--moon:#7fa8d9;--moon-dim:#4a6a94;--text:#d8d5c8;--muted:#8a8878;
--warn:#c86a4a;--warn-bg:#2a1a14;--ok:#7fc98a;--item:#7fd8d0;--rec:#e05252}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);
font-family:'Roboto','Segoe UI',system-ui,-apple-system,Arial,sans-serif;
line-height:1.55;padding-bottom:80px;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
header{padding:30px 20px 18px;text-align:center;
background:linear-gradient(180deg,#131625 0%,var(--bg) 100%);border-bottom:1px solid var(--line);position:relative}
header h1{font-size:1.5em;color:var(--gold);letter-spacing:3px;font-weight:500}
header p.sub{color:var(--muted);margin-top:6px;font-style:italic}
header p.sub .by{color:var(--gold)}
header p.meta{color:var(--moon);margin-top:8px;font-size:.85em}
.langsel{display:inline-flex;align-items:center;gap:6px;font-size:.82em;letter-spacing:1px;
background:var(--panel);border:1px solid var(--gold-dim);border-radius:8px;padding:5px 8px 5px 11px}
.langsel .lbl{color:var(--muted);font-size:.86em;margin-right:2px}
.langsel a{padding:4px 11px;border:1px solid var(--line);border-radius:5px;color:var(--muted);
font-weight:bold;letter-spacing:1px}
.langsel a:hover{border-color:var(--gold);color:var(--gold);background:var(--panel2)}
.langsel a.on{background:var(--gold-dim);border-color:var(--gold);color:#12141c}
.langsel-top{position:absolute;top:14px;right:16px;z-index:30}
@media(max-width:700px){.langsel-top{position:static;margin:0 auto 10px;display:inline-flex}}
.wrap{max-width:900px;margin:0 auto;padding:0 16px}
.back{display:inline-block;margin:16px 0 0;font-size:.85em;color:var(--muted)}
.back:hover{color:var(--gold)}
/* ---- hub cards ---- */
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(390px,1fr));gap:16px;margin:24px 0}
@media(max-width:840px){.cards{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 20px;
display:block;transition:border-color .18s,transform .18s;position:relative;overflow:hidden}
.card:hover{border-color:var(--gold-dim);transform:translateY(-2px)}
.card .stripe{position:absolute;left:0;top:0;bottom:0;width:4px}
.card h2{font-size:1.05em;font-weight:500;color:var(--gold);letter-spacing:1px;margin-bottom:4px}
.card .cardart{display:block;width:calc(100% + 40px);height:auto;margin:-18px -20px 14px;
border-radius:11px 11px 0 0;border-bottom:1px solid var(--line)}
.card .tag2{font-size:.84em;color:var(--muted);font-style:italic;margin-bottom:12px;display:block}
.card .facts{font-size:.78em;color:var(--moon);margin-bottom:12px}
.card .prow{display:flex;align-items:center;gap:10px;margin-top:7px}
.card .prow .lb{font-size:.74em;color:var(--muted);min-width:100px}
.card .when{font-size:.7em;color:#5f5d50;margin-top:9px;font-style:italic}
.bar{flex:1;height:10px;background:#0a0c10;border-radius:6px;overflow:hidden;
border:1px solid var(--line);min-width:110px}
.bar>div{height:100%;width:0%;background:linear-gradient(90deg,var(--gold-dim),var(--gold));transition:width .3s}
.bar.moonbar>div{background:linear-gradient(90deg,var(--moon-dim),var(--moon))}
.count{font-size:.8em;color:var(--gold);min-width:66px;text-align:right;font-variant-numeric:tabular-nums}
.count.mooncount{color:var(--moon)}
.hubnote{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:14px 18px;font-size:.85em;color:var(--muted);margin:8px 0 18px}
.hubnote b{color:var(--gold);font-weight:normal}
.hubnote h3{color:var(--gold);font-weight:normal;font-size:1em;letter-spacing:1px;margin-bottom:6px}
.hubnote .btns{margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
/* ---- checklist ---- */
.progress-panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:14px 18px;margin:18px auto;position:sticky;top:0;z-index:20;box-shadow:0 4px 18px rgba(0,0,0,.6)}
.progress-row{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.progress-row .label{font-size:.85em;color:var(--muted);min-width:120px}
.toolbar{display:flex;gap:8px;margin-top:11px;flex-wrap:wrap;align-items:center}
button,.btn{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:6px;
padding:6px 12px;cursor:pointer;font-family:inherit;font-size:.8em}
button:hover,.btn:hover{border-color:var(--gold-dim);color:var(--gold)}
button.danger:hover{border-color:var(--warn);color:var(--warn)}
#filterBox{flex:1;min-width:190px;background:#0a0c10;border:1px solid var(--line);border-radius:6px;
color:var(--text);padding:6px 10px;font-size:.82em;font-family:inherit}
#filterBox:focus{outline:none;border-color:var(--gold-dim)}
.chk{display:inline-flex;align-items:center;gap:6px;font-size:.78em;color:var(--muted);cursor:pointer;
padding:5px 9px;border:1px solid var(--line);border-radius:6px;user-select:none}
.chk:hover{border-color:var(--gold-dim);color:var(--gold)}
.chk input{accent-color:var(--gold);width:14px;height:14px}
#saveState{font-size:.75em;color:var(--ok);min-width:92px;font-style:italic}
#saveState.pending{color:var(--muted)}
#saveState.err{color:var(--warn)}
section.notes-sec{background:var(--warn-bg);border:1px solid #4a2a1e;border-radius:10px;margin:18px auto;overflow:hidden}
section.notes-sec .phase-head{background:#33201a}
section.notes-sec .phase-head:hover{background:#3d271f}
section.notes-sec .phase-head h2{color:var(--warn)}
section.notes-sec .phase-head .num{color:var(--warn)}
.rules{padding:4px 2px 2px}
.rules h3{color:var(--warn);font-size:.82em;letter-spacing:2px;text-transform:uppercase;
margin:14px 0 8px;font-weight:500}
.rules h3:first-child{margin-top:6px}
.rules ul{list-style:none}
.rules li{position:relative;padding:6px 0 6px 18px;font-size:.9em;line-height:1.5}
.rules li::before{content:"▸";position:absolute;left:0;color:var(--warn);opacity:.8}
.buildbox li::before{color:var(--ok)}
.buildbox li{color:var(--ok)}
.buildbox .bh{color:#a8e6b4;font-weight:700;letter-spacing:.4px}
.buildbox .bh::after{content:" — ";color:var(--muted);font-weight:400}
.cap{color:var(--item);font-weight:500}
.legend{margin-top:14px;padding-top:10px;border-top:1px solid #4a2a1e;font-size:.8em;color:#8a8878}
section.phase{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:16px auto;overflow:hidden}
.phase-head{display:flex;align-items:center;gap:12px;padding:14px 18px;cursor:pointer;background:var(--panel2);
user-select:none}
.phase-head:hover{background:#20253a}
.phase-head .num{color:var(--moon);font-size:.8em;letter-spacing:2px;white-space:nowrap}
.phase-head h2{font-size:1em;color:var(--gold);font-weight:500;flex:1}
.phase-head .mini{font-size:.8em;color:var(--muted);font-variant-numeric:tabular-nums}
.phase-head .chev{color:var(--muted);transition:transform .2s}
section.phase.open .chev{transform:rotate(90deg)}
.phase-body{display:none;padding:6px 18px 16px}
section.phase.open .phase-body{display:block}
.phase-note{font-size:.85em;color:var(--muted);font-style:italic;padding:8px 2px 10px;
border-bottom:1px dashed var(--line);margin-bottom:6px}
label.item{display:flex;gap:12px;padding:11px 8px;border-bottom:1px solid #1d2130;cursor:pointer;
align-items:flex-start;min-height:44px;border-radius:6px;scroll-margin-top:calc(var(--stick,0px) + 64px)}
label.item:last-child{border-bottom:none}
label.item:hover{background:#181c2a}
label.item input{margin-top:3px;accent-color:var(--gold);width:20px;height:20px;flex-shrink:0;cursor:pointer}
label.item .txt{flex:1;font-size:.92em}
label.item .txt .loc{display:block;font-size:.82em;color:var(--muted)}
label.item.checked .txt{color:#5a5848;text-decoration:line-through}
label.item.checked .txt .loc{text-decoration:line-through}
label.item.hit{outline:1px solid var(--gold-dim);background:#1d2032}
label.item.here{animation:pulse 1.4s ease-out 1;background:#20263c}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(200,162,74,.55)}100%{box-shadow:0 0 0 16px rgba(200,162,74,0)}}
body.hidedone label.item.checked{display:none}
label.item.filtered{display:none}
section.phase.filtered{display:none}
#noMatch{display:none;color:var(--muted);font-style:italic;text-align:center;padding:24px}
#noMatch.show{display:block}
.tag{display:inline-block;font-size:.68em;letter-spacing:1px;padding:1px 7px;border-radius:4px;
margin-left:6px;vertical-align:1px;text-decoration:none !important}
.tag.trophy{background:#2a2413;color:var(--gold);border:1px solid var(--gold-dim)}
.tag.coll{background:#221d10;color:#c8a24a;border:1px dashed var(--gold-dim)}
.tag.quest{background:#141d2a;color:var(--moon);border:1px solid var(--moon-dim)}
.tag.miss{background:var(--warn-bg);color:var(--warn);border:1px solid #4a2a1e}
.tag.build{background:#14241a;color:var(--ok);border:1px solid #2e5a3a}
table.stats{width:100%;border-collapse:collapse;font-size:.85em;margin:10px 0}
table.stats th{background:var(--panel2);color:var(--gold);padding:7px 6px;text-align:center;
border:1px solid var(--line);font-weight:normal;letter-spacing:1px}
table.stats td{padding:6px;text-align:center;border:1px solid #1d2130;color:var(--text);font-variant-numeric:tabular-nums}
table.stats td:first-child{color:var(--moon);font-weight:bold}
table.stats td:last-child{text-align:left;font-size:.92em;color:var(--muted)}
table.stats tr:hover td{background:#181c2a}
table.gloss{width:100%;border-collapse:collapse;font-size:.85em;margin:8px 0}
table.gloss td{padding:5px 8px;border-bottom:1px solid #1d2130}
table.gloss td:first-child{color:var(--muted);width:48%}
table.gloss td:last-child{color:var(--gold)}
textarea.notes{width:100%;min-height:130px;background:#0a0c10;border:1px solid var(--line);border-radius:8px;
color:var(--text);padding:10px;font-family:inherit;font-size:.9em;resize:vertical}
footer{text-align:center;color:var(--muted);font-size:.8em;padding:30px 16px;font-style:italic}
.plat{background:linear-gradient(135deg,#1a1e2c,#232a44);border:1px solid var(--moon-dim);border-radius:10px;
padding:20px;text-align:center;margin:18px auto;display:none}
.plat.show{display:block}
.plat h2{color:var(--moon);font-weight:normal;letter-spacing:2px}

/* ---- mode + tabs ---- */
.modesel{display:inline-flex;align-items:center;gap:6px;font-size:.8em;letter-spacing:1px;
background:var(--panel);border:1px solid var(--gold-dim);border-radius:8px;padding:5px 8px 5px 11px}
.modesel .lbl{color:var(--muted);font-size:.86em}
.modesel a{padding:4px 11px;border:1px solid var(--line);border-radius:5px;color:var(--muted);font-weight:bold}
.modesel a:hover{border-color:var(--gold);color:var(--gold)}
.modesel a.on{background:var(--gold-dim);border-color:var(--gold);color:#12141c}
.topright{position:absolute;top:14px;right:16px;z-index:30;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
@media(max-width:820px){.topright{position:static;justify-content:center;margin-bottom:10px}}
/* pannello delle scorciatoie: si apre da un pulsante o col tasto ? */
.hkbtn{font-size:.8em;letter-spacing:1px;padding:5px 11px;background:var(--panel);
border:1px solid var(--gold-dim);border-radius:8px;color:var(--muted);cursor:pointer}
.hkbtn:hover{border-color:var(--gold);color:var(--gold)}
.hkmodal{position:fixed;inset:0;z-index:200;display:none;align-items:center;justify-content:center;
background:rgba(6,8,12,.72);padding:20px}
.hkmodal.open{display:flex}
.hkbox{background:var(--panel);border:1px solid var(--gold-dim);border-radius:12px;
max-width:680px;width:100%;max-height:86vh;overflow:auto;padding:22px 24px}
.hkbox h2{margin:0 0 10px;font-size:1.05em;color:var(--gold);letter-spacing:2px;text-transform:uppercase;
font-weight:500}
.hkbox .intro{color:var(--muted);font-size:.9em;line-height:1.6;margin-bottom:16px}
.hkrow{display:flex;gap:14px;align-items:baseline;padding:9px 0;border-top:1px solid var(--line);
flex-wrap:wrap}
.hkrow .what{flex:1;min-width:220px}
kbd,.hkkey{font-family:inherit;font-size:.82em;letter-spacing:1px;background:var(--panel2);
border:1px solid var(--line);border-bottom-width:2px;border-radius:5px;padding:3px 8px;color:var(--text);
white-space:nowrap}
.hkfoot{margin-top:18px;padding-top:14px;border-top:1px solid var(--line);display:flex;gap:12px;
align-items:center;flex-wrap:wrap;font-size:.88em;color:var(--muted)}
.hkwarn{color:var(--warn);font-size:.88em;line-height:1.6;margin-top:12px;background:var(--warn-bg);
border:1px solid var(--warn);border-radius:8px;padding:10px 13px}
.tabs{display:flex;gap:8px;margin:16px 0 0}
.tabs a{background:var(--panel2);border:1px solid var(--line);color:var(--muted);
border-radius:7px 7px 0 0;padding:7px 15px;font-size:.85em}
.tabs a.on{background:var(--panel);color:var(--gold);border-color:var(--gold-dim);border-bottom-color:var(--panel)}
.tabs a:hover{color:var(--gold)}
/* ---- session bar ---- */
.sessionbar{background:linear-gradient(180deg,#1b1420,#151823);border:1px solid #4a2a3a;
border-radius:10px;padding:12px 16px;margin:14px auto}
.sessionbar .row1{display:flex;align-items:center;gap:13px;flex-wrap:wrap}
.recdot{width:9px;height:9px;border-radius:50%;background:var(--rec);display:inline-block;
box-shadow:0 0 0 0 rgba(224,82,82,.6);animation:recpulse 1.8s infinite}
@keyframes recpulse{70%{box-shadow:0 0 0 9px rgba(224,82,82,0)}100%{box-shadow:0 0 0 0 rgba(224,82,82,0)}}
.recdot.off{background:#555;animation:none}
.reclab{color:var(--rec);font-weight:700;letter-spacing:1px;font-size:.85em}
.reclab.off{color:var(--muted)}
.tc{font-variant-numeric:tabular-nums;font-size:1.12em;letter-spacing:1px}
.chip{font-size:.76em;border-radius:5px;padding:2px 9px;letter-spacing:1px}
.chip.ok{color:var(--ok);border:1px solid #2e5a3a;background:#14241a}
.chip.bad{color:var(--warn);border:1px solid #4a2a1e;background:var(--warn-bg)}
.chip.ep{color:var(--moon);border:1px solid var(--moon-dim);background:#141d2a}
.sessionbar .spacer{flex:1}
.doing{margin-top:10px;padding-top:9px;border-top:1px solid #33203a;font-size:.86em;
display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.doing .lab{color:var(--muted);letter-spacing:1px;font-size:.9em}
.doing .task{color:var(--gold)}
.doing .since{color:var(--muted);font-variant-numeric:tabular-nums}
/* ---- avviso di aggiornamento ---- */
.updbox{border:1px solid var(--gold-dim);background:linear-gradient(90deg,#1a1608,#12141c);
border-radius:9px;padding:14px 18px;margin:0 0 18px}
.updbox .uh{color:var(--gold);letter-spacing:1px;font-size:.95em;margin-bottom:5px}
.updbox .ub{color:var(--muted);font-size:.88em;line-height:1.55}
.updbox .ur{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-top:11px}
.updbox .updbtn{background:var(--gold);color:#14100a;border-radius:6px;padding:7px 15px;
text-decoration:none;font-size:.9em;letter-spacing:.5px}
.updbox .updlnk{color:var(--muted);font-size:.85em;text-decoration:none;border-bottom:1px dotted var(--line)}
.chlog{max-width:820px;margin:0 auto;line-height:1.65}
.chlog h2{color:var(--gold);font-size:1.05em;margin:26px 0 6px;letter-spacing:.5px}
.chlog h3{color:var(--moon);font-size:.9em;margin:16px 0 4px;letter-spacing:1px;text-transform:uppercase}
.chlog li{margin:4px 0}
.chlog code{background:var(--panel2);padding:1px 6px;border-radius:4px;font-size:.9em}
/* ---- coda dei link video mancanti ---- */
.linkq{margin-top:10px;padding-top:10px;border-top:1px solid #33203a}
.linkq .lqh{color:var(--warn);font-size:.86em;letter-spacing:.5px;margin-bottom:8px}
.linkq .lqrow{display:flex;align-items:center;gap:9px;flex-wrap:wrap;padding:5px 0}
.linkq .lqep{color:var(--moon);font-size:.8em;letter-spacing:1px;min-width:56px}
.linkq .lqmeta{color:var(--muted);font-size:.8em;min-width:150px}
.linkq .lqin{flex:1;min-width:210px;background:#0a0c10;border:1px solid var(--line);
border-radius:6px;color:var(--text);padding:5px 9px;font-size:.9em;font-family:inherit}
.linkq .lqst{font-size:.9em;min-width:14px}
/* ---- step stamps ---- */
.stamp{display:inline-block;font-size:.72em;letter-spacing:.5px;padding:2px 8px;border-radius:5px;
margin-left:8px;white-space:nowrap;vertical-align:1px;background:#161d2c;border:1px solid var(--moon-dim);
color:var(--moon);text-decoration:none !important}
.stamp:hover{background:#1d2740;border-color:var(--moon);color:#a8c8e8}
.stamp .ep{color:var(--gold);font-weight:700}
.stamp.two{border-style:dashed}
.stamp.live{border-color:var(--rec);color:var(--rec);background:#241416}
label.item.checked .stamp{text-decoration:none;color:var(--moon)}
label.item.current{background:#1c2436;outline:1px solid var(--moon-dim)}
.doingtag{display:inline-block;font-size:.7em;letter-spacing:1px;color:var(--rec);
border:1px solid var(--rec);border-radius:5px;padding:1px 7px;margin-left:8px;vertical-align:1px}
/* ---- episodes ---- */
.epcard{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:14px 0;overflow:hidden}
.epcard .h{display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--panel2);flex-wrap:wrap}
.epcard .h h3{font-size:1em;color:var(--gold);font-weight:500;letter-spacing:1px}
.epcard .h .meta{font-size:.8em;color:var(--muted)}
.epcard .h .spacer{flex:1}
.epcard .b{padding:6px 16px 14px}
.tl{display:grid;grid-template-columns:84px 1fr;gap:1px 14px;font-size:.88em;margin:6px 0}
.tl .t{color:var(--moon);font-variant-numeric:tabular-nums;padding:5px 0;text-align:right}
.tl .t a{color:var(--moon)} .tl .t a:hover{color:var(--gold)}
.tl .d{padding:5px 0;border-bottom:1px solid #1a1e2b}
.tl .d.tro{color:var(--gold)}
.setrow{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:10px;font-size:.84em;color:var(--muted)}
.setrow input[type=text],.setrow input[type=password]{background:#0a0c10;border:1px solid var(--line);
border-radius:6px;color:var(--text);padding:6px 10px;font-family:inherit;font-size:.95em;min-width:210px}
.setrow input[type=number]{background:#0a0c10;border:1px solid var(--line);border-radius:6px;
color:var(--text);padding:6px 8px;font-family:inherit;width:78px;font-size:.95em}
textarea.mono{width:100%;min-height:110px;background:#0a0c10;border:1px solid var(--line);border-radius:8px;
color:var(--text);padding:10px;font-family:ui-monospace,Consolas,monospace;font-size:.82em;
resize:vertical;margin-top:10px;line-height:1.7}
@media print{header,.progress-panel,.toolbar,.langsel,.back,footer,.hubnote,.sessionbar,.tabs,.topright{display:none}
section.phase .phase-body{display:block !important}body{background:#fff;color:#000}}
"""


# words that are capitalised for emphasis, not because they name a thing
_STOP = {
    "NON", "MAI", "NIENTE", "SOLO", "TUTTI", "TUTTO", "TUTTE", "PRIMA", "DOPO", "SEMPRE", "OGNI",
    "QUI", "ORA", "POI", "SE", "MA", "E", "O", "UNA", "UNO", "DUE", "TRE", "QUATTRO", "VOLTA",
    "VOLTE", "SUBITO", "ANCHE", "ADESSO", "QUANDO", "PERCHE", "PERCHÉ", "COSA", "FASE",
    "NOT", "NEVER", "ONLY", "ALL", "EVERY", "ALWAYS", "FIRST", "THEN", "BEFORE", "AFTER", "NOW",
    "ONE", "TWO", "THREE", "FOUR", "ONCE", "TWICE", "MUST", "DO", "DON'T", "AND", "OR", "IF",
    "THIS", "THAT", "HERE", "YES", "NO", "PHASE", "STEP", "OK",
    "CIASCUNA", "CIASCUNO", "ENTRAMBI", "ENTRAMBE", "SOLTANTO", "QUALSIASI", "QUALUNQUE",
    "NESSUNO", "NESSUNA", "MENO", "PIU", "PIÙ", "MOLTO", "TROPPO", "ASSOLUTAMENTE",
    "EACH", "BOTH", "ANY", "ANYTHING", "NOTHING", "MORE", "LESS", "VERY", "ABSOLUTELY", "JUST",
}
_CAPS = re.compile(r"(?<![\w'’])([A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9'’+\-]{1,}(?:[  ][A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9'’+\-]{1,})*)(?![\w'’])")


def esc(s):
    return html.escape(str(s), quote=False)


def hl(s):
    """Escape, then paint ALL-CAPS in-game nouns in the item colour."""
    out = html.escape(str(s), quote=False)

    def repl(m):
        tok = m.group(1)
        if all(w in _STOP for w in tok.split()):
            return tok
        if len(tok.replace(" ", "")) < 2:
            return tok
        return '<span class="cap">%s</span>' % tok

    return _CAPS.sub(repl, out)


def short(s, n):
    s = str(s).strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    if "(" in cut and ")" not in cut[cut.index("("):]:
        trimmed = cut[:cut.index("(")].rstrip()
        if len(trimmed) >= 12:
            cut = trimmed
    cut = cut.rsplit(" ", 1)[0].rstrip(" ,;:-—·(")
    return cut + "…"


def langsel(lg, path, top=False):
    q = urllib.parse.quote(path, safe="/")
    a = lambda code, txt: (f'<a class="{"on" if lg == code else ""}" href="/lang/{code}?next={q}">{txt}</a>')
    cls = "langsel langsel-top" if top else "langsel"
    return (f'<div class="{cls}"><span class="lbl">🌐 {T[lg]["lang_label"]}</span>'
            f'{a("it", "ITA")}{a("en", "ENG")}</div>')


# ------------------------------------------------------------------- home page
def md_lite(text):
    """Markdown minimo per il changelog: titoli, elenchi, grassetto, codice.

    Non serve una libreria: il file lo scrivo io e conosco la forma che ha."""
    out, in_ul = [], False
    for raw in str(text).splitlines():
        line = html.escape(raw.rstrip(), quote=False)
        line = re.sub(r"`([^`]+)`", r"<code>\1</code>", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line)
        line = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
                      r'<a href="\2" target="_blank" rel="noopener">\1</a>', line)
        stripped = line.strip()
        is_li = stripped.startswith(("- ", "* "))
        if is_li and not in_ul:
            out.append("<ul>")
            in_ul = True
        elif not is_li and in_ul:
            out.append("</ul>")
            in_ul = False
        if is_li:
            out.append("<li>%s</li>" % stripped[2:])
        elif stripped.startswith("### "):
            out.append("<h3>%s</h3>" % stripped[4:])
        elif stripped.startswith("## "):
            out.append("<h2>%s</h2>" % stripped[3:])
        elif stripped.startswith("# "):
            continue                       # il titolo del file lo mettiamo noi
        elif stripped.startswith("---"):
            out.append('<hr style="border:0;border-top:1px solid var(--line);margin:18px 0">')
        elif stripped:
            out.append("<p>%s</p>" % stripped)
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


def mode():
    m = get_pref("mode", "gamer")
    return m if m in ("gamer", "streamer") else "gamer"


def modesel(lg, path):
    q = urllib.parse.quote(path, safe="/")
    t = T[lg]
    m = mode()
    a = lambda code, txt: f'<a class="{"on" if m == code else ""}" href="/mode/{code}?next={q}">{txt}</a>'
    return (f'<div class="modesel"><span class="lbl">🎮 {t["mode"]}</span>'
            f'{a("gamer", t["gamer"])}{a("streamer", t["streamer"])}</div>')


def tabs(lg, run_id, active):
    t = T[lg]
    if mode() != "streamer":
        return ""
    def a(key, href, label):
        return f'<a class="{"on" if active == key else ""}" href="{href}">{label}</a>'
    return ('<div class="tabs">'
            + a("check", f"/run/{run_id}", "📋 " + t["tab_check"])
            + a("eps", f"/episodes/{run_id}", "🎬 " + t["tab_eps"])
            + a("ses", f"/session/{run_id}", "⚙️ " + t["tab_ses"])
            + a("thumb", f"/thumb/{run_id}", "🖼 " + t["tab_thumb"])
            + "</div>")


def stamp_html(st, lg):
    """The EP · mm:ss ▶ badge for one step."""
    done, start = st.get("done"), st.get("start")
    t = T[lg]
    if done and done["url"]:
        main = f'<span class="ep">{t["ep"]} {done["ep"]}</span> · {fmt_tc(done["t"])} ▶'
        cls = "stamp"
        extra = ""
        if start and start["ep"] != done["ep"]:
            cls += " two"
            if start["url"]:
                extra = (f' · <a class="stamp" style="border:none;padding:0;margin:0;background:none" '
                         f'href="{video_link(start["url"], start["t"])}" target="_blank">'
                         f'{t["ep"]} {start["ep"]} · {fmt_tc(start["t"])}</a>')
            else:
                extra = f' · {t["ep"]} {start["ep"]}'
        return (f'<a class="{cls}" href="{video_link(done["url"], done["t"])}" target="_blank">'
                f'{main}{extra}</a>')
    if done:
        return (f'<span class="stamp" title="{t["no_video"]}">'
                f'<span class="ep">{t["ep"]} {done["ep"]}</span> · {fmt_tc(done["tc"])}</span>')
    if start:
        return (f'<span class="stamp live"><span class="ep">{t["ep"]} {start["ep"]}</span> · '
                f'{fmt_tc(start["tc"])}</span>')
    return ""


# ============================================================ scorciatoie da
# tastiera globali (Windows) + coda comandi
#
# Il browser non riceve tasti quando il gioco ha il fuoco: le scorciatoie le
# registra il processo Python con RegisterHotKey (user32, via ctypes: nessuna
# dipendenza in piu'). Il thread non esegue nulla di suo, si limita a mettere
# un comando in coda; a eseguirlo e' la pagina gia' aperta, che e' l'unica ad
# avere il WebSocket di OBS e lo stato della checklist. Cosi' i tasti passano
# esattamente per lo stesso codice dei pulsanti, e non esiste una seconda
# implementazione da tenere allineata.

# ==================================================== controllo aggiornamenti
# Una sola chiamata all'avvio, in un thread, con timeout corto. Se non c'e'
# rete non succede niente: l'app non deve MAI dipendere da GitHub per partire.
# Nessun download automatico e nessuna installazione silenziosa: si avvisa e
# basta, il file lo scarica l'utente. Su un'app non firmata, un aggiornamento
# che si installa da solo e' esattamente quello che fa un malware.


# ------------------------------------------------------------- episodes page
def hk_button(lg):
    """Il pulsante che apre il pannello delle scorciatoie."""
    t = T[lg]
    return ('<button class="hkbtn" onclick="hkOpen()" title="%s  (?)">⌨ %s</button>'
            % (esc(t["hk_panel_title"]), esc(t["hk_btn"])))


# Le combinazioni arrivano dalle preferenze, cioe' sono testo scritto dall'utente:
# passano tutte da hkEsc() prima di finire in innerHTML.
HK_PANEL_JS = """
function hkEsc(s){ var d=document.createElement('div'); d.textContent=(s==null?'':s); return d.innerHTML; }
function hkPretty(s){
  return String(s).split('+').map(function(x){
    x = x.trim();
    return x.length > 1 ? x.charAt(0).toUpperCase() + x.slice(1) : x.toUpperCase();
  }).join(' + ');
}
function hkRow(key, action, state, cls){
  return '<div class="hkrow"><span class="hkkey">' + hkEsc(hkPretty(key)) + '</span>' +
         '<span class="what">' + hkEsc(HK_DESC[action] || action) + '</span>' +
         '<span class="chip ' + cls + '">' + hkEsc(state) + '</span></div>';
}
function hkClose(){ var m = document.getElementById('hkModal'); if(m) m.classList.remove('open'); }
function hkOpen(){
  var m = document.getElementById('hkModal'); if(!m) return;
  m.classList.add('open');
  var box = document.getElementById('hkRows');
  fetch('/api/hotkeys').then(function(r){ return r.json(); }).then(function(d){
    var act = {}, fail = {};
    (d.active || []).forEach(function(p){ act[p[0]] = 1; });
    (d.failed || []).forEach(function(p){ fail[p[0]] = 1; });
    var rows = (d.configured || []).map(function(p){
      if(act[p[0]])  return hkRow(p[0], p[1], HK_TXT.ok, 'ok');
      if(fail[p[0]]) return hkRow(p[0], p[1], HK_TXT.taken, 'bad');
      return hkRow(p[0], p[1], d.why || HK_TXT.off, '');
    });
    box.innerHTML = rows.length ? rows.join('')
      : '<div class="hkrow"><span class="what">' + HK_TXT.offnote + ' ' + HK_TXT.where + '</span></div>';
    document.getElementById('hkWarn').innerHTML =
      (d.failed && d.failed.length) ? '<div class="hkwarn">' + HK_TXT.thieves + '</div>' : '';
  }).catch(function(){ box.textContent = '\\u2014'; });
}
document.addEventListener('keydown', function(e){
  var tag = ((e.target && e.target.tagName) || '').toLowerCase();
  if(tag === 'input' || tag === 'textarea' || tag === 'select') return;
  if(e.key === '?'){ e.preventDefault(); hkOpen(); }
  else if(e.key === 'Escape'){ hkClose(); }
});
"""


def hk_panel(lg, run_id=None):
    """Il pannello delle scorciatoie, identico su ogni pagina.

    Non e' documentazione incollata: legge /api/hotkeys e dice quali
    combinazioni Windows ha davvero registrato e quali gli ha rubato un altro
    programma. Quel dato non sta in nessun file di testo, e in un file di testo
    non potrebbe starci."""
    t = T[lg]
    where = ('<a href="/session/%s">%s</a>' % (esc(str(run_id)), esc(t["hk_settings"]))
             if run_id else esc(t["hk_settings"]))
    txt = {"ok": t["hk_ok"], "taken": t["hk_taken"], "off": t["hk_state_off"],
           "thieves": t["hk_thieves"], "offnote": t["hk_off_note"], "where": where}
    desc = {a: t["hk_act_" + a] for a in HOTKEY_ACTIONS}
    return ('<div class="hkmodal" id="hkModal" onclick="if(event.target===this)hkClose()">'
            '<div class="hkbox" role="dialog" aria-modal="true" aria-label="%s">'
            '<h2>⌨ %s</h2><div class="intro">%s</div>'
            '<div id="hkRows">%s</div><div id="hkWarn"></div>'
            '<div class="hkfoot"><button onclick="hkClose()">%s</button><span>%s</span></div>'
            '</div></div><script>var HK_DESC=%s;var HK_TXT=%s;%s</script>'
            % (esc(t["hk_panel_title"]), esc(t["hk_panel_title"]), t["hk_panel_intro"],
               esc(t["hk_loading"]), esc(t["hk_close"]), esc(t["hk_restart"]),
               json.dumps(desc, ensure_ascii=False), json.dumps(txt, ensure_ascii=False),
               HK_PANEL_JS))


def page_head(lg, title, run_id, active, subtitle=""):
    t = T[lg]
    return ('<!DOCTYPE html><html lang="%s"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            '<title>%s</title><style>%s</style></head><body>%s'
            '<header><div class="topright">%s%s%s</div><h1>%s</h1>'
            '<p class="sub">%s · <span class="by">%s</span></p></header>'
            '<div class="wrap"><a class="back" href="/">← %s</a>%s'
            % (lg, esc(title), CSS, hk_panel(lg, run_id),
               hk_button(lg),
               modesel(lg, "/%s/%s" % (active_path(active), run_id)),
               langsel(lg, "/%s/%s" % (active_path(active), run_id)),
               esc(title), esc(subtitle), t["by"], t["back"],
               tabs(lg, run_id, active)))


def active_path(active):
    return {"check": "run", "eps": "episodes", "ses": "session", "thumb": "thumb"}[active]


def render_404():
    lg = lang()
    return ('<!DOCTYPE html><html><head><meta charset="UTF-8"><title>404</title><style>' + CSS +
            f'</style></head><body><header><h1>404</h1><p class="sub">{T[lg]["notfound"]}</p></header>'
            f'<div class="wrap"><a class="back" href="/">← {T[lg]["back"]}</a></div></body></html>')
