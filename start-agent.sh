#!/bin/bash
echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║       RemoteLink Agent  v2.0          ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""
echo "  Installation des dépendances..."
pip3 install websockets pyautogui pyperclip -q 2>/dev/null || \
pip  install websockets pyautogui pyperclip -q 2>/dev/null
echo "  Démarrage de l'agent..."
echo ""
python3 remotelink-agent.py || python remotelink-agent.py
