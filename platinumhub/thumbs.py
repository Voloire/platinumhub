# -*- coding: utf-8 -*-
"""Le thumbnail YouTube: design per gioco, arte in canvas, pagina di download."""

import json

from .i18n import T
from .routes import ROUTES
from .store import lang
from .ui import esc, page_head


# ------------------------------------------------------- thumbnail YouTube
# La miniatura non e' un file: e' un disegno rifatto da capo a ogni apertura,
# nel canvas del browser. Cosi' la "base comune" della serie e' codice
# versionato (identica per sempre, particelle comprese: il seme e' fisso), la
# riga variabile e' un campo di testo, e non serve nessuna libreria di
# immagini ne' un file sorgente che si puo' perdere. Il numero dei trofei
# arriva dalla route, non e' scritto qui: la thumbnail non puo' mentire.
#
# I testi del canvas sono volutamente SOLO in italiano: sono il brand del
# canale, non interfaccia. L'interfaccia intorno e' bilingue come il resto.
#
# Il design per gioco vive nel meta.thumb della route (icona, glow, seme,
# statistiche, tag): e' parte della route, viaggia con lei. Qui resta solo
# il ripiego, cosi' una route senza design ha comunque una thumbnail seria.
THUMB_FALLBACK = {"icon": "trophy", "glow": "110,80,25", "seed": 5, "stats": [], "tag": None}
THUMB_TAG_DEFAULT = "Niente glitch · niente skip · route verificata"


def thumb_design(route):
    """Il design della thumbnail di una route: meta.thumb con il ripiego sotto."""
    meta = route.get("meta") or {}
    design = dict(THUMB_FALLBACK)
    design.update({k: v for k, v in (meta.get("thumb") or {}).items()
                   if k in THUMB_FALLBACK})
    return design

# L'arte (sfondo, particelle, icone) e' separata dalla pagina che la usa:
# la disegnano sia /thumb/<run> sia le card della home, e deve esistere UNA
# sola implementazione di ogni icona.
THUMB_ART_JS = r"""
'use strict';
const W = 1280, H = 720, CTX = 352, CTY = 362;
const SERIF = 'Georgia, "Times New Roman", serif';
let ctx = null;
function setCtx(c) { ctx = c; }

function mulberry32(a){ return function(){ a|=0; a=a+0x6D2B79F5|0;
  let t=Math.imul(a^a>>>15,1|a); t=t+Math.imul(t^t>>>7,61|t)^t;
  return ((t^t>>>14)>>>0)/4294967296; }; }

function drawBg(glow, seed){
  let g = ctx.createLinearGradient(0,0,0,H);
  g.addColorStop(0,'#17110a'); g.addColorStop(1,'#0d0a07');
  ctx.fillStyle = g; ctx.fillRect(0,0,W,H);
  let r = ctx.createRadialGradient(CTX,CTY,40,CTX,CTY,540);
  r.addColorStop(0,'rgba('+glow+',0.34)'); r.addColorStop(0.55,'rgba('+glow+',0.16)');
  r.addColorStop(1,'rgba(0,0,0,0)');
  ctx.fillStyle = r; ctx.fillRect(0,0,W,H);
  r = ctx.createRadialGradient(950,640,60,950,640,480);
  r.addColorStop(0,'rgba(85,55,18,0.20)'); r.addColorStop(1,'rgba(0,0,0,0)');
  ctx.fillStyle = r; ctx.fillRect(0,0,W,H);
  const rnd = mulberry32(seed);
  for (let i=0;i<110;i++){
    const right = (i%9===0);
    const x = right ? 700+rnd()*560 : rnd()*690, y = rnd()*H;
    ctx.beginPath(); ctx.arc(x,y,0.8+rnd()*2.7,0,Math.PI*2);
    ctx.fillStyle = 'rgba('+glow+','+(0.10+rnd()*0.6).toFixed(2)+')'; ctx.fill();
  }
}

"""

THUMB_PAGE_JS = r"""
const cv = document.getElementById('thumbCanvas');
setCtx(cv.getContext('2d'));

// misura che TIENE CONTO dello spacing (measureText lo include quando la
// proprieta' e' impostata sul contesto: qui la si imposta sempre prima)
function fitLine(text, maxW, px, ls, weight, minPx){
  ctx.letterSpacing = '0px';
  ctx.font = weight+' '+px+'px '+SERIF;
  let w0 = ctx.measureText(text).width;
  if (w0 > maxW){
    px = Math.max(minPx, Math.floor(px*maxW/w0));
    ctx.font = weight+' '+px+'px '+SERIF;
    w0 = ctx.measureText(text).width;
  }
  // il corpo giusto prima, poi lo spacing esatto dallo spazio che avanza:
  // ridurli insieme a piccoli passi tocca il corpo minimo troppo presto
  ctx.letterSpacing = Math.max(0, Math.min(ls, (maxW-w0)/Math.max(1,text.length-1)-0.2)).toFixed(2)+'px';
}

function statW(stats, s){
  let w = 0;
  for (let i=0;i<stats.length;i++){
    if (i>0) w += 44*s;
    const [n,l] = stats[i];
    if (n){ ctx.letterSpacing='0px'; ctx.font='700 '+Math.round(54*s)+'px '+SERIF;
            w += ctx.measureText(n).width + 11*s; }
    ctx.letterSpacing = (3*s)+'px'; ctx.font='600 '+Math.round(26*s)+'px '+SERIF;
    w += ctx.measureText(l).width;
  }
  ctx.letterSpacing='0px'; return w;
}

function drawText(name, slot, ep, stats, tag){
  const LX = 700, RX = 1212;
  ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
  fitLine(name, RX-LX, 40, 16, '600', 24);
  ctx.fillStyle = '#e9d8a6'; ctx.fillText(name, LX, 128);
  ctx.fillStyle = 'rgba(185,145,72,0.55)'; ctx.fillRect(LX,152,RX-LX,2);
  fitLine('PLATINO', RX-LX+10, 110, 4, '700', 84);
  ctx.fillStyle = '#f0d894'; ctx.fillText('PLATINO', LX-6, 290);
  fitLine(slot, RX-LX, 47, 8, '600', 26);
  ctx.fillStyle = slot === 'TUTTI I TROFEI' ? '#dcbc7c' : '#f2d894';
  ctx.fillText(slot, LX, 370);
  ctx.fillStyle = 'rgba(185,145,72,0.55)'; ctx.fillRect(LX,406,RX-LX,2);
  let s = 1;
  while (s > 0.6 && statW(stats, s) > RX-LX) s -= 0.05;
  let x = LX;
  for (let i=0;i<stats.length;i++){
    if (i>0){ ctx.font='700 '+Math.round(34*s)+'px '+SERIF; ctx.fillStyle='#c9a96a';
              ctx.fillText('·', x+15*s, 474); x += 44*s; }
    const [n,l] = stats[i];
    if (n){ ctx.letterSpacing='0px'; ctx.font='700 '+Math.round(54*s)+'px '+SERIF;
            ctx.fillStyle='#f4d27a'; ctx.fillText(n, x, 480);
            x += ctx.measureText(n).width + 11*s; }
    ctx.letterSpacing=(3*s)+'px'; ctx.font='600 '+Math.round(26*s)+'px '+SERIF;
    ctx.fillStyle='#c9a96a'; ctx.fillText(l, x, 478);
    x += ctx.measureText(l).width; ctx.letterSpacing='0px';
  }
  fitLine(tag, RX-LX, 30, 2, '400', 20);
  ctx.fillStyle = '#b39a6b'; ctx.fillText(tag, LX, 542);
  ctx.letterSpacing='1px'; ctx.font='400 25px '+SERIF; ctx.fillStyle='#9a8258';
  ctx.fillText('by Voloirex', LX, 618);
  ctx.textAlign='right'; ctx.font='700 25px '+SERIF; ctx.fillText('ITA', RX, 618);
  ctx.textAlign='left'; ctx.letterSpacing='0px';
  if (ep){
    ctx.save();
    ctx.shadowColor='rgba(0,0,0,0.8)'; ctx.shadowBlur=14;
    ctx.letterSpacing='3px'; ctx.font='700 46px '+SERIF; ctx.fillStyle='#f0d894';
    ctx.fillText('EP. '+ep, 42, 686);
    ctx.restore();
  }
}

"""

THUMB_ART_JS += r"""
const ICONS = {
ring: function(){
  const R=202, g=ctx.createLinearGradient(CTX-R,CTY+R,CTX+R,CTY-R);
  g.addColorStop(0,'#ffdf82'); g.addColorStop(0.55,'#f2b93f'); g.addColorStop(1,'#d1952b');
  ctx.save();
  ctx.shadowColor='rgba(250,190,70,0.85)'; ctx.shadowBlur=55;
  ctx.strokeStyle=g; ctx.lineWidth=17; ctx.lineCap='round';
  ctx.beginPath(); ctx.arc(CTX,CTY,R,-34*Math.PI/180,(326)*Math.PI/180); ctx.stroke();
  const sa=-51*Math.PI/180, sr=R+44;
  ctx.translate(CTX+sr*Math.cos(sa), CTY+sr*Math.sin(sa)); ctx.rotate(sa+Math.PI/2);
  ctx.fillStyle=g; ctx.shadowBlur=30; ctx.fillRect(-9,-6,19,13);
  ctx.restore();
},
bonfire: function(){
  ctx.save();
  let g=ctx.createRadialGradient(CTX,520,10,CTX,520,190);
  g.addColorStop(0,'rgba(255,140,40,0.55)'); g.addColorStop(1,'rgba(0,0,0,0)');
  ctx.fillStyle=g; ctx.fillRect(CTX-220,380,440,220);
  ctx.fillStyle='#241a10';
  ctx.beginPath(); ctx.ellipse(CTX,522,175,42,0,0,Math.PI*2); ctx.fill();
  for (const [dx,h,col] of [[-55,96,'#d85a14'],[0,150,'#f08828'],[48,82,'#e87018'],[14,108,'#ffc858']]){
    ctx.shadowColor='rgba(255,150,50,0.8)'; ctx.shadowBlur=34; ctx.fillStyle=col;
    ctx.beginPath();
    ctx.moveTo(CTX+dx-26,512);
    ctx.quadraticCurveTo(CTX+dx-30,470-h*0.4,CTX+dx+4,512-h);
    ctx.quadraticCurveTo(CTX+dx+32,480-h*0.2,CTX+dx+26,512);
    ctx.closePath(); ctx.fill();
  }
  ctx.shadowBlur=0;
  const b=ctx.createLinearGradient(CTX-14,0,CTX+14,0);
  b.addColorStop(0,'#2c2824'); b.addColorStop(0.5,'#57504a'); b.addColorStop(1,'#26221e');
  ctx.fillStyle=b;
  ctx.beginPath();
  ctx.moveTo(CTX+2,142);
  ctx.quadraticCurveTo(CTX+20,260,CTX+12,360); ctx.lineTo(CTX+16,452); ctx.lineTo(CTX-12,452);
  ctx.quadraticCurveTo(CTX-22,300,CTX-4,142);
  ctx.closePath(); ctx.fill();
  ctx.strokeStyle='rgba(255,150,60,0.55)'; ctx.lineWidth=2; ctx.stroke();
  ctx.strokeStyle='#7a6248'; ctx.lineWidth=7;
  ctx.beginPath(); ctx.arc(CTX+2,440,26,Math.PI*0.15,Math.PI*1.2); ctx.stroke();
  ctx.beginPath(); ctx.arc(CTX-2,452,20,Math.PI*0.9,Math.PI*2.05); ctx.stroke();
  const rnd=mulberry32(31);
  for (let i=0;i<26;i++){
    ctx.fillStyle='rgba(255,'+(120+Math.floor(rnd()*100))+',40,'+(0.25+rnd()*0.6).toFixed(2)+')';
    ctx.beginPath(); ctx.arc(CTX-90+rnd()*180,200+rnd()*300,1+rnd()*2.6,0,Math.PI*2); ctx.fill();
  }
  ctx.restore();
},
darksign: function(){
  const R=150; ctx.save();
  ctx.shadowColor='rgba(255,80,20,0.9)'; ctx.shadowBlur=70;
  const g=ctx.createLinearGradient(CTX,CTY+R,CTX,CTY-R);
  g.addColorStop(0,'#ff9838'); g.addColorStop(0.5,'#e84818'); g.addColorStop(1,'#a82810');
  ctx.strokeStyle=g; ctx.lineWidth=30;
  ctx.beginPath(); ctx.arc(CTX,CTY,R,0,Math.PI*2); ctx.stroke();
  const rnd=mulberry32(53); ctx.shadowBlur=26;
  for (let i=0;i<16;i++){
    const a=(i/16)*Math.PI*2+rnd()*0.2, h=26+rnd()*44;
    const bx=CTX+(R+15)*Math.cos(a), by=CTY+(R+15)*Math.sin(a);
    ctx.fillStyle=i%3?'#f06020':'#ffb040';
    ctx.beginPath();
    ctx.moveTo(bx+12*Math.cos(a+Math.PI/2),by+12*Math.sin(a+Math.PI/2));
    ctx.quadraticCurveTo(CTX+(R+15+h)*Math.cos(a+0.12),CTY+(R+15+h)*Math.sin(a+0.12),
                         bx+12*Math.cos(a-Math.PI/2),by+12*Math.sin(a-Math.PI/2));
    ctx.closePath(); ctx.fill();
  }
  ctx.shadowBlur=0;
  const c=ctx.createRadialGradient(CTX,CTY,20,CTX,CTY,R-12);
  c.addColorStop(0,'#000000'); c.addColorStop(0.85,'#0a0402'); c.addColorStop(1,'#2a0e04');
  ctx.fillStyle=c;
  ctx.beginPath(); ctx.arc(CTX,CTY,R-13,0,Math.PI*2); ctx.fill();
  ctx.restore();
},
crescent: function(){
  ctx.save(); ctx.translate(CTX,CTY); ctx.rotate(-0.5);
  for (let t=3;t>=1;t--){
    ctx.strokeStyle='rgba(120,220,240,'+(0.10*t)+')'; ctx.lineWidth=5-t;
    ctx.beginPath(); ctx.arc(0,0,195+t*17,Math.PI*0.55,Math.PI*1.55); ctx.stroke();
  }
  ctx.shadowColor='rgba(120,225,245,0.95)'; ctx.shadowBlur=55;
  const g=ctx.createLinearGradient(0,-200,0,200);
  g.addColorStop(0,'#eafdff'); g.addColorStop(0.5,'#8ce4f4'); g.addColorStop(1,'#38a8c8');
  ctx.fillStyle=g;
  ctx.beginPath();
  ctx.arc(0,0,190,Math.PI*0.52,Math.PI*1.58);
  ctx.arc(38,0,158,Math.PI*1.52,Math.PI*0.58,true);
  ctx.closePath(); ctx.fill();
  const rnd=mulberry32(77); ctx.shadowBlur=12;
  for (let i=0;i<18;i++){
    const a=Math.PI*(0.55+rnd()*1.0), r=150+rnd()*90;
    ctx.fillStyle='rgba(220,250,255,'+(0.3+rnd()*0.6).toFixed(2)+')';
    ctx.beginPath(); ctx.arc(r*Math.cos(a),r*Math.sin(a),1+rnd()*2.4,0,Math.PI*2); ctx.fill();
  }
  ctx.restore();
},
slashes: function(){
  ctx.save();
  const rnd=mulberry32(99);
  for (const [off,rot,len,bulge] of [[-92,0.56,205,30],[0,0.62,245,38],[90,0.68,210,30]]){
    ctx.save(); ctx.translate(CTX+off,CTY); ctx.rotate(rot);
    ctx.shadowColor='rgba(230,40,50,0.85)'; ctx.shadowBlur=44;
    const g=ctx.createLinearGradient(0,-len,0,len);
    g.addColorStop(0,'#ff6858'); g.addColorStop(0.5,'#d81c28'); g.addColorStop(1,'#5e0a12');
    ctx.fillStyle=g;
    ctx.beginPath();
    ctx.moveTo(0,-len);
    ctx.quadraticCurveTo(bulge,0,2,len);
    ctx.quadraticCurveTo(bulge-30,0,0,-len);
    ctx.closePath(); ctx.fill();
    ctx.restore();
  }
  for (let i=0;i<24;i++){
    ctx.fillStyle='rgba(216,40,50,'+(0.2+rnd()*0.5).toFixed(2)+')';
    ctx.beginPath(); ctx.arc(CTX-190+rnd()*380,CTY-210+rnd()*420,1+rnd()*3.2,0,Math.PI*2); ctx.fill();
  }
  ctx.restore();
},
strings: function(){
  ctx.save();
  for (const [gx,gy,gr,teeth,al] of [[CTX-20,CTY+90,165,13,0.16],[CTX+168,CTY-96,84,9,0.13]]){
    ctx.strokeStyle='rgba(140,170,215,'+al+')'; ctx.lineWidth=13;
    ctx.beginPath(); ctx.arc(gx,gy,gr,0,Math.PI*2); ctx.stroke();
    ctx.beginPath(); ctx.arc(gx,gy,gr*0.45,0,Math.PI*2); ctx.stroke();
    for (let i=0;i<teeth;i++){
      const a=(i/teeth)*Math.PI*2;
      ctx.save(); ctx.translate(gx+gr*Math.cos(a),gy+gr*Math.sin(a)); ctx.rotate(a);
      ctx.fillStyle='rgba(140,170,215,'+al+')'; ctx.fillRect(-11,-19,22,38);
      ctx.restore();
    }
  }
  const wood=ctx.createLinearGradient(0,130,0,200);
  wood.addColorStop(0,'#8a6c4a'); wood.addColorStop(1,'#4e3a28');
  ctx.shadowColor='rgba(150,185,235,0.55)'; ctx.shadowBlur=30; ctx.fillStyle=wood;
  ctx.fillRect(CTX-150,168,300,20); ctx.fillRect(CTX-10,112,20,118); ctx.fillRect(CTX-66,130,132,14);
  ctx.shadowBlur=12; ctx.strokeStyle='rgba(210,230,255,0.85)'; ctx.lineWidth=2.8;
  const xs=[-140,-70,70,140];
  for (let i=0;i<xs.length;i++){
    const x0=CTX+xs[i];
    ctx.beginPath(); ctx.moveTo(x0,188);
    if (i===2){
      ctx.quadraticCurveTo(x0+12,270,x0+4,356); ctx.stroke();
      ctx.beginPath(); ctx.arc(x0+10,376,14,-0.6,2.6); ctx.stroke();
    } else {
      ctx.quadraticCurveTo(x0+(i<2?16:-16),400,x0+(i<2?7:-7),596); ctx.stroke();
    }
  }
  ctx.restore();
},
paw: function(){
  ctx.save();
  for (const [dr,lw,al] of [[0,24,0.85],[7,9,0.35],[-8,7,0.3]]){
    ctx.strokeStyle='rgba(232,224,208,'+al+')'; ctx.lineWidth=lw; ctx.lineCap='round';
    ctx.beginPath(); ctx.arc(CTX,CTY,172+dr,-0.35,Math.PI*2-0.85); ctx.stroke();
  }
  ctx.shadowColor='rgba(224,80,56,0.7)'; ctx.shadowBlur=28; ctx.fillStyle='#d84a30';
  ctx.beginPath(); ctx.ellipse(CTX,CTY+52,52,44,0,0,Math.PI*2); ctx.fill();
  for (const [dx,dy,r] of [[-62,-28,21],[-24,-58,23],[24,-58,23],[62,-28,21]]){
    ctx.beginPath(); ctx.ellipse(CTX+dx,CTY+dy,r,r*1.25,dx/160,0,Math.PI*2); ctx.fill();
  }
  ctx.restore();
},
staff: function(){
  ctx.save(); ctx.translate(CTX,CTY); ctx.rotate(0.62);
  const rod=ctx.createLinearGradient(-10,0,10,0);
  rod.addColorStop(0,'#8a2018'); rod.addColorStop(0.5,'#c03428'); rod.addColorStop(1,'#701812');
  ctx.shadowColor='rgba(232,176,58,0.6)'; ctx.shadowBlur=30; ctx.fillStyle=rod;
  ctx.fillRect(-9,-230,18,460);
  const gold=ctx.createLinearGradient(-16,0,16,0);
  gold.addColorStop(0,'#ffe088'); gold.addColorStop(0.5,'#f0b83a'); gold.addColorStop(1,'#c8922a');
  ctx.fillStyle=gold;
  for (const y of [-268,224]) ctx.fillRect(-15,y,30,46);
  for (const y of [-176,138]) ctx.fillRect(-12,y,24,12);
  ctx.restore();
  ctx.save();
  ctx.shadowColor='rgba(255,214,100,0.8)'; ctx.shadowBlur=34;
  ctx.strokeStyle='#f5cd5e'; ctx.lineWidth=11;
  ctx.beginPath(); ctx.arc(CTX+118,CTY-168,62,0.25,Math.PI*2); ctx.stroke();
  ctx.beginPath(); ctx.arc(CTX+145,CTY-224,17,Math.PI,Math.PI*2.6); ctx.stroke();
  ctx.beginPath(); ctx.arc(CTX+178,CTY-208,13,Math.PI*1.1,Math.PI*2.8); ctx.stroke();
  ctx.restore();
},
hitodama: function(){
  ctx.save();
  ctx.strokeStyle='rgba(190,64,52,0.30)'; ctx.lineWidth=17;
  ctx.beginPath();
  ctx.moveTo(CTX-130,520); ctx.lineTo(CTX-118,240);
  ctx.moveTo(CTX+130,520); ctx.lineTo(CTX+118,240);
  ctx.stroke();
  ctx.lineWidth=20;
  ctx.beginPath(); ctx.moveTo(CTX-172,232); ctx.quadraticCurveTo(CTX,208,CTX+172,232); ctx.stroke();
  ctx.lineWidth=12;
  ctx.beginPath(); ctx.moveTo(CTX-138,286); ctx.lineTo(CTX+138,286); ctx.stroke();
  for (const [dx,dy,r] of [[-64,40,46],[86,-34,36],[6,128,30]]){
    const x=CTX+dx, y=CTY+dy;
    ctx.shadowColor='rgba(90,130,255,0.9)'; ctx.shadowBlur=46;
    const g=ctx.createRadialGradient(x,y,2,x,y,r);
    g.addColorStop(0,'#eef4ff'); g.addColorStop(0.4,'#7c98f8'); g.addColorStop(1,'rgba(60,80,220,0)');
    ctx.fillStyle=g;
    ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2); ctx.fill();
    ctx.beginPath();
    ctx.moveTo(x-r*0.4,y+4);
    ctx.quadraticCurveTo(x-r*1.7,y+r*1.3,x-r*2.4,y+r*0.6);
    ctx.quadraticCurveTo(x-r*1.4,y+r*0.9,x-r*0.2,y+r*0.5);
    ctx.closePath();
    ctx.fillStyle='rgba(110,140,250,0.5)'; ctx.fill();
  }
  ctx.restore();
},
cube: function(){
  ctx.save();
  const s=128, k=0.55, P=(dx,dy,dz)=>[CTX+(dx-dz)*0.87, CTY+30+(dx+dz)*k*0.5-dy];
  const V={}; let i=0;
  for (const dx of [-s,s]) for (const dy of [-s,s]) for (const dz of [-s,s]) V[i++]=P(dx,dy,dz);
  ctx.strokeStyle='rgba(216,203,176,0.92)'; ctx.lineWidth=3.4;
  ctx.shadowColor='rgba(216,203,176,0.4)'; ctx.shadowBlur=14;
  for (const [a,b] of [[0,1],[0,2],[0,4],[3,1],[3,2],[3,7],[5,1],[5,4],[5,7],[6,2],[6,4],[6,7]]){
    ctx.beginPath(); ctx.moveTo(V[a][0],V[a][1]); ctx.lineTo(V[b][0],V[b][1]); ctx.stroke();
  }
  ctx.shadowColor='rgba(230,60,60,0.95)'; ctx.shadowBlur=44;
  const g=ctx.createRadialGradient(CTX,CTY+30,4,CTX,CTY+30,46);
  g.addColorStop(0,'#ffb0a0'); g.addColorStop(0.5,'#e04040'); g.addColorStop(1,'#701414');
  ctx.fillStyle=g; ctx.fillRect(CTX-34,CTY-4,68,68);
  ctx.shadowBlur=8; ctx.fillStyle='rgba(216,203,176,0.7)';
  const rnd=mulberry32(42);
  for (let j=0;j<8;j++) ctx.fillRect(CTX-240+rnd()*480,CTY-220+rnd()*440,3+rnd()*14,3);
  ctx.restore();
},
trophy: function(){
  // il ripiego per un gioco senza design suo: una coppa, onesta e leggibile
  ctx.save();
  ctx.shadowColor='rgba(240,200,90,0.8)'; ctx.shadowBlur=45;
  const g=ctx.createLinearGradient(CTX-120,CTY+140,CTX+120,CTY-140);
  g.addColorStop(0,'#d1952b'); g.addColorStop(0.5,'#f2b93f'); g.addColorStop(1,'#ffdf82');
  ctx.fillStyle=g; ctx.strokeStyle=g;
  ctx.beginPath();
  ctx.moveTo(CTX-110,CTY-140);
  ctx.bezierCurveTo(CTX-110,CTY+10,CTX-40,CTY+60,CTX,CTY+60);
  ctx.bezierCurveTo(CTX+40,CTY+60,CTX+110,CTY+10,CTX+110,CTY-140);
  ctx.closePath(); ctx.fill();
  ctx.lineWidth=13;
  ctx.beginPath(); ctx.arc(CTX-128,CTY-80,44,Math.PI*0.5,Math.PI*1.6); ctx.stroke();
  ctx.beginPath(); ctx.arc(CTX+128,CTY-80,44,Math.PI*1.4,Math.PI*0.5); ctx.stroke();
  ctx.fillRect(CTX-14,CTY+60,28,72);
  ctx.fillRect(CTX-72,CTY+132,144,22);
  ctx.restore();
}
};
"""

THUMB_PAGE_JS += r"""
function render(){
  const slotRaw = document.getElementById('thSlot').value.trim().toUpperCase();
  const slot = slotRaw || 'TUTTI I TROFEI';
  const ep = document.getElementById('thEp').value.trim();
  ctx.clearRect(0,0,W,H);
  drawBg(CFG.glow, CFG.seed);
  (ICONS[CFG.icon] || ICONS.trophy)();
  drawText(CFG.game, slot, ep, CFG.stats, CFG.tag);
  return {slot: slot, ep: ep};
}

function download(){
  const cur = render();
  cv.toBlob(function(blob){
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = CFG.file + (cur.ep ? '-ep' + cur.ep : '') + '.jpg';
    a.click();
    setTimeout(function(){ URL.revokeObjectURL(a.href); }, 4000);
  }, 'image/jpeg', 0.9);
}

document.getElementById('thSlot').addEventListener('input', render);
document.getElementById('thEp').addEventListener('input', render);
document.getElementById('thDl').addEventListener('click', download);
render();
"""


def render_thumb(run_id):
    lg = lang()
    t = T[lg]
    d = ROUTES[run_id]
    design = thumb_design(d)
    cfg = {
        "game": str(d["game"]).upper(),
        "stats": [[str(d.get("trophy_total") or "?"), "TROFEI"]] + design["stats"],
        "tag": design["tag"] or THUMB_TAG_DEFAULT,
        "glow": design["glow"],
        "seed": design["seed"],
        "icon": design["icon"],
        "file": "thumb-%s-platino" % run_id,
    }
    p = [page_head(lg, d["game"], run_id, "thumb", t["th_title"])]
    p.append(f'<h2 style="font-size:.85em;color:var(--gold);letter-spacing:2px;margin:24px 0 4px;'
             f'text-transform:uppercase;font-weight:500">🖼 {t["th_sub"]}</h2>')
    p.append('<div class="epcard"><div class="b">')
    p.append('<canvas id="thumbCanvas" width="1280" height="720" '
             'style="width:100%;max-width:820px;display:block;border:1px solid var(--line);'
             'border-radius:8px;margin-bottom:12px"></canvas>')
    p.append(f'<div class="setrow"><span>{t["th_var"]}</span>'
             f'<input type="text" id="thSlot" maxlength="26" style="min-width:340px" '
             f'placeholder="{esc(t["th_var_ph"])}"></div>')
    p.append(f'<div class="setrow"><span>{t["th_ep"]}</span>'
             f'<input type="number" id="thEp" min="1" max="999" style="width:90px">'
             f'<button id="thDl">💾 {t["th_dl"]}</button></div>')
    p.append(f'<div class="setrow" style="max-width:680px;color:var(--muted)">{t["th_note"]}</div>')
    p.append('</div></div>')
    p.append(f'<footer>{t["footer_run"]}</footer></div>')
    cfg_js = json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")
    p.append("<script>var CFG = %s;\n%s\n%s</script></body></html>"
             % (cfg_js, THUMB_ART_JS, THUMB_PAGE_JS))
    return "\n".join(p)
