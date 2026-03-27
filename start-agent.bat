@echo off
chcp 65001 >nul
title RemoteLink Agent
echo.
echo  ╔═══════════════════════════════════════╗
echo  ║       RemoteLink Agent  v2.0          ║
echo  ╚═══════════════════════════════════════╝
echo.
echo  Installation des dépendances si nécessaire...
pip install websockets pyautogui pyperclip -q 2>nul
echo  Démarrage de l'agent...
echo.
python remotelink-agent.py
pause
