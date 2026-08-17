# -*- coding: utf-8 -*-
"""La pagina della checklist: rendering e JavaScript (salvataggio per sid)."""

import json

from .i18n import T, L
from .page_streamer import OBS_JS
from .routes import ROUTES
from .store import get_note, get_pref, lang, step_stamps
from .ui import (CSS, esc, hl, hk_button, hk_panel, langsel, mode, modesel,
                 stamp_html, tabs)


# -------------------------------------------------------------- checklist page
CHECKLIST_JS = r"""
var RUN = __RUN__, S = __STR__;
var items = Array.prototype.slice.call(document.querySelectorAll('label.item input'));
var stateEl = document.getElementById('saveState');
var saveTimer = null, firstLoad = true;

/* Ogni casella porta il sid del suo passo: e' la chiave con cui il progresso
   vive nel database. La posizione serve solo dentro questa pagina. */
function sidOf(i){ return items[i] ? (items[i].getAttribute('data-sid') || null) : null; }
function doneSids(){
  return items.filter(function(cb){ return cb.checked; })
              .map(function(cb){ return cb.getAttribute('data-sid'); })
              .filter(function(s){ return !!s; });
}
function flag(txt, cls){ stateEl.textContent = txt; stateEl.className = cls || ''; }

function refresh(){
  var all = items.length, done = 0, tAll = 0, tDone = 0;
  items.forEach(function(cb){
    var lab = cb.closest('label');
    var isT = lab.getAttribute('data-t') === '1';
    if(isT) tAll++;
    if(cb.checked){ done++; if(isT) tDone++; lab.classList.add('checked'); }
    else lab.classList.remove('checked');
  });
  document.getElementById('barAll').style.width = (all? done/all*100:0)+'%';
  document.getElementById('cntAll').textContent = done+' / '+all;
  document.getElementById('barTrophy').style.width = (tAll? tDone/tAll*100:0)+'%';
  document.getElementById('cntTrophy').textContent = tDone+' / '+tAll;
  document.querySelectorAll('section.phase').forEach(function(sec){
    var cbs = sec.querySelectorAll('input[type=checkbox]'), d = 0;
    cbs.forEach(function(c){ if(c.checked) d++; });
    if(cbs.length) sec.querySelector('.mini').textContent = d+'/'+cbs.length;
  });
  document.getElementById('platBox').classList.toggle('show', all>0 && done === all);
}
function push(){
  flag(S.saving, 'pending');
  fetch('/api/progress', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({run: RUN, done: doneSids()})})
    .then(function(r){ if(!r.ok) throw 0; flag(S.saved); })
    .catch(function(){ flag(S.save_failed, 'err'); });
}
function scheduleSave(){ if(saveTimer) clearTimeout(saveTimer); flag(S.saving,'pending'); saveTimer = setTimeout(push, 350); }
items.forEach(function(cb, idx){ cb.addEventListener('change', function(){
  refresh(); applyView(); scheduleSave();
  if(typeof onTickMarker === 'function') onTickMarker(idx, cb.checked);
}); });

/* the only sticky element is the progress panel: keep scroll targets clear of it */
function measureStick(){
  var panel = document.querySelector('.progress-panel');
  if(panel) document.documentElement.style.setProperty('--stick', panel.offsetHeight + 'px');
}
window.addEventListener('resize', measureStick);
measureStick();

function toggle(head){ head.parentElement.classList.toggle('open'); }
function expandAll(){ document.querySelectorAll('section.phase').forEach(function(s){ s.classList.add('open'); }); }
function collapseAll(){ document.querySelectorAll('section.phase').forEach(function(s){ s.classList.remove('open'); }); }

function resetRun(){
  if(!confirm(S.confirm_reset)) return;
  fetch('/api/run/reset', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({run: RUN})})
    .then(function(r){ if(!r.ok) throw 0; return r.json(); })
    .then(function(){ location.reload(); })
    .catch(function(){ flag(S.save_failed, 'err'); });
}

/* ---- view: filter + hide done + only missable ---- */
function applyView(){
  var q = document.getElementById('filterBox').value.trim().toLowerCase();
  var onlyMiss = document.getElementById('missOnly').checked;
  document.body.classList.toggle('hidedone', document.getElementById('hideDone').checked);
  var anyVisible = false;
  document.querySelectorAll('section.phase').forEach(function(sec){
    var shown = 0;
    sec.querySelectorAll('label.item').forEach(function(lab){
      var hideMiss = onlyMiss && lab.getAttribute('data-miss') !== '1';
      var hideQ = q && lab.textContent.toLowerCase().indexOf(q) < 0;
      lab.classList.toggle('filtered', hideMiss || hideQ);
      lab.classList.toggle('hit', !!q && !hideMiss && !hideQ);
      var visible = !(hideMiss || hideQ) &&
        !(document.body.classList.contains('hidedone') && lab.classList.contains('checked'));
      if(visible) shown++;
    });
    var empty = (q || onlyMiss) && shown === 0;
    sec.classList.toggle('filtered', empty);
    if(!empty) anyVisible = true;
    if((q || onlyMiss) && shown > 0) sec.classList.add('open');
  });
  document.getElementById('noMatch').classList.toggle('show', !anyVisible);
  if(!firstLoad) savePrefs();
}
function savePrefs(){
  fetch('/api/pref', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({hide_done: document.getElementById('hideDone').checked ? '1':'0',
                          only_miss: document.getElementById('missOnly').checked ? '1':'0'})}).catch(function(){});
}
document.getElementById('filterBox').addEventListener('input', applyView);
document.getElementById('hideDone').addEventListener('change', applyView);
document.getElementById('missOnly').addEventListener('change', applyView);
document.addEventListener('keydown', function(e){
  if(e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA'){
    e.preventDefault(); document.getElementById('filterBox').focus();
  }
});

/* ---- where I left off ---- */
function resume(){
  var next = items.find(function(cb){ return !cb.checked; });
  if(!next) return;
  var lab = next.closest('label');
  var sec = lab.closest('section.phase');
  if(sec) sec.classList.add('open');
  lab.classList.remove('filtered');
  lab.scrollIntoView({block:'center', behavior:'smooth'});
  lab.classList.remove('here'); void lab.offsetWidth; lab.classList.add('here');
}

/* ---- notes ---- */
var noteTimer = null, noteEl = document.getElementById('notesBox');
if(noteEl){
  noteEl.addEventListener('input', function(){
    if(noteTimer) clearTimeout(noteTimer);
    flag(S.saving, 'pending');
    noteTimer = setTimeout(function(){
      fetch('/api/notes', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({run: RUN, body: noteEl.value})})
        .then(function(r){ if(!r.ok) throw 0; flag(S.saved); })
        .catch(function(){ flag(S.save_failed, 'err'); });
    }, 600);
  });
}

/* ---- boot ---- */
fetch('/api/progress?run=' + RUN).then(function(r){ return r.json(); }).then(function(j){
  var done = {};
  (j.done || []).forEach(function(s){ done[s] = true; });
  items.forEach(function(cb){ cb.checked = !!done[cb.getAttribute('data-sid')]; });
  refresh(); applyView(); firstLoad = false;
  flag(j.updated_at ? S.loaded + ' (' + j.updated_at + ')' : S.new_run);
  if((j.done || []).length) setTimeout(resume, 250);
}).catch(function(){ refresh(); applyView(); firstLoad = false; flag(S.offline, 'err'); });

/* ============================ sessioni e marker ============================ */
var CFG = __CFG__;
var SES = null;              /* sessione aperta */
var CUR = null;              /* indice del passo in corso */
var startedAt = null;        /* tc di inizio del passo in corso */

function nowTc(){
  var o = (typeof obsTime === 'function') ? obsTime() : null;
  if(o) return {tc: o.tc, kind: o.kind};
  if(SES && SES._t0) return {tc: (Date.now() - SES._t0)/1000, kind: 'clock'};
  return {tc: 0, kind: 'none'};
}
function fmtTc(sec){
  sec = Math.max(0, Math.round(sec));
  var h = Math.floor(sec/3600), m = Math.floor(sec%3600/60), x = sec%60;
  return (h ? h + ':' + String(m).padStart(2,'0') : String(m).padStart(2,'0')) + ':' + String(x).padStart(2,'0');
}
function firstUnchecked(from){
  for(var i = (from||0); i < items.length; i++){ if(!items[i].checked) return i; }
  return null;
}
function paintCurrent(){
  document.querySelectorAll('label.item.current').forEach(function(e){ e.classList.remove('current'); });
  if(CUR === null || CUR === undefined) return;
  var cb = document.getElementById('s' + (CUR+1));
  if(cb) cb.closest('label').classList.add('current');
}
function setCurrent(i, alsoMark){
  CUR = i;
  paintCurrent();
  fetch('/api/current', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({run: RUN, sid: (i === null ? null : sidOf(i))})}).catch(function(){});
  if(alsoMark && SES && i !== null){
    var n = nowTc();
    startedAt = n.tc;
    postMarker(sidOf(i), 'start', n.tc);
  }
}
function postMarker(sid, kind, tc, note){
  if(!SES) return;
  fetch('/api/marker', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({run: RUN, session: SES.id, sid: sid, kind: kind, tc: tc, note: note||''})})
    .catch(function(){});
}
function startSession(){
  var o = (typeof obsTime === 'function') ? obsTime() : null;
  fetch('/api/session/start', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({run: RUN, source: (o ? 'obs' : 'clock')})})
    .then(function(r){ return r.json(); })
    .then(function(j){ SES = j.session; SES._t0 = Date.now(); paintBar();
                       setCurrent(firstUnchecked(0), true); });
}
function stopSession(){
  if(!SES) return;
  var id = SES.id;
  fetch('/api/session/stop', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({id: id})})
    .then(function(){ SES = null; paintBar(); paintLinkQueue(); })
    .catch(function(){ SES = null; paintBar(); });
}
function markFree(){
  if(!SES) return;
  var note = prompt('📍', '');
  if(note === null) return;
  postMarker(null, 'free', nowTc().tc, note);
}
function ytNormalize(u){
  u = (u || '').trim();
  if(!u) return '';
  var m = u.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?(?:.*&)?v=|live\/|embed\/|shorts\/))([A-Za-z0-9_-]{6,})/);
  if(m) return 'https://youtu.be/' + m[1];
  if(/^[A-Za-z0-9_-]{11}$/.test(u)) return 'https://youtu.be/' + u;
  if(!/^https?:\/\//i.test(u)) return 'https://' + u;
  return u;
}
function saveUrl(){
  if(!SES) return;
  var el = document.getElementById('epUrlBar'), st = document.getElementById('urlState');
  var clean = ytNormalize(el.value);
  el.value = clean;
  fetch('/api/session/update', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({id: SES.id, video_url: clean})})
    .then(function(r){ return r.json(); })
    .then(function(j){ SES = j.session; st.style.color = 'var(--ok)';
      st.textContent = clean ? '✓' : '';
      setTimeout(function(){ st.textContent = ''; }, 2500); })
    .catch(function(){ st.style.color = 'var(--warn)'; st.textContent = '✕'; });
}
function paintBar(){
  var bar = document.getElementById('recDot');
  if(!bar) return;
  var o = (typeof obsTime === 'function') ? obsTime() : null;
  var chip = document.getElementById('obsChip');
  if(OBS.ok){ chip.className = 'chip ok'; chip.title = '';
    chip.textContent = '● ' + S.obs_on +
      (o ? ' · ' + (o.kind === 'stream' ? ('live' + (OBS.svc ? ' ' + OBS.svc : '')) : 'rec')
         : ' · nessun output attivo'); }
  else { chip.className = 'chip bad';
    chip.textContent = S.obs_off + (OBS.err ? ' · ' + OBS.err : '') + (SES ? ' · ' + S.clock_mode : '');
    chip.title = 'OBS: Strumenti > Impostazioni server WebSocket > abilita il server, poi incolla la password nella scheda Sessione.'; }
  var dot = document.getElementById('recDot'), lab = document.getElementById('recLab');
  var ep = document.getElementById('epChip');
  document.getElementById('btnStart').style.display = SES ? 'none' : '';
  document.getElementById('btnStop').style.display  = SES ? '' : 'none';
  document.getElementById('btnMark').style.display  = SES ? '' : 'none';
  if(SES){
    dot.className = 'recdot'; lab.className = 'reclab'; lab.textContent = S.rec;
    ep.style.display = ''; ep.textContent = S.ep.toUpperCase() + ' ' + SES.number;
    var ur = document.getElementById('urlRow');
    if(ur){ ur.style.display = '';
      var eu = document.getElementById('epUrlBar');
      if(document.activeElement !== eu && eu.value !== (SES.video_url || '')) eu.value = SES.video_url || ''; }
    document.getElementById('tcNow').textContent = fmtTc(nowTc().tc);
    var row = document.getElementById('doingRow');
    if(CUR !== null && CUR !== undefined && items[CUR]){
      row.style.display = '';
      var lb = items[CUR].closest('label').querySelector('.txt').firstChild;
      document.getElementById('doingTask').textContent =
        (items[CUR].closest('label').innerText || '').split('\n')[0].slice(0, 90);
      document.getElementById('doingSince').textContent =
        (startedAt !== null ? '— ' + S.started_at + ' ' + fmtTc(startedAt) : '');
    } else { row.style.display = 'none'; }
  } else {
    dot.className = 'recdot off'; lab.className = 'reclab off'; lab.textContent = S.idle;
    ep.style.display = 'none';
    var ur0 = document.getElementById('urlRow'); if(ur0) ur0.style.display = 'none';
    document.getElementById('tcNow').textContent = '--:--';
    document.getElementById('doingRow').style.display = 'none';
  }
}
function onTickMarker(idx, checked){
  if(!SES) return;
  var n = nowTc();
  if(checked){
    postMarker(sidOf(idx), 'done', n.tc);
    var nx = firstUnchecked(0);
    setCurrent(nx, true);
  } else {
    fetch('/api/marker/delete', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({session: SES.id, sid: sidOf(idx)})}).catch(function(){});
    setCurrent(firstUnchecked(0), false);
  }
}
/* boot della parte streamer */
if(CFG.mode === 'streamer'){
  OBS.prefer = CFG.obs_prefer || 'auto';
  obsConnect(CFG.obs_url, CFG.obs_pass, function(){ paintBar(); });
  setInterval(paintBar, 1000);
  /* riprova da sola ogni 15 s rileggendo le preferenze: cambi la password
     nella scheda Sessione e si riattacca senza ricaricare la pagina */
  setInterval(function(){
    if(OBS.ok) return;
    fetch('/api/prefs').then(function(r){ return r.json(); }).then(function(p){
      OBS.prefer = p.obs_prefer || 'auto';
      obsConnect(p.obs_url, p.obs_pass, function(){ paintBar(); });
    }).catch(function(){});
  }, 15000);
  fetch('/api/current?run=' + RUN).then(function(r){ return r.json(); }).then(function(j){
    if(j.session){ SES = j.session; SES._t0 = Date.now(); }
    CUR = j.current ? j.current.i : null;
    paintCurrent(); paintBar();
  }).catch(function(){});
  document.querySelectorAll('label.item').forEach(function(lab, i){
    lab.addEventListener('dblclick', function(ev){
      if(ev.target.tagName === 'INPUT') return;
      ev.preventDefault(); setCurrent(i, true);
    });
  });
  paintLinkQueue();
  setInterval(pollCmd, 700);
}

/* ===================== comandi dalle scorciatoie globali =====================
   Il tasto lo intercetta Python (che riceve anche a gioco in primo piano) e
   mette un comando in coda. Qui lo eseguiamo passando per le STESSE funzioni
   dei pulsanti: niente logica duplicata. */

function hkToast(txt){
  fetch('/api/toast', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({run: RUN, text: txt})}).catch(function(){});
  flag(txt);
}
function stepLabel(i){
  if(i === null || i === undefined || !items[i]) return '';
  return (items[i].closest('label').innerText || '').split('\n')[0].slice(0, 60);
}
function cmdNext(){
  var i = (CUR !== null && CUR !== undefined && items[CUR] && !items[CUR].checked)
            ? CUR : firstUnchecked(0);
  if(i === null){ hkToast(S.hk_all_done); return; }
  var lb = stepLabel(i);
  items[i].checked = true;
  items[i].dispatchEvent(new Event('change'));     /* stesso percorso del click */
  hkToast('✓ ' + lb);
}
function cmdUndo(){
  var last = null;
  for(var i = 0; i < items.length; i++){ if(items[i].checked) last = i; }
  if(last === null){ hkToast(S.hk_nothing); return; }
  var lb = stepLabel(last);
  items[last].checked = false;
  items[last].dispatchEvent(new Event('change'));
  hkToast('↶ ' + lb);
}
function cmdMark(){
  if(!SES){ hkToast(S.hk_no_ses); return; }
  postMarker(null, 'free', nowTc().tc, '📍');
  hkToast('📍 ' + fmtTc(nowTc().tc));
}
function cmdRec(){
  if(SES){
    if(OBS.ok) obsSend('StopRecord');
    hkToast(S.hk_stop);
    stopSession();
  } else {
    if(OBS.ok) obsSend('StartRecord');
    hkToast(S.hk_start);
    /* diamo a OBS un secondo per far partire l'output, cosi' il timecode
       della sessione nasce gia' allineato al video */
    setTimeout(startSession, 1200);
  }
}
function runCmd(c){
  if(c.a === 'next') return cmdNext();
  if(c.a === 'undo') return cmdUndo();
  if(c.a === 'mark') return cmdMark();
  if(c.a === 'rec')  return cmdRec();
}
function pollCmd(){
  fetch('/api/pending?run=' + RUN).then(function(r){ return r.json(); })
    .then(function(j){ (j.cmds || []).forEach(runCmd); })
    .catch(function(){});
}

/* ======================= episodi in attesa del link video ===================
   Il link non esiste quando chiudi la registrazione: esiste dopo, quando il
   video e' online. Quindi non lo chiediamo in quel momento — lo teniamo in
   una lista visibile finche' non lo incolli. */

function paintLinkQueue(){
  var box = document.getElementById('linkQueue');
  if(!box) return;
  fetch('/api/episodes?run=' + RUN).then(function(r){ return r.json(); }).then(function(eps){
    var miss = (eps || []).filter(function(e){ return !e.video_url && e.ended_at; });
    if(!miss.length){ box.style.display = 'none'; box.innerHTML = ''; return; }
    var h = '<div class="lqh">▶ ' + S.lq_title.replace('{n}', miss.length) + '</div>';
    miss.forEach(function(e){
      var n = (e.markers || []).filter(function(m){ return m.kind === 'done'; }).length;
      h += '<div class="lqrow" data-id="' + e.id + '">' +
           '<span class="lqep">' + S.ep.toUpperCase() + ' ' + e.number + '</span>' +
           '<span class="lqmeta">' + (e.started_at || '').slice(0, 16) + ' · ' +
              n + ' ' + S.lq_tasks + '</span>' +
           '<input type="text" class="lqin" placeholder="' + S.url_ph + '">' +
           '<button class="lqok">💾</button>' +
           '<span class="lqst"></span></div>';
    });
    box.innerHTML = h;
    box.style.display = '';
    box.querySelectorAll('.lqrow').forEach(function(row){
      var inp = row.querySelector('.lqin'), st = row.querySelector('.lqst');
      var send = function(){
        var clean = ytNormalize(inp.value);
        if(!clean){ st.textContent = '✕'; st.style.color = 'var(--warn)'; return; }
        st.textContent = '…'; st.style.color = 'var(--muted)';
        fetch('/api/session/update', {method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({id: parseInt(row.getAttribute('data-id'), 10), video_url: clean})})
          .then(function(r){ if(!r.ok) throw 0; st.textContent = '✓';
                             st.style.color = 'var(--ok)'; setTimeout(paintLinkQueue, 700); })
          .catch(function(){ st.textContent = '✕'; st.style.color = 'var(--warn)'; });
      };
      row.querySelector('.lqok').addEventListener('click', send);
      inp.addEventListener('keydown', function(ev){ if(ev.key === 'Enter') send(); });
    });
  }).catch(function(){});
}
"""


def render_run(run_id):
    lg = lang()
    t = T[lg]
    d = ROUTES[run_id]
    hide_done = get_pref("hide_done", "0") == "1"
    only_miss = get_pref("only_miss", "0") == "1"
    note_body = get_note(run_id)
    p = ['<!DOCTYPE html><html lang="%s"><head><meta charset="UTF-8">' % lg,
         '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
         f"<title>{esc(d['game'])} - {t['checklist']} - Voloirex</title>",
         "<style>" + CSS + "</style></head><body>", hk_panel(lg, run_id)]
    p.append(f'<header><div class="topright">{hk_button(lg)}{modesel(lg, "/run/" + run_id)}'
             f'{langsel(lg, "/run/" + run_id)}</div><h1>{esc(d["game"]).upper()} · {t["checklist"]}</h1>'
             f'<p class="sub">{t["sub_run"]} · <span class="by">{t["by"]}</span></p>'
             f'<p class="meta">🏆 {d["trophy_total"]} {t["trophies"]} · {esc(L(d, "playthroughs", lg))} · '
             f'⏱ {esc(L(d, "hours", lg))}</p></header>')
    p.append('<div class="wrap">')
    p.append(f'<a class="back" href="/">← {t["back"]}</a>')
    p.append(tabs(lg, run_id, "check"))
    p.append(f'''<div class="progress-panel">
    <div class="progress-row"><span class="label">🏆 {t["trophy_steps"]}</span><div class="bar"><div id="barTrophy"></div></div><span class="count" id="cntTrophy">0 / 0</span></div>
    <div class="progress-row" style="margin-top:7px"><span class="label">📋 {t["total_steps"]}</span><div class="bar moonbar"><div id="barAll"></div></div><span class="count mooncount" id="cntAll">0 / 0</span></div>
    <div class="toolbar">
      <input id="filterBox" placeholder="{t["filter_ph"]}">
      <label class="chk"><input type="checkbox" id="hideDone"{" checked" if hide_done else ""}>{t["hide_done"]}</label>
      <label class="chk"><input type="checkbox" id="missOnly"{" checked" if only_miss else ""}>{t["only_miss"]}</label>
      <button onclick="resume()">📍 {t["resume"]}</button>
      <button onclick="expandAll()">⤵ {t["expand"]}</button>
      <button onclick="collapseAll()">⤴ {t["collapse"]}</button>
      <button class="danger" onclick="resetRun()">🗑 {t["reset"]}</button>
      {langsel(lg, "/run/" + run_id)}
      <span id="saveState">{t["loading"]}</span>
    </div>
  </div>''')
    if mode() == "streamer":
        p.append(f'''<div class="sessionbar">
      <div class="row1">
        <span class="recdot off" id="recDot"></span><span class="reclab off" id="recLab">{t["idle"]}</span>
        <span class="tc" id="tcNow">--:--</span>
        <span class="chip bad" id="obsChip">{t["obs_off"]}</span>
        <span class="chip ep" id="epChip" style="display:none"></span>
        <span class="spacer"></span>
        <button id="btnStart" onclick="startSession()">🔴 {t["start_ses"]}</button>
        <button id="btnMark" onclick="markFree()" style="display:none">📍 {t["mark"]}</button>
        <button id="btnStop" class="danger" onclick="stopSession()" style="display:none">⏹ {t["stop_ses"]}</button>
      </div>
      <div class="doing" id="doingRow" style="display:none">
        <span class="lab">{t["doing"]}</span><span class="task" id="doingTask">—</span>
        <span class="since" id="doingSince"></span>
      </div>
      <div class="doing" id="urlRow" style="display:none">
        <span class="lab">▶ {t["ep_url"]}</span>
        <input type="text" id="epUrlBar" placeholder="{t["url_ph"]}"
               style="flex:1;min-width:200px;background:#0a0c10;border:1px solid var(--line);border-radius:6px;color:var(--text);padding:5px 9px;font-size:.9em;font-family:inherit">
        <button onclick="saveUrl()">💾</button>
        <span id="urlState" style="font-size:.9em"></span>
      </div>
      <div id="linkQueue" class="linkq" style="display:none"></div>
    </div>''')

    rules = L(d, "golden_rules", lg) or d["golden_rules"]
    bullets = (d.get("build_bullets_it") if lg == "it" else None) or d.get("build_bullets") or []
    p.append('<section class="phase notes-sec">')
    p.append(f'<div class="phase-head" onclick="toggle(this)"><span class="num">⚠️</span>'
             f'<h2>{t["notes_sec"]}</h2>'
             f'<span class="mini">{t["notes_sec_sub"].format(r=len(rules), b=len(bullets))}</span>'
             f'<span class="chev">▶</span></div>')
    p.append('<div class="phase-body"><div class="rules">')
    p.append(f'<h3>{t["rules_h"]}</h3><ul>')
    for r in rules:
        p.append(f"<li>{hl(r)}</li>")
    p.append("</ul>")
    if bullets:
        p.append(f'<h3>🛡 {t["build_h"]}</h3><ul class="buildbox">')
        for bl in bullets:
            p.append(f'<li><span class="bh">{esc(bl["h"])}</span>{hl(bl["t"])}</li>')
        p.append("</ul>")
    else:
        p.append(f'<h3>🛡 {t["build_h"]}</h3><ul class="buildbox">'
                 f'<li>{hl(L(d, "build_summary", lg))}</li></ul>')
    p.append(f'<h3>{t["legend_h"]}</h3><p class="legend">{t["legend"]}</p>')
    p.append("</div></div></section>")

    stamps = step_stamps(run_id) if mode() == "streamer" or True else {}
    n = 0
    for pi, ph in enumerate(d["phases"]):
        opencls = " open" if pi == 0 else ""
        p.append(f'<section class="phase{opencls}">')
        p.append(f'<div class="phase-head" onclick="toggle(this)"><span class="num">P{pi+1}</span>'
                 f'<h2>{esc(L(ph, "title", lg))}</h2><span class="mini"></span><span class="chev">▶</span></div>')
        p.append('<div class="phase-body">')
        note = L(ph, "note", lg)
        if note:
            p.append(f'<div class="phase-note">{hl(note)}</div>')
        for st in ph["steps"]:
            n += 1
            tags = st.get("tags", [])
            dt = ' data-t="1"' if st.get("trophy") else ""
            dm = ' data-miss="1"' if any(x["type"] == "miss" for x in tags) else ""
            tg = "".join(f'<span class="tag {x["type"]}">{esc(L(x, "label", lg))}</span>' for x in tags)
            if tg:
                tg = " " + tg
            step_sid = st.get("sid") or ""
            sh = stamp_html(stamps.get(step_sid, {}), lg) if stamps.get(step_sid) else ""
            p.append(f'<label class="item"{dt}{dm}><input type="checkbox" id="s{n}" data-sid="{esc(step_sid)}">'
                     f'<span class="txt">{hl(L(st, "text", lg))}{tg}{sh}'
                     f'<span class="loc">{esc(L(st, "loc", lg))}</span></span></label>')
        p.append("</div></section>")

    p.append(f'<div id="noMatch">{t["no_match"]}</div>')

    stt = (d.get("stat_table_it") if lg == "it" else None) or d["stat_table"]
    p.append(f'<section class="phase"><div class="phase-head" onclick="toggle(this)">'
             f'<span class="num">📊 REF</span><h2>{t["stats_ref"]}</h2>'
             f'<span class="mini"></span><span class="chev">▶</span></div><div class="phase-body">')
    p.append(f'<div class="phase-note">{esc(stt["note"])}</div><table class="stats">')
    p.append("<tr>" + "".join(f"<th>{esc(c)}</th>" for c in stt["columns"]) + "</tr>")
    for row in stt["rows"]:
        p.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>")
    p.append("</table></div></section>")

    gloss = d.get("glossary_it") or {}
    if lg == "it" and gloss:
        p.append(f'<section class="phase"><div class="phase-head" onclick="toggle(this)">'
                 f'<span class="num">📖 GLOS</span><h2>{t["gloss_title"]}</h2>'
                 f'<span class="mini">{len(gloss)}</span><span class="chev">▶</span></div><div class="phase-body">')
        p.append(f'<div class="phase-note">{t["gloss_note"]}</div><table class="gloss">')
        for k, v in sorted(gloss.items(), key=lambda kv: kv[0].lower()):
            p.append(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>")
        p.append("</table></div></section>")

    p.append(f'<section class="phase"><div class="phase-head" onclick="toggle(this)">'
             f'<span class="num">📝 {"NOTE" if lg == "it" else "NOTES"}</span><h2>{t["notes_title"]}</h2>'
             f'<span class="mini"></span><span class="chev">▶</span></div><div class="phase-body">'
             f'<div class="phase-note">{t["notes_note"]}</div>'
             f'<textarea class="notes" id="notesBox" placeholder="{t["notes_ph"]}">{esc(note_body)}</textarea>'
             "</div></section>")

    p.append(f'<div class="plat" id="platBox"><h2>{t["plat_done"]}</h2></div></div>')
    p.append(f'<footer>{t["footer_run"]}</footer>')
    strings = {k: t[k] for k in ("saving", "saved", "save_failed", "offline", "loaded", "new_run",
                                 "confirm_reset", "obs_on", "obs_off", "clock_mode", "rec", "idle",
                                 "ep", "doing", "started_at", "since", "mark", "no_session_warn",
                                 "ask_url", "url_ph", "lq_title", "lq_tasks", "hk_all_done",
                                 "hk_nothing", "hk_no_ses", "hk_start", "hk_stop")}
    cfg = {"mode": mode(),
           "obs_url": get_pref("obs_url", "ws://127.0.0.1:4455"),
           "obs_pass": get_pref("obs_pass", ""),
           "obs_prefer": get_pref("obs_prefer", "auto")}
    js = (OBS_JS + CHECKLIST_JS).replace("__RUN__", json.dumps(run_id)) \
        .replace("__STR__", json.dumps(strings, ensure_ascii=False)) \
        .replace("__CFG__", json.dumps(cfg, ensure_ascii=False))
    p.append("<script>" + js + "</script></body></html>")
    return "\n".join(p)
