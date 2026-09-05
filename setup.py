# setup.py
# Interactive setup script for new users

import os
import sys

print("=" * 60)
print("CANVAS DASHBOARD SETUP")
print("=" * 60)

# Check if config already exists
if os.path.exists("config.py"):
    print("\nconfig.py already exists!")
    response = input("Do you want to overwrite it? (y/n): ").strip().lower()
    if response != "y":
        print("Setup cancelled.")
        sys.exit(0)

print("\nLet's set up your Canvas connection.\n")

# Get Canvas URL
print("Step 1: Your school's Canvas URL")
print("   Example: https://myschool.instructure.com")
canvas_url = input("\nEnter your Canvas URL: ").strip()

# Clean up URL
if not canvas_url.startswith("http"):
    canvas_url = "https://" + canvas_url
if canvas_url.endswith("/"):
    canvas_url = canvas_url[:-1]

# Get API Token
print("\n" + "-" * 60)
print("Step 2: Your Canvas API Token")
print("-" * 60)
print("""
To get your token:
1. Log into Canvas
2. Click your profile picture → Settings
3. Scroll to "Approved Integrations"
4. Click "+ New Access Token"
5. Name it "Dashboard" and click Generate
6. Copy the token (you won't see it again!)
""")
api_token = input("Paste your API token here: ").strip()

# Create config file
config_content = f'''# config.py
# Your personal Canvas configuration
# DO NOT SHARE THIS FILE - it contains your private API token!

CANVAS_URL = "{canvas_url}"
API_TOKEN = "{api_token}"
'''

with open("config.py", "w") as f:
    f.write(config_content)

print("\n" + "=" * 60)
print("SUCCESS! config.py has been created.")
print("=" * 60)

# Test connection
print("\nTesting connection to Canvas...")

try:
    import requests
    headers = {"Authorization": f"Bearer {api_token}"}
    response = requests.get(f"{canvas_url}/api/v1/users/self", headers=headers)

    if response.status_code == 200:
        user = response.json()
        print(f"Connected as: {user.get('name', 'Unknown')}")
        print("\nYou're all set! Run the dashboard with:")
        print("   python all_courses_dashboard.py")
    else:
        print(f"Warning: Connection test failed (status {response.status_code})")
        print("Check your Canvas URL and API token.")
except ImportError:
    print("\nNote: Install 'requests' library first:")
    print("   pip install requests")
except Exception as e:
    print(f"\nWarning: Could not test connection: {e}")

print("\n" + "=" * 60)
