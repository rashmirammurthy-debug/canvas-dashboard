# ap_stats_detailed.py
# Detailed view of AP Stats assignments with links and unit content

import requests
import re
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
# Helper: Extract links from HTML using regex (more reliable)
# ============================================================
def extract_links(html):
    """Extract all links from HTML content using regex"""
    if not html:
        return []

    links = []
    # Pattern to match <a href="URL">Link Text</a>
    pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>'
    matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)

    for url, text in matches:
        links.append({
            "url": url.strip(),
            "text": text.strip() or "Link"
        })

    return links

def html_to_text(html):
    """Convert HTML to plain text"""
    if not html:
        return ""
    # Remove HTML tags but keep the text
    text = re.sub(r'<br\s*/?>', '\n', html)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    # Clean up extra whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    # Decode HTML entities
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&nbsp;', ' ')
    return text.strip()

def find_unit_references(text):
    """Find unit references like 'Unit 6.2' or 'Chapter 5'"""
    patterns = [
        r'[Uu]nit\s*(\d+\.?\d*)',
        r'[Cc]hapter\s*(\d+\.?\d*)',
        r'[Ss]ection\s*(\d+\.?\d*)',
        r'[Ll]esson\s*(\d+\.?\d*)',
    ]
    references = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            references.append(match)
    return references

# ============================================================
# STEP 1: Find AP Stats course
# ============================================================
print("Connecting to Canvas...\n")

response = requests.get(f"{CANVAS_URL}/api/v1/courses", headers=headers)
courses = response.json()

stats_course = None
for course in courses:
    course_name = course.get("name", "").lower()
    if "stat" in course_name:
        stats_course = course
        break

if not stats_course:
    print("Could not find AP Stats course.")
    exit()

course_id = stats_course["id"]
course_name = stats_course["name"]
print(f"Course: {course_name}\n")

# ============================================================
# STEP 2: Get ALL modules (units) and their content
# ============================================================
print("Loading course modules (units)...\n")

modules_url = f"{CANVAS_URL}/api/v1/courses/{course_id}/modules"
params = {"include[]": "items", "per_page": 100}
response = requests.get(modules_url, headers=headers, params=params)
modules = response.json() if response.status_code == 200 else []

# Build a lookup dictionary for modules
module_lookup = {}
module_items = {}

for module in modules:
    module_name = module.get("name", "")
    module_id = module.get("id")

    # Store module info
    module_lookup[module_id] = module_name

    # Get items in this module
    items_url = f"{CANVAS_URL}/api/v1/courses/{course_id}/modules/{module_id}/items"
    items_response = requests.get(items_url, headers=headers, params={"per_page": 100})
    if items_response.status_code == 200:
        items = items_response.json()
        module_items[module_name] = items

        # Also index by unit number if present
        unit_match = re.search(r'(\d+\.?\d*)', module_name)
        if unit_match:
            module_items[unit_match.group(1)] = items

print(f"Found {len(modules)} modules/units\n")

# ============================================================
# STEP 3: Get all course files
# ============================================================
print("Loading course files...\n")

files_url = f"{CANVAS_URL}/api/v1/courses/{course_id}/files"
response = requests.get(files_url, headers=headers, params={"per_page": 100})
all_files = response.json() if response.status_code == 200 else []

print(f"Found {len(all_files)} files\n")

# ============================================================
# STEP 4: Get assignments with FULL details
# ============================================================
print("Loading assignments...\n")

assignments_url = f"{CANVAS_URL}/api/v1/courses/{course_id}/assignments"
params = {"per_page": 100, "order_by": "due_at"}
response = requests.get(assignments_url, headers=headers, params=params)
assignments = response.json()

# Filter to upcoming assignments
upcoming = []
now = datetime.now(timezone.utc)

for assignment in assignments:
    due_date_str = assignment.get("due_at")
    if due_date_str:
        due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
        if due_date > now:
            upcoming.append({
                "name": assignment.get("name"),
                "due_date": due_date,
                "points": assignment.get("points_possible"),
                "description": assignment.get("description", ""),  # This is HTML
                "submission_types": assignment.get("submission_types", []),
                "html_url": assignment.get("html_url", ""),
                "id": assignment.get("id")
            })

upcoming.sort(key=lambda x: x["due_date"])

# ============================================================
# STEP 5: Display detailed assignment info
# ============================================================
print("=" * 70)
print(f"DETAILED ASSIGNMENTS - {course_name}")
print("=" * 70)

for i, assignment in enumerate(upcoming, 1):
    due = assignment["due_date"]
    days_until = (due - now).days

    # Urgency indicator
    if days_until <= 2:
        urgency = "🔴 URGENT"
    elif days_until <= 7:
        urgency = "🟡 THIS WEEK"
    else:
        urgency = "🟢 UPCOMING"

    print(f"\n{'─' * 70}")
    print(f"#{i} {urgency} | Due in {days_until} days")
    print(f"{'─' * 70}")
    print(f"📝 ASSIGNMENT: {assignment['name']}")
    print(f"📅 DUE: {due.strftime('%A, %B %d at %I:%M %p')}")
    if assignment['points']:
        print(f"⭐ POINTS: {assignment['points']}")
    print(f"🔗 CANVAS LINK: {assignment['html_url']}")

    # Get description HTML
    description_html = assignment["description"] or ""
    description_text = html_to_text(description_html)

    if description_text:
        print(f"\n📋 DESCRIPTION:")
        print("-" * 40)
        for line in description_text.split('\n'):
            if line.strip():
                print(f"   {line}")

    # Extract and show links from the HTML
    links = extract_links(description_html)

    if links:
        print(f"\n🔗 LINKS IN ASSIGNMENT ({len(links)} found):")
        print("-" * 40)
        for link in links:
            print(f"   📎 {link['text']}")
            print(f"      {link['url']}")
    else:
        print(f"\n🔗 NO LINKS FOUND IN DESCRIPTION")
        if description_html:
            print(f"   (Raw HTML length: {len(description_html)} chars)")

    # Find unit references
    unit_refs = find_unit_references(assignment['name'] + " " + description_text)
    if unit_refs:
        print(f"\n📚 UNIT REFERENCES FOUND:")
        print("-" * 40)
        for unit_num in set(unit_refs):
            print(f"   Unit {unit_num}")
            # Look up module content for this unit
            if unit_num in module_items:
                items = module_items[unit_num]
                print(f"   Content in this unit:")
                for item in items[:5]:  # Show first 5 items
                    item_title = item.get('title', 'Unknown')
                    item_type = item.get('type', '')
                    print(f"      - {item_title} ({item_type})")
                if len(items) > 5:
                    print(f"      ... and {len(items) - 5} more items")

    # Find related files (homework sheets, etc.)
    related_files = []
    for f in all_files:
        file_name = f.get('display_name', '').lower()
        # Match if file name contains similar keywords
        if any(word in file_name for word in ['homework', 'hw', 'worksheet', 'practice']):
            # Check if unit number matches
            for unit_num in unit_refs:
                if unit_num in file_name or f"unit{unit_num}" in file_name.replace(" ", ""):
                    related_files.append(f)
                    break

    if related_files:
        print(f"\n📎 POSSIBLY RELATED FILES:")
        print("-" * 40)
        for f in related_files[:5]:
            print(f"   • {f.get('display_name')}")
            print(f"     Download: {f.get('url')}")

# ============================================================
# STEP 6: Show all modules overview
# ============================================================
print(f"\n\n{'=' * 70}")
print("ALL COURSE MODULES (UNITS)")
print("=" * 70)

for module in modules:
    module_name = module.get("name", "Unknown")
    items_count = module.get("items_count", 0)
    print(f"\n📁 {module_name} ({items_count} items)")

    # Show items in this module
    if module_name in module_items:
        for item in module_items[module_name][:3]:
            item_title = item.get('title', 'Unknown')
            item_type = item.get('type', '')
            print(f"   • {item_title} [{item_type}]")
        if len(module_items[module_name]) > 3:
            print(f"   ... and more")

print(f"\n{'=' * 70}")
print("Done! Run this script anytime to see updated deadlines.")
print("=" * 70)