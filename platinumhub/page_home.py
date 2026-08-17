# -*- coding: utf-8 -*-
"""La home con le card delle run e la pagina del changelog."""

import json
import os

from .config import BASE, RELEASES_PAGE, UPDATE, VERSION
from .i18n import T
from .routes import ROUTES
from .store import lang, stats
from .thumbs import THUMB_ART_JS, thumb_design
from .ui import CSS, esc, hk_button, hk_panel, langsel, md_lite


def render_changelog():
    lg = lang()
    t = T[lg]
    body = ""
    for name in ("CHANGELOG.md", os.path.join("docs", "CHANGELOG.md")):
        fp = os.path.join(BASE, name)
        if os.path.exists(fp):
            try:
                with open(fp, encoding="utf-8") as fh:
                    body = md_lite(fh.read()[:60000])
            except Exception:
                body = ""
            break
    if not body:
        body = '<p>%s <a href="%s" target="_blank" rel="noopener">GitHub</a>.</p>' % (
            t["chlog_none"], RELEASES_PAGE)
    p = ['<!DOCTYPE html><html lang="%s"><head><meta charset="UTF-8">' % lg,
         '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
         "<title>%s - Platinum Hub</title>" % t["chlog_title"],
         "<style>" + CSS + "</style></head><body>",
         f'<header><h1>{t["chlog_title"]}</h1>'
         f'<p class="sub">Platinum Hub v{VERSION} · <span class="by">by Voloirex</span></p></header>',
         '<div class="wrap"><p><a href="/">&larr; %s</a></p>' % t["chlog_back"],
         '<div class="chlog">', body, "</div>",
         f'<p style="margin-top:26px"><a href="{RELEASES_PAGE}" target="_blank" rel="noopener">'
         f'{RELEASES_PAGE}</a></p>',
         f'</div><footer>{t["footer"]}</footer></body></html>']
    return "\n".join(p)


def render_home():
    lg = lang()
    t = T[lg]
    p = ['<!DOCTYPE html><html lang="%s"><head><meta charset="UTF-8">' % lg,
         '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
         "<title>Platinum Hub - by Voloirex</title>", "<style>" + CSS + "</style></head><body>",
         hk_panel(lg)]
    p.append(f'<header><div class="topright">{hk_button(lg)}{langsel(lg, "/")}</div>'
             f'<h1>{t["hub_title"]}</h1>'
             f'<p class="sub">{t["hub_sub"]} · <span class="by">{t["by"]}</span></p>'
             f'<p class="meta">{t["hub_meta"]}</p></header>')
    p.append('<div class="wrap">')
    if UPDATE["latest"]:
        p.append(f'<div class="updbox"><div class="uh">⬆ {t["upd_title"].format(v=esc(UPDATE["latest"]))}</div>'
                 f'<div class="ub">{t["upd_body"].format(cur=VERSION)}</div>'
                 f'<div class="ur"><a class="updbtn" href="{esc(UPDATE["url"])}" target="_blank" '
                 f'rel="noopener">{t["upd_get"]}</a>'
                 f'<a class="updlnk" href="/changelog">{t["upd_notes"]}</a>'
                 f'<a class="updlnk" href="/update/off">{t["upd_off"]}</a></div></div>')
    p.append('<div class="cards">')
    for rid, d in ROUTES.items():
        done, total, tdone, ttotal, when = stats(rid)
        pct = (done / total * 100) if total else 0
        tpct = (tdone / ttotal * 100) if ttotal else 0
        p.append(f'<a class="card" href="/run/{rid}">')
        p.append(f'<span class="stripe" style="background:{esc(d["meta"]["accent"])}"></span>')
        # l'arte della thumbnail al posto della vecchia descrizione testuale:
        # stesso codice di disegno di /thumb/<run>, ritagliato a fascia
        p.append(f'<canvas class="cardart" data-run="{rid}" width="640" height="270"></canvas>')
        p.append(f'<h2>{esc(d["game"])}{" &nbsp;🏆" if total and done == total else ""}</h2>')
        p.append(f'<div class="prow"><span class="lb">🏆 {t["trophy_steps"]}</span><div class="bar">'
                 f'<div style="width:{tpct:.1f}%"></div></div><span class="count">{tdone} / {ttotal}</span></div>')
        p.append(f'<div class="prow"><span class="lb">📋 {t["steps"]}</span><div class="bar moonbar">'
                 f'<div style="width:{pct:.1f}%"></div></div>'
                 f'<span class="count mooncount">{done} / {total}</span></div>')
        if when:
            p.append(f'<div class="when">↻ {esc(when)}</div>')
        p.append("</a>")
    p.append("</div>")
    p.append(f'<div class="hubnote">{t["hubnote"]}</div>')
    p.append(f'<div class="hubnote"><h3>💾 {t["backup_title"]}</h3>{t["backup_note"]}'
             f'<div class="btns"><a class="btn" href="/api/export">⬇ {t["download_backup"]}</a>'
             f'<button onclick="document.getElementById(\'impf\').click()">⬆ {t["restore_backup"]}</button>'
             f'<input type="file" id="impf" accept="application/json,.json" style="display:none">'
             f'<span id="impState" style="font-size:.8em;color:var(--muted)"></span></div></div>')
    p.append("</div>")
    p.append(f'<footer>{t["footer"]}</footer>')
    # disegna l'arte delle card: stesse icone di /thumb/<run>, una implementazione
    art_map = {rid: {k: thumb_design(d)[k] for k in ("icon", "glow", "seed")}
               for rid, d in ROUTES.items()}
    p.append("<script>var ART = %s;\n%s\n"
             "document.querySelectorAll('canvas.cardart').forEach(function(c){\n"
             "  var d = ART[c.dataset.run]; if (!d) return;\n"
             "  setCtx(c.getContext('2d'));\n"
             "  ctx.save(); ctx.scale(0.5, 0.5); ctx.translate(0, -90);\n"
             "  drawBg(d.glow, d.seed);\n"
             "  (ICONS[d.icon] || ICONS.trophy)();\n"
             "  ctx.restore();\n"
             "});</script>"
             % (json.dumps(art_map, ensure_ascii=False).replace("</", "<\\/"), THUMB_ART_JS))
    p.append("""<script>
document.getElementById('impf').addEventListener('change', function(){
  var f = this.files[0]; if(!f) return;
  if(!confirm(%s)) { this.value=''; return; }
  var fr = new FileReader();
  fr.onload = function(){
    fetch('/api/import', {method:'POST', headers:{'Content-Type':'application/json'}, body: fr.result})
      .then(function(r){ if(!r.ok) throw 0; return r.json(); })
      .then(function(){ document.getElementById('impState').textContent = %s; setTimeout(function(){location.reload();}, 700); })
      .catch(function(){ document.getElementById('impState').textContent = %s; });
  };
  fr.readAsText(f);
});
</script></body></html>""" % (json.dumps(T[lg]["confirm_import"]), json.dumps(T[lg]["import_ok"]),
                              json.dumps(T[lg]["import_bad"])))
    return "\n".join(p)
