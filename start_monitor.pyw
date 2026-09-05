"""
Silent launcher - starts both the monitor and dashboard without showing a window.
Use .pyw extension so Windows runs it without a console window.
Place a shortcut to this file in the Startup folder to auto-launch on login.
"""

import subprocess
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
python = sys.executable

# Launch both scripts as hidden background processes
subprocess.Popen(
    [python, os.path.join(script_dir, "monitor_service.py")],
    creationflags=0x08000000,  # CREATE_NO_WINDOW
    cwd=script_dir,
)

subprocess.Popen(
    [python, os.path.join(script_dir, "dashboard.py")],
    creationflags=0x08000000,  # CREATE_NO_WINDOW
    cwd=script_dir,
)
