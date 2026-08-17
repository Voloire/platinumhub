# -*- coding: utf-8 -*-
"""La guida pubblicabile: fotografia HTML autonoma della run."""

import datetime

from .i18n import T, L
from .routes import ROUTES
from .store import done_sids, lang, sessions_of, step_stamps
from .ui import esc, fmt_tc, hl, video_link


# ------------------------------------------------------- guida pubblicabile
EXPORT_CSS = """
:root{--bg:#0d0f14;--panel:#151823;--panel2:#1a1e2c;--line:#2a2f42;--gold:#c8a24a;
--gold-dim:#8a7134;--moon:#7fa8d9;--moon-dim:#4a6a94;--text:#d8d5c8;--muted:#8a8878;
--warn:#c86a4a;--warn-bg:#2a1a14;--ok:#7fc98a;--item:#7fd8d0}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);line-height:1.6;padding:0 0 60px;
font-family:'Roboto','Segoe UI',system-ui,-apple-system,Arial,sans-serif}
a{color:inherit}
.wrap{max-width:900px;margin:0 auto;padding:0 16px}
header{text-align:center;padding:34px 20px 22px;border-bottom:1px solid var(--line);
background:linear-gradient(180deg,#131625,var(--bg))}
header h1{font-size:1.5em;color:var(--gold);letter-spacing:3px;font-weight:500}
header .sub{color:var(--muted);font-style:italic;margin-top:6px}
header .meta{color:var(--moon);font-size:.85em;margin-top:9px}
.bar{display:flex;align-items:center;gap:12px;background:var(--panel);border:1px solid var(--line);
border-radius:10px;padding:14px 18px;margin:20px 0;flex-wrap:wrap}
.bar .n{font-size:1.5em;color:var(--gold);font-variant-numeric:tabular-nums}
.bar .l{font-size:.8em;color:var(--muted);text-transform:uppercase;letter-spacing:1px}
.bar .sep{width:1px;align-self:stretch;background:var(--line)}
h2.sec{font-size:.85em;color:var(--gold);letter-spacing:2px;text-transform:uppercase;
margin:28px 0 10px;font-weight:500;border-bottom:1px solid var(--line);padding-bottom:7px}
.eps{display:grid;gap:8px}
.ep{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 14px;
display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:.9em}
.ep b{color:var(--gold);font-weight:500}
.ep .m{color:var(--muted);font-size:.9em}
.ep a{color:var(--moon);text-decoration:none;border:1px solid var(--moon-dim);
border-radius:5px;padding:2px 9px;font-size:.85em}
.ep a:hover{color:var(--gold);border-color:var(--gold)}
section.phase{background:var(--panel);border:1px solid var(--line);border-radius:10px;
margin:14px 0;overflow:hidden}
.ph{display:flex;gap:12px;align-items:center;padding:12px 16px;background:var(--panel2)}
.ph .num{color:var(--moon);font-size:.78em;letter-spacing:2px}
.ph h3{font-size:1em;color:var(--gold);font-weight:500;flex:1}
.ph .mini{font-size:.8em;color:var(--muted)}
.body{padding:4px 16px 12px}
.note{font-size:.85em;color:var(--muted);font-style:italic;padding:8px 2px 10px;
border-bottom:1px dashed var(--line);margin-bottom:4px}
.step{display:flex;gap:11px;padding:9px 4px;border-bottom:1px solid #1d2130;align-items:flex-start}
.step:last-child{border-bottom:none}
.step .mk{flex-shrink:0;width:18px;text-align:center;color:var(--ok)}
.step.todo .mk{color:#3a3f52}
.step .tx{flex:1;font-size:.93em}
.step .loc{display:block;font-size:.83em;color:var(--muted)}
.step.done .tx{color:#8a8878}
.cap{color:var(--item);font-weight:500}
.tag{display:inline-block;font-size:.68em;letter-spacing:1px;padding:1px 7px;border-radius:4px;margin-left:6px}
.tag.trophy{background:#2a2413;color:var(--gold);border:1px solid var(--gold-dim)}
.tag.coll{background:#221d10;color:var(--gold);border:1px dashed var(--gold-dim)}
.tag.quest{background:#141d2a;color:var(--moon);border:1px solid var(--moon-dim)}
.tag.miss{background:var(--warn-bg);color:var(--warn);border:1px solid #4a2a1e}
.tag.build{background:#14241a;color:var(--ok);border:1px solid #2e5a3a}
.at{display:inline-block;font-size:.72em;letter-spacing:.5px;padding:2px 8px;border-radius:5px;
margin-left:8px;white-space:nowrap;background:#161d2c;border:1px solid var(--moon-dim);
color:var(--moon);text-decoration:none}
.at:hover{background:#1d2740;border-color:var(--moon);color:#a8c8e8}
.at .epn{color:var(--gold);font-weight:700}
.rules{background:var(--warn-bg);border:1px solid #4a2a1e;border-radius:10px;padding:14px 20px;margin:16px 0}
.rules h3{color:var(--warn);font-size:.82em;letter-spacing:2px;text-transform:uppercase;
margin:10px 0 8px;font-weight:500}
.rules ul{list-style:none}
.rules li{position:relative;padding:5px 0 5px 18px;font-size:.9em}
.rules li::before{content:"\\25b8";position:absolute;left:0;color:var(--warn);opacity:.8}
.rules .bx li{color:var(--ok)}
.rules .bx li::before{color:var(--ok)}
.rules .bx .bh{color:#a8e6b4;font-weight:700}
.rules .bx .bh::after{content:" \\2014 ";color:var(--muted);font-weight:400}
footer{text-align:center;color:var(--muted);font-size:.8em;padding:28px 16px;font-style:italic}
@media print{body{background:#fff;color:#111}header{background:none}}
"""


def render_export(run_id):
    lg, t = lang(), T[lang()]
    d = ROUTES[run_id]
    done_set = done_sids(run_id) & d["_sidset"]
    stamps = step_stamps(run_id)
    eps = sorted(sessions_of(run_id), key=lambda e: e["number"])
    done = len(done_set)
    tdone = len(done_set & d["_trophy_sids"])
    when = datetime.datetime.now().strftime("%d/%m/%Y")
    IT = lg == "it"

    p = ['<!DOCTYPE html>', '<html lang="%s">' % lg, '<head><meta charset="UTF-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
         '<title>%s — %s</title>' % (esc(d["game"]), "Guida" if IT else "Guide"),
         '<style>%s</style></head>' % EXPORT_CSS,
         '<!--',
         '   Questa pagina e\' una FOTOGRAFIA della run al %s.' % when if IT
         else '   This page is a SNAPSHOT of the run taken on %s.' % when,
         '   E\' HTML semplice: puoi modificarla a mano con un editor di testo.' if IT
         else '   It is plain HTML: edit it by hand with any text editor.',
         '   I link ai video hanno la forma  https://youtu.be/ID?t=SECONDI' if IT
         else '   Video links look like  https://youtu.be/ID?t=SECONDS',
         '-->', '<body>']
    p.append('<header><h1>%s</h1>'
             '<p class="sub">%s · <span style="color:var(--gold)">%s</span></p>'
             '<p class="meta">%s %s</p></header>'
             % (esc(d["game"]).upper(),
                "Guida cliccabile della run" if IT else "Clickable run guide",
                t["by"], "Fotografia del" if IT else "Snapshot taken", when))
    p.append('<div class="wrap">')
    p.append('<div class="bar"><span class="n">%d/%d</span><span class="l">%s</span><span class="sep"></span>'
             '<span class="n">%d/%d</span><span class="l">%s</span><span class="sep"></span>'
             '<span class="n">%d</span><span class="l">%s</span></div>'
             % (tdone, d["_tsteps"], "trofei" if IT else "trophies",
                done, d["_steps"], "passi" if IT else "steps",
                len([e for e in eps if e["video_url"]]), "episodi" if IT else "episodes"))

    linked = [e for e in eps if e["video_url"]]
    if linked:
        p.append('<h2 class="sec">%s</h2><div class="eps">' % ("Gli episodi" if IT else "The episodes"))
        for e in linked:
            n_done = len({m["sid"] for m in e["markers"] if m["kind"] == "done"})
            p.append('<div class="ep"><b>%s %d</b>%s<span class="m">%s %s</span>'
                     '<span style="flex:1"></span><a href="%s" target="_blank">%s</a></div>'
                     % ("EPISODIO" if IT else "EPISODE", e["number"],
                        (" — " + esc(e["title"])) if e["title"] else "",
                        n_done, "task", esc(e["video_url"]), "guarda ▶" if IT else "watch ▶"))
        p.append('</div>')

    rules = L(d, "golden_rules", lg) or d["golden_rules"]
    bullets = (d.get("build_bullets_it") if lg == "it" else None) or d.get("build_bullets") or []
    p.append('<h2 class="sec">%s</h2><div class="rules">'
             % (t["notes_sec"].replace("&amp;", "&")))
    p.append('<h3>%s</h3><ul>' % t["rules_h"])
    for r in rules:
        p.append("<li>%s</li>" % hl(r))
    p.append('</ul>')
    if bullets:
        p.append('<h3>%s</h3><ul class="bx">' % t["build_h"])
        for bl in bullets:
            p.append('<li><span class="bh">%s</span>%s</li>' % (esc(bl["h"]), hl(bl["t"])))
        p.append('</ul>')
    p.append('</div>')

    p.append('<h2 class="sec">%s</h2>' % ("Il percorso" if IT else "The route"))
    for pi, ph in enumerate(d["phases"]):
        cnt = len(ph["steps"])
        dn = sum(1 for st in ph["steps"] if st.get("sid") in done_set)
        p.append('<section class="phase"><div class="ph"><span class="num">P%d</span>'
                 '<h3>%s</h3><span class="mini">%d/%d</span></div><div class="body">'
                 % (pi + 1, esc(L(ph, "title", lg)), dn, cnt))
        note = L(ph, "note", lg)
        if note:
            p.append('<div class="note">%s</div>' % hl(note))
        for st in ph["steps"]:
            ok = st.get("sid") in done_set
            tags = "".join('<span class="tag %s">%s</span>' % (x["type"], esc(L(x, "label", lg)))
                           for x in st.get("tags", []))
            at = ""
            sm = stamps.get(st.get("sid"), {})
            dnm = sm.get("done")
            if dnm and dnm.get("url"):
                at = ('<a class="at" href="%s" target="_blank"><span class="epn">%s %d</span> · %s ▶</a>'
                      % (video_link(dnm["url"], dnm["t"]), t["ep"], dnm["ep"], fmt_tc(dnm["t"])))
            p.append('<div class="step %s"><span class="mk">%s</span><span class="tx">%s%s%s'
                     '<span class="loc">%s</span></span></div>'
                     % ("done" if ok else "todo", "&#10003;" if ok else "&#9675;",
                        hl(L(st, "text", lg)), tags, at, esc(L(st, "loc", lg))))
        p.append('</div></section>')

    p.append('</div><footer>%s · %s</footer></body></html>'
             % (esc(t["footer_run"]),
                "pagina generata da Platinum Hub" if IT else "page generated by Platinum Hub"))
    return "\n".join(p)
