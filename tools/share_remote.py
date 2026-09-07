#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CLOUDFLARED_BIN = Path('/tmp/cloudflared')
LOG_FILE = Path('/tmp/tunnel.log')
PORT = 3000

def ensure_cloudflared():
    if not CLOUDFLARED_BIN.exists():
        print("⬇️  מוריד מודול שיתוף מאובטח (Cloudflare Tunnel)...")
        cmd = "curl -sL https://github.com/cloudflare/cloudflared/releases/download/2026.8.3/cloudflared-darwin-arm64.tgz | tar -xz -C /tmp"
        subprocess.run(cmd, shell=True, check=True)
        CLOUDFLARED_BIN.chmod(0o755)

def get_active_url():
    if LOG_FILE.exists():
        content = LOG_FILE.read_text(encoding="utf-8", errors="ignore")
        matches = re.findall(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", content)
        if matches:
            return matches[-1]
    return None

def start_tunnel():
    ensure_cloudflared()
    url = get_active_url()
    
    check = subprocess.run("pgrep -f 'cloudflared tunnel' > /dev/null", shell=True)
    if check.returncode == 0 and url:
        print_banner(url)
        return

    print("🚀 מייצר קישור מאובטח (HTTPS) לעבודה מרחוק...")
    if LOG_FILE.exists():
        LOG_FILE.unlink()

    proc = subprocess.Popen(
        [str(CLOUDFLARED_BIN), "tunnel", "--url", f"http://localhost:{PORT}", "--logfile", str(LOG_FILE)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    for _ in range(20):
        time.sleep(1)
        url = get_active_url()
        if url:
            print_banner(url)
            return

    print("⚠️ לא הצלחנו לקבל כתובת תוך 20 שניות. בדוק את /tmp/tunnel.log")

def print_banner(url):
    sep = "=" * 65
    print("\n" + sep)
    print("✨ הדשבורד של אריאל פיט & ספא זמין כעת לשיתוף מרחוק!")
    print(sep)
    print("\n🌐 קישור מאובטח (HTTPS) לשליחה לשותף / עובד:")
    print(f"👉  {url}")
    print("\nℹ️  הערות:")
    print("• עובד מכל מחשב, טלפון או רשת בעולם (גם ללא אותו Wi-Fi).")
    print("• מוצפן ומאובטח ע״י Cloudflare ללא צורך בהרשמה.")
    print("• כל עוד המחשב שלך דולק, הדשבורד זמין ומסונכרן בלייב.")
    print(sep + "\n")

if __name__ == "__main__":
    start_tunnel()
