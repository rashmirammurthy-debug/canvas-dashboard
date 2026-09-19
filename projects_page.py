"""Builds projects.html: a public one-page summary of my projects, refreshed weekly by GitHub Actions.

What appears on the page is deliberately limited to (a) the hand-written, generic text in
projects.json, (b) numbers computed from the repo (commit count, workflow files), and (c) one sentence
per project written by Claude from recent commit messages only.
Set REDACT_TERMS (a GitHub secret, comma-separated, e.g. names and places) to drop any commit message
or sentence that mentions those words. Run with --no-claude to preview without an API call."""
import glob
import html
import json
import os
import subprocess
import sys
from datetime import date

import daily_feed as df

ROOT = os.path.dirname(os.path.abspath(__file__))
SINCE_DAYS = 14      # how far back to look for recent activity
ACTIVE_DAYS = 30     # a project with a commit this recently is "Active"
MAX_COMMITS = 15


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    return result.stdout


def make_is_private():
    terms = [t.strip().lower() for t in os.environ.get("REDACT_TERMS", "").split(",") if t.strip()]
    return lambda text: any(term in text.lower() for term in terms)


def gather(project, is_private):
    """Last-commit date, status and recent commit subjects for a project's files."""
    paths = project.get("paths")
    info = {"last": "", "status": project.get("status", ""), "subjects": []}
    if not paths:
        return info
    info["last"] = git("log", "-1", "--format=%cs", "--", *paths).strip()
    subjects = git("log", "--no-merges", f"--since={SINCE_DAYS} days ago", "--format=%s", "--", *paths)
    info["subjects"] = [s for s in subjects.splitlines() if s.strip() and not is_private(s)][:MAX_COMMITS]
    if info["last"]:
        age = (date.today() - date.fromisoformat(info["last"])).days
        info["status"] = "Active" if age <= ACTIVE_DAYS else "Quiet"
    return info


def write_activity(projects, infos, is_private):
    """One plain-English sentence per project from its recent commit messages (Claude)."""
    listing = "\n\n".join(
        f"[{p['id']}] {p['name']}: {p['approach']}\nRecent commit messages:\n"
        + "\n".join(f"- {s}" for s in infos[p["id"]]["subjects"])
        for p in projects if infos[p["id"]]["subjects"]
    )
    if not listing:
        return {}
    prompt = (
        "Below are projects from a public portfolio page, each with its recent commit messages. For each "
        "project write ONE plain-English sentence (at most 25 words) saying what changed recently in that "
        "project, for a non-technical reader. Do not mention other projects. Use only the text given. "
        "Never include personal names, family details, school, employer or place names, credentials or "
        "anything private; leave out anything a commit message hints at that seems private. "
        'Reply with only JSON: [{"id": "<project id>", "activity": "<sentence>"}].\n\n' + listing
    )
    try:
        result = {r["id"]: str(r["activity"]).strip() for r in df.ask_json(prompt, effort="low")}
    except Exception as e:
        print(f"Claude summaries failed, leaving them out: {e}", file=sys.stderr)
        return {}
    print("Activity sentences written by Claude")
    return {k: v for k, v in result.items() if v and not is_private(v)}


def compute_stats(projects):
    """Facts computed from the repo itself, so the numbers are always true."""
    workflows = glob.glob(os.path.join(ROOT, ".github", "workflows", "*.yml"))
    scheduled = sum(1 for w in workflows if "schedule:" in open(w, encoding="utf-8").read())
    commits = git("rev-list", "--count", "HEAD").strip() or "0"
    first = git("log", "--reverse", "--format=%cs").splitlines()
    since = f"{date.fromisoformat(first[0]):%b %Y}" if first else "-"
    return [
        (str(len(projects)), "projects"),
        (str(scheduled), "automations on a schedule"),
        (commits, "commits of iteration"),
        (since, "building since"),
    ]


CSS = """
:root {
  --bg:#f4f6fc; --card:#ffffff; --text:#151a2e; --muted:#586179; --border:#e1e5f0;
  --chip:#eef2ff; --chip-text:#2a4bc4; --note:#f3f6fd; --shadow:0 1px 2px rgba(20,30,70,.06),0 8px 24px rgba(20,30,70,.06);
  --active:#137333; --active-bg:#e3f4e8; --quiet:#586179; --quiet-bg:#eceff6; --kept:#2a4bc4; --kept-bg:#eaf0ff;
  --step:#f3f6fd; --step-border:#d9e0f2;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg:#0c0f1d; --card:#161b30; --text:#eaedf7; --muted:#9ba4bd; --border:#272e49;
    --chip:#1e2646; --chip-text:#b3c6ff; --note:#1b213b; --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.25);
    --active:#86dd9f; --active-bg:#173023; --quiet:#aab2c8; --quiet-bg:#232a44; --kept:#b3c6ff; --kept-bg:#1e2646;
    --step:#1b213b; --step-border:#2c3454;
  }
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--text); line-height:1.55;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
.hero { background:linear-gradient(135deg,#131c4d 0%,#1a3fb8 55%,#4d7cff 100%); color:#fff; padding:56px 16px 92px; }
.wrap { max-width:1080px; margin:0 auto; }
.eyebrow { font-size:.78rem; letter-spacing:.16em; text-transform:uppercase; color:#b9ccff; font-weight:700; margin:0 0 12px; }
h1 { font-size:clamp(1.9rem,4.6vw,3rem); line-height:1.1; margin:0 0 14px; letter-spacing:-.025em; max-width:18ch; }
.lead { font-size:clamp(1rem,2vw,1.2rem); color:#dbe5ff; max-width:60ch; margin:0; }
.stats { display:grid; gap:14px; grid-template-columns:repeat(auto-fit,minmax(min(100%,190px),1fr)); margin:-56px auto 40px; max-width:1080px; padding:0 16px; }
.stat { background:var(--card); border:1px solid var(--border); border-radius:14px; padding:16px 18px; box-shadow:var(--shadow); }
.stat b { display:block; font-size:1.8rem; line-height:1.1; letter-spacing:-.02em; }
.stat span { color:var(--muted); font-size:.85rem; }
main { max-width:1080px; margin:0 auto; padding:0 16px 56px; }
h2.section { font-size:1.35rem; margin:36px 0 16px; letter-spacing:-.01em; }
.grid { display:grid; gap:20px; grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr)); }
.card { --soft:rgba(80,100,200,.12); background:var(--card); border:1px solid var(--border); border-top:4px solid var(--accent);
  border-radius:16px; padding:22px; display:flex; flex-direction:column; gap:14px; box-shadow:var(--shadow);
  transition:transform .15s ease, box-shadow .15s ease; }
@media (prefers-reduced-motion: no-preference) { .card:hover { transform:translateY(-3px); } }
.card-head { display:flex; gap:14px; align-items:flex-start; }
.icon { flex:none; width:46px; height:46px; border-radius:12px; background:var(--soft); display:grid; place-items:center; font-size:1.4rem; }
.titles { flex:1; min-width:0; }
h3 { font-size:1.2rem; margin:0; line-height:1.25; }
.tagline { margin:2px 0 0; color:var(--muted); font-size:.95rem; }
.pill { font-size:.72rem; font-weight:700; padding:3px 10px; border-radius:999px; white-space:nowrap; }
.pill.active { color:var(--active); background:var(--active-bg); }
.pill.quiet { color:var(--quiet); background:var(--quiet-bg); }
.pill.kept { color:var(--kept); background:var(--kept-bg); }
.story { margin:0; display:grid; gap:10px; }
.story div { display:grid; grid-template-columns:78px 1fr; gap:10px; }
.story dt { font-size:.68rem; font-weight:800; letter-spacing:.09em; text-transform:uppercase; color:var(--accent); padding-top:3px; }
.story dd { margin:0; font-size:.93rem; }
.flow { list-style:none; margin:0; padding:0; display:flex; flex-wrap:wrap; align-items:center; gap:8px 6px; }
.flow li { display:flex; align-items:center; gap:6px; }
.step { background:var(--step); border:1px solid var(--step-border); border-radius:10px; padding:6px 10px; font-size:.8rem; font-weight:600; }
.step.llm { background:var(--accent); border-color:var(--accent); color:#fff; }
.step .badge { display:block; font-size:.6rem; letter-spacing:.1em; text-transform:uppercase; opacity:.85; font-weight:800; }
.arrow { color:var(--muted); font-weight:700; }
.runs { margin:0; font-size:.85rem; color:var(--muted); }
.chips { display:flex; flex-wrap:wrap; gap:6px; margin:0; padding:0; list-style:none; }
.chips li { background:var(--chip); color:var(--chip-text); font-size:.75rem; padding:3px 10px; border-radius:999px; }
.chips li.hl { background:var(--accent); color:#fff; font-weight:700; }
.recent { background:var(--note); border-left:3px solid var(--accent); border-radius:8px; padding:10px 12px; font-size:.9rem; margin-top:auto; }
.recent .label { font-size:.66rem; font-weight:800; letter-spacing:.09em; text-transform:uppercase; color:var(--muted); }
.recent p { margin:3px 0 0; }
.updated { color:var(--muted); font-size:.78rem; margin:0; }
.principles { display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr)); }
.principle { background:var(--card); border:1px solid var(--border); border-radius:14px; padding:18px; }
.principle .pi { font-size:1.5rem; }
.principle h4 { margin:6px 0 4px; font-size:1rem; }
.principle p { margin:0; color:var(--muted); font-size:.9rem; }
.terms { margin-top:36px; background:var(--card); border:1px solid var(--border); border-radius:14px; padding:20px 22px; }
.terms h2 { font-size:1.05rem; margin:0 0 10px; }
.terms dt { font-weight:700; }
.terms dd { margin:4px 0 12px; color:var(--muted); }
.terms dd:last-child { margin-bottom:0; }
footer { margin-top:36px; color:var(--muted); font-size:.85rem; }
"""


def hex_to_soft(hex_color, alpha=0.14):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def render_flow(flow):
    if not flow:
        return ""
    e = html.escape
    items = []
    for n, s in enumerate(flow):
        step = (
            f'<span class="step llm"><span class="badge">Claude</span>{e(s["label"])}</span>' if s["kind"] == "llm"
            else f'<span class="step">{e(s["label"])}</span>'
        )
        # The arrow lives with the step before it, so a line break never strands an arrow
        arrow = '<span class="arrow" aria-hidden="true">&rarr;</span>' if n < len(flow) - 1 else ""
        items.append(f"<li>{step}{arrow}</li>")
    return f'<ol class="flow" aria-label="How it works">{"".join(items)}</ol>'


def render_card(project, info, activity):
    e = html.escape
    status = info["status"]
    pill_class = "active" if status == "Active" else "quiet" if status == "Quiet" else "kept"
    pill = f'<span class="pill {pill_class}">{e(status)}</span>' if status else ""
    chips = "".join(
        f'<li class="hl">{e(t)}</li>' if t == "LLM workflow" else f"<li>{e(t)}</li>" for t in project.get("tech", [])
    )
    recent = f'<div class="recent"><span class="label">Recently</span><p>{e(activity)}</p></div>' if activity else ""
    updated = f'<p class="updated">Last updated {date.fromisoformat(info["last"]):%b %d, %Y}</p>' if info["last"] else ""
    accent = project.get("accent", "#1a4fd6")
    return (
        f'<section class="card" style="--accent:{e(accent)};--soft:{hex_to_soft(accent)}">'
        f'<div class="card-head"><div class="icon" aria-hidden="true">{project.get("icon", "")}</div>'
        f'<div class="titles"><h3>{e(project["name"])}</h3><p class="tagline">{e(project["tagline"])}</p></div>{pill}</div>'
        '<dl class="story">'
        f'<div><dt>Problem</dt><dd>{e(project["problem"])}</dd></div>'
        f'<div><dt>Approach</dt><dd>{e(project["approach"])}</dd></div>'
        f'<div><dt>Result</dt><dd>{e(project["outcome"])}</dd></div></dl>'
        f'{render_flow(project.get("flow"))}'
        f'<p class="runs">&#9201; {e(project["runs"])}</p>'
        f'<ul class="chips">{chips}</ul>{recent}{updated}</section>'
    )


def render_principles(principles):
    if not principles:
        return ""
    e = html.escape
    tiles = "".join(
        f'<div class="principle"><div class="pi" aria-hidden="true">{p["icon"]}</div>'
        f'<h4>{e(p["title"])}</h4><p>{e(p["text"])}</p></div>'
        for p in principles
    )
    return f'<h2 class="section">How I build</h2><div class="principles">{tiles}</div>'


def render_terms(glossary):
    if not glossary:
        return ""
    e = html.escape
    entries = "".join(f'<dt>{e(g["term"])}</dt><dd>{e(g["definition"])}</dd>' for g in glossary)
    return f'<section class="terms"><h2>Terms</h2><dl>{entries}</dl></section>'


def render_page(config, cards, refreshed, stats):
    e = html.escape
    stat_html = "".join(f'<div class="stat"><b>{e(n)}</b><span>{e(label)}</span></div>' for n, label in stats)
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{e(config["title"])}</title>'
        f'<meta name="description" content="{e(config["subtitle"])}">'
        '<meta name="robots" content="noindex, nofollow">'
        f"<style>{CSS}</style></head><body>"
        f'<header class="hero"><div class="wrap"><p class="eyebrow">{e(config["title"])}</p>'
        f'<h1>{e(config["headline"])}</h1><p class="lead">{e(config["lead"])}</p></div></header>'
        f'<div class="stats">{stat_html}</div>'
        f'<main><h2 class="section" style="margin-top:0">What I\'ve built</h2><div class="grid">{cards}</div>'
        f'{render_principles(config.get("principles"))}{render_terms(config.get("glossary"))}'
        f'<footer>Refreshed {refreshed} by a scheduled GitHub Actions workflow. Numbers are computed from the '
        'repository; the "Recently" notes are written by Claude from recent commit messages.</footer>'
        "</main></body></html>"
    )


if __name__ == "__main__":
    with open(os.path.join(ROOT, "projects.json"), encoding="utf-8") as f:
        config = json.load(f)
    projects = config["projects"]
    is_private = make_is_private()
    infos = {p["id"]: gather(p, is_private) for p in projects}
    print("Projects:", "; ".join(f"{p['id']}: {infos[p['id']]['status'] or '-'}, {len(infos[p['id']]['subjects'])} recent commits" for p in projects))
    activity = {} if "--no-claude" in sys.argv else write_activity(projects, infos, is_private)
    cards = "".join(render_card(p, infos[p["id"]], activity.get(p["id"], "")) for p in projects)
    page = render_page(config, cards, f"{df.local_now():%B %d, %Y}", compute_stats(projects))
    with open(os.path.join(ROOT, "projects.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("Wrote projects.html")
