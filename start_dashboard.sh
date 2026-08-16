#!/usr/bin/env bash
# Ariel Fit & Spa - Launch Dashboard
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".venv/bin/python" ]; then
  PYTHON_CMD=".venv/bin/python"
elif command -v python3 &>/dev/null; then
  PYTHON_CMD="python3"
else
  PYTHON_CMD="python"
fi

echo "=========================================================="
echo " 🚀 אריאל פיט & ספא - פתיחת דשבורד מנהלים אינטראקטיבי"
echo "=========================================================="
echo "מפעיל את השרת המקומי בכתובת: http://localhost:3000"
echo "לסגירה: לחץ Ctrl+C"
echo ""

# Open browser automatically on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
  (sleep 1.5 && open "http://localhost:3000") &
fi

$PYTHON_CMD dashboard/backend/server.py 3000
