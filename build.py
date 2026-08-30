#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AskSia × Apple Notes — growth-hack MVP builder (v2: one-tap via the AskSia Notes shortcut).
python3 build.py → docs/ (library page + note page + note.html payload + QR + hosted .shortcut)
Flow: Library → QR → iPhone note page → [Add to Apple Notes] → shortcuts://run-shortcut (AskSia Notes)
      → fetch note.html → rich text → Create Note → Notes opens. One-time: install the shortcut.
"""
import io, json, shutil, html as H
from pathlib import Path
import qrcode, qrcode.image.svg
from content import NOTES, SITE

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs"
ASSETS = ROOT / "assets"
TODAY = "30 Aug 2026"
GRAD = "linear-gradient(100deg,#ff8a6b,#b06ff0 40%,#6d6ff5 72%,#4ea8ff)"
SHORTCUT_NAME = "AskSia Notes"
SHORTCUT_FILE = "AskSia-Notes.shortcut"
FEATURED = ["ecb1101"]          # Mark 2026-08-30: 先就尝试一门 ECB

TONES = {"yellow": ("#FFF8DF", "#F1E2A7", "#7A5A00"), "green": ("#EDF8EE", "#C5E6CA", "#1F6B32"),
         "purple": ("#F5EFFF", "#DCCBF7", "#5B2FA8"), "red": ("#FFF4F2", "#F3C9C2", "#9E2A1E"),
         "rose": ("#FFF0F3", "#F3C4CF", "#A31F44"), "blue": ("#EEF4FF", "#C6D8F8", "#1C4FA3")}

def e(s): return H.escape(str(s), quote=True)
def note_url(n): return f"{SITE}/n/{n['id']}/"
def payload_url(n): return f"{SITE}/n/{n['id']}/note.json"
def visual_url(n): return f"{SITE}/n/{n['id']}/{n['visual']}" if n.get("visual") else None
def tags(n): return [f"#{n['code']}", f"#{n['uni_short']}", f"#{n['discipline'].replace(' ', '')}", "#ExamBible", f"#{n['term'].replace(' ', '')}"]

def qr_svg(url):
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=12, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    buf = io.BytesIO(); img.save(buf); return buf.getvalue().decode()

# ───────────────────────────── payload for Notes (HTML → rich text via the shortcut)
def notes_html(n):
    """Order Mark asked for: school · course · tags → AI visual → structured text. No h1 (the title is the note name)."""
    P = [f"<p><b>{e(n['uni'])}</b> · {e(n['code'])} {e(n['subtitle'].split(' · ')[0])} · {e(n['term'])}<br>{e(' '.join(tags(n)))}</p>"]
    if n.get("visual"): P.append(f'<p><img src="{visual_url(n)}" width="620" alt="Sia visual"></p><p><i>🦭 {e(n["visual_caption"])}</i></p>')
    for s in n["sections"]:
        P.append(f"<h2>{s['emoji']} {e(s['title'])}</h2>")
        k = s["kind"]
        if k in ("facts", "formulas"):
            P.append("<ul>" + "".join(f"<li><b>{e(a)}:</b> {e(b)}</li>" for a, b in s["items"]) + "</ul>")
        elif k == "tree":
            P.append("<ul>" + "".join(f"<li><b>{e(a)}</b> → {e(b)}</li>" for a, b in s["steps"]) + "</ul>")
        elif k == "terms":
            P.append("<ul>" + "".join(f"<li><b>{e(a)}</b>（{e(z)}）— {e(g)}</li>" for a, z, g in s["items"]) + "</ul>")
        elif k == "traps":
            P.append("<ol>" + "".join(f"<li>{e(t)}</li>" for t in s["items"]) + "</ol>")
        elif k == "ritual":
            P.append("<ol>" + "".join(f"<li>{e(t)}</li>" for t in s["steps"]) + "</ol>")
        elif k == "table":
            P.append("<ul>" + "".join(f"<li><b>{e(r[0])}</b> — {e(r[1])} — {e(r[2])}</li>" for r in s["rows"]) + "</ul>")
            if s.get("foot"): P.append(f"<p>→ {e(s['foot'])}</p>")
    P.append(f"<p><i>✎ {e(n['handwriting'])}</i></p>")
    P.append(f"<p>Source: <a href='{n['source_url']}'>{e(n['source_name'])}</a> · {n['source_pages']} pages · {n['source_chapters']} chapters → this note<br>"
             f"Note link: <a href='{note_url(n)}'>{note_url(n)}</a><br>Made with AskSia — your personal college study AI copilot</p>")
    return '<!doctype html><html><head><meta charset="utf-8"></head><body>' + "".join(P) + "</body></html>"


def notes_md(n):
    """Markdown payload for iOS 26 Notes import (Files → Share → Notes → Import): headings, bold, lists and
    links survive. Layout per Mark 2026-08-30: 学校 · 科名 · tag → AI 图 → 结构化编排（无 intro）.
    NB: the tag line must NOT start with '#' or Markdown reads it as a heading — hence the 🏷 prefix."""
    L = [f"# {n['emoji']} {n['code']} · {n['subtitle'].split(' · ')[0]}", "",
         f"**{n['uni']}** · {n['term']} · {n['discipline']}  ",
         "🏷 " + " ".join(tags(n)), ""]
    if n.get("visual"): L += [f"![Sia visual]({visual_url(n)})", "", f"*🦭 {n['visual_caption']}*", ""]
    for s in n["sections"]:
        L.append(f"## {s['emoji']} {s['title']}"); L.append(""); k = s["kind"]
        if k in ("facts", "formulas"): L += [f"- **{a}:** {b}" for a, b in s["items"]]
        elif k == "tree": L += [f"- **{a}** → {b}" for a, b in s["steps"]]
        elif k == "terms": L += [f"- **{a}**（{z}）— {g}" for a, z, g in s["items"]]
        elif k in ("traps", "ritual"): L += [f"{i}. {t}" for i, t in enumerate(s.get("items") or s.get("steps"), 1)]
        elif k == "table":
            L += [f"- **{r[0]}** — {r[1]} — {r[2]}" for r in s["rows"]]
            if s.get("foot"): L += ["", f"→ {s['foot']}"]
        L.append("")
    L += [f"*✎ {n['handwriting']}*", "", f"Source: [{n['source_name']}]({n['source_url']}) · {n['source_pages']} pages · {n['source_chapters']} chapters → this note  ",
          f"Note link: {note_url(n)}  ", "Made with AskSia — your personal college study AI copilot"]
    return "\n".join(L) + "\n"

def plain_text(n):
    L = [f"{n['emoji']} {n['title']}", f"{n['uni']} · {n['code']} · {n['term']}", " ".join(tags(n)), ""]
    for s in n["sections"]:
        L.append(f"{s['emoji']} {s['title'].upper()}"); k = s["kind"]
        if k in ("facts", "formulas"): L += [f"• {a}: {b}" for a, b in s["items"]]
        elif k == "tree": L += [f"• {a} → {b}" for a, b in s["steps"]]
        elif k == "terms": L += [f"• {a}（{z}）— {g}" for a, z, g in s["items"]]
        elif k in ("traps", "ritual"): L += [f"{i}. {t}" for i, t in enumerate(s.get("items") or s.get("steps"), 1)]
        elif k == "table":
            L += [f"• {r[0]} — {r[1]} — {r[2]}" for r in s["rows"]]
            if s.get("foot"): L.append(f"→ {s['foot']}")
        L.append("")
    L += [f"✎ {n['handwriting']}", "", f"Source: {n['source_name']} · {n['source_url']}", f"This note: {note_url(n)}", "Made with AskSia"]
    return "\n".join(L)

# ───────────────────────────── note page (mobile)
CSS = """
:root{--yellow:#D9A400;--ink:#111;--ink2:#444;--ink3:#8a8a8e;--grad:__GRAD__}
*{box-sizing:border-box}body{margin:0;background:#f2f2f4;color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Helvetica Neue",Arial,sans-serif;-webkit-font-smoothing:antialiased}
.notes{max-width:760px;margin:0 auto;background:#fff;min-height:100vh;padding:0 20px 150px;position:relative}
.nbar{display:flex;justify-content:space-between;align-items:center;height:52px;font-size:17px;color:var(--yellow);border-bottom:1px solid #eee;position:sticky;top:0;background:rgba(255,255,255,.92);backdrop-filter:blur(10px);z-index:5;margin:0 -20px;padding:0 20px}
.nbar .back b{font-size:22px;font-weight:400;margin-right:2px}.nbar .done{font-weight:600}
.date{text-align:center;color:var(--ink3);font-size:12px;margin:14px 0 10px}
.head{margin:0 0 12px}.head .uni{font-size:12px;letter-spacing:1.6px;text-transform:uppercase;color:#6d6ff5;font-weight:700}
.head h1{font-size:26px;line-height:1.2;margin:4px 0 6px;font-weight:800;letter-spacing:-.4px}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 14px}.tags span{background:#f1f1f5;border-radius:999px;padding:4px 10px;font-size:12.5px;color:#444}
.visual{border-radius:14px;overflow:hidden;border:1px solid #e6e6ea;margin:0 0 6px}.visual img{display:block;width:100%}.cap{font-size:12px;color:var(--ink3);margin:0 0 16px}
.card{border-radius:14px;border:1px solid;padding:14px 16px;margin:0 0 14px}.card h2{margin:0 0 10px;font-size:16.5px;font-weight:700;display:flex;gap:8px;align-items:center}
.kv{margin:0;padding:0;list-style:none}.kv li{display:flex;gap:10px;padding:5px 0;border-top:1px dashed rgba(0,0,0,.08);font-size:14px;line-height:1.45}.kv li:first-child{border-top:0}.kv li .k{flex:0 0 38%;font-weight:600}.kv li .v{flex:1}
.fbox{background:#fff;border:1px solid #F0CFC8;border-radius:9px;padding:8px 11px;margin:6px 0;font-family:"Iowan Old Style","Palatino","Times New Roman",serif;font-size:15px}
.fbox small{display:block;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC",sans-serif;font-size:11.5px;color:#9E2A1E;font-weight:600;margin-bottom:2px}
.tree{margin:0;padding:0;list-style:none}.tree li{display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:center;padding:6px 0;border-top:1px dashed rgba(0,0,0,.08);font-size:13.5px}.tree li:first-child{border-top:0}.tree li .a{font-weight:600}.tree li .arr{color:#6d6ff5;font-weight:700}.tree li .b{font-family:"Iowan Old Style","Palatino",serif;background:#fff;border-radius:7px;padding:5px 8px;border:1px solid #d6e1f7}
table.tb{width:100%;border-collapse:collapse;font-size:13.5px;background:#fff;border-radius:9px;overflow:hidden}table.tb th{text-align:left;background:#f1f1f4;padding:7px 9px;font-size:12px;color:#555}table.tb td{padding:7px 9px;border-top:1px solid #ececf0;vertical-align:top}table.tb td.zh{color:#5B2FA8;white-space:nowrap}
ol.traps{margin:0;padding-left:22px}ol.traps li{padding:4px 0;font-size:14px;line-height:1.45}ol.traps li::marker{font-weight:700;color:#A31F44}
ol.steps{margin:0;padding-left:0;list-style:none;counter-reset:s}ol.steps li{counter-increment:s;display:flex;gap:10px;padding:5px 0;font-size:14px;line-height:1.45}ol.steps li::before{content:counter(s);flex:0 0 22px;height:22px;border-radius:50%;background:#1F6B32;color:#fff;font-weight:700;font-size:12px;display:flex;align-items:center;justify-content:center;margin-top:1px}
.hand{font-family:"Noteworthy","Bradley Hand","Marker Felt","Segoe Print",cursive;color:#D8261C;font-size:19px;line-height:1.35;margin:6px 0 18px;transform:rotate(-1deg)}
.source{font-size:12.5px;color:var(--ink3);border-top:1px solid #eee;padding-top:12px}.source a{color:#6d6ff5;text-decoration:none}
.cta{position:fixed;left:0;right:0;bottom:0;background:rgba(255,255,255,.94);backdrop-filter:blur(14px);border-top:1px solid #e9e9ee;padding:10px 16px calc(10px + env(safe-area-inset-bottom));z-index:9}
.cta .in{max-width:720px;margin:0 auto;display:flex;flex-direction:column;gap:7px;align-items:center}
.btn{width:100%;max-width:520px;border:0;border-radius:14px;padding:15px 18px;font-size:17px;font-weight:700;color:#fff;background:#111;display:flex;align-items:center;justify-content:center;gap:9px;cursor:pointer;box-shadow:0 6px 18px rgba(0,0,0,.18);text-decoration:none}
.btn.sec{background:#fff;color:#111;border:1px solid #ddd;box-shadow:none;font-size:15px;padding:12px}
.alt{font-size:13px;color:#555}.alt a{color:#6d6ff5;text-decoration:none;font-weight:600;margin:0 5px;cursor:pointer}
.toast{position:fixed;left:50%;bottom:130px;transform:translateX(-50%);background:#111;color:#fff;padding:10px 16px;border-radius:12px;font-size:14px;opacity:0;transition:.25s;pointer-events:none;z-index:20;max-width:90vw;text-align:center}.toast.on{opacity:1}
.sheet{position:fixed;inset:0;background:rgba(0,0,0,.45);display:none;align-items:flex-end;justify-content:center;z-index:30}.sheet.on{display:flex}
.sheet .box{background:#fff;border-radius:22px 22px 0 0;padding:22px 20px calc(22px + env(safe-area-inset-bottom));width:100%;max-width:720px;position:relative}
.sheet h3{margin:0 0 6px;font-size:19px}.sheet p{margin:0 0 12px;font-size:14px;color:#444;line-height:1.5}.sheet ol{margin:0 0 14px;padding-left:20px;font-size:14px;line-height:1.7}
.sheet .x{position:absolute;right:18px;top:12px;font-size:26px;color:#999;background:none;border:0}
.nicon{vertical-align:middle}
.aside{display:none}
@media(min-width:1040px){body{background:#ebebef}.wrap{display:grid;grid-template-columns:760px 300px;gap:24px;justify-content:center;padding:28px 0}
.notes{margin:0;border-radius:24px;min-height:auto;box-shadow:0 20px 60px rgba(0,0,0,.12);padding-bottom:40px}.cta{position:sticky;bottom:0;border-radius:0 0 24px 24px;margin:0 -20px -40px}
.aside{display:block;position:sticky;top:28px;align-self:start}.aside .box{background:#fff;border-radius:20px;padding:20px;box-shadow:0 12px 40px rgba(0,0,0,.08)}.aside h3{margin:0 0 6px;font-size:16px}.aside p{font-size:13px;color:#555;margin:0 0 12px;line-height:1.5}.aside svg{width:100%;height:auto;border-radius:10px;border:1px solid #eee}.aside .u{font-size:11.5px;color:#888;word-break:break-all;margin-top:8px}}
""".replace("__GRAD__", GRAD)

ICON = ('<svg class="nicon" viewBox="0 0 40 40" width="22" height="22" aria-hidden="true"><rect x="2" y="2" width="36" height="36" rx="9" fill="#fff" stroke="#d9d9de"/>'
        '<path d="M2 11 A9 9 0 0 1 11 2 H29 A9 9 0 0 1 38 11 V12 H2 Z" fill="#F5C542"/><rect x="9" y="18" width="22" height="2.4" rx="1.2" fill="#9a9aa2"/><rect x="9" y="24" width="22" height="2.4" rx="1.2" fill="#9a9aa2"/><rect x="9" y="30" width="14" height="2.4" rx="1.2" fill="#9a9aa2"/></svg>')

def render_section(s):
    bg, bd, hc = TONES[s["tone"]]; k = s["kind"]
    P = [f'<section class="card" style="background:{bg};border-color:{bd}"><h2 style="color:{hc}"><span>{s["emoji"]}</span>{e(s["title"])}</h2>']
    if k == "facts": P.append('<ul class="kv">' + "".join(f'<li><span class="k">{e(a)}</span><span class="v">{e(b)}</span></li>' for a, b in s["items"]) + "</ul>")
    elif k == "formulas": P.append("".join(f'<div class="fbox"><small>{e(a)}</small>{e(b)}</div>' for a, b in s["items"]))
    elif k == "tree": P.append('<ul class="tree">' + "".join(f'<li><span class="a">{e(a)}</span><span class="arr">→</span><span class="b">{e(b)}</span></li>' for a, b in s["steps"]) + "</ul>")
    elif k == "terms": P.append('<table class="tb"><tr><th>Term</th><th>中文</th><th>Meaning</th></tr>' + "".join(f'<tr><td><b>{e(a)}</b></td><td class="zh">{e(z)}</td><td>{e(g)}</td></tr>' for a, z, g in s["items"]) + "</table>")
    elif k == "traps": P.append('<ol class="traps">' + "".join(f"<li>{e(t)}</li>" for t in s["items"]) + "</ol>")
    elif k == "ritual": P.append('<ol class="steps">' + "".join(f"<li><span>{e(t)}</span></li>" for t in s["steps"]) + "</ol>")
    elif k == "table":
        h = s["head"]; P.append(f'<table class="tb"><tr><th>{e(h[0])}</th><th>{e(h[1])}</th><th>{e(h[2])}</th></tr>' + "".join(f'<tr><td><b>{e(r[0])}</b></td><td>{e(r[1])}</td><td>{e(r[2])}</td></tr>' for r in s["rows"]) + "</table>")
        if s.get("foot"): P.append(f'<p style="margin:10px 0 0;font-size:13.5px;font-weight:600;color:{hc}">→ {e(s["foot"])}</p>')
    P.append("</section>"); return "".join(P)

def note_page(n, qr):
    url = note_url(n); title = f"{n['emoji']} {n['title']}"
    fname = f"{n['code']} Exam Cheat-Note.md"
    visual = f'<div class="visual"><img src="{n["visual"]}" alt="Sia visual"></div><p class="cap">🦭 {e(n["visual_caption"])}</p>' if n.get("visual") else ""
    body = "".join(render_section(s) for s in n["sections"])
    cfg = json.dumps(dict(title=title, md=f"{SITE}/n/{n['id']}/note.md", html=f"{SITE}/n/{n['id']}/note.html",
                          url=url, text=plain_text(n), file=fname), ensure_ascii=False)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(n['title'])} · AskSia Note</title><link rel="icon" href="data:,">
<meta property="og:title" content="{e(n['title'])}"><meta property="og:image" content="{visual_url(n) or ''}">
<style>{CSS}</style></head><body>
<div class="wrap"><main class="notes">
  <div class="nbar"><span class="back"><b>‹</b> Notes</span><span class="done">Done</span></div>
  <div class="date">{TODAY} · AskSia · {e(n['code'])}</div>
  <div class="head"><div class="uni">{e(n['uni'])} · {e(n['term'])}</div><h1>{n['emoji']} {e(n['code'])} {e(n['subtitle'].split(' · ')[0])}</h1></div>
  <div class="tags">{''.join(f'<span>{e(t)}</span>' for t in tags(n))}</div>
  {visual}
  {body}
  <p class="hand">✎ {e(n['handwriting'])}</p>
  <p class="source">Source: <a href="{n['source_url']}">{e(n['source_name'])}</a> · {n['source_pages']} pages · {n['source_chapters']} chapters → compressed into this one note.</p>
  <div class="cta"><div class="in">
    <a class="btn" id="add" href="#">{ICON} Add to Apple Notes</a>
    <div class="alt"><a id="help">How it works</a>·<a id="dl" href="note.md" download="{fname}">Save the .md</a>·<a id="copyrich">Copy rich text</a></div>
  </div></div>
</main>
<aside class="aside"><div class="box"><h3>📱 Scan with your iPhone</h3><p>Camera app → the note opens in Safari → tap <b>Add to Apple Notes</b> → pick <b>Notes</b> in the share sheet → <b>Import</b>. Headings, bold and lists come through as a real, editable Apple Note.</p>{qr}<div class="u">{url}</div></div></aside></div>
<div class="sheet" id="sheet"><div class="box"><button class="x" data-close>×</button><h3>Add to Apple Notes</h3>
<p>Tapping the button hands this note to iOS as a Markdown file. In the share sheet:</p>
<ol><li>Pick <b>Notes</b> (备忘录)</li><li>Choose <b>Import</b> — not “Save as attachment”</li></ol>
<p>Needs <b>iOS 26 or later</b> (Notes gained Markdown import there). If Notes isn't in the sheet: tap <b>Save the .md</b> below, then open <b>Files</b>, long-press the file → <b>Share</b> → <b>Notes</b> → <b>Import</b>.</p>
<p style="margin-top:12px"><a class="btn sec" id="dl2" href="note.md" download="{fname}">Save the .md to Files</a></p></div></div>
<div class="toast" id="toast"></div>
<script>
const N={cfg};const $=s=>document.querySelector(s);
const isIOS=/iPhone|iPad|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
function track(k){{try{{const d=JSON.parse(localStorage.getItem('asksia_notes_exp')||'{{}}');d[k]=(d[k]||0)+1;d._last=new Date().toISOString();localStorage.setItem('asksia_notes_exp',JSON.stringify(d));}}catch(e){{}}}}
let T;function toast(m,ms=3200){{const t=$('#toast');t.textContent=m;t.classList.add('on');clearTimeout(T);T=setTimeout(()=>t.classList.remove('on'),ms);}}
// prefetch the markdown so the share() call stays inside the tap gesture
let MD=null,mdErr=null;
fetch(N.md).then(r=>r.text()).then(t=>{{MD=t;}}).catch(e=>{{mdErr=e;}});
function mdFile(){{return new File([new Blob([MD],{{type:'text/markdown'}})],N.file,{{type:'text/markdown'}});}}
async function addToNotes(){{
  track('notes_cta');
  if(!MD){{toast('Still loading the note… tap again in a second');return;}}
  if(navigator.canShare&&navigator.share){{
    const f=mdFile();
    if(navigator.canShare({{files:[f]}})){{
      try{{await navigator.share({{files:[f],title:N.title}});track('shared_file');toast('Pick Notes → Import ✓');return;}}
      catch(err){{if(err&&err.name==='AbortError'){{track('share_cancel');return;}}}}
    }}
  }}
  $('#sheet').classList.add('on');   // no file sharing here → show the Files fallback
}}
$('#add').addEventListener('click',ev=>{{ev.preventDefault();
  if(!isIOS){{track('notes_cta_desktop');toast('Scan the QR with your iPhone to add it to Notes →');return;}}
  addToNotes();}});
$('#help').addEventListener('click',()=>$('#sheet').classList.add('on'));
document.querySelectorAll('[data-close]').forEach(x=>x.addEventListener('click',()=>$('#sheet').classList.remove('on')));
document.querySelectorAll('#dl,#dl2').forEach(a=>a.addEventListener('click',()=>track('download_md')));
$('#copyrich').addEventListener('click',async()=>{{track('copy_rich');
  try{{const html=await (await fetch(N.html)).text();
    await navigator.clipboard.write([new ClipboardItem({{'text/html':new Blob([html],{{type:'text/html'}}),'text/plain':new Blob([N.text],{{type:'text/plain'}})}})]);
    toast('Copied ✓ open Notes → paste (keeps formatting)');}}
  catch(e){{try{{await navigator.clipboard.writeText(N.text);toast('Copied as plain text ✓');}}catch(e2){{toast('Copy blocked by the browser');}}}}}});
if(new URLSearchParams(location.search).get('src')==='qr')track('qr_scan');
track(isIOS?'note_open_ios':'note_open_other');
</script></body></html>"""

# ───────────────────────────── library page (featured course only)
def library_page(items):
    rows = "".join(f"""
<article class="row">
  <a class="thumb" href="n/{n['id']}/"><img src="n/{n['id']}/{n['visual']}" alt=""><span class="tag">SIA VISUAL</span></a>
  <div class="meta"><div class="crumb">{e(n['uni'])} · {e(n['term'])} · {e(n['discipline'])}</div>
    <h2>{e(n['code'])} <span class="g">{e(n['subtitle'].split(' · ')[0])}</span></h2>
    <p class="tag2">{e(n['source_name'])} · {n['source_pages']} pages · {n['source_chapters']} chapters</p>
    <p class="hero">{e(n['hero_line'])}</p>
    <div class="ctas"><a class="b pdf" href="{n['source_url']}" target="_blank" rel="noopener" data-track="pdf_click"><span>📄</span> Download PDF</a>
      <button class="b notes" data-open="{n['id']}" data-track="notes_click">{ICON} Add to Apple Notes <em>NEW</em></button></div>
    <div class="fine">{'·'.join(f' {a} {b} ' for a, b in n['stats'])}</div></div>
</article>
<div class="modal" id="m-{n['id']}"><div class="mbox"><button class="x" data-close>×</button>
  <div class="mhead">{ICON}<div><b>Add {e(n['code'])} to Apple Notes</b><div class="msub">{e(n['subtitle'].split(' · ')[0])}</div></div></div>
  <div class="mgrid"><div class="qrcol">{n['qr_svg']}<div class="u">{n['url']}</div></div>
    <div class="how"><ol><li>Open the <b>Camera</b> app on your iPhone and point it here</li><li>Tap the link → the note opens in Safari (no login)</li><li>Tap <b>Add to Apple Notes</b> → pick <b>Notes</b> in the share sheet → <b>Import</b></li></ol>
      <p class="get">Needs <b>iOS 26+</b> — Notes gained Markdown import there, so headings, bold and lists survive.<br>You get: course header · the visual Sia drew · exam facts · formulas · bilingual key terms · traps — as a real, editable Apple Note.</p>
      <a class="b ghost" href="n/{n['id']}/" target="_blank" rel="noopener">Open the note page ↗</a></div></div></div></div>""" for n in items)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AskSia Library · Add to Apple Notes (MVP)</title><link rel="icon" href="data:,">
<style>
:root{{--grad:{GRAD};--ink:#111;--ink2:#555;--line:#e7e7ec}}*{{box-sizing:border-box}}body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Helvetica Neue",Arial,sans-serif;color:var(--ink);background:#fafafc;-webkit-font-smoothing:antialiased}}
.nav{{height:64px;display:flex;align-items:center;justify-content:space-between;padding:0 40px;background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}}.nav img{{height:30px}}.nav .links{{display:flex;gap:26px;font-size:15px;color:#333}}.nav .links span.on{{background:#eef0ff;color:#4a4fd8;padding:8px 14px;border-radius:999px}}.nav .right{{display:flex;gap:16px;align-items:center;font-size:14px}}.nav .dl{{background:#111;color:#fff;padding:10px 16px;border-radius:10px;font-weight:600}}
.crumbbar{{display:flex;justify-content:space-between;align-items:center;padding:12px 40px;font-size:14px;color:#666;background:#fff;border-bottom:1px solid var(--line)}}.crumbbar .pill{{background:linear-gradient(100deg,#6d6ff5,#4ea8ff);color:#fff;padding:8px 16px;border-radius:999px;font-weight:600}}
.lab{{max-width:1180px;margin:22px auto 0;padding:0 24px}}.banner{{background:#fff;border:1px solid var(--line);border-radius:18px;padding:18px 22px;display:grid;grid-template-columns:1.4fr 1fr;gap:22px;align-items:center}}
.banner h1{{margin:0 0 6px;font-size:24px;letter-spacing:-.3px}}.banner h1 .g{{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}}.banner p{{margin:0;color:var(--ink2);font-size:14px;line-height:1.55}}
.exp{{background:#0f1020;color:#fff;border-radius:14px;padding:14px 16px;font-size:13px}}.exp .t{{font-weight:700;margin-bottom:8px;display:flex;justify-content:space-between}}.exp .t small{{opacity:.6;font-weight:400}}.exp .bars{{display:grid;grid-template-columns:auto 1fr auto;gap:6px 10px;align-items:center}}.exp .bar{{height:8px;border-radius:99px;background:#2a2b45;overflow:hidden}}.exp .bar i{{display:block;height:100%;background:var(--grad)}}.exp .bar.pdf i{{background:#8a8aa0}}.exp .n{{font-variant-numeric:tabular-nums;font-weight:700}}.exp .ratio{{margin-top:8px;font-size:12px;opacity:.85}}.exp .ratio b{{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;font-size:16px}}.exp .rs{{margin-top:8px;font-size:11px;opacity:.5;cursor:pointer}}
.list{{max-width:1180px;margin:18px auto 60px;padding:0 24px;display:flex;flex-direction:column;gap:16px}}.row{{background:#fff;border:1px solid var(--line);border-radius:20px;padding:20px;display:grid;grid-template-columns:300px 1fr;gap:24px}}
.thumb{{display:block;position:relative;border-radius:14px;overflow:hidden;border:1px solid var(--line);background:#f2f2f5}}.thumb img{{width:100%;display:block}}.thumb .tag{{position:absolute;top:10px;left:10px;background:#5b5fe8;color:#fff;font-size:10px;letter-spacing:1px;padding:4px 8px;border-radius:6px;font-weight:700}}
.meta .crumb{{font-size:11.5px;letter-spacing:1.6px;text-transform:uppercase;color:#6d6ff5;font-weight:700;margin-bottom:6px}}.meta h2{{margin:0 0 4px;font-size:26px;letter-spacing:-.3px}}.meta h2 .g{{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;font-weight:700}}.meta .tag2{{margin:0 0 8px;font-size:13px;color:#777}}.meta .hero{{margin:0 0 14px;font-size:15px;line-height:1.5}}
.ctas{{display:flex;gap:12px;flex-wrap:wrap}}.b{{display:inline-flex;align-items:center;gap:8px;border-radius:12px;padding:12px 18px;font-size:15px;font-weight:700;text-decoration:none;cursor:pointer;border:1px solid var(--line);background:#fff;color:#111;font-family:inherit}}.b.notes{{background:#111;color:#fff;border-color:#111}}.b.notes em{{font-style:normal;background:var(--grad);font-size:9px;letter-spacing:1px;padding:2px 6px;border-radius:5px;margin-left:4px}}.fine{{margin-top:12px;font-size:12.5px;color:#888}}
.modal{{position:fixed;inset:0;background:rgba(10,10,20,.55);display:none;align-items:center;justify-content:center;z-index:50;padding:20px}}.modal.on{{display:flex}}.mbox{{background:#fff;border-radius:24px;width:min(760px,100%);padding:26px 28px;position:relative;box-shadow:0 30px 80px rgba(0,0,0,.3)}}.x{{position:absolute;top:12px;right:16px;border:0;background:none;font-size:28px;cursor:pointer;color:#999}}
.mhead{{display:flex;gap:12px;align-items:center;margin-bottom:18px}}.mhead .nicon{{width:34px;height:34px}}.mhead b{{font-size:20px}}.msub{{font-size:13px;color:#777}}.mgrid{{display:grid;grid-template-columns:260px 1fr;gap:26px;align-items:start}}.qrcol svg{{width:100%;height:auto;border:1px solid var(--line);border-radius:14px;padding:6px}}.qrcol .u{{font-size:11px;color:#888;word-break:break-all;margin-top:8px;text-align:center}}
.how ol{{margin:0 0 12px;padding-left:20px;font-size:15px;line-height:1.7}}.how .get{{font-size:13px;color:#555;line-height:1.55;background:#f6f6fa;border-radius:12px;padding:12px}}.b.ghost{{background:#fff;margin-top:10px}}.nicon{{vertical-align:middle}}
@media(max-width:820px){{.nav .links{{display:none}}.banner,.row,.mgrid{{grid-template-columns:1fr}}}}
</style></head><body>
<div class="nav"><img src="assets/logo.png" alt="AskSia"><div class="links"><span class="on">For Students ⌄</span><span>Useful Tools ⌄</span><span>Resources ⌄</span><span>Pricing</span></div><div class="right"><span>Log in</span><span class="dl">Download App →</span></div></div>
<div class="crumbbar"><span>Library / <b>Exam Bibles</b> / Add to Apple Notes</span><span class="pill">Get A+ · $0.99 Trial</span></div>
<div class="lab"><div class="banner"><div><h1>Every Bible, one tap into <span class="g">your Apple Notes</span></h1>
<p><b>Internal MVP v2 · 2026-08-30 · Kai.</b> Next to “Download PDF”, a second exit: the bible compressed into one editable Apple Note — course header → the visual Sia drew → exam facts · formulas · bilingual terms · traps. Handed to iOS as a Markdown file, so Notes imports it as a real editable note — headings, bold, lists intact (iOS 26+).<br><b>Test:</b> click <b>Add to Apple Notes</b> → scan the QR with your iPhone → tap the button → pick <b>Notes</b> → <b>Import</b>.</p></div>
<div class="exp"><div class="t">Experiment: Notes CTR vs PDF CTR <small>this browser only</small></div><div class="bars"><span>📝 Notes</span><div class="bar"><i id="b1" style="width:0"></i></div><span class="n" id="n1">0</span><span>📄 PDF</span><div class="bar pdf"><i id="b2" style="width:0"></i></div><span class="n" id="n2">0</span></div><div class="ratio">Notes ÷ PDF = <b id="ratio">—</b> · hypothesis: ≥ 2×</div><div class="rs" id="reset">reset counters</div></div></div></div>
<div class="list">{rows}</div>
<script>
const isIOS=/iPhone|iPad|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);const KEY='asksia_notes_exp';
function load(){{try{{return JSON.parse(localStorage.getItem(KEY)||'{{}}')}}catch(e){{return {{}}}}}}
function track(k){{const d=load();d[k]=(d[k]||0)+1;d._last=new Date().toISOString();try{{localStorage.setItem(KEY,JSON.stringify(d))}}catch(e){{}}paint();}}
function paint(){{const d=load();const a=d.notes_click||0,b=d.pdf_click||0,m=Math.max(a,b,1);document.getElementById('n1').textContent=a;document.getElementById('n2').textContent=b;document.getElementById('b1').style.width=(a/m*100)+'%';document.getElementById('b2').style.width=(b/m*100)+'%';document.getElementById('ratio').textContent=b?(a/b).toFixed(1)+'×':(a?'∞':'—');}}
document.getElementById('reset').onclick=()=>{{localStorage.removeItem(KEY);paint();}};
document.querySelectorAll('[data-track]').forEach(el=>el.addEventListener('click',()=>track(el.dataset.track)));
document.querySelectorAll('[data-open]').forEach(b=>b.addEventListener('click',()=>{{const id=b.dataset.open;if(isIOS){{location.href='n/'+id+'/';return;}}document.getElementById('m-'+id).classList.add('on');}}));
document.querySelectorAll('[data-close]').forEach(x=>x.addEventListener('click',()=>x.closest('.modal').classList.remove('on')));
document.querySelectorAll('.modal').forEach(m=>m.addEventListener('click',ev=>{{if(ev.target===m)m.classList.remove('on')}}));
paint();
</script></body></html>"""

def main():
    OUT.mkdir(exist_ok=True); (OUT / "assets").mkdir(exist_ok=True)
    for f in ("logo.png", "sia.png"): shutil.copy(ASSETS / f, OUT / "assets" / f)
    (OUT / ".nojekyll").write_text("")
    (OUT / SHORTCUT_FILE).unlink(missing_ok=True)   # Shortcut route dropped: Create Note coerces to plain text
    items = []
    for n in NOTES:
        if n["id"] not in FEATURED: continue
        d = OUT / "n" / n["id"]; d.mkdir(parents=True, exist_ok=True)
        svg = qr_svg(note_url(n) + "?src=qr"); (d / "qr.svg").write_text(svg)
        if n.get("visual"): shutil.copy(ASSETS / n["visual"], d / n["visual"])
        (d / "index.html").write_text(note_page(n, svg), encoding="utf-8")
        (d / "note.html").write_text(notes_html(n), encoding="utf-8")
        (d / "note.md").write_text(notes_md(n), encoding="utf-8")
        (d / "note.json").write_text(json.dumps({"title": f"{n['emoji']} {n['title']}", "md": notes_md(n)}, ensure_ascii=False), encoding="utf-8")
        (d / "note.txt").write_text(plain_text(n), encoding="utf-8")
        for stale in ("card.png", "_card.html"): (d / stale).unlink(missing_ok=True)
        items.append(dict(n, url=note_url(n), qr_svg=svg)); print("note →", d)
    for stale in ("buss1020", "sat-math"):   # not featured this round
        if (OUT / "n" / stale).exists(): shutil.rmtree(OUT / "n" / stale)
    (OUT / "index.html").write_text(library_page(items), encoding="utf-8"); print("library →", OUT / "index.html")

if __name__ == "__main__":
    main()
