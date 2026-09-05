# ap_stats_deadlines.py
# Shows upcoming deadlines for your AP Stats course

import requests
from datetime import datetime, timezone

# ============================================================
# Your Canvas credentials (same as before)
# ============================================================
CANVAS_URL = "https://bbns.instructure.com"
API_TOKEN = "21714~3xNaYnwUyEyx3zhhwZRtQktCP34LH6eJ88ADVRPrn8r9v2TH9fUaC7N4JNC3WAu4"

headers = {
    "Authorization": f"Bearer {API_TOKEN}"
}

# ============================================================
# STEP 1: Find your AP Stats course
# ============================================================
print("Finding your courses...\n")

response = requests.get(f"{CANVAS_URL}/api/v1/courses", headers=headers)
courses = response.json()

# Look for AP Stats course (search for "stat" in the name)
stats_course = None
for course in courses:
    course_name = course.get("name", "").lower()
    if "stat" in course_name:
        stats_course = course
        break

if not stats_course:
    print("Could not find AP Stats course. Here are your courses:")
    for course in courses:
        print(f"  - {course.get('name')} (ID: {course.get('id')})")
    print("\nUpdate the script with the correct course ID.")
    exit()

course_id = stats_course["id"]
course_name = stats_course["name"]
print(f"Found: {course_name} (ID: {course_id})\n")

# ============================================================
# STEP 2: Get all assignments with due dates
# ============================================================
print("Fetching assignments...\n")

assignments_url = f"{CANVAS_URL}/api/v1/courses/{course_id}/assignments"
response = requests.get(assignments_url, headers=headers)
assignments = response.json()

# ============================================================
# STEP 3: Filter and sort by due date
# ============================================================
upcoming = []
now = datetime.now(timezone.utc)

for assignment in assignments:
    due_date_str = assignment.get("due_at")

    if due_date_str:
        # Parse the date string into a datetime object
        due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))

        # Only include future assignments
        if due_date > now:
            upcoming.append({
                "name": assignment.get("name"),
                "due_date": due_date,
                "points": assignment.get("points_possible"),
                "description": assignment.get("description", "")[:200]  # First 200 chars
            })

# Sort by due date (soonest first)
upcoming.sort(key=lambda x: x["due_date"])

# ============================================================
# STEP 4: Display upcoming deadlines
# ============================================================
print("=" * 60)
print(f"UPCOMING DEADLINES - {course_name}")
print("=" * 60)

if not upcoming:
    print("No upcoming assignments found!")
else:
    for assignment in upcoming:
        due = assignment["due_date"]
        days_until = (due - now).days

        # Format the date nicely
        due_str = due.strftime("%A, %B %d at %I:%M %p")

        # Color-code urgency (using text markers)
        if days_until <= 2:
            urgency = "🔴 URGENT"
        elif days_until <= 7:
            urgency = "🟡 Soon"
        else:
            urgency = "🟢 Upcoming"

        print(f"\n{urgency} - Due in {days_until} days")
        print(f"  Assignment: {assignment['name']}")
        print(f"  Due: {due_str}")
        if assignment["points"]:
            print(f"  Points: {assignment['points']}")

print("\n" + "=" * 60)
print(f"Total upcoming assignments: {len(upcoming)}")
print("=" * 60)