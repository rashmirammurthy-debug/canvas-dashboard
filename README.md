# Canvas Assignment Dashboard

A beautiful dashboard that shows all your upcoming assignments and events from Canvas LMS.

![Dashboard Preview](https://img.shields.io/badge/Made%20with-Python-blue)

## Features

- View assignments from **all your courses** in one place
- See **calendar events** (homework, readings, etc.)
- **Color-coded** by urgency (red = urgent, yellow = soon, green = upcoming)
- **Filter** by course or by type (assignments, events, due dates)
- **Clickable links** to Canvas and attached documents
- Works with any school using Canvas LMS

## Quick Start

### 1. Install Python

If you don't have Python installed:
- Download from [python.org](https://www.python.org/downloads/)
- During installation, check "Add Python to PATH"

### 2. Install Required Library

Open a terminal/command prompt and run:

```bash
pip install requests
```

### 3. Download the Code

Download or clone this repository to your computer.

### 4. Set Up Your Config

1. Copy `config_template.py` to a new file called `config.py`
2. Edit `config.py` with your school's Canvas URL and your API token

### 5. Get Your Canvas API Token

1. Log into your school's Canvas
2. Click your **profile picture** → **Settings**
3. Scroll down to **"Approved Integrations"**
4. Click **"+ New Access Token"**
5. Enter a name (e.g., "Dashboard") and click **Generate Token**
6. **Copy the token immediately** - you won't see it again!
7. Paste the token into your `config.py` file

### 6. Run the Dashboard

```bash
python all_courses_dashboard.py
```

Or double-click `Update Dashboard.bat` (Windows)

The dashboard will open in your browser automatically!

## Customization

### Change Which Courses Appear

Edit the `COURSES_TO_INCLUDE` list in `all_courses_dashboard.py`:

```python
COURSES_TO_INCLUDE = [
    "stat",      # Matches "AP Statistics"
    "chem",      # Matches "Chemistry"
    "english",   # Matches "English 10"
    # Add more search terms...
]
```

### Change Course Colors

Edit the `COURSE_COLORS` dictionary to customize the color for each course.

## Files

| File | Purpose |
|------|---------|
| `all_courses_dashboard.py` | Main script - generates the dashboard |
| `config.py` | Your personal settings (DO NOT SHARE) |
| `config_template.py` | Template for config - share this |
| `Update Dashboard.bat` | Windows shortcut to run the script |
| `my_dashboard.html` | Generated dashboard (open in browser) |

## Security Note

Your `config.py` contains your API token which gives access to your Canvas account.
- **Never share your config.py file**
- **Never commit it to GitHub** (it's in .gitignore)
- If you accidentally share it, generate a new token in Canvas immediately

## Troubleshooting

**"config.py not found"**
- Make sure you copied `config_template.py` to `config.py`

**"401 Unauthorized"**
- Your API token is invalid or expired
- Generate a new token in Canvas Settings

**"No courses found"**
- Check your Canvas URL is correct (should be like `https://yourschool.instructure.com`)
- Make sure your courses match the search terms in `COURSES_TO_INCLUDE`

**Some events not showing**
- Only future events are shown
- Some item types may not be supported

## License

Free to use and modify. Share with your classmates!