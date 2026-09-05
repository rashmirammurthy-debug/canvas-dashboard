# all_courses_dashboard.py
# Generates a pretty HTML dashboard with ALL your courses
#
# SETUP: Copy config_template.py to config.py and add your Canvas token

import requests
import re
import webbrowser
import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone

# ============================================================
# Load your Canvas credentials from config file
# ============================================================
try:
    from config import CANVAS_URL, API_TOKEN, EMAIL_FROM, EMAIL_TO, EMAIL_APP_PASSWORD, DASHBOARD_URL, DASHBOARD_PASSWORD
except ImportError:
    print("=" * 60)
    print("ERROR: config.py not found!")
    print("=" * 60)
    print("\nTo set up:")
    print("1. Copy 'config_template.py' to 'config.py'")
    print("2. Edit config.py with your Canvas URL and API token")
    print("\nSee README.md for detailed instructions.")
    print("=" * 60)
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {API_TOKEN}"
}

# Courses to include (search terms - case insensitive)
COURSES_TO_INCLUDE = [
    "physics",   # AP Physics 1
    "history",   # History
    "english",   # English
    "calc",      # Pre Calc BC
    "french",    # AP French
]

# Colors for each course (for visual distinction)
COURSE_COLORS = {
    "physics":  {"primary": "#00d9ff", "secondary": "#0099cc"},  # Cyan
    "history":  {"primary": "#ff6b6b", "secondary": "#cc5555"},  # Red
    "english":  {"primary": "#ffd93d", "secondary": "#ccad31"},  # Yellow
    "calc":     {"primary": "#6bcb77", "secondary": "#55a35f"},  # Green
    "french":   {"primary": "#a66cff", "secondary": "#8555cc"},  # Purple
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

def get_course_color(course_name):
    """Get color scheme for a course"""
    course_lower = course_name.lower()
    for key, colors in COURSE_COLORS.items():
        if key in course_lower:
            return colors
    return {"primary": "#888888", "secondary": "#666666"}

def get_course_emoji(course_name):
    """Get emoji for a course"""
    course_lower = course_name.lower()
    if "physics" in course_lower:
        return "⚛️"
    elif "history" in course_lower:
        return "🏛️"
    elif "english" in course_lower:
        return "📚"
    elif "calc" in course_lower or "math" in course_lower:
        return "📐"
    elif "french" in course_lower:
        return "🇫🇷"
    return "📖"

# ============================================================
# Fetch data from Canvas
# ============================================================
print("Fetching courses from Canvas...")

response = requests.get(f"{CANVAS_URL}/api/v1/courses", headers=headers, params={"per_page": 100})

if response.status_code != 200:
    print(f"ERROR: Canvas API returned status {response.status_code}")
    print(response.text[:500])
    sys.exit(1)

all_courses = response.json()

if not isinstance(all_courses, list):
    print(f"ERROR: Unexpected response from Canvas API:")
    print(str(all_courses)[:500])
    sys.exit(1)

# Filter to courses we want
selected_courses = []
for course in all_courses:
    if not isinstance(course, dict):
        continue
    course_name = course.get("name", "").lower()
    for search_term in COURSES_TO_INCLUDE:
        if search_term in course_name:
            selected_courses.append(course)
            print(f"  ✓ Found: {course.get('name')}")
            break

print(f"\nFound {len(selected_courses)} courses")

# Fetch assignments for each course
all_assignments = []
now = datetime.now(timezone.utc)

for course in selected_courses:
    course_id = course["id"]
    course_name = course["name"]
    print(f"Loading assignments for {course_name}...")

    assignments_url = f"{CANVAS_URL}/api/v1/courses/{course_id}/assignments"
    response = requests.get(assignments_url, headers=headers, params={"per_page": 100})

    if response.status_code == 200:
        assignments = response.json()

        for assignment in assignments:
            due_date_str = assignment.get("due_at")

            # Check if assignment is published/available
            if assignment.get("workflow_state") != "published":
                continue

            if due_date_str:
                due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
                all_assignments.append({
                    "name": assignment.get("name"),
                    "due_date": due_date,
                    "has_due_date": True,
                    "is_past": due_date < now,
                    "points": assignment.get("points_possible"),
                    "description": assignment.get("description", ""),
                    "html_url": assignment.get("html_url", ""),
                    "course_name": course_name,
                    "course_id": course_id,
                })
            else:
                # Include assignments without due dates
                all_assignments.append({
                    "name": assignment.get("name"),
                    "due_date": None,
                    "has_due_date": False,
                    "points": assignment.get("points_possible"),
                    "description": assignment.get("description", ""),
                    "html_url": assignment.get("html_url", ""),
                    "course_name": course_name,
                    "course_id": course_id,
                })

# Fetch calendar events using Planner API (works better with permissions)
all_events = []
print("\nLoading calendar events via Planner API...")

# Build lookup for course names by ID
course_name_lookup = {str(c["id"]): c["name"] for c in selected_courses}
course_ids_set = set(str(c["id"]) for c in selected_courses)

planner_url = f"{CANVAS_URL}/api/v1/planner/items"
params = {
    "per_page": 100,
    "start_date": now.strftime("%Y-%m-%d"),
}
response = requests.get(planner_url, headers=headers, params=params)

if response.status_code == 200:
    planner_items = response.json()

    for item in planner_items:
        plannable_type = item.get("plannable_type", "")
        plannable = item.get("plannable", {})
        course_id = str(item.get("course_id", ""))

        # Only include items from our selected courses
        if course_id not in course_ids_set:
            continue

        # Only include calendar_event types (assignments already fetched above)
        if plannable_type != "calendar_event":
            continue

        course_name = item.get("context_name", course_name_lookup.get(course_id, "Unknown"))
        title = plannable.get("title", "Untitled Event")
        date_str = item.get("plannable_date")
        description = plannable.get("description", "")
        html_url = item.get("html_url", "")

        if date_str:
            event_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if event_date > now:
                all_events.append({
                    "name": title,
                    "due_date": event_date,
                    "has_due_date": True,
                    "points": None,
                    "description": description,
                    "html_url": html_url,
                    "course_name": course_name,
                    "course_id": course_id,
                    "is_event": True,
                })

print(f"Found {len(all_events)} upcoming events")

# Combine assignments and events
all_items = all_assignments + all_events

# Separate items with and without due dates
with_due_date = [a for a in all_items if a.get("has_due_date")]
without_due_date = [a for a in all_items if not a.get("has_due_date")]

# Sort: upcoming items by date ascending, past items at the end by date descending
with_due_date.sort(key=lambda x: (x.get("is_past", False), x["due_date"] if not x.get("is_past") else -x["due_date"].timestamp()))

# Sort items without due dates by course name
without_due_date.sort(key=lambda x: x["course_name"])

print(f"\nTotal upcoming items: {len(all_items)}")
print(f"  - With due dates: {len(with_due_date)} ({len([a for a in with_due_date if a.get('is_event')])} events)")
print(f"  - Without due dates: {len(without_due_date)}")

# ============================================================
# Generate HTML
# ============================================================
print("Generating HTML dashboard...")

now = datetime.now(timezone.utc)

html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Assignments Dashboard</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
            color: #fff;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
        }

        h1 {
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
            background: linear-gradient(90deg, #00d9ff, #ff6b6b, #ffd93d, #6bcb77, #a66cff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .subtitle {
            text-align: center;
            color: #888;
            margin-bottom: 20px;
        }

        .filters {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }

        .filter-btn {
            padding: 8px 16px;
            border-radius: 20px;
            border: 2px solid #444;
            background: transparent;
            color: #fff;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.2s;
        }

        .filter-btn:hover, .filter-btn.active {
            border-color: #00d9ff;
            background: rgba(0, 217, 255, 0.1);
        }

        .filter-btn.active {
            background: rgba(0, 217, 255, 0.2);
        }

        .stats-bar {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }

        .stat-item {
            text-align: center;
        }

        .stat-number {
            font-size: 2em;
            font-weight: bold;
        }

        .stat-label {
            font-size: 0.85em;
            color: #888;
        }

        .assignment {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            border-left: 4px solid var(--course-color, #888);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .assignment:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        }

        .assignment-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 10px;
        }

        .assignment-title {
            font-size: 1.3em;
            font-weight: 600;
        }

        .assignment-title a {
            color: #fff;
            text-decoration: none;
        }

        .assignment-title a:hover {
            text-decoration: underline;
        }

        .badges {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .badge {
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: 600;
            white-space: nowrap;
        }

        .course-badge {
            background: var(--course-color, #888);
            color: #1a1a2e;
        }

        .urgent {
            background: linear-gradient(90deg, #ff4757, #ff3838);
            color: white;
        }

        .soon {
            background: linear-gradient(90deg, #ffa502, #ff9500);
            color: #1a1a2e;
        }

        .upcoming {
            background: linear-gradient(90deg, #2ed573, #00d573);
            color: #1a1a2e;
        }

        .past-due {
            background: #444;
            color: #aaa;
        }

        .due-info {
            display: flex;
            gap: 20px;
            margin-bottom: 12px;
            color: #aaa;
            font-size: 0.9em;
            flex-wrap: wrap;
        }

        .description {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            padding: 14px;
            margin-bottom: 14px;
            color: #bbb;
            line-height: 1.5;
            font-size: 0.95em;
        }

        .links-section {
            margin-top: 14px;
        }

        .links-title {
            font-size: 0.85em;
            color: #666;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .link-card {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--course-color, #0066ff);
            color: #1a1a2e;
            padding: 8px 14px;
            border-radius: 8px;
            text-decoration: none;
            margin-right: 8px;
            margin-bottom: 8px;
            font-weight: 500;
            font-size: 0.9em;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .link-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3);
        }

        .link-card svg {
            width: 16px;
            height: 16px;
        }

        .no-assignments {
            text-align: center;
            padding: 60px;
            color: #888;
        }

        .section-header {
            font-size: 1.1em;
            color: #666;
            margin: 30px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 1px solid #333;
        }

        .last-updated {
            text-align: center;
            color: #555;
            margin-top: 30px;
            font-size: 0.85em;
        }
    </style>
</head>
<body>
    __PASSWORD_GATE__
    <div class="container">
        <h1>📚 My Assignments</h1>
        <p class="subtitle">All upcoming work across your courses</p>

        <div class="filters">
            <button class="filter-btn active" onclick="filterCourse('all')">All Courses</button>
'''

# Add filter buttons for each course
for course in selected_courses:
    emoji = get_course_emoji(course["name"])
    html_content += f'            <button class="filter-btn" onclick="filterCourse(\'{course["id"]}\')">{emoji} {course["name"][:20]}</button>\n'

html_content += '''        </div>

        <div class="filters" style="margin-top: 10px;">
            <button class="filter-btn type-filter active" onclick="filterType('all')">All Types</button>
            <button class="filter-btn type-filter" onclick="filterType('assignment')">📝 Assignments</button>
            <button class="filter-btn type-filter" onclick="filterType('event')">📅 Events</button>
            <button class="filter-btn type-filter" onclick="filterType('due')">⏰ With Due Date</button>
            <button class="filter-btn type-filter" onclick="filterType('nodue')">📋 No Due Date</button>
        </div>

        <div class="stats-bar">
'''

# Calculate stats (only for items with due dates)
urgent_count = sum(1 for a in with_due_date if not a.get("is_past") and (a["due_date"] - now).days <= 2)
week_count = sum(1 for a in with_due_date if not a.get("is_past") and (a["due_date"] - now).days <= 7)
no_date_count = len(without_due_date)
event_count = sum(1 for a in with_due_date if a.get("is_event"))

html_content += f'''
            <div class="stat-item">
                <div class="stat-number" style="color: #ff4757">{urgent_count}</div>
                <div class="stat-label">Due in 2 days</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" style="color: #ffa502">{week_count}</div>
                <div class="stat-label">Due this week</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" style="color: #2ed573">{len(with_due_date)}</div>
                <div class="stat-label">With due dates</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" style="color: #9b59b6">{event_count}</div>
                <div class="stat-label">Events</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" style="color: #888">{no_date_count}</div>
                <div class="stat-label">No due date</div>
            </div>
        </div>

        <div id="assignments-container">
'''

if not with_due_date and not without_due_date:
    html_content += '''
        <div class="no-assignments">
            <h2>🎉 No upcoming assignments!</h2>
            <p>Enjoy your free time.</p>
        </div>
'''
else:
    current_section = None

    # First, show assignments WITH due dates
    for assignment in with_due_date:
        due = assignment["due_date"]
        days_until = (due - now).days

        # Section headers by timeframe
        is_past = assignment.get("is_past", False)
        if is_past:
            section = "⚫ Past Due"
        elif days_until <= 2:
            section = "🔴 Due Very Soon (Next 2 Days)"
        elif days_until <= 7:
            section = "🟡 Due This Week"
        else:
            section = "🟢 Coming Up"

        if section != current_section:
            current_section = section
            html_content += f'        <div class="section-header">{section}</div>\n'

        # Urgency badge
        if is_past:
            urgency_class = "past-due"
            urgency_text = due.strftime("%b %d, %Y")
        elif days_until <= 2:
            urgency_class = "urgent"
            urgency_text = f"{days_until}d" if days_until > 0 else "TODAY"
        elif days_until <= 7:
            urgency_class = "soon"
            urgency_text = f"{days_until}d"
        else:
            urgency_class = "upcoming"
            urgency_text = f"{days_until}d"

        # Check if this is an event (not an assignment)
        is_event = assignment.get("is_event", False)
        event_badge = '<span class="badge" style="background: #9b59b6; color: white;">📅 Event</span>' if is_event else ""

        # Get course color
        colors = get_course_color(assignment["course_name"])
        emoji = get_course_emoji(assignment["course_name"])

        # Format date
        due_str = due.strftime("%A, %b %d at %I:%M %p")

        # Get description and links
        description_html = assignment["description"] or ""
        description_text = html_to_text(description_html)
        links = extract_links(description_html)

        # Build assignment card
        item_type = "event" if is_event else "assignment"
        html_content += f'''
        <div class="assignment" style="--course-color: {colors['primary']}" data-course="{assignment['course_id']}" data-type="{item_type}" data-hasdue="true">
            <div class="assignment-header">
                <div class="assignment-title">
                    <a href="{assignment['html_url']}" target="_blank">{assignment['name']}</a>
                </div>
                <div class="badges">
                    <span class="badge course-badge">{emoji} {assignment['course_name'][:15]}</span>
                    {event_badge}
                    <span class="badge {urgency_class}">{urgency_text}</span>
                </div>
            </div>

            <div class="due-info">
                <span>📅 {due_str}</span>
                {"<span>⭐ " + str(assignment['points']) + " pts</span>" if assignment['points'] else ""}
            </div>
'''

        if description_text:
            safe_desc = description_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            # Truncate long descriptions
            if len(safe_desc) > 300:
                safe_desc = safe_desc[:300] + "..."
            html_content += f'''
            <div class="description">{safe_desc}</div>
'''

        if links:
            html_content += '''
            <div class="links-section">
                <div class="links-title">📎 Links</div>
'''
            for link in links:
                if "google.com/document" in link["url"]:
                    icon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/></svg>'
                elif "google.com/spreadsheet" in link["url"]:
                    icon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19,3H5C3.9,3 3,3.9 3,5V19C3,20.1 3.9,21 5,21H19C20.1,21 21,20.1 21,19V5C21,3.9 20.1,3 19,3Z"/></svg>'
                else:
                    icon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.89 3,5V19C3,20.1 3.89,21 5,21H19C20.1,21 21,20.1 21,19V12H19V19Z"/></svg>'

                html_content += f'''
                <a href="{link['url']}" target="_blank" class="link-card">{icon} {link['text']}</a>
'''
            html_content += '''
            </div>
'''

        html_content += '''
        </div>
'''

    # Now show assignments WITHOUT due dates
    if without_due_date:
        html_content += '        <div class="section-header">📋 No Due Date Set</div>\n'

        for assignment in without_due_date:
            # Get course color
            colors = get_course_color(assignment["course_name"])
            emoji = get_course_emoji(assignment["course_name"])

            # Get description and links
            description_html = assignment["description"] or ""
            description_text = html_to_text(description_html)
            links = extract_links(description_html)

            # Build assignment card
            is_event = assignment.get("is_event", False)
            item_type = "event" if is_event else "assignment"
            event_badge = '<span class="badge" style="background: #9b59b6; color: white;">📅 Event</span>' if is_event else ""
            html_content += f'''
        <div class="assignment" style="--course-color: {colors['primary']}" data-course="{assignment['course_id']}" data-type="{item_type}" data-hasdue="false">
            <div class="assignment-header">
                <div class="assignment-title">
                    <a href="{assignment['html_url']}" target="_blank">{assignment['name']}</a>
                </div>
                <div class="badges">
                    <span class="badge course-badge">{emoji} {assignment['course_name'][:15]}</span>
                    {event_badge}
                    <span class="badge" style="background: #555; color: #fff;">No due date</span>
                </div>
            </div>

            <div class="due-info">
                {"<span>⭐ " + str(assignment['points']) + " pts</span>" if assignment['points'] else "<span>No points assigned</span>"}
            </div>
'''

            if description_text:
                safe_desc = description_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
                if len(safe_desc) > 300:
                    safe_desc = safe_desc[:300] + "..."
                html_content += f'''
            <div class="description">{safe_desc}</div>
'''

            if links:
                html_content += '''
            <div class="links-section">
                <div class="links-title">📎 Links</div>
'''
                for link in links:
                    if "google.com/document" in link["url"]:
                        icon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/></svg>'
                    elif "google.com/spreadsheet" in link["url"]:
                        icon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19,3H5C3.9,3 3,3.9 3,5V19C3,20.1 3.9,21 5,21H19C20.1,21 21,20.1 21,19V5C21,3.9 20.1,3 19,3Z"/></svg>'
                    else:
                        icon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.89 3,5V19C3,20.1 3.89,21 5,21H19C20.1,21 21,20.1 21,19V12H19V19Z"/></svg>'

                    html_content += f'''
                <a href="{link['url']}" target="_blank" class="link-card">{icon} {link['text']}</a>
'''
                html_content += '''
            </div>
'''

            html_content += '''
        </div>
'''

# Add JavaScript for filtering and footer
html_content += f'''
        </div>

        <p class="last-updated">Last updated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
    </div>

    <script>
        // Track current filters
        let currentCourse = 'all';
        let currentType = 'all';

        function filterCourse(courseId) {{
            currentCourse = courseId;

            // Update active button (only course buttons, not type buttons)
            document.querySelectorAll('.filter-btn:not(.type-filter)').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            applyFilters();
        }}

        function filterType(type) {{
            currentType = type;

            // Update active button (only type buttons)
            document.querySelectorAll('.type-filter').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            applyFilters();
        }}

        function applyFilters() {{
            // Filter assignments based on both course and type
            document.querySelectorAll('.assignment').forEach(card => {{
                let showCourse = (currentCourse === 'all' || card.dataset.course === currentCourse);
                let showType = true;

                if (currentType === 'assignment') {{
                    showType = card.dataset.type === 'assignment';
                }} else if (currentType === 'event') {{
                    showType = card.dataset.type === 'event';
                }} else if (currentType === 'due') {{
                    showType = card.dataset.hasdue === 'true';
                }} else if (currentType === 'nodue') {{
                    showType = card.dataset.hasdue === 'false';
                }}

                card.style.display = (showCourse && showType) ? 'block' : 'none';
            }});

            // Show/hide section headers based on visible assignments
            document.querySelectorAll('.section-header').forEach(header => {{
                let nextEl = header.nextElementSibling;
                let hasVisible = false;
                while (nextEl && !nextEl.classList.contains('section-header')) {{
                    if (nextEl.classList.contains('assignment') && nextEl.style.display !== 'none') {{
                        hasVisible = true;
                        break;
                    }}
                    nextEl = nextEl.nextElementSibling;
                }}
                header.style.display = hasVisible ? 'block' : 'none';
            }});
        }}
    </script>
</body>
</html>
'''

# ============================================================
# Save and open HTML file
# ============================================================
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "my_dashboard.html")

import hashlib
pw_hash = hashlib.sha256(DASHBOARD_PASSWORD.encode()).hexdigest()
password_gate = f"""
    <div id="pw-gate" style="display:flex;position:fixed;inset:0;background:#1a1a2e;z-index:9999;align-items:center;justify-content:center;">
      <div style="text-align:center;padding:40px;background:#16213e;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,.5);">
        <div style="font-size:2em;margin-bottom:12px;">&#128274;</div>
        <h2 style="color:#fff;margin-bottom:20px;font-family:sans-serif;">Canvas Dashboard</h2>
        <input id="pw-input" type="password" placeholder="Enter password" autofocus
          style="padding:12px 16px;border-radius:8px;border:none;font-size:1em;width:220px;display:block;margin:0 auto 12px;">
        <button onclick="checkPw()"
          style="padding:12px 32px;background:#00d9ff;color:#1a1a2e;border:none;border-radius:8px;font-size:1em;font-weight:700;cursor:pointer;">
          Enter
        </button>
        <p id="pw-error" style="color:#ff6b6b;margin-top:12px;font-family:sans-serif;display:none;">Wrong password</p>
      </div>
    </div>
    <script>
      const HASH = "{pw_hash}";
      async function sha256(str) {{
        const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
        return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2,"0")).join("");
      }}
      async function checkPw() {{
        const h = await sha256(document.getElementById("pw-input").value);
        if (h === HASH) {{
          document.getElementById("pw-gate").style.display = "none";
          sessionStorage.setItem("canvas-auth", h);
        }} else {{
          document.getElementById("pw-error").style.display = "block";
        }}
      }}
      document.getElementById("pw-input").addEventListener("keydown", e => e.key === "Enter" && checkPw());
      (async () => {{
        if (sessionStorage.getItem("canvas-auth") === HASH)
          document.getElementById("pw-gate").style.display = "none";
      }})();
    </script>"""

html_content = html_content.replace("    __PASSWORD_GATE__", password_gate)

with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"\n✅ Dashboard saved to: {output_path}")
print("Opening in browser...")

webbrowser.open(f"file://{output_path}")

# Auto-push to GitHub Pages
import subprocess
script_dir = os.path.dirname(os.path.abspath(__file__))
print("\nPushing to GitHub...")
subprocess.run(["git", "add", "my_dashboard.html"], cwd=script_dir)
subprocess.run(["git", "commit", "-m", "update dashboard"], cwd=script_dir)
subprocess.run(["git", "push"], cwd=script_dir)
print("✅ Dashboard pushed to GitHub Pages")

# ============================================================
# Send daily email digest
# ============================================================
def send_email_digest(assignments_with_due, assignments_no_due):
    upcoming = [a for a in assignments_with_due if not a.get("is_past")]
    past     = [a for a in assignments_with_due if a.get("is_past")]

    def urgency_color(a):
        days = (a["due_date"] - now).days
        if days <= 2:   return "#e74c3c"
        if days <= 7:   return "#f39c12"
        return "#27ae60"

    def fmt_date(a):
        return a["due_date"].astimezone().strftime("%a %b %d")

    rows_upcoming = ""
    for a in upcoming:
        color = urgency_color(a)
        emoji = get_course_emoji(a["course_name"])
        rows_upcoming += f"""
        <tr>
          <td style="padding:10px 8px;border-bottom:1px solid #2a2a3e;">
            <a href="{a['html_url']}" style="color:#fff;text-decoration:none;font-weight:600;">{a['name']}</a><br>
            <span style="color:#aaa;font-size:13px;">{emoji} {a['course_name']}</span>
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #2a2a3e;text-align:right;white-space:nowrap;">
            <span style="background:{color};color:#fff;padding:3px 10px;border-radius:12px;font-size:13px;">{fmt_date(a)}</span>
          </td>
        </tr>"""

    rows_past = ""
    for a in past:
        emoji = get_course_emoji(a["course_name"])
        rows_past += f"""
        <tr>
          <td style="padding:10px 8px;border-bottom:1px solid #2a2a3e;color:#888;">
            <a href="{a['html_url']}" style="color:#888;text-decoration:none;">{a['name']}</a><br>
            <span style="color:#666;font-size:13px;">{emoji} {a['course_name']}</span>
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #2a2a3e;text-align:right;white-space:nowrap;">
            <span style="background:#444;color:#aaa;padding:3px 10px;border-radius:12px;font-size:13px;">{fmt_date(a)}</span>
          </td>
        </tr>"""

    past_section = f"""
      <h3 style="color:#666;margin:24px 0 8px;">Past Due</h3>
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
        {rows_past}
      </table>""" if rows_past else ""

    no_upcoming_msg = "<p style='color:#aaa;'>No upcoming assignments right now.</p>" if not rows_upcoming else ""

    body = f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0f0f1a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#fff;">
  <div style="max-width:560px;margin:0 auto;padding:24px 16px;">
    <h2 style="color:#00d9ff;margin:0 0 4px;">📚 Canvas Digest</h2>
    <p style="color:#aaa;margin:0 0 20px;font-size:14px;">{datetime.now().strftime("%A, %B %d")}</p>

    <h3 style="color:#fff;margin:0 0 8px;">Upcoming</h3>
    {no_upcoming_msg}
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
      {rows_upcoming}
    </table>

    {past_section}

    <div style="margin-top:28px;text-align:center;">
      <a href="{DASHBOARD_URL}" style="display:inline-block;padding:12px 28px;background:#00d9ff;color:#1a1a2e;text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;">
        View Full Dashboard →
      </a>
      <p style="color:#555;font-size:12px;margin-top:10px;">Password: <code style="color:#888;">{DASHBOARD_PASSWORD}</code></p>
    </div>
  </div>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📚 Canvas: {len(upcoming)} upcoming assignment{'s' if len(upcoming) != 1 else ''} — {datetime.now().strftime('%b %d')}"
    recipients = EMAIL_TO if isinstance(EMAIL_TO, list) else [EMAIL_TO]
    msg["From"] = EMAIL_FROM
    msg["To"]   = ", ".join(recipients)
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
        print("✅ Email digest sent to", ", ".join(recipients))
    except Exception as e:
        print(f"⚠️  Email failed: {e}")

print("\nSending email digest...")
send_email_digest(with_due_date, without_due_date)