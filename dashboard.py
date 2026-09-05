"""
Parental Browser Monitor - Web Dashboard
Serves a live web dashboard so parents can view browsing activity
from any device on the same network (phone, laptop, etc.).

Run this on the child's computer alongside monitor_service.py.
Then open http://<childs-computer-ip>:8585 from your device.
"""

import json
import os
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

LOG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", "."), "BrowserMonitor")
HISTORY_LOG = os.path.join(LOG_DIR, "history_log.json")
PORT = 8585

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Browser Activity Monitor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f172a; color: #e2e8f0;
            min-height: 100vh;
        }
        .header {
            background: #1e293b; padding: 20px 30px;
            border-bottom: 1px solid #334155;
            display: flex; justify-content: space-between; align-items: center;
            flex-wrap: wrap; gap: 10px;
        }
        .header h1 { font-size: 1.4rem; color: #60a5fa; }
        .status { font-size: 0.85rem; color: #94a3b8; }
        .status .live { color: #34d399; font-weight: bold; }
        .controls {
            display: flex; gap: 10px; padding: 15px 30px;
            background: #1e293b; border-bottom: 1px solid #334155;
            flex-wrap: wrap;
        }
        .controls input, .controls select {
            background: #0f172a; border: 1px solid #334155;
            color: #e2e8f0; padding: 8px 12px; border-radius: 6px;
            font-size: 0.9rem;
        }
        .controls input { flex: 1; min-width: 200px; }
        .controls select { min-width: 120px; }
        .container { padding: 20px 30px; }
        .entry {
            background: #1e293b; border-radius: 8px; padding: 14px 18px;
            margin-bottom: 8px; border-left: 3px solid #3b82f6;
            transition: background 0.2s;
        }
        .entry:hover { background: #263548; }
        .entry.new { border-left-color: #34d399; animation: fadeIn 0.5s; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-5px); } to { opacity: 1; } }
        .entry-title { font-weight: 600; color: #f1f5f9; margin-bottom: 4px;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .entry-url { font-size: 0.8rem; color: #60a5fa; word-break: break-all;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .entry-url a { color: #60a5fa; text-decoration: none; }
        .entry-url a:hover { text-decoration: underline; }
        .entry-meta { font-size: 0.78rem; color: #94a3b8; margin-top: 4px;
            display: flex; gap: 15px; }
        .badge {
            display: inline-block; padding: 2px 8px; border-radius: 4px;
            font-size: 0.72rem; font-weight: 600;
        }
        .badge-chrome { background: #234; color: #60a5fa; }
        .badge-edge { background: #1a3a2a; color: #34d399; }
        .empty { text-align: center; padding: 60px; color: #64748b; }
        .count { color: #94a3b8; font-size: 0.85rem; padding: 0 0 10px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Browser Activity Monitor</h1>
        <div class="status">
            <span class="live">LIVE</span> &mdash; Auto-refreshing every 10s
        </div>
    </div>
    <div class="controls">
        <input type="text" id="search" placeholder="Search URLs or titles..." oninput="filterEntries()">
        <select id="browserFilter" onchange="filterEntries()">
            <option value="all">All Browsers</option>
            <option value="Chrome">Chrome</option>
            <option value="Edge">Edge</option>
        </select>
    </div>
    <div class="container">
        <div class="count" id="count"></div>
        <div id="entries"></div>
    </div>

    <script>
        let allEntries = [];
        let lastCount = 0;

        async function fetchEntries() {
            try {
                const resp = await fetch('/api/history');
                const data = await resp.json();
                allEntries = data.entries || [];
                filterEntries();
            } catch (e) {
                console.error('Fetch error:', e);
            }
        }

        function filterEntries() {
            const search = document.getElementById('search').value.toLowerCase();
            const browser = document.getElementById('browserFilter').value;
            let filtered = allEntries;

            if (browser !== 'all') {
                filtered = filtered.filter(e => e.browser === browser);
            }
            if (search) {
                filtered = filtered.filter(e =>
                    (e.title && e.title.toLowerCase().includes(search)) ||
                    (e.url && e.url.toLowerCase().includes(search))
                );
            }
            renderEntries(filtered);
        }

        function renderEntries(entries) {
            const container = document.getElementById('entries');
            const countEl = document.getElementById('count');
            countEl.textContent = `Showing ${entries.length} entries`;

            if (entries.length === 0) {
                container.innerHTML = '<div class="empty">No browsing activity recorded yet.<br>Make sure monitor_service.py is running.</div>';
                return;
            }

            const isNew = entries.length > lastCount;
            lastCount = entries.length;

            container.innerHTML = entries.map((e, i) => {
                const badgeClass = e.browser === 'Chrome' ? 'badge-chrome' : 'badge-edge';
                const newClass = isNew && i === 0 ? 'new' : '';
                return `
                    <div class="entry ${newClass}">
                        <div class="entry-title">${escapeHtml(e.title)}</div>
                        <div class="entry-url"><a href="${escapeHtml(e.url)}" target="_blank">${escapeHtml(e.url)}</a></div>
                        <div class="entry-meta">
                            <span class="badge ${badgeClass}">${escapeHtml(e.browser)}</span>
                            <span>${escapeHtml(e.last_visit)}</span>
                            <span>${e.visit_count} visit${e.visit_count !== 1 ? 's' : ''}</span>
                        </div>
                    </div>`;
            }).join('');
        }

        function escapeHtml(str) {
            if (!str) return '';
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        fetchEntries();
        setInterval(fetchEntries, 10000);
    </script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/history":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                with open(HISTORY_LOG, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.wfile.write(json.dumps({"entries": data.get("entries", [])}).encode())
            except (FileNotFoundError, json.JSONDecodeError):
                self.wfile.write(b'{"entries":[]}')
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())

    def log_message(self, format, *args):
        pass  # Suppress console logging


def get_local_ip():
    """Get this machine's local network IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    local_ip = get_local_ip()
    server = HTTPServer(("0.0.0.0", PORT), DashboardHandler)
    print(f"Dashboard running!")
    print(f"  Local:   http://localhost:{PORT}")
    print(f"  Network: http://{local_ip}:{PORT}")
    print(f"\nOpen the Network URL from your phone or laptop to view activity.")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
