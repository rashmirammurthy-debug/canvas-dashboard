# debug_assignment.py
# Debug script to see raw assignment data from Canvas

import requests
import json
from datetime import datetime, timezone

# ============================================================
# Your Canvas credentials
# ============================================================
CANVAS_URL = "https://bbns.instructure.com"
API_TOKEN = "21714~3xNaYnwUyEyx3zhhwZRtQktCP34LH6eJ88ADVRPrn8r9v2TH9fUaC7N4JNC3WAu4"

headers = {
    "Authorization": f"Bearer {API_TOKEN}"
}

# Find AP Stats course
response = requests.get(f"{CANVAS_URL}/api/v1/courses", headers=headers)
courses = response.json()

stats_course = None
for course in courses:
    if "stat" in course.get("name", "").lower():
        stats_course = course
        break

if not stats_course:
    print("Could not find AP Stats course")
    exit()

course_id = stats_course["id"]
print(f"Course: {stats_course['name']}\n")

# Get assignments
assignments_url = f"{CANVAS_URL}/api/v1/courses/{course_id}/assignments"
response = requests.get(assignments_url, headers=headers, params={"per_page": 100})
assignments = response.json()

# Filter to upcoming and get first few
now = datetime.now(timezone.utc)
upcoming = []

for a in assignments:
    due = a.get("due_at")
    if due:
        due_date = datetime.fromisoformat(due.replace("Z", "+00:00"))
        if due_date > now:
            upcoming.append(a)

upcoming.sort(key=lambda x: x.get("due_at", ""))

# Show raw data for first 3 upcoming assignments
print("=" * 70)
print("RAW ASSIGNMENT DATA (first 3 upcoming)")
print("=" * 70)

for i, assignment in enumerate(upcoming[:3], 1):
    print(f"\n{'─' * 70}")
    print(f"ASSIGNMENT #{i}: {assignment.get('name')}")
    print(f"{'─' * 70}")

    # Show all keys available
    print(f"\nAvailable fields: {list(assignment.keys())}")

    # Show description field specifically
    print(f"\n--- 'description' field ---")
    desc = assignment.get("description")
    if desc:
        print(f"Type: {type(desc)}")
        print(f"Length: {len(desc)} characters")
        print(f"\nRAW HTML CONTENT:")
        print(desc[:2000])  # First 2000 chars
        if len(desc) > 2000:
            print(f"\n... (truncated, {len(desc) - 2000} more characters)")
    else:
        print("Description is None or empty")

    # Check for other fields that might contain links
    print(f"\n--- Other potentially useful fields ---")
    for key in ['html_url', 'url', 'submission_types', 'external_tool_tag_attributes']:
        if key in assignment and assignment[key]:
            print(f"{key}: {assignment[key]}")

    print()

# Also check if there's a separate endpoint for assignment content
print("\n" + "=" * 70)
print("CHECKING INDIVIDUAL ASSIGNMENT ENDPOINT")
print("=" * 70)

if upcoming:
    first_assignment = upcoming[0]
    assignment_id = first_assignment.get("id")

    # Try getting single assignment with more details
    single_url = f"{CANVAS_URL}/api/v1/courses/{course_id}/assignments/{assignment_id}"
    response = requests.get(single_url, headers=headers)
    single_assignment = response.json()

    print(f"\nSingle assignment fetch for: {single_assignment.get('name')}")
    print(f"\nDescription from single fetch:")
    desc = single_assignment.get("description")
    if desc:
        print(desc[:2000])
    else:
        print("No description")