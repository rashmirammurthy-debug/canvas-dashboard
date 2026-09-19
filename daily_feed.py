"""Daily curated feed: pulls RSS feeds, has Claude pick the 5 best items, emails them."""
import email
import html
import imaplib
import json
import os
import re
import smtplib
import sys
from calendar import timegm
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr, parsedate_to_datetime
from urllib.parse import quote

import anthropic
import feedparser

MODEL = "claude-sonnet-5"
NUM_ITEMS = 5
LOOKBACK_HOURS = 30
MAX_PER_FEED = 8
MY_SOURCES = "My sources"
MY_SOURCES_LOOKBACK_HOURS = 96
SEEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen.json")
SEEN_LIMIT = 500

FEEDS = {
    "Tech / AI": [
        "https://hnrss.org/frontpage?points=150",
        "https://www.anthropic.com/news/rss.xml",
        "https://simonwillison.net/atom/everything/",
        "https://www.technologyreview.com/feed/",
    ],
    "Data / analytics": [
        "https://towardsdatascience.com/feed",
        "https://www.kdnuggets.com/feed",
        "https://realpython.com/atom.xml",
    ],
    "Business / career": [
        "https://hbr.org/feed",
        "https://www.ben-evans.com/benedictevans?format=rss",
        "https://feeds.a16z.com/a16z.rss",
    ],
    "General reads": [
        "https://aeon.co/feed.rss",
        "https://www.quantamagazine.org/feed/",
        "https://www.theatlantic.com/feed/best-of/",
    ],
}


def load_my_sources():
    """Read feed URLs from sources.txt (one per line, '#' starts a comment)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources.txt")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        lines = (line.split("#", 1)[0].strip() for line in f)
        return [line for line in lines if line]


def load_seen():
    try:
        with open(SEEN_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def save_seen(seen, new_links):
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump((seen + new_links)[-SEEN_LIMIT:], f, indent=0)


def strip_html(raw):
    raw = re.sub(r"(?is)<(style|script).*?</\1>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def decode(value):
    return str(make_header(decode_header(value or "")))


def newsletter_link(html_body, message_id):
    """Prefer a 'view in browser' style link; fall back to opening the email in Gmail."""
    for href, text in re.findall(r'(?is)<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', html_body):
        label = strip_html(text).lower()
        if re.search(r"view|read|browser|online|web", label) and "unsubscribe" not in href.lower():
            return html.unescape(href)
    return "https://mail.google.com/mail/u/0/#search/rfc822msgid%3A" + quote(message_id.strip("<>"))


def fetch_newsletters():
    """Read recent emails from the Gmail label named by NEWSLETTER_LABEL (default 'Newsletters')."""
    user, password = os.environ.get("EMAIL_FROM"), os.environ.get("EMAIL_APP_PASSWORD")
    if not (user and password):
        return []
    label = os.environ.get("NEWSLETTER_LABEL", "Newsletters")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MY_SOURCES_LOOKBACK_HOURS)
    items = []
    try:
        conn = imaplib.IMAP4_SSL("imap.gmail.com")
        conn.login(user, password)
        if conn.select(f'"{label}"', readonly=True)[0] != "OK":
            print(f"Gmail label '{label}' not found; skipping newsletters", file=sys.stderr)
            return []
        since = (cutoff - timedelta(days=1)).strftime("%d-%b-%Y")
        for num in conn.search(None, "SINCE", since)[1][0].split():
            msg = email.message_from_bytes(conn.fetch(num, "(RFC822)")[1][0][1])
            sent = parsedate_to_datetime(msg["Date"])
            if sent.tzinfo is None:
                sent = sent.replace(tzinfo=timezone.utc)
            if sent < cutoff:
                continue
            plain, html_body = "", ""
            for part in msg.walk():
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                if part.get_content_type() == "text/plain":
                    plain += text
                elif part.get_content_type() == "text/html":
                    html_body += text
            name, addr = parseaddr(decode(msg["From"]))
            items.append({
                "category": MY_SOURCES,
                "source": name or addr,
                "title": decode(msg["Subject"]).strip(),
                "link": newsletter_link(html_body, msg["Message-ID"] or ""),
                "summary": (strip_html(html_body) if html_body else plain)[:400],
            })
        conn.logout()
    except Exception as e:
        print(f"Newsletter fetch failed: {e}", file=sys.stderr)
    return items


def fetch_items(seen):
    now = datetime.now(timezone.utc)
    feeds = {**FEEDS, MY_SOURCES: load_my_sources()}
    items = []
    for category, urls in feeds.items():
        # Personal blogs post less often, so look back further for them
        hours = MY_SOURCES_LOOKBACK_HOURS if category == MY_SOURCES else LOOKBACK_HOURS
        cutoff = now - timedelta(hours=hours)
        for url in urls:
            try:
                feed = feedparser.parse(url, agent="daily-feed/1.0")
            except Exception as e:
                print(f"skip {url}: {e}", file=sys.stderr)
                continue
            source = feed.feed.get("title", url)
            for entry in feed.entries[:MAX_PER_FEED]:
                stamp = entry.get("published_parsed") or entry.get("updated_parsed")
                if stamp and datetime.fromtimestamp(timegm(stamp), timezone.utc) < cutoff:
                    continue
                items.append({
                    "category": category,
                    "source": source,
                    "title": entry.get("title", "").strip(),
                    "link": entry.get("link", ""),
                    "summary": html.unescape(entry.get("summary", ""))[:400],
                })
    items += fetch_newsletters()
    items = [i for i in items if i["link"] not in seen]
    for n, item in enumerate(items):
        item["id"] = n
    return items


def pick_items(items):
    """Ask Claude to choose NUM_ITEMS, returning [(item, reason)]."""
    if len(items) <= NUM_ITEMS:
        return [(i, "") for i in items]

    listing = "\n".join(
        f"[{i['id']}] ({i['category']}) {i['title']} - {i['source']}\n    {i['summary'][:200]}"
        for i in items
    )
    prompt = (
        f"Pick the {NUM_ITEMS} most worthwhile items for a curious reader interested in tech/AI, "
        "data/analytics, business/career and general long-form reads. Favor substance and originality "
        "over hype or news churn, and cover at least 3 different categories. "
        f'Items in the "{MY_SOURCES}" category come from sources the reader chose themselves, '
        "so include the best 1-2 of them whenever any are listed. "
        'Reply with only JSON: [{"id": <int>, "reason": "<one sentence on why it is worth reading>"}].\n\n'
        + listing
    )
    try:
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text
        picks = json.loads(text[text.index("["): text.rindex("]") + 1])
        by_id = {i["id"]: i for i in items}
        chosen = [(by_id[p["id"]], p.get("reason", "")) for p in picks if p["id"] in by_id]
        if chosen:
            return chosen[:NUM_ITEMS]
    except Exception as e:
        print(f"Claude ranking failed, falling back: {e}", file=sys.stderr)

    # Fallback: round-robin across categories
    buckets = {}
    for i in items:
        buckets.setdefault(i["category"], []).append(i)
    chosen = []
    while len(chosen) < NUM_ITEMS and any(buckets.values()):
        for b in buckets.values():
            if b and len(chosen) < NUM_ITEMS:
                chosen.append((b.pop(0), ""))
    return chosen


def render_html(picks):
    today = datetime.now().strftime("%A, %B %d")
    rows = []
    for item, reason in picks:
        why = f'<p style="margin:4px 0 0;color:#444">{html.escape(reason)}</p>' if reason else ""
        rows.append(
            f'<div style="margin:0 0 20px">'
            f'<div style="font-size:12px;color:#888;text-transform:uppercase">'
            f'{html.escape(item["category"])} · {html.escape(item["source"])}</div>'
            f'<a href="{html.escape(item["link"])}" style="font-size:17px;font-weight:600;'
            f'color:#1a4fd6;text-decoration:none">{html.escape(item["title"])}</a>{why}</div>'
        )
    return (
        '<div style="font-family:Segoe UI,Arial,sans-serif;max-width:600px;margin:auto">'
        f'<h2 style="margin-bottom:4px">Your daily reads</h2>'
        f'<div style="color:#888;margin-bottom:24px">{today}</div>'
        + "".join(rows)
        + "</div>"
    )


def send_email(body_html):
    sender = os.environ["EMAIL_FROM"]
    recipients = [r.strip() for r in os.environ["EMAIL_TO"].split(",")]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Daily reads - {datetime.now().strftime('%b %d')}"
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(body_html, "html"))
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, os.environ["EMAIL_APP_PASSWORD"])
        server.sendmail(sender, recipients, msg.as_string())


if __name__ == "__main__":
    seen = load_seen()
    items = fetch_items(seen)
    print(f"Fetched {len(items)} new items")
    if not items:
        sys.exit("No items fetched; not sending.")
    picks = pick_items(items)
    body = render_html(picks)
    if "--dry-run" in sys.argv:
        print(body)
    else:
        send_email(body)
        save_seen(seen, [item["link"] for item, _ in picks])
        print("Sent.")
