#!/usr/bin/env python3
"""
Ariel Fit & Spa - Dashboard Local Server
Serves the interactive executive dashboard and REST API endpoints.
"""
import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from dashboard.backend.data_service import DashboardDataService

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
PORT = 3000

data_service = DashboardDataService()

class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/months":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            months = data_service.get_available_months()
            self.wfile.write(json.dumps(months, ensure_ascii=False).encode("utf-8"))
            return

        elif path == "/api/data":
            month = int(query.get("month", ["6"])[0])
            club = query.get("club", ["all"])[0]
            holiday_mode = query.get("holiday", ["false"])[0].lower() == "true"
            snapshot = query.get("snapshot", [None])[0]

            summary = data_service.get_dashboard_summary(month=month, club_filter=club, holiday_mode=holiday_mode, snapshot=snapshot)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(summary, ensure_ascii=False).encode("utf-8"))
            return

        elif path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        # Serve static assets
        super().do_GET()

    def do_POST(self):
        global data_service
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == "/api/target":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                club = data.get("club", "חדר כושר")
                code = data.get("code", "")
                month = int(data.get("month", 6))
                target = float(data.get("target", 0.0))

                success = data_service.save_custom_target(club, code, month, target)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": success, "message": "היעד עודכן בהצלחה"}, ensure_ascii=False).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        elif parsed.path == "/api/sync":
            data_service = DashboardDataService()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "message": "סנכרון הנתונים הושלם בהצלחה"}, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def run_server(port=PORT):
    server_address = ("", port)
    httpd = HTTPServer(server_address, DashboardHandler)
    print(f"🚀 Ariel Fit & Spa Dashboard is running at http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server...")
        httpd.server_close()

if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port_arg)
