"""
Parental Browser Monitor - Background Service
Continuously monitors browser history and logs new entries to a JSON file.
Runs silently in the background on the child's computer.
"""

import sqlite3
import os
import sys
import shutil
import json
import tempfile
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

# --- Configuration ---
CHECK_INTERVAL_SECONDS = 30  # How often to check for new history
LOG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", "."), "BrowserMonitor")
HISTORY_LOG = os.path.join(LOG_DIR, "history_log.json")
MAX_LOG_ENTRIES = 5000  # Keep the last N entries to avoid huge files

# Set up logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "monitor.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def get_browser_paths():
    """Return a list of (browser_name, history_db_path) tuples."""
    local = os.environ.get("LOCALAPPDATA", "")
    browsers = [
        ("Chrome", os.path.join(local, r"Google\Chrome\User Data\Default\History")),
        ("Edge", os.path.join(local, r"Microsoft\Edge\User Data\Default\History")),
    ]
    return [(name, path) for name, path in browsers if os.path.exists(path)]


def chrome_time_to_datetime(chrome_timestamp):
    epoch_start = datetime(1601, 1, 1)
    return epoch_start + timedelta(microseconds=chrome_timestamp)


def read_new_history(db_path, browser_name, since_timestamp=0):
    """Read history entries newer than since_timestamp."""
    temp_dir = tempfile.mkdtemp()
    temp_db = os.path.join(temp_dir, "History_copy")
    shutil.copy2(db_path, temp_db)

    results = []
    try:
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT url, title, visit_count, last_visit_time
            FROM urls
            WHERE last_visit_time > ?
            ORDER BY last_visit_time DESC
        """, (since_timestamp,))

        for row in cursor.fetchall():
            url, title, visit_count, last_visit_time = row
            visit_time = chrome_time_to_datetime(last_visit_time)
            results.append({
                "browser": browser_name,
                "url": url,
                "title": title or "(No title)",
                "visit_count": visit_count,
                "last_visit": visit_time.strftime("%Y-%m-%d %H:%M:%S"),
                "raw_timestamp": last_visit_time,
            })
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Database error for {browser_name}: {e}")
    finally:
        try:
            os.remove(temp_db)
            os.rmdir(temp_dir)
        except OSError:
            pass

    return results


def load_log():
    """Load existing history log from disk."""
    if os.path.exists(HISTORY_LOG):
        try:
            with open(HISTORY_LOG, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"last_timestamps": {}, "entries": []}
    return {"last_timestamps": {}, "entries": []}


def save_log(log_data):
    """Save history log to disk."""
    # Trim to max entries
    if len(log_data["entries"]) > MAX_LOG_ENTRIES:
        log_data["entries"] = log_data["entries"][:MAX_LOG_ENTRIES]
    with open(HISTORY_LOG, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)


def monitor_loop():
    """Main monitoring loop."""
    logging.info("Browser monitor started.")
    print("Browser Monitor is running in the background...")
    print(f"Logs saved to: {LOG_DIR}")
    print(f"Checking every {CHECK_INTERVAL_SECONDS} seconds.")
    print("Press Ctrl+C to stop.\n")

    log_data = load_log()

    while True:
        try:
            browsers = get_browser_paths()
            new_count = 0

            for browser_name, db_path in browsers:
                last_ts = log_data["last_timestamps"].get(browser_name, 0)
                new_entries = read_new_history(db_path, browser_name, last_ts)

                if new_entries:
                    # Update the last seen timestamp
                    max_ts = max(e["raw_timestamp"] for e in new_entries)
                    log_data["last_timestamps"][browser_name] = max_ts

                    # Remove raw_timestamp before storing
                    for entry in new_entries:
                        del entry["raw_timestamp"]

                    # Prepend new entries (newest first)
                    log_data["entries"] = new_entries + log_data["entries"]
                    new_count += len(new_entries)

            if new_count > 0:
                save_log(log_data)
                logging.info(f"Logged {new_count} new entries.")

            time.sleep(CHECK_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logging.info("Monitor stopped by user.")
            print("\nMonitor stopped.")
            sys.exit(0)
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    monitor_loop()
