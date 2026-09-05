# test_regex.py
# Quick test to debug link extraction

import re

# This is the exact HTML from your Canvas assignment
test_html = '''<p><a class="inline_disabled" href="https://docs.google.com/document/d/1Wgu84GsKPq4TClS-UA22ZJsexzvPxfRT7Qw-A0ywsb0/edit?usp=sharing" target="_blank">B Block HW Sheet</a></p>
<p><a class="inline_disabled" href="https://docs.google.com/document/d/1oyJQJY0mO9ELWNbjo5BPM8wVribEYh5kECqYWkb-nQQ/edit?usp=sharing" target="_blank">D Block HW Sheet</a></p>'''

print("=" * 60)
print("TESTING LINK EXTRACTION")
print("=" * 60)

print("\nInput HTML:")
print(test_html)

# Test pattern 1 (original)
pattern1 = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>'
matches1 = re.findall(pattern1, test_html, re.IGNORECASE | re.DOTALL)
print(f"\nPattern 1 results: {matches1}")

# Test pattern 2 (simpler)
pattern2 = r'href="([^"]+)"[^>]*>([^<]+)</a>'
matches2 = re.findall(pattern2, test_html, re.IGNORECASE)
print(f"\nPattern 2 results: {matches2}")

# Test pattern 3 (even simpler)
pattern3 = r'href="(https?://[^"]+)"'
matches3 = re.findall(pattern3, test_html)
print(f"\nPattern 3 (URLs only): {matches3}")

# Test pattern 4 (most flexible)
pattern4 = r'<a\s+[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
matches4 = re.findall(pattern4, test_html, re.IGNORECASE | re.DOTALL)
print(f"\nPattern 4 results: {matches4}")

print("\n" + "=" * 60)
print("Now testing with actual Canvas data...")
print("=" * 60)

# Now let's fetch real data from Canvas
import requests

CANVAS_URL = "https://bbns.instructure.com"
API_TOKEN = "21714~3xNaYnwUyEyx3zhhwZRtQktCP34LH6eJ88ADVRPrn8r9v2TH9fUaC7N4JNC3WAu4"

headers = {"Authorization": f"Bearer {API_TOKEN}"}

# Get courses
response = requests.get(f"{CANVAS_URL}/api/v1/courses", headers=headers)
courses = response.json()

stats_course = None
for course in courses:
    if "stat" in course.get("name", "").lower():
        stats_course = course
        break

if stats_course:
    course_id = stats_course["id"]

    # Get first assignment with description
    assignments_url = f"{CANVAS_URL}/api/v1/courses/{course_id}/assignments"
    response = requests.get(assignments_url, headers=headers)
    assignments = response.json()

    for a in assignments:
        desc = a.get("description")
        if desc and "<a" in desc:
            print(f"\nAssignment: {a.get('name')}")
            print(f"Description type: {type(desc)}")
            print(f"Description repr: {repr(desc)}")

            # Test all patterns
            print(f"\nPattern 1: {re.findall(pattern1, desc, re.IGNORECASE | re.DOTALL)}")
            print(f"Pattern 2: {re.findall(pattern2, desc, re.IGNORECASE)}")
            print(f"Pattern 3: {re.findall(pattern3, desc)}")
            print(f"Pattern 4: {re.findall(pattern4, desc, re.IGNORECASE | re.DOTALL)}")
            break