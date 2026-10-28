"""report.md for a case: answer first, then candidates, evidence and the run log."""
from __future__ import annotations

import html
import re
import urllib.parse

from .cases import Case


def _dms(v: float, pos: str, neg: str) -> str:
    h = pos if v >= 0 else neg
    v = abs(v)
    d = int(v)
    m = int((v - d) * 60)
    s = (v - d - m / 60) * 3600
    return f"{d}°{m:02d}'{s:04.1f}\"{h}"


import json


def write_report(case: Case) -> None:
    d = case.load()
    f = d.get("final") or {}
    lines = [f"# SAQR · {d['id']}", "", f"- File: `{d.get('filename')}` · mode: {d.get('mode')} · created {d.get('created')}",
             f"- Engine: {d.get('engine') or 'local'} · status: {d.get('status')}"]
    if d.get("rerun_of"):
        lines.append(f"- Re-run of `{d['rerun_of']}`")
    if d.get("error"):
        lines.append(f"- Error: {d['error']}")
    lines.append("")
    if d.get("mode") in ("region", "street", "private") and f:
        lat, lon = f.get("lat", 0), f.get("lon", 0)
        place = " / ".join(x for x in (f.get("country"), f.get("region"), f.get("city")) if x)
        lines += [f"## **{place}**", "",
                  f"**{_dms(lat, 'N', 'S')} {_dms(lon, 'E', 'W')}** · `{lat:.6f}, {lon:.6f}`", "",
                  f"Confidence **{f.get('confidence')}** · level {f.get('level')} · radius ~{f.get('radius_km')} km", "",
                  f.get("summary", ""), "", "### Decisive clues"]
        lines += [f"- {c}" for c in f.get("clues", [])] or ["- (none)"]
        if f.get("alternatives"):
            lines += ["", "### Alternatives"]
            lines += [f"- {a.get('place')}: {a.get('why')}" for a in f["alternatives"]]
        if f.get("unverified"):
            lines += ["", "### Not verified"] + [f"- {u}" for u in f["unverified"]]
    elif d.get("mode") == "person" and f:
        lines += [f"## {f.get('name') or 'ما تحدد شخص'}", "",
                  f"- الثقة: {f.get('confidence')} · دور: {f.get('role') or '—'}"]
        if f.get("place"):
            lines.append(f"- المكان: {f['place']}")
        lines += ["", f.get("summary", "")]
        if f.get("accounts"):
            lines += ["", "### حسابات", "", "| موقع | حساب | لماذا |", "|---|---|---|"] + \
                     [f"| {a.get('site', '')} | {a.get('handle', '')} | {a.get('why', '')} |" for a in f["accounts"]]
        if f.get("evidence"):
            lines += ["", "### الأدلة"] + [f"- {x}" for x in f["evidence"]]
        if f.get("unverified"):
            lines += ["", "### ما تحقق منه"] + [f"- {x}" for x in f["unverified"]]
    elif d.get("mode") == "plate" and f:
        lines += [f"## {f.get('plate') or 'لوحة غير مقروءة'}", "",
                  f"- الدولة: {f.get('country')} · النوع: {f.get('plate_type') or '—'}",
                  f"- المركبة: {f.get('vehicle')}",
                  f"- المالك: {f.get('owner') or 'غير متاح علناً'}", f"- الثقة: {f.get('confidence')}"]
        if f.get("region_hint"):
            lines.append(f"- دلالة الموقع: {f['region_hint']}")
        if f.get("owner_note"):
            lines.append(f"- عن المالك: {f['owner_note']}")
        lines += ["", f.get("summary", "")]
        if f.get("evidence"):
            lines += ["", "### الأدلة"] + [f"- {x}" for x in f["evidence"]]
        if f.get("unverified"):
            lines += ["", "### ما تحقق منه"] + [f"- {x}" for x in f["unverified"]]
    elif f:
        lines += ["## Result", "", "```json", json.dumps(f, ensure_ascii=False, indent=1), "```"]
    cands = d.get("candidates", [])
    if cands:
        lines += ["", "## Candidates on the map", "", "| # | Place | lat, lon | conf | radius km | why |", "|---|---|---|---|---|---|"]
        cell = lambda v: " ".join(str(v).replace("|", "/").split())
        lines += [f"| {c['n']} | {cell(c['label'])} | {c['lat']:.5f}, {c['lon']:.5f} | {c['confidence']} | {c['radius_km']} | {cell(c['reason'])} |"
                  for c in cands]
    notes = case.dir / "notes.md"
    if notes.exists() and notes.read_text(encoding="utf-8").strip():
        lines += ["", "## Analyst notes", ""] + notes.read_text(encoding="utf-8").strip().splitlines()
    ev = [e for e in case.events() if e["kind"] == "evidence"]
    if ev:
        lines += ["", "## Evidence", ""] + [f"![{e['caption']}]({e['path']})" for e in ev]
    tools = [e for e in case.events() if e["kind"] == "tool"]
    if tools:
        lines += ["", "## Tools run", ""] + [f"- `{e['name']}` {e.get('input')}" for e in tools]
    (case.dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _inline(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", t)


def render_html(cid: str, md: str) -> str:
    """The report.md subset SAQR writes (headings, lists, tables, images, code) as a self-contained page."""
    out, in_list, in_code, table = [], False, False, []
    base = f"/api/cases/{urllib.parse.quote(cid)}/file/"

    def flush():
        nonlocal in_list, table
        if in_list:
            out.append("</ul>")
            in_list = False
        if table:
            rows = [r for r in table if not re.fullmatch(r"\|?[\s|:-]+\|?", r)]
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            out.append("<table>" + "".join(
                "<tr>" + "".join(f"<{'th' if i == 0 else 'td'}>{_inline(c)}</{'th' if i == 0 else 'td'}>" for c in row) + "</tr>"
                for i, row in enumerate(cells)) + "</table>")
            table = []

    for line in md.splitlines():
        if line.startswith("```"):
            flush()
            out.append("</pre>" if in_code else "<pre>")
            in_code = not in_code
            continue
        if in_code:
            out.append(html.escape(line))
            continue
        if line.startswith("|"):
            table.append(line)
            continue
        if table:
            flush()
        m = re.match(r"(#{1,4}) (.*)", line)
        img = re.match(r"!\[(.*?)\]\((.*?)\)", line)
        if m:
            flush()
            n = len(m.group(1))
            out.append(f"<h{n}>{_inline(m.group(2))}</h{n}>")
        elif img:
            flush()
            src = base + urllib.parse.quote(img.group(2))
            out.append(f'<figure><img src="{src}" alt=""><figcaption>{html.escape(img.group(1))}</figcaption></figure>')
        elif line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_inline(line[2:])}</li>")
        elif line.strip():
            flush()
            out.append(f"<p>{_inline(line)}</p>")
        else:
            flush()
    flush()
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>SAQR · {html.escape(cid)}</title>
<style>
body{{margin:0;background:#05080c;color:#dce7f0;font:15px/1.8 "IBM Plex Sans Arabic",system-ui,sans-serif}}
main{{max-width:880px;margin:0 auto;padding:32px 20px 80px}}
h1{{font:600 15px ui-monospace,Consolas,monospace;color:#5ee7ff;letter-spacing:.06em;direction:ltr;text-align:start}}
h2{{font-size:24px;margin:24px 0 8px}} h3{{color:#8fa3b5;font-size:14px;margin:26px 0 8px}}
code,pre{{font:12.5px ui-monospace,Consolas,monospace;color:#9fdfff}} pre{{background:#0b131b;padding:12px;border-radius:10px;overflow:auto;direction:ltr;text-align:left}}
ul{{padding:0;list-style:none;display:grid;gap:6px}} li{{background:#0b131b;border:1px solid #162533;border-radius:10px;padding:8px 12px}}
table{{border-collapse:collapse;width:100%;font-size:13px}} th,td{{border-bottom:1px solid #162533;padding:6px 8px;text-align:start}}
figure{{margin:14px 0}} img{{max-width:100%;border-radius:10px;border:1px solid #162533}} figcaption{{color:#8fa3b5;font-size:12px;direction:ltr;text-align:start}}
</style></head><body><main>{"".join(out)}</main></body></html>"""
