# canvas_courses.py
# A simple script to list your Canvas courses

# ============================================================
# STEP 1: Import the 'requests' library
# ============================================================
# 'requests' is a tool that lets Python talk to websites and APIs.
# Think of it like a messenger that sends requests and brings back responses.
import requests

# ============================================================
# STEP 2: Set up your Canvas information
# ============================================================
# Replace these with YOUR values:

# Your school's Canvas URL (no trailing slash)
# Example: "https://myschool.instructure.com"
CANVAS_URL = "https://bbns.instructure.com"

# Your API token (the long string you generated in Canvas settings)
# IMPORTANT: Never share this token with anyone!
API_TOKEN = "21714~3xNaYnwUyEyx3zhhwZRtQktCP34LH6eJ88ADVRPrn8r9v2TH9fUaC7N4JNC3WAu4"

# ============================================================
# STEP 3: Set up the connection details
# ============================================================
# The "headers" tell Canvas who we are (using our token)
# It's like showing your ID card at the door
headers = {
    "Authorization": f"Bearer {API_TOKEN}"
}

# This is the specific "address" (endpoint) to get courses
# Canvas has many endpoints - this one returns your courses
api_endpoint = f"{CANVAS_URL}/api/v1/courses"

# ============================================================
# STEP 4: Make the request to Canvas
# ============================================================
print("Connecting to Canvas...")

# requests.get() sends a "GET" request - asking Canvas to give us data
# We pass the URL and our headers (with the token)
response = requests.get(api_endpoint, headers=headers)

# ============================================================
# STEP 5: Check if it worked
# ============================================================
# Every response has a "status code" - 200 means success!
if response.status_code == 200:
    print("Connected successfully!\n")

    # Convert the response from JSON format into a Python list
    # JSON is a common format for sending data over the internet
    courses = response.json()

    # ========================================================
    # STEP 6: Print out the course names
    # ========================================================
    print("Your Courses:")
    print("-" * 40)

    # Loop through each course in the list
    for course in courses:
        # Each course is a "dictionary" - a collection of key-value pairs
        # We use .get() to safely get the 'name' - if it doesn't exist,
        # it returns "Unnamed Course" instead of crashing
        course_name = course.get("name", "Unnamed Course")
        print(f"  - {course_name}")

    # Show how many courses we found
    print("-" * 40)
    print(f"Total: {len(courses)} courses")

else:
    # If something went wrong, show the error
    print(f"Error connecting to Canvas!")
    print(f"Status code: {response.status_code}")
    print(f"Message: {response.text}")
    print("\nCommon issues:")
    print("  - 401 error: Your API token is invalid or expired")
    print("  - 404 error: Check your Canvas URL is correct")