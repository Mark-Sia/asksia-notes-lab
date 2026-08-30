#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AskSia × Apple Notes — growth-hack MVP builder.
python3 build.py            → docs/ (static site: library page + one note page per course + card PNG + QR)
python3 build.py --no-shots → skip Playwright card rendering (fast HTML-only rebuild)
"""
import base64, io, json, os, shutil, sys, html as H
from pathlib import Path
import qrcode, qrcode.image.svg
from content import NOTES, SITE

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs"
ASSETS = ROOT / "assets"
TODAY = "30 Aug 2026"
GRAD = "linear-gradient(100deg,#ff8a6b,#b06ff0 40%,#6d6ff5 72%,#4ea8ff)"

TONES = {  # bg, border, heading colour
    "yellow": ("#FFF8DF", "#F1E2A7", "#7A5A00"),
    "gray":   ("#F4F4F6", "#E3E3E8", "#333"),
    "green":  ("#EDF8EE", "#C5E6CA", "#1F6B32"),
    "purple": ("#F5EFFF", "#DCCBF7", "#5B2FA8"),
    "red":    ("#FFF4F2", "#F3C9C2", "#9E2A1E"),
    "rose":   ("#FFF0F3", "#F3C4CF", "#A31F44"),
    "blue":   ("#EEF4FF", "#C6D8F8", "#1C4FA3"),
}

def e(s): return H.escape(str(s), quote=True)

def b64file(p: Path, mime=None):
    mime = mime or ("image/png" if p.suffix == ".png" else "image/jpeg")
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()

# ───────────────────────────────────────────── QR
def qr_svg(url):
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=12, border=2,
                      error_correction=qrcode.constants.ERROR_CORRECT_M)
    buf = io.BytesIO(); img.save(buf); return buf.getvalue().decode()

def qr_png_datauri(url):
    q = qrcode.QRCode(box_size=10, border=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(url); q.make(fit=True)
    im = q.make_image(fill_color="#1b1b3a", back_color="white").convert("RGB")
    buf = io.BytesIO(); im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

# ───────────────────────────────────────────── share payloads
def note_url(n): return f"{SITE}/n/{n['id']}/"

def plain_text(n):
    L = [f"{n['emoji']} {n['title']}", n["subtitle"], "", n["hero_line"], n["hero_line_zh"], ""]
    for s in n["sections"]:
        L.append(f"{s['emoji']} {s['title'].upper()}")
        k = s["kind"]
        if k in ("facts", "formulas"):
            L += [f"• {a}: {b}" for a, b in s["items"]]
        elif k == "tree":
            L += [f"• {a} → {b}" for a, b in s["steps"]]
        elif k == "terms":
            L += [f"• {a}（{zh}）— {g}" for a, zh, g in s["items"]]
        elif k == "traps":
            L += [f"{i}. {t}" for i, t in enumerate(s["items"], 1)]
        elif k == "ritual":
            L += [f"{i}. {t}" for i, t in enumerate(s["steps"], 1)]
        elif k == "table":
            L += [f"• {r[0]} — {r[1]} — {r[2]}" for r in s["rows"]]
            if s.get("foot"): L.append(f"→ {s['foot']}")
        L.append("")
    L.append(f"✎ {n['handwriting']}")
    L.append("")
    L.append(f"Source: {n['source_name']} · {n['source_pages']} pages · {n['source_url']}")
    L.append(f"This note: {note_url(n)}")
    L.append("Made with AskSia — your personal college study AI copilot")
    return "\n".join(L)

def rich_html(n):
    P = [f"<h1>{n['emoji']} {e(n['title'])}</h1>", f"<p><i>{e(n['subtitle'])}</i></p>",
         f"<p>{e(n['hero_line'])}<br>{e(n['hero_line_zh'])}</p>"]
    for s in n["sections"]:
        P.append(f"<h2>{s['emoji']} {e(s['title'])}</h2>")
        k = s["kind"]
        if k in ("facts", "formulas"):
            P.append("<ul>" + "".join(f"<li><b>{e(a)}:</b> {e(b)}</li>" for a, b in s["items"]) + "</ul>")
        elif k == "tree":
            P.append("<table border='1'><tr><th>Situation</th><th>Use</th></tr>" +
                     "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td></tr>" for a, b in s["steps"]) + "</table>")
        elif k == "terms":
            P.append("<table border='1'><tr><th>Term</th><th>中文</th><th>Meaning</th></tr>" +
                     "".join(f"<tr><td><b>{e(a)}</b></td><td>{e(z)}</td><td>{e(g)}</td></tr>" for a, z, g in s["items"]) + "</table>")
        elif k == "traps":
            P.append("<ol>" + "".join(f"<li>{e(t)}</li>" for t in s["items"]) + "</ol>")
        elif k == "ritual":
            P.append("<ol>" + "".join(f"<li>{e(t)}</li>" for t in s["steps"]) + "</ol>")
        elif k == "table":
            h = s["head"]
            P.append(f"<table border='1'><tr><th>{e(h[0])}</th><th>{e(h[1])}</th><th>{e(h[2])}</th></tr>" +
                     "".join(f"<tr><td><b>{e(r[0])}</b></td><td>{e(r[1])}</td><td>{e(r[2])}</td></tr>" for r in s["rows"]) + "</table>")
            if s.get("foot"): P.append(f"<p>→ {e(s['foot'])}</p>")
    P.append(f"<p><i>✎ {e(n['handwriting'])}</i></p>")
    P.append(f"<p>Source: <a href='{n['source_url']}'>{e(n['source_name'])}</a> · {n['source_pages']} pages<br>"
             f"This note: <a href='{note_url(n)}'>{note_url(n)}</a><br>Made with AskSia</p>")
    return "".join(P)

# ───────────────────────────────────────────── shared CSS (note look)
NOTE_CSS = """
:root{--yellow:#D9A400;--ink:#111;--ink2:#444;--ink3:#8a8a8e;--grad:__GRAD__;}
*{box-sizing:border-box}
body{margin:0;background:#f2f2f4;color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Helvetica Neue",Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
.notes{max-width:760px;margin:0 auto;background:#fff;min-height:100vh;padding:0 20px 140px;position:relative}
.nbar{display:flex;justify-content:space-between;align-items:center;height:52px;font-size:17px;color:var(--yellow);font-weight:500;border-bottom:1px solid #eee;position:sticky;top:0;background:rgba(255,255,255,.92);backdrop-filter:blur(10px);z-index:5;margin:0 -20px;padding:0 20px}
.nbar .back{font-weight:400}.nbar .back b{font-size:22px;font-weight:400;margin-right:2px;position:relative;top:1px}
.nbar .done{font-weight:600}
.date{text-align:center;color:var(--ink3);font-size:12px;margin:14px 0 8px}
h1.t{font-size:28px;line-height:1.2;margin:0 0 8px;font-weight:800;letter-spacing:-.4px}
h1.t .g{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:var(--ink2);font-size:14px;margin:0 0 12px}
.hero{font-size:15px;line-height:1.5;margin:0 0 4px}.hero.zh{color:var(--ink2);font-size:13.5px;margin-bottom:12px}
.stats{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px}
.stats span{background:#f4f4f6;border:1px solid #e6e6ea;border-radius:999px;padding:5px 11px;font-size:12.5px;color:#333}
.stats span b{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;font-size:14px;margin-right:4px}
.card{border-radius:14px;border:1px solid;padding:14px 16px;margin:0 0 14px}
.card h2{margin:0 0 10px;font-size:16.5px;font-weight:700;display:flex;gap:8px;align-items:center}
.card h2 .zh{font-weight:500;color:var(--ink3);font-size:13px;margin-left:auto}
.kv{margin:0;padding:0;list-style:none}.kv li{display:flex;gap:10px;padding:5px 0;border-top:1px dashed rgba(0,0,0,.08);font-size:14px;line-height:1.45}
.kv li:first-child{border-top:0}.kv li .k{flex:0 0 38%;font-weight:600}.kv li .v{flex:1;color:#222}
.hl{background:#FFF1A8;padding:0 4px;border-radius:3px}.hlg{background:#CDEFD6;padding:0 4px;border-radius:3px}.hlp{background:#F3D7FF;padding:0 4px;border-radius:3px}
.fbox{background:#fff;border:1px solid #F0CFC8;border-radius:9px;padding:8px 11px;margin:6px 0;font-family:"Iowan Old Style","Palatino","Times New Roman",serif;font-size:15px;color:#1b1b1b}
.fbox small{display:block;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC",sans-serif;font-size:11.5px;color:#9E2A1E;font-weight:600;letter-spacing:.2px;margin-bottom:2px}
.tree{margin:0;padding:0;list-style:none}.tree li{display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:center;padding:6px 0;border-top:1px dashed rgba(0,0,0,.08);font-size:13.5px}
.tree li:first-child{border-top:0}.tree li .a{font-weight:600}.tree li .arr{color:#6d6ff5;font-weight:700}.tree li .b{font-family:"Iowan Old Style","Palatino",serif;background:#fff;border-radius:7px;padding:5px 8px;border:1px solid #d6e1f7}
table.tb{width:100%;border-collapse:collapse;font-size:13.5px;background:#fff;border-radius:9px;overflow:hidden}
table.tb th{text-align:left;background:#f1f1f4;padding:7px 9px;font-size:12px;color:#555}table.tb td{padding:7px 9px;border-top:1px solid #ececf0;vertical-align:top}
table.tb td.zh{color:#5B2FA8;white-space:nowrap}
ol.traps{margin:0;padding-left:22px}ol.traps li{padding:4px 0;font-size:14px;line-height:1.45}ol.traps li::marker{font-weight:700;color:#A31F44}
ol.steps{margin:0;padding-left:0;list-style:none;counter-reset:s}ol.steps li{counter-increment:s;display:flex;gap:10px;padding:5px 0;font-size:14px;line-height:1.45}
ol.steps li::before{content:counter(s);flex:0 0 22px;height:22px;border-radius:50%;background:#1F6B32;color:#fff;font-weight:700;font-size:12px;display:flex;align-items:center;justify-content:center;margin-top:1px}
.hand{font-family:"Noteworthy","Bradley Hand","Marker Felt","Segoe Print","Comic Sans MS",cursive;color:#D8261C;font-size:19px;line-height:1.35;margin:6px 0 18px;transform:rotate(-1deg)}
.visual{border-radius:12px;overflow:hidden;border:1px solid #e6e6ea;margin:0 0 6px}.visual img{display:block;width:100%}
.cap{font-size:12px;color:var(--ink3);margin:0 0 16px}
.source{font-size:12.5px;color:var(--ink3);border-top:1px solid #eee;padding-top:12px;margin-top:6px}.source a{color:#6d6ff5;text-decoration:none}
.pfoot{position:absolute;left:0;right:0;bottom:92px;text-align:center;color:var(--ink3);font-size:12px}
.cta{position:fixed;left:0;right:0;bottom:0;background:rgba(255,255,255,.94);backdrop-filter:blur(14px);border-top:1px solid #e9e9ee;padding:10px 16px calc(10px + env(safe-area-inset-bottom));z-index:9}
.cta .in{max-width:720px;margin:0 auto;display:flex;flex-direction:column;gap:7px;align-items:center}
.btn{width:100%;max-width:520px;border:0;border-radius:14px;padding:15px 18px;font-size:17px;font-weight:700;color:#fff;background:#111;display:flex;align-items:center;justify-content:center;gap:9px;cursor:pointer;box-shadow:0 6px 18px rgba(0,0,0,.18)}
.btn:active{transform:scale(.985)}.btn .nicon{width:24px;height:24px}
.alt{font-size:13px;color:#555}.alt a{color:#6d6ff5;text-decoration:none;font-weight:600;margin:0 5px;cursor:pointer}
.toast{position:fixed;left:50%;bottom:120px;transform:translateX(-50%);background:#111;color:#fff;padding:10px 16px;border-radius:12px;font-size:14px;opacity:0;transition:.25s;pointer-events:none;z-index:20;max-width:90vw;text-align:center}
.toast.on{opacity:1}
.aside{display:none}
@media(min-width:1040px){body{background:#ebebef}.wrap{display:grid;grid-template-columns:760px 300px;gap:24px;justify-content:center;padding:28px 0}
.notes{margin:0;border-radius:24px;min-height:auto;box-shadow:0 20px 60px rgba(0,0,0,.12);padding-bottom:40px}.pfoot{position:static;margin-top:20px}.cta{position:sticky;bottom:0;border-radius:0 0 24px 24px;margin:0 -20px -40px}
.aside{display:block;position:sticky;top:28px;align-self:start}.aside .box{background:#fff;border-radius:20px;padding:20px;box-shadow:0 12px 40px rgba(0,0,0,.08)}
.aside h3{margin:0 0 6px;font-size:16px}.aside p{font-size:13px;color:#555;margin:0 0 12px;line-height:1.5}.aside svg{width:100%;height:auto;border-radius:10px;border:1px solid #eee}
.aside .u{font-size:11.5px;color:#888;word-break:break-all;margin-top:8px}}
""".replace("__GRAD__", GRAD)

# ───────────────────────────────────────────── section renderers (note page + card share the same markup)
def render_section(s):
    bg, bd, hc = TONES[s["tone"]]
    k = s["kind"]
    parts = [f'<section class="card" style="background:{bg};border-color:{bd}"><h2 style="color:{hc}"><span>{s["emoji"]}</span>{e(s["title"])}</h2>']
    if k == "facts":
        parts.append('<ul class="kv">' + "".join(f'<li><span class="k">{e(a)}</span><span class="v">{e(b)}</span></li>' for a, b in s["items"]) + "</ul>")
    elif k == "formulas":
        parts.append('<div class="fgrid">' + "".join(f'<div class="fbox"><small>{e(a)}</small>{e(b)}</div>' for a, b in s["items"]) + "</div>")
    elif k == "tree":
        parts.append('<ul class="tree">' + "".join(f'<li><span class="a">{e(a)}</span><span class="arr">→</span><span class="b">{e(b)}</span></li>' for a, b in s["steps"]) + "</ul>")
    elif k == "terms":
        parts.append('<table class="tb"><tr><th>Term</th><th>中文</th><th>Meaning</th></tr>' +
                     "".join(f'<tr><td><b>{e(a)}</b></td><td class="zh">{e(z)}</td><td>{e(g)}</td></tr>' for a, z, g in s["items"]) + "</table>")
    elif k == "traps":
        parts.append('<ol class="traps">' + "".join(f"<li>{e(t)}</li>" for t in s["items"]) + "</ol>")
    elif k == "ritual":
        parts.append('<ol class="steps">' + "".join(f"<li><span>{e(t)}</span></li>" for t in s["steps"]) + "</ol>")
    elif k == "table":
        h = s["head"]
        parts.append(f'<table class="tb"><tr><th>{e(h[0])}</th><th>{e(h[1])}</th><th>{e(h[2])}</th></tr>' +
                     "".join(f'<tr><td><b>{e(r[0])}</b></td><td>{e(r[1])}</td><td>{e(r[2])}</td></tr>' for r in s["rows"]) + "</table>")
        if s.get("foot"): parts.append(f'<p style="margin:10px 0 0;font-size:13.5px;font-weight:600;color:{hc}">→ {e(s["foot"])}</p>')
    parts.append("</section>")
    return "".join(parts)

def stats_html(n):
    return '<div class="stats">' + "".join(f"<span><b>{e(a)}</b>{e(b)}</span>" for a, b in n["stats"]) + "</div>"

# ───────────────────────────────────────────── NOTE PAGE
def note_page(n, qr):
    url = note_url(n)
    images = ["card.png"] + ([n["visual"]] if n.get("visual") else [])
    payload = json.dumps(dict(title=f"{n['emoji']} {n['title']}", text=plain_text(n), html=rich_html(n), images=images, id=n["id"]), ensure_ascii=False)
    visual = ""
    if n.get("visual"):
        visual = f'<div class="visual"><img src="{n["visual"]}" alt="Sia visual"></div><p class="cap">🦭 {e(n["visual_caption"])}</p>'
    body = "".join(render_section(s) for s in n["sections"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(n['title'])} · AskSia Note</title>
<meta property="og:title" content="{e(n['title'])}"><meta property="og:description" content="{e(n['hero_line'])}"><meta property="og:image" content="{url}card.png">
<link rel="icon" href="data:,">
<style>{NOTE_CSS}
.fgrid{{display:grid;grid-template-columns:1fr;gap:0}}@media(min-width:560px){{.fgrid{{grid-template-columns:1fr 1fr;gap:0 10px}}}}
</style></head><body>
<div class="wrap">
<main class="notes">
  <div class="nbar"><span class="back"><b>‹</b> Notes</span><span class="done">Done</span></div>
  <div class="date">{TODAY} · AskSia · {e(n['code'])}</div>
  <h1 class="t">{n['emoji']} {e(n['title'])}</h1>
  <p class="sub">{e(n['subtitle'])}</p>
  <p class="hero">{e(n['hero_line'])}</p><p class="hero zh">{e(n['hero_line_zh'])}</p>
  {stats_html(n)}
  {visual}
  {body}
  <p class="hand">✎ {e(n['handwriting'])}</p>
  <p class="source">Source: <a href="{n['source_url']}">{e(n['source_name'])}</a> · {n['source_pages']} pages · {n['source_chapters']} chapters → compressed into this one note by AskSia.<br>Note link: <a href="{url}">{url.replace('https://','')}</a></p>
  <div class="pfoot">P1 / 1 · AskSia Note</div>
  <div class="cta"><div class="in">
    <button class="btn" id="add"><svg class="nicon" viewBox="0 0 40 40" width="22" height="22" aria-hidden="true"><rect x="2" y="2" width="36" height="36" rx="9" fill="#fff" stroke="#d9d9de"/><path d="M2 11 A9 9 0 0 1 11 2 H29 A9 9 0 0 1 38 11 V12 H2 Z" fill="#F5C542"/><rect x="9" y="18" width="22" height="2.4" rx="1.2" fill="#9a9aa2"/><rect x="9" y="24" width="22" height="2.4" rx="1.2" fill="#9a9aa2"/><rect x="9" y="30" width="14" height="2.4" rx="1.2" fill="#9a9aa2"/></svg> Add to Apple Notes</button>
    <div class="alt"><a id="copyrich">Copy as rich text</a>·<a id="sharetext">Share text only</a>·<a id="saveimg" href="card.png" download="{n['id']}-asksia-note.png">Save image</a></div>
  </div></div>
</main>
<aside class="aside"><div class="box"><h3>📱 Send to your iPhone</h3><p>Scan with the Camera app → Safari opens this note → tap <b>Add to Apple Notes</b>.</p>{qr}<div class="u">{url}</div></div></aside>
</div>
<div class="toast" id="toast"></div>
<script>
const NOTE={payload};
const $=s=>document.querySelector(s);
const isIOS=/iPhone|iPad|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
function track(k){{try{{const d=JSON.parse(localStorage.getItem('asksia_notes_exp')||'{{}}');d[k]=(d[k]||0)+1;d['_last']=new Date().toISOString();localStorage.setItem('asksia_notes_exp',JSON.stringify(d));}}catch(e){{}}}}
let T;function toast(m,ms=2600){{const t=$('#toast');t.textContent=m;t.classList.add('on');clearTimeout(T);T=setTimeout(()=>t.classList.remove('on'),ms);}}
// prefetch images so the share call stays inside the tap gesture
const files=[];
(async()=>{{for(const u of NOTE.images){{try{{const r=await fetch(u);const b=await r.blob();files.push(new File([b],u,{{type:b.type||'image/png'}}));}}catch(err){{}}}}}})();
async function copyRich(){{
  try{{
    if(navigator.clipboard&&window.ClipboardItem){{
      await navigator.clipboard.write([new ClipboardItem({{'text/html':new Blob([NOTE.html],{{type:'text/html'}}),'text/plain':new Blob([NOTE.text],{{type:'text/plain'}})}})]);
    }}else{{await navigator.clipboard.writeText(NOTE.text);}}
    track('copy_rich');toast('Copied ✓  Open Notes → new note → Paste',3800);
  }}catch(err){{try{{await navigator.clipboard.writeText(NOTE.text);toast('Copied as text ✓ — paste into Notes',3200);}}catch(e2){{toast('Copy blocked — long-press the text to copy');}}}}
}}
async function share(withFiles){{
  const data={{title:NOTE.title,text:NOTE.text}};
  if(withFiles&&files.length&&navigator.canShare&&navigator.canShare({{files}}))data.files=files;
  if(!navigator.share){{await copyRich();return;}}
  try{{await navigator.share(data);track(withFiles?'notes_shared':'notes_shared_text');toast('Pick “Notes” in the sheet → Save ✓',3600);}}
  catch(err){{if(err&&err.name==='AbortError'){{track('share_cancel');return;}}
    if(withFiles&&data.files){{delete data.files;try{{await navigator.share(data);track('notes_shared_text');toast('Shared as text ✓');return;}}catch(e2){{}}}}
    await copyRich();}}
}}
$('#add').addEventListener('click',()=>{{track('notes_cta');share(true);}});
$('#sharetext').addEventListener('click',()=>{{track('notes_cta_text');share(false);}});
$('#copyrich').addEventListener('click',copyRich);
$('#saveimg').addEventListener('click',()=>track('save_image'));
track(isIOS?'note_open_ios':'note_open_other');
if(new URLSearchParams(location.search).get('src')==='qr')track('qr_scan');
</script></body></html>"""

# ───────────────────────────────────────────── CARD (shareable image)
def card_html(n, qr_png):
    logo = b64file(ASSETS / "logo.png"); sia = b64file(ASSETS / "sia.png")
    body = "".join(render_section(s) for s in n["sections"])
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{NOTE_CSS}
body{{background:#fff;width:1080px}}
.cardwrap{{width:1080px;padding:0;background:#fff}}
.top{{height:14px;background:{GRAD}}}
.head{{display:flex;align-items:center;justify-content:space-between;padding:26px 44px 0}}
.head img.logo{{height:46px}}.head .eyebrow{{font-size:15px;letter-spacing:2.4px;color:#6d6ff5;font-weight:700;text-transform:uppercase}}
.inner{{padding:14px 44px 34px}}
h1.t{{font-size:46px}}.sub{{font-size:20px}}.hero{{font-size:21px}}.hero.zh{{font-size:18px}}
.stats span{{font-size:17px;padding:8px 16px}}.stats span b{{font-size:20px}}
.card{{padding:20px 24px;margin-bottom:18px;border-radius:18px}}.card h2{{font-size:24px}}
.kv li{{font-size:19px}}.fbox{{font-size:21px;padding:10px 14px}}.fbox small{{font-size:14px}}.fgrid{{display:grid;grid-template-columns:1fr 1fr;gap:0 14px}}
.tree li{{font-size:18.5px}}table.tb{{font-size:18px}}table.tb th{{font-size:15px}}ol.traps li{{font-size:19px}}ol.steps li{{font-size:19px}}ol.steps li::before{{flex-basis:28px;height:28px;font-size:15px}}
.hand{{font-size:30px;margin:10px 0 22px}}
.foot{{display:flex;align-items:center;gap:22px;border-top:2px solid #eee;padding-top:22px;margin-top:6px}}
.foot img.qr{{width:132px;height:132px;border-radius:12px;border:1px solid #e6e6ea}}
.foot .s{{flex:1;font-size:16px;color:#555;line-height:1.5}}.foot .s b{{color:#111}}.foot .s .u{{color:#6d6ff5;font-weight:600}}
.foot img.sia{{width:86px}}
.date{{font-size:15px;margin:10px 0 6px}}
</style></head><body><div class="cardwrap" id="card">
<div class="top"></div>
<div class="head"><img class="logo" src="{logo}"><span class="eyebrow">The complete exam bible → 1 note</span></div>
<div class="inner">
<div class="date">{TODAY} · AskSia Note · {e(n['code'])}</div>
<h1 class="t">{n['emoji']} {e(n['title'])}</h1>
<p class="sub">{e(n['subtitle'])}</p>
<p class="hero">{e(n['hero_line'])}</p><p class="hero zh">{e(n['hero_line_zh'])}</p>
{stats_html(n)}
{body}
<p class="hand">✎ {e(n['handwriting'])}</p>
<div class="foot"><img class="qr" src="{qr_png}"><div class="s"><b>Scan → this note lands in your Apple Notes.</b><br>Source: {e(n['source_name'])} · {n['source_pages']} pages · {n['source_chapters']} chapters<br><span class="u">{note_url(n).replace('https://','')}</span></div><img class="sia" src="{sia}"></div>
</div></div></body></html>"""

def render_cards(jobs):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1080, "height": 1200}, device_scale_factor=2)
        pg = ctx.new_page()
        for html_path, png_path in jobs:
            pg.goto(html_path.as_uri()); pg.wait_for_timeout(300)
            pg.locator("#card").screenshot(path=str(png_path))
            print("  card →", png_path.name, f"{png_path.stat().st_size//1024} KB")
        b.close()

# ───────────────────────────────────────────── LIBRARY PAGE
def library_page(notes_meta):
    logo = "assets/logo.png"
    rows = []
    for n in notes_meta:
        rows.append(f"""
<article class="row" data-id="{n['id']}">
  <a class="thumb" href="n/{n['id']}/"><img src="n/{n['id']}/card.png" alt=""><span class="tag">PREVIEW</span></a>
  <div class="meta">
    <div class="crumb">{e(n['uni'])} · {e(n['term'])} · {e(n['discipline'])}</div>
    <h2>{e(n['code'])} <span class="g">{e(n['name'])}</span></h2>
    <p class="tag2">{e(n['source_name'])} · {n['source_pages']} pages · {n['source_chapters']} chapters</p>
    <p class="hero">{e(n['hero_line'])}</p>
    <div class="ctas">
      <a class="b pdf" href="{n['source_url']}" target="_blank" rel="noopener" data-track="pdf_click"><span>📄</span> Download PDF</a>
      <button class="b notes" data-open="{n['id']}" data-track="notes_click"><svg class="nicon" viewBox="0 0 40 40" width="22" height="22" aria-hidden="true"><rect x="2" y="2" width="36" height="36" rx="9" fill="#fff" stroke="#d9d9de"/><path d="M2 11 A9 9 0 0 1 11 2 H29 A9 9 0 0 1 38 11 V12 H2 Z" fill="#F5C542"/><rect x="9" y="18" width="22" height="2.4" rx="1.2" fill="#9a9aa2"/><rect x="9" y="24" width="22" height="2.4" rx="1.2" fill="#9a9aa2"/><rect x="9" y="30" width="14" height="2.4" rx="1.2" fill="#9a9aa2"/></svg> Add to Apple Notes <em>NEW</em></button>
    </div>
    <div class="fine">{'·'.join(f' {a} {b} ' for a,b in n['stats'])}</div>
  </div>
</article>""")
    modals = "".join(f"""
<div class="modal" id="m-{n['id']}"><div class="mbox">
  <button class="x" data-close>×</button>
  <div class="mhead"><svg class="nicon" viewBox="0 0 40 40" width="22" height="22" aria-hidden="true"><rect x="2" y="2" width="36" height="36" rx="9" fill="#fff" stroke="#d9d9de"/><path d="M2 11 A9 9 0 0 1 11 2 H29 A9 9 0 0 1 38 11 V12 H2 Z" fill="#F5C542"/><rect x="9" y="18" width="22" height="2.4" rx="1.2" fill="#9a9aa2"/><rect x="9" y="24" width="22" height="2.4" rx="1.2" fill="#9a9aa2"/><rect x="9" y="30" width="14" height="2.4" rx="1.2" fill="#9a9aa2"/></svg><div><b>Add {e(n['code'])} to Apple Notes</b><div class="msub">{e(n['name'])}</div></div></div>
  <div class="mgrid">
    <div class="qrcol">{n['qr_svg']}<div class="u">{n['url']}</div></div>
    <div class="how">
      <ol><li>Open the <b>Camera</b> app on your iPhone and point it here</li><li>Tap the link → the note opens in Safari (no login)</li><li>Tap <b> Add to Apple Notes</b> → choose <b>Notes</b> → Save</li></ol>
      <p class="get">You get: title · exam facts · formulas · bilingual key terms · exam traps · the structured card image{' · the visual Sia drew' if n.get('visual') else ''} — searchable and editable in your own Notes.</p>
      <a class="b ghost" href="n/{n['id']}/" target="_blank" rel="noopener">Open the note page ↗</a>
      <button class="b mac" data-macshare="{n['id']}" hidden><svg class="nicon" viewBox="0 0 40 40" width="22" height="22" aria-hidden="true"><rect x="2" y="2" width="36" height="36" rx="9" fill="#fff" stroke="#fff"/><path d="M2 11 A9 9 0 0 1 11 2 H29 A9 9 0 0 1 38 11 V12 H2 Z" fill="#F5C542"/><rect x="9" y="18" width="22" height="2.4" rx="1.2" fill="#9a9aa2"/><rect x="9" y="24" width="22" height="2.4" rx="1.2" fill="#9a9aa2"/><rect x="9" y="30" width="14" height="2.4" rx="1.2" fill="#9a9aa2"/></svg> Add from this Mac</button>
    </div>
  </div>
</div></div>""" for n in notes_meta)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AskSia Library · Add to Apple Notes (MVP)</title><link rel="icon" href="data:,">
<style>
:root{{--grad:{GRAD};--ink:#111;--ink2:#555;--line:#e7e7ec}}
*{{box-sizing:border-box}}body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Helvetica Neue",Arial,sans-serif;color:var(--ink);background:#fafafc;-webkit-font-smoothing:antialiased}}
.nav{{height:64px;display:flex;align-items:center;justify-content:space-between;padding:0 40px;background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}}
.nav img{{height:30px}}.nav .links{{display:flex;gap:26px;font-size:15px;color:#333}}.nav .links span.on{{background:#eef0ff;color:#4a4fd8;padding:8px 14px;border-radius:999px}}
.nav .right{{display:flex;gap:16px;align-items:center;font-size:14px}}.nav .dl{{background:#111;color:#fff;padding:10px 16px;border-radius:10px;font-weight:600}}
.crumbbar{{display:flex;justify-content:space-between;align-items:center;padding:12px 40px;font-size:14px;color:#666;background:#fff;border-bottom:1px solid var(--line)}}
.crumbbar .pill{{background:linear-gradient(100deg,#6d6ff5,#4ea8ff);color:#fff;padding:8px 16px;border-radius:999px;font-weight:600}}
.lab{{max-width:1180px;margin:22px auto 0;padding:0 24px}}
.banner{{background:#fff;border:1px solid var(--line);border-radius:18px;padding:18px 22px;display:grid;grid-template-columns:1.4fr 1fr;gap:22px;align-items:center}}
.banner h1{{margin:0 0 6px;font-size:24px;letter-spacing:-.3px}}.banner h1 .g{{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}}
.banner p{{margin:0;color:var(--ink2);font-size:14px;line-height:1.55}}
.exp{{background:#0f1020;color:#fff;border-radius:14px;padding:14px 16px;font-size:13px}}
.exp .t{{font-weight:700;margin-bottom:8px;display:flex;justify-content:space-between}}.exp .t small{{opacity:.6;font-weight:400}}
.nicon{{vertical-align:middle}}.mhead .nicon{{width:34px;height:34px}}.exp .bars{{display:grid;grid-template-columns:auto 1fr auto;gap:6px 10px;align-items:center}}.exp .bar{{height:8px;border-radius:99px;background:#2a2b45;overflow:hidden}}.exp .bar i{{display:block;height:100%;background:var(--grad)}}
.exp .bar.pdf i{{background:#8a8aa0}}.exp .n{{font-variant-numeric:tabular-nums;font-weight:700}}
.exp .ratio{{margin-top:8px;font-size:12px;opacity:.85}}.exp .ratio b{{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;font-size:16px}}
.exp .rs{{margin-top:8px;font-size:11px;opacity:.5;cursor:pointer}}
.list{{max-width:1180px;margin:18px auto 60px;padding:0 24px;display:flex;flex-direction:column;gap:16px}}
.row{{background:#fff;border:1px solid var(--line);border-radius:20px;padding:20px;display:grid;grid-template-columns:230px 1fr;gap:24px}}
.thumb{{display:block;position:relative;border-radius:14px;overflow:hidden;border:1px solid var(--line);aspect-ratio:3/4;background:#f2f2f5}}
.thumb img{{width:100%;display:block;object-fit:cover;object-position:top}}.thumb .tag{{position:absolute;top:10px;left:10px;background:#5b5fe8;color:#fff;font-size:10px;letter-spacing:1px;padding:4px 8px;border-radius:6px;font-weight:700}}
.meta .crumb{{font-size:11.5px;letter-spacing:1.6px;text-transform:uppercase;color:#6d6ff5;font-weight:700;margin-bottom:6px}}
.meta h2{{margin:0 0 4px;font-size:26px;letter-spacing:-.3px}}.meta h2 .g{{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;font-weight:700}}
.meta .tag2{{margin:0 0 8px;font-size:13px;color:#777}}.meta .hero{{margin:0 0 14px;font-size:15px;line-height:1.5;color:#222}}
.ctas{{display:flex;gap:12px;flex-wrap:wrap}}
.b{{display:inline-flex;align-items:center;gap:8px;border-radius:12px;padding:12px 18px;font-size:15px;font-weight:700;text-decoration:none;cursor:pointer;border:1px solid var(--line);background:#fff;color:#111;font-family:inherit}}
.b.pdf:hover{{background:#f6f6f9}}.b.notes{{background:#111;color:#fff;border-color:#111;position:relative}}.b.notes em{{font-style:normal;background:var(--grad);font-size:9px;letter-spacing:1px;padding:2px 6px;border-radius:5px;margin-left:4px}}
.b .ap{{font-size:17px}}.fine{{margin-top:12px;font-size:12.5px;color:#888}}
.modal{{position:fixed;inset:0;background:rgba(10,10,20,.55);display:none;align-items:center;justify-content:center;z-index:50;padding:20px}}.modal.on{{display:flex}}
.mbox{{background:#fff;border-radius:24px;width:min(760px,100%);padding:26px 28px;position:relative;box-shadow:0 30px 80px rgba(0,0,0,.3)}}
.x{{position:absolute;top:12px;right:16px;border:0;background:none;font-size:28px;cursor:pointer;color:#999}}
.mhead{{display:flex;gap:12px;align-items:center;margin-bottom:18px}}.mhead .ap{{font-size:30px}}.mhead b{{font-size:20px}}.msub{{font-size:13px;color:#777}}
.mgrid{{display:grid;grid-template-columns:260px 1fr;gap:26px;align-items:start}}
.qrcol svg{{width:100%;height:auto;border:1px solid var(--line);border-radius:14px;padding:6px}}.qrcol .u{{font-size:11px;color:#888;word-break:break-all;margin-top:8px;text-align:center}}
.how ol{{margin:0 0 12px;padding-left:20px;font-size:15px;line-height:1.7}}.how .get{{font-size:13px;color:#555;line-height:1.55;background:#f6f6fa;border-radius:12px;padding:12px}}
.b.ghost{{background:#fff;margin-top:10px}}.b.mac{{background:#111;color:#fff;margin:10px 0 0 8px}}
@media(max-width:820px){{.nav .links{{display:none}}.banner,.row,.mgrid{{grid-template-columns:1fr}}.thumb{{max-width:260px}}}}
</style></head><body>
<div class="nav"><img src="{logo}" alt="AskSia"><div class="links"><span class="on">For Students ⌄</span><span>Useful Tools ⌄</span><span>Resources ⌄</span><span>Pricing</span></div><div class="right"><span>Log in</span><span class="dl">Download App →</span></div></div>
<div class="crumbbar"><span>Library / <b>Exam Bibles</b> / Add to Apple Notes</span><span class="pill">Get A+ · $0.99 Trial</span></div>
<div class="lab"><div class="banner">
  <div><h1>Every Bible, one tap into <span class="g">your Apple Notes</span></h1>
  <p><b>Internal MVP · 2026-08-30 · Kai.</b> The bible stays where it is. This adds a second exit next to “Download PDF”: a structured cheat-note (facts · formulas · bilingual terms · traps · the card image · Sia's visual) that lands in the student's own Notes app — searchable, editable, offline.<br><b>How to test:</b> click <b> Add to Apple Notes</b> → scan the QR with your iPhone → tap the button on the note page → choose <b>Notes</b>. On a Mac with Safari the “Add from this Mac” button shares straight into macOS Notes.</p></div>
  <div class="exp"><div class="t">Experiment: Notes CTR vs PDF CTR <small>this browser only</small></div>
    <div class="bars"><span>📝 Notes</span><div class="bar"><i id="b1" style="width:0"></i></div><span class="n" id="n1">0</span>
    <span>📄 PDF</span><div class="bar pdf"><i id="b2" style="width:0"></i></div><span class="n" id="n2">0</span></div>
    <div class="ratio">Notes ÷ PDF = <b id="ratio">—</b> &nbsp;·&nbsp; the hypothesis worth testing: ≥ 2×</div>
    <div class="rs" id="reset">reset counters</div></div>
</div></div>
<div class="list">{''.join(rows)}</div>
{modals}
<script>
const isIOS=/iPhone|iPad|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
const KEY='asksia_notes_exp';
function load(){{try{{return JSON.parse(localStorage.getItem(KEY)||'{{}}')}}catch(e){{return {{}}}}}}
function track(k){{const d=load();d[k]=(d[k]||0)+1;d._last=new Date().toISOString();try{{localStorage.setItem(KEY,JSON.stringify(d))}}catch(e){{}}paint();}}
function paint(){{const d=load();const a=d.notes_click||0,b=d.pdf_click||0,m=Math.max(a,b,1);
  document.getElementById('n1').textContent=a;document.getElementById('n2').textContent=b;
  document.getElementById('b1').style.width=(a/m*100)+'%';document.getElementById('b2').style.width=(b/m*100)+'%';
  document.getElementById('ratio').textContent=b?(a/b).toFixed(1)+'×':(a?'∞':'—');}}
document.getElementById('reset').onclick=()=>{{localStorage.removeItem(KEY);paint();}};
document.querySelectorAll('[data-track]').forEach(el=>el.addEventListener('click',()=>track(el.dataset.track)));
document.querySelectorAll('[data-open]').forEach(b=>b.addEventListener('click',()=>{{
  const id=b.dataset.open;
  if(isIOS){{location.href='n/'+id+'/';return;}}
  const m=document.getElementById('m-'+id);m.classList.add('on');
  const mac=m.querySelector('[data-macshare]');if(navigator.share)mac.hidden=false;}}));
document.querySelectorAll('[data-close]').forEach(x=>x.addEventListener('click',()=>x.closest('.modal').classList.remove('on')));
document.querySelectorAll('.modal').forEach(m=>m.addEventListener('click',ev=>{{if(ev.target===m)m.classList.remove('on')}}));
document.querySelectorAll('[data-macshare]').forEach(async b=>{{b.addEventListener('click',async()=>{{
  const id=b.dataset.macshare;track('mac_share');
  try{{const r=await fetch('n/'+id+'/note.json');const N=await r.json();
    let files=[];try{{const ir=await fetch('n/'+id+'/card.png');const bl=await ir.blob();files=[new File([bl],'card.png',{{type:'image/png'}})];}}catch(e){{}}
    const data={{title:N.title,text:N.text}};if(files.length&&navigator.canShare&&navigator.canShare({{files}}))data.files=files;
    await navigator.share(data);}}catch(e){{if(e.name!=='AbortError')alert('Share not available here — use the QR.');}}
}});}});
paint();
</script></body></html>"""

# ───────────────────────────────────────────── main
def main():
    shots = "--no-shots" not in sys.argv
    OUT.mkdir(exist_ok=True); (OUT / "assets").mkdir(exist_ok=True)
    for f in ("logo.png", "sia.png"): shutil.copy(ASSETS / f, OUT / "assets" / f)
    (OUT / ".nojekyll").write_text("")
    jobs, meta = [], []
    for n in NOTES:
        d = OUT / "n" / n["id"]; d.mkdir(parents=True, exist_ok=True)
        url = note_url(n) + "?src=qr"
        svg = qr_svg(url); (d / "qr.svg").write_text(svg)
        if n.get("visual"): shutil.copy(ASSETS / n["visual"], d / n["visual"])
        (d / "index.html").write_text(note_page(n, svg), encoding="utf-8")
        (d / "note.json").write_text(json.dumps(dict(title=f"{n['emoji']} {n['title']}", text=plain_text(n), html=rich_html(n)), ensure_ascii=False), encoding="utf-8")
        (d / "note.txt").write_text(plain_text(n), encoding="utf-8")
        ch = d / "_card.html"; ch.write_text(card_html(n, qr_png_datauri(url)), encoding="utf-8")
        jobs.append((ch, d / "card.png"))
        meta.append(dict(n, name=n["title"].replace(n["code"] + " ", "").replace(" Cheat-Note", "") if n["id"] != "sat-math" else "Math · Digital SAT", url=note_url(n), qr_svg=svg))
        print("note →", d / "index.html")
    if shots: render_cards(jobs)
    for ch, _ in jobs: ch.unlink(missing_ok=True)
    names = {"buss1020": "Quantitative Business Analysis", "sat-math": "Digital SAT · Math", "ecb1101": "Introductory Microeconomics"}
    for m in meta: m["name"] = names[m["id"]]
    (OUT / "index.html").write_text(library_page(meta), encoding="utf-8")
    print("library →", OUT / "index.html")

if __name__ == "__main__":
    main()
