"""Builds projects.html: a public one-page summary of my projects, refreshed weekly by GitHub Actions.

What appears on the page is deliberately limited to (a) the hand-written, generic descriptions in
projects.json and (b) one sentence per project, written by Claude from recent commit messages only.
Set REDACT_TERMS (a GitHub secret, comma-separated, e.g. names and places) to drop any commit message
or sentence that mentions those words. Run with --no-claude to preview without an API call."""
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
        f"[{p['id']}] {p['name']}: {p['description']}\nRecent commit messages:\n"
        + "\n".join(f"- {s}" for s in infos[p["id"]]["subjects"])
        for p in projects if infos[p["id"]]["subjects"]
    )
    if not listing:
        return {}
    prompt = (
        "Below are projects from a public portfolio page, each with its recent commit messages. For each "
        "project write ONE plain-English sentence (at most 25 words) saying what changed recently, for a "
        "non-technical reader. Use only the text given. Never include personal names, family details, "
        "school, employer or place names, credentials or anything private; leave out anything a commit "
        "message hints at that seems private. "
        'Reply with only JSON: [{"id": "<project id>", "activity": "<sentence>"}].\n\n' + listing
    )
    try:
        result = {r["id"]: str(r["activity"]).strip() for r in df.ask_json(prompt, effort="low")}
    except Exception as e:
        print(f"Claude summaries failed, leaving them out: {e}", file=sys.stderr)
        return {}
    print("Activity sentences written by Claude")
    return {k: v for k, v in result.items() if v and not is_private(v)}


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{subtitle}">
<meta name="robots" content="noindex, nofollow">
<style>
:root {{
  --bg:#f5f6fb; --card:#ffffff; --text:#161a2b; --muted:#5b6478; --border:#e2e5ef;
  --accent:#1a4fd6; --chip:#eaf0ff; --chip-text:#1a4fd6; --note:#f1f4fb;
  --active:#137333; --active-bg:#e6f4ea; --quiet:#5b6478; --quiet-bg:#eceef4;
  --kept:#1a4fd6; --kept-bg:#eaf0ff;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg:#0f1220; --card:#181c2e; --text:#e9ecf5; --muted:#9aa3ba; --border:#2a3048;
    --accent:#7ea2ff; --chip:#1f2745; --chip-text:#a9c0ff; --note:#1d2238;
    --active:#7fd99a; --active-bg:#183324; --quiet:#a9b0c4; --quiet-bg:#242a40;
    --kept:#a9c0ff; --kept-bg:#1f2745;
  }}
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); line-height:1.5;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }}
main {{ max-width:1080px; margin:0 auto; padding:40px 16px 56px; }}
h1 {{ font-size:2.1rem; margin:0 0 6px; letter-spacing:-0.02em; }}
.subtitle {{ color:var(--muted); margin:0 0 32px; font-size:1.05rem; }}
.grid {{ display:grid; gap:18px; grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr)); }}
.card {{ background:var(--card); border:1px solid var(--border); border-radius:14px; padding:22px;
  display:flex; flex-direction:column; gap:12px; }}
.card-top {{ display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }}
h2 {{ font-size:1.25rem; margin:0; }}
.pill {{ font-size:.75rem; font-weight:600; padding:3px 10px; border-radius:999px; white-space:nowrap; }}
.pill.active {{ color:var(--active); background:var(--active-bg); }}
.pill.quiet {{ color:var(--quiet); background:var(--quiet-bg); }}
.pill.kept {{ color:var(--kept); background:var(--kept-bg); }}
.tagline {{ margin:0; font-weight:600; }}
.desc {{ margin:0; color:var(--muted); }}
.runs {{ margin:0; font-size:.9rem; }}
.label {{ font-size:.7rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }}
.chips {{ display:flex; flex-wrap:wrap; gap:6px; margin:0; padding:0; list-style:none; }}
.chips li {{ background:var(--chip); color:var(--chip-text); font-size:.78rem; padding:3px 10px; border-radius:999px; }}
.recent {{ background:var(--note); border-radius:10px; padding:10px 12px; font-size:.92rem; margin-top:auto; }}
.recent p {{ margin:4px 0 0; }}
.updated {{ color:var(--muted); font-size:.8rem; margin:0; }}
.terms {{ margin-top:32px; background:var(--card); border:1px solid var(--border); border-radius:14px; padding:20px 22px; }}
.terms h2 {{ font-size:1.05rem; margin:0 0 10px; }}
.terms dt {{ font-weight:700; }}
.terms dd {{ margin:4px 0 12px; color:var(--muted); }}
.terms dd:last-child {{ margin-bottom:0; }}
footer {{ margin-top:36px; color:var(--muted); font-size:.85rem; }}
</style>
</head>
<body>
<main>
<h1>{title}</h1>
<p class="subtitle">{subtitle}</p>
<div class="grid">
{cards}
</div>
{terms}
<footer>Refreshed {refreshed} by a scheduled GitHub Actions workflow. The "Recently" notes are written by Claude from recent commit messages.</footer>
</main>
</body>
</html>
"""


def render_card(project, info, activity):
    e = html.escape
    status = info["status"]
    pill = f'<span class="pill {"active" if status == "Active" else "quiet" if status == "Quiet" else "kept"}">{e(status)}</span>' if status else ""
    chips = "".join(f"<li>{e(t)}</li>" for t in project.get("tech", []))
    recent = f'<div class="recent"><span class="label">Recently</span><p>{e(activity)}</p></div>' if activity else ""
    updated = f'<p class="updated">Last updated {date.fromisoformat(info["last"]):%b %d, %Y}</p>' if info["last"] else ""
    return (
        '<section class="card">'
        f'<div class="card-top"><h2>{e(project["name"])}</h2>{pill}</div>'
        f'<p class="tagline">{e(project["tagline"])}</p>'
        f'<p class="desc">{e(project["description"])}</p>'
        f'<p class="runs"><span class="label">Runs</span><br>{e(project["runs"])}</p>'
        f'<ul class="chips">{chips}</ul>{recent}{updated}</section>'
    )


def render_terms(glossary):
    if not glossary:
        return ""
    e = html.escape
    entries = "".join(f'<dt>{e(g["term"])}</dt><dd>{e(g["definition"])}</dd>' for g in glossary)
    return f'<section class="terms"><h2>Terms</h2><dl>{entries}</dl></section>'


if __name__ == "__main__":
    with open(os.path.join(ROOT, "projects.json"), encoding="utf-8") as f:
        config = json.load(f)
    projects = config["projects"]
    is_private = make_is_private()
    infos = {p["id"]: gather(p, is_private) for p in projects}
    print("Projects:", "; ".join(f"{p['id']}: {infos[p['id']]['status'] or '-'}, {len(infos[p['id']]['subjects'])} recent commits" for p in projects))
    activity = {} if "--no-claude" in sys.argv else write_activity(projects, infos, is_private)
    cards = "\n".join(render_card(p, infos[p["id"]], activity.get(p["id"], "")) for p in projects)
    page = PAGE.format(
        title=html.escape(config["title"]), subtitle=html.escape(config["subtitle"]),
        cards=cards, terms=render_terms(config.get("glossary", [])), refreshed=f"{df.local_now():%B %d, %Y}",
    )
    with open(os.path.join(ROOT, "projects.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("Wrote projects.html")
