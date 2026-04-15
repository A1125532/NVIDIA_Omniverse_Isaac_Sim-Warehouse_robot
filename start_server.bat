@echo off
chcp 65001 >nul
echo 正在啟動 Dashboard 伺服器...
echo 網址: http://127.0.0.1:8000
echo.
python -m uvicorn dashboard_server:app --reload --host 127.0.0.1 --port 8000 --log-level warning
pause

