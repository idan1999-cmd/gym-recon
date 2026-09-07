#!/usr/bin/env python3
"""
Ariel Fit & Spa - Dashboard Local Server
Serves the interactive executive dashboard and REST API endpoints.
"""
import os
import sys
import json
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from datetime import datetime

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
            cur_m = datetime.now().month
            month = int(query.get("month", [str(cur_m)])[0])
            club = query.get("club", ["all"])[0]
            snapshot = query.get("snapshot", [None])[0]

            summary = data_service.get_dashboard_summary(month=month, club_filter=club, snapshot=snapshot)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(summary, ensure_ascii=False).encode("utf-8"))
            return

        elif path == "/api/schedule_analytics":
            club = query.get("club", ["all"])[0]
            time_range = query.get("range", ["1m"])[0]
            min_occ = int(query.get("min_occurrences", ["3"])[0])
            month_param = query.get("month", [None])[0]
            target_month = int(month_param) if month_param and month_param.isdigit() else None

            analytics = data_service.get_schedule_analytics(
                club_filter=club,
                time_range=time_range,
                min_occurrences=min_occ,
                target_month=target_month
            )

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(analytics, ensure_ascii=False).encode("utf-8"))
            return

        elif path == "/api/suppliers":
            month_param = query.get("month", ["8"])[0]
            month = int(month_param) if month_param.isdigit() else 8
            suppliers_data = data_service.get_suppliers_dashboard(month=month)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(suppliers_data, ensure_ascii=False).encode("utf-8"))
            return

        elif path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        elif path == "/api/tasks":
            tasks_data = data_service.get_tasks_board()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(tasks_data, ensure_ascii=False).encode("utf-8"))
            return

        elif path == "/api/revenue_breakdown":
            month_param = query.get("month", [str(datetime.now().month)])[0]
            month = int(month_param) if str(month_param).isdigit() else datetime.now().month
            rb = data_service.get_revenue_breakdown(month=month)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(rb, ensure_ascii=False).encode("utf-8"))
            return

        # Serve static assets
        super().do_GET()

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return
        super().do_HEAD()

    def do_POST(self):
        global data_service
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == "/api/suppliers/state":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                month = int(data.get("month", 8))
                bank_balance = data.get("bank_balance")
                approved_ids = data.get("approved_ids")
                
                updated = data_service.save_suppliers_state(month, bank_balance=bank_balance, approved_ids=approved_ids)
                # Re-fetch full suppliers payload
                payload = data_service.get_suppliers_dashboard(month=month)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "data": payload}, ensure_ascii=False).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        elif parsed.path == "/api/target":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                club = data.get("club", "חדר כושר")
                code = data.get("code", "")
                month = int(data.get("month", 6))
                raw_target = data.get("target")
                target = float(raw_target) if (raw_target is not None and raw_target != "") else None

                success = data_service.save_custom_target(club, code, month, target)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": success, "message": "הנתונים עודכנו בהצלחה"}, ensure_ascii=False).encode("utf-8"))
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

        elif parsed.path == "/api/tasks":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                result = data_service.save_task(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        elif parsed.path == "/api/tasks/complete":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                result = data_service.complete_task(data.get("task_id"))
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        elif parsed.path == "/api/revenue_breakdown/override":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                result = data_service.save_revenue_override(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        elif parsed.path == "/api/suppliers/transmit":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8")) if body else {}
                month = int(data.get("month", 8))
                result = data_service.archive_approved_suppliers(month=month)
                # Re-fetch updated suppliers state
                payload = data_service.get_suppliers_dashboard(month=month)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "result": result, "data": payload}, ensure_ascii=False).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        elif parsed.path == "/api/upload_invoice":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                # Accept base64 encoded invoice upload
                data = json.loads(body.decode("utf-8"))
                filename = data.get("filename", "invoice.pdf")
                file_b64 = data.get("content_base64", "")
                
                # Target folder: dropzone/invoices or dropzone/invoices_suppliers
                import base64
                target_dir = BASE_DIR / "📥_לגרור_לכאן_את_קבצי_החודש" / "invoices_suppliers"
                target_dir.mkdir(parents=True, exist_ok=True)
                
                file_path = target_dir / filename
                with open(file_path, "wb") as f:
                    f.write(base64.b64decode(file_b64))
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "filename": filename,
                    "message": f"החשבונית {filename} נשמרה בהצלחה בתיקיית הספקים"
                }, ensure_ascii=False).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        self.send_response(404)
        self.end_headers()

def run_server(port=PORT):
    print("🔄 Pre-warming dashboard cache...")
    try:
        data_service.get_dashboard_summary(month=6, club_filter="all")
        print("✅ Dashboard cache ready!")
    except Exception as e:
        print("⚠️ Cache pre-warm notice:", e)

    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, DashboardHandler)
    print(f"🚀 Ariel Fit & Spa Dashboard is running at http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server...")
        httpd.server_close()

if __name__ == "__main__":
    port_env = os.environ.get("PORT")
    port_arg = int(port_env) if port_env else (int(sys.argv[1]) if len(sys.argv) > 1 else PORT)
    run_server(port_arg)
