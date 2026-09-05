# debug_events.py
# Debug script to see all calendar events from Canvas

import requests
from datetime import datetime, timezone, timedelta

CANVAS_URL = "https://bbns.instructure.com"
API_TOKEN = "21714~3xNaYnwUyEyx3zhhwZRtQktCP34LH6eJ88ADVRPrn8r9v2TH9fUaC7N4JNC3WAu4"

headers = {"Authorization": f"Bearer {API_TOKEN}"}

print("=" * 70)
print("DEBUGGING CANVAS EVENTS")
print("=" * 70)

# Get all courses first
response = requests.get(f"{CANVAS_URL}/api/v1/courses", headers=headers, params={"per_page": 100})
courses = response.json()

print(f"\nFound {len(courses)} total courses")

# Build context codes for all courses
context_codes = [f"course_{c['id']}" for c in courses]
print(f"Context codes: {context_codes[:5]}...")

# Try different ways to fetch events
now = datetime.now(timezone.utc)

print("\n" + "=" * 70)
print("METHOD 1: Calendar events with type=event")
print("=" * 70)

events_url = f"{CANVAS_URL}/api/v1/calendar_events"
params = {
    "context_codes[]": context_codes,
    "per_page": 100,
    "type": "event",
    "start_date": (now - timedelta(days=7)).strftime("%Y-%m-%d"),
    "end_date": (now + timedelta(days=60)).strftime("%Y-%m-%d"),
}
response = requests.get(events_url, headers=headers, params=params)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    events = response.json()
    print(f"Found {len(events)} events")
    for e in events[:10]:
        print(f"  - {e.get('title')} | {e.get('start_at')} | Context: {e.get('context_code')}")
else:
    print(f"Error: {response.text[:500]}")

print("\n" + "=" * 70)
print("METHOD 2: Calendar events with type=assignment")
print("=" * 70)

params["type"] = "assignment"
response = requests.get(events_url, headers=headers, params=params)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    events = response.json()
    print(f"Found {len(events)} assignment events")
    for e in events[:10]:
        print(f"  - {e.get('title')} | {e.get('start_at')} | Context: {e.get('context_code')}")

print("\n" + "=" * 70)
print("METHOD 3: Calendar events without type filter (all)")
print("=" * 70)

params.pop("type", None)
response = requests.get(events_url, headers=headers, params=params)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    events = response.json()
    print(f"Found {len(events)} total calendar items")
    for e in events[:15]:
        event_type = e.get('type', 'unknown')
        print(f"  [{event_type}] {e.get('title')} | {e.get('start_at')}")

print("\n" + "=" * 70)
print("METHOD 4: User's personal calendar events")
print("=" * 70)

params = {
    "context_codes[]": ["user_" + str(c.get('id', '')) for c in courses[:1]] + context_codes,
    "per_page": 100,
    "start_date": (now - timedelta(days=7)).strftime("%Y-%m-%d"),
    "end_date": (now + timedelta(days=60)).strftime("%Y-%m-%d"),
}

# Also try to get the user ID
user_response = requests.get(f"{CANVAS_URL}/api/v1/users/self", headers=headers)
if user_response.status_code == 200:
    user_id = user_response.json().get("id")
    print(f"User ID: {user_id}")
    params["context_codes[]"] = [f"user_{user_id}"] + context_codes

response = requests.get(events_url, headers=headers, params=params)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    events = response.json()
    print(f"Found {len(events)} items including personal events")
    for e in events[:15]:
        event_type = e.get('type', 'unknown')
        context = e.get('context_code', 'unknown')
        print(f"  [{event_type}] {e.get('title')} | Context: {context}")

print("\n" + "=" * 70)
print("METHOD 5: Planner items (newer Canvas API)")
print("=" * 70)

planner_url = f"{CANVAS_URL}/api/v1/planner/items"
params = {
    "per_page": 100,
    "start_date": now.strftime("%Y-%m-%d"),
}
response = requests.get(planner_url, headers=headers, params=params)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    items = response.json()
    print(f"Found {len(items)} planner items")
    for item in items[:15]:
        plannable_type = item.get('plannable_type', 'unknown')
        plannable = item.get('plannable', {})
        title = plannable.get('title') or plannable.get('name') or item.get('plannable_id')
        course = item.get('context_name', 'Unknown course')
        due = item.get('plannable_date', 'No date')
        print(f"  [{plannable_type}] {title} | {course} | {due}")
else:
    print(f"Error: {response.text[:500]}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("""
If you see events in Canvas app but not here, they might be:
1. Personal calendar events (not course events)
2. Planner items (use METHOD 5)
3. Announcements (different API)
4. To-do items created by you

Please compare the events you see in Canvas with this output.
""")