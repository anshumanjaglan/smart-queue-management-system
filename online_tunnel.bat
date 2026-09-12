@echo off
title SmartQueue Online Public Tunnel
echo =======================================================
echo   SmartQueue: Live Online Public Tunnel (Cloudflare)
echo =======================================================
echo.
echo Starting secure HTTPS tunnel for http://127.0.0.1:5000 ...
echo Share the generated https://*.trycloudflare.com link with anyone!
echo.
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://127.0.0.1:5000
pause
