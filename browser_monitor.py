"""
Browser Activity Monitor
Reads browsing history from local browser databases (Chrome/Edge).
Usage: Run with appropriate permissions on your own machine.
"""

import sqlite3
import os
import shutil
import tempfile
from datetime import datetime, timedelta


def get_chrome_history_path():
    """Get the default Chrome history database path on Windows."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    return os.path.join(local_app_data, r"Google\Chrome\User Data\Default\History")


def get_edge_history_path():
    """Get the default Edge history database path on Windows."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    return os.path.join(local_app_data, r"Microsoft\Edge\User Data\Default\History")


def chrome_time_to_datetime(chrome_timestamp):
    """Convert Chrome's timestamp format to a Python datetime."""
    # Chrome stores time as microseconds since 1601-01-01
    epoch_start = datetime(1601, 1, 1)
    return epoch_start + timedelta(microseconds=chrome_timestamp)


def read_browser_history(db_path, browser_name, limit=50):
    """Read browsing history from a Chromium-based browser's SQLite database."""
    if not os.path.exists(db_path):
        print(f"[!] {browser_name} history database not found at: {db_path}")
        return []

    # Copy the database to a temp file (browser may lock the original)
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
            ORDER BY last_visit_time DESC
            LIMIT ?
        """, (limit,))

        for row in cursor.fetchall():
            url, title, visit_count, last_visit_time = row
            visit_time = chrome_time_to_datetime(last_visit_time)
            results.append({
                "url": url,
                "title": title or "(No title)",
                "visit_count": visit_count,
                "last_visit": visit_time.strftime("%Y-%m-%d %H:%M:%S"),
            })
        conn.close()
    except sqlite3.Error as e:
        print(f"[!] Database error: {e}")
    finally:
        os.remove(temp_db)
        os.rmdir(temp_dir)

    return results


def display_history(entries, browser_name):
    """Print browsing history in a readable format."""
    if not entries:
        return
    print(f"\n{'=' * 70}")
    print(f"  {browser_name} - Recent Browsing History ({len(entries)} entries)")
    print(f"{'=' * 70}")
    for i, entry in enumerate(entries, 1):
        print(f"\n  [{i}] {entry['title']}")
        print(f"      URL:      {entry['url'][:80]}")
        print(f"      Visited:  {entry['last_visit']}  (x{entry['visit_count']})")


def main():
    print("Browser Activity Monitor")
    print("Reading local browsing history...\n")

    # Chrome
    chrome_path = get_chrome_history_path()
    chrome_history = read_browser_history(chrome_path, "Chrome", limit=25)
    display_history(chrome_history, "Google Chrome")

    # Edge
    edge_path = get_edge_history_path()
    edge_history = read_browser_history(edge_path, "Microsoft Edge", limit=25)
    display_history(edge_history, "Microsoft Edge")

    if not chrome_history and not edge_history:
        print("[!] No browser history found. Make sure Chrome or Edge is installed.")
    else:
        print(f"\n{'=' * 70}")
        print("  Done.")


if __name__ == "__main__":
    main()
