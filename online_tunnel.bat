@echo off
title SmartQueue Online Public Tunnel
echo =======================================================
echo   SmartQueue: Live Online Public Tunnel (Cloudflare)
echo =======================================================
echo.
echo Ensuring SmartQueue Flask server is running...
start /b "" .venv\Scripts\python.exe app.py
timeout /t 2 >nul
echo.
echo Starting secure HTTPS tunnel for http://127.0.0.1:5000 ...
echo.
echo Visit and share the generated https://*.trycloudflare.com URL below!
echo.
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --protocol http2 --url http://127.0.0.1:5000
pause
