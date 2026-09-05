# ap_stats_html.py
# Generates a pretty HTML page with your AP Stats assignments

import requests
import re
import webbrowser
import os
from datetime import datetime, timezone

# ============================================================
# Your Canvas credentials
# ============================================================
CANVAS_URL = "https://bbns.instructure.com"
API_TOKEN = "21714~3xNaYnwUyEyx3zhhwZRtQktCP34LH6eJ88ADVRPrn8r9v2TH9fUaC7N4JNC3WAu4"

headers = {
    "Authorization": f"Bearer {API_TOKEN}"
}

# ============================================================
# Helper functions
# ============================================================
def extract_links(html):
    """Extract all links from HTML content"""
    if not html:
        return []
    pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>'
    matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
    return [{"url": url.strip(), "text": text.strip() or "Link"} for url, text in matches]

def html_to_text(html):
    """Convert HTML to plain text"""
    if not html:
        return ""
    text = re.sub(r'<br\s*/?>', '\n', html)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

# ============================================================
# Fetch data from Canvas
# ============================================================
print("Fetching data from Canvas...")

# Get courses
response = requests.get(f"{CANVAS_URL}/api/v1/courses", headers=headers)
courses = response.json()

stats_course = None
for course in courses:
    if "stat" in course.get("name", "").lower():
        stats_course = course
        break

if not stats_course:
    print("Could not find AP Stats course.")
    exit()

course_id = stats_course["id"]
course_name = stats_course["name"]
print(f"Found: {course_name}")

# Get assignments
print("Loading assignments...")
assignments_url = f"{CANVAS_URL}/api/v1/courses/{course_id}/assignments"
response = requests.get(assignments_url, headers=headers, params={"per_page": 100})
assignments = response.json()

# Filter upcoming
now = datetime.now(timezone.utc)
upcoming = []

for assignment in assignments:
    due_date_str = assignment.get("due_at")
    if due_date_str:
        due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
        if due_date > now:
            upcoming.append({
                "name": assignment.get("name"),
                "due_date": due_date,
                "points": assignment.get("points_possible"),
                "description": assignment.get("description", ""),
                "html_url": assignment.get("html_url", ""),
            })

upcoming.sort(key=lambda x: x["due_date"])
print(f"Found {len(upcoming)} upcoming assignments")

# ============================================================
# Generate HTML
# ============================================================
print("Generating HTML...")

html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AP Stats Assignments</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
            color: #fff;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}

        h1 {{
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .subtitle {{
            text-align: center;
            color: #888;
            margin-bottom: 30px;
        }}

        .assignment {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .assignment:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 40px rgba(0, 217, 255, 0.1);
        }}

        .assignment-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .assignment-title {{
            font-size: 1.4em;
            font-weight: 600;
            color: #fff;
        }}

        .assignment-title a {{
            color: #00d9ff;
            text-decoration: none;
        }}

        .assignment-title a:hover {{
            text-decoration: underline;
        }}

        .urgency-badge {{
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            white-space: nowrap;
        }}

        .urgent {{
            background: linear-gradient(90deg, #ff4757, #ff3838);
            color: white;
        }}

        .soon {{
            background: linear-gradient(90deg, #ffa502, #ff9500);
            color: #1a1a2e;
        }}

        .upcoming {{
            background: linear-gradient(90deg, #2ed573, #00d573);
            color: #1a1a2e;
        }}

        .due-info {{
            display: flex;
            gap: 20px;
            margin-bottom: 16px;
            color: #aaa;
            font-size: 0.95em;
            flex-wrap: wrap;
        }}

        .due-info span {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .description {{
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 16px;
            color: #ccc;
            line-height: 1.6;
        }}

        .links-section {{
            margin-top: 16px;
        }}

        .links-title {{
            font-size: 0.9em;
            color: #888;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .link-card {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(90deg, #0066ff, #0099ff);
            color: white;
            padding: 10px 18px;
            border-radius: 10px;
            text-decoration: none;
            margin-right: 10px;
            margin-bottom: 10px;
            font-weight: 500;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .link-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 102, 255, 0.4);
        }}

        .link-card svg {{
            width: 18px;
            height: 18px;
        }}

        .no-assignments {{
            text-align: center;
            padding: 60px;
            color: #888;
        }}

        .last-updated {{
            text-align: center;
            color: #555;
            margin-top: 30px;
            font-size: 0.85em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 {course_name}</h1>
        <p class="subtitle">Upcoming Assignments</p>
'''

if not upcoming:
    html_content += '''
        <div class="no-assignments">
            <h2>🎉 No upcoming assignments!</h2>
            <p>Enjoy your free time.</p>
        </div>
'''
else:
    for assignment in upcoming:
        due = assignment["due_date"]
        days_until = (due - now).days

        # Determine urgency
        if days_until <= 2:
            urgency_class = "urgent"
            urgency_text = f"🔴 Due in {days_until} day{'s' if days_until != 1 else ''}"
        elif days_until <= 7:
            urgency_class = "soon"
            urgency_text = f"🟡 Due in {days_until} days"
        else:
            urgency_class = "upcoming"
            urgency_text = f"🟢 Due in {days_until} days"

        # Format date
        due_str = due.strftime("%A, %B %d at %I:%M %p")

        # Get description and links
        description_html = assignment["description"] or ""
        description_text = html_to_text(description_html)
        links = extract_links(description_html)

        # Build assignment card
        html_content += f'''
        <div class="assignment">
            <div class="assignment-header">
                <div class="assignment-title">
                    <a href="{assignment['html_url']}" target="_blank">{assignment['name']}</a>
                </div>
                <span class="urgency-badge {urgency_class}">{urgency_text}</span>
            </div>

            <div class="due-info">
                <span>📅 {due_str}</span>
                {"<span>⭐ " + str(assignment['points']) + " points</span>" if assignment['points'] else ""}
            </div>
'''

        if description_text:
            # Escape HTML entities in description text
            safe_desc = description_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            html_content += f'''
            <div class="description">
                {safe_desc}
            </div>
'''

        if links:
            html_content += '''
            <div class="links-section">
                <div class="links-title">📎 Attached Links</div>
'''
            for link in links:
                # Icon based on link type
                if "google.com/document" in link["url"]:
                    icon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20M9,13V15H15V13H9M9,17V19H13V17H9Z"/></svg>'
                elif "google.com/spreadsheet" in link["url"]:
                    icon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19,3H5C3.9,3 3,3.9 3,5V19C3,20.1 3.9,21 5,21H19C20.1,21 21,20.1 21,19V5C21,3.9 20.1,3 19,3M9,17H7V15H9V17M9,13H7V11H9V13M9,9H7V7H9V9M13,17H11V15H13V17M13,13H11V11H13V13M13,9H11V7H13V9M17,17H15V15H17V17M17,13H15V11H17V13M17,9H15V7H17V9Z"/></svg>'
                else:
                    icon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.89 3,5V19C3,20.1 3.89,21 5,21H19C20.1,21 21,20.1 21,19V12H19V19Z"/></svg>'

                html_content += f'''
                <a href="{link['url']}" target="_blank" class="link-card">
                    {icon}
                    {link['text']}
                </a>
'''
            html_content += '''
            </div>
'''

        html_content += '''
        </div>
'''

# Footer
html_content += f'''
        <p class="last-updated">Last updated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
    </div>
</body>
</html>
'''

# ============================================================
# Save and open HTML file
# ============================================================
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ap_stats_dashboard.html")

with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"\n✅ Dashboard saved to: {output_path}")
print("Opening in browser...")

# Open in default browser
webbrowser.open(f"file://{output_path}")