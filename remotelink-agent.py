#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║   RemoteLink Agent — Contrôle OS réel via WebSocket  ║
║   Usage: python remotelink-agent.py                  ║
╚══════════════════════════════════════════════════════╝
"""

import asyncio
import json
import logging
import platform
import subprocess
import sys

# ─── Auto-install deps ─────────────────────────────────
def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

for dep in ["websockets", "pyautogui", "pyperclip"]:
    try:
        __import__(dep)
    except ImportError:
        print(f"  → Installation de {dep}…")
        install(dep)

import websockets
import pyautogui
import pyperclip

# ─── Config ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="\033[36m%(asctime)s\033[0m  %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("RemoteLink")

pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0

SYSTEM   = platform.system()          # Windows / Darwin / Linux
WS_HOST  = "localhost"
WS_PORT  = 8765
SCREEN_W, SCREEN_H = pyautogui.size()

log.info(f"Écran détecté : {SCREEN_W}×{SCREEN_H}  |  Système : {SYSTEM}")

# ─── Correspondance touches ─────────────────────────────
KEY_MAP = {
    "enter":"enter","return":"enter","backspace":"backspace",
    "delete":"delete","tab":"tab","escape":"esc","esc":"esc",
    "space":"space",
    "arrowup":"up","arrowdown":"down","arrowleft":"left","arrowright":"right",
    "up":"up","down":"down","left":"left","right":"right",
    "home":"home","end":"end","pageup":"pageup","pagedown":"pagedown",
    "f1":"f1","f2":"f2","f3":"f3","f4":"f4","f5":"f5","f6":"f6",
    "f7":"f7","f8":"f8","f9":"f9","f10":"f10","f11":"f11","f12":"f12",
    "printscreen":"printscreen","insert":"insert","capslock":"capslock",
    "volumeup":"volumeup","volumedown":"volumedown","volumemute":"volumemute",
    "win":"win","windows":"win","command":"command","cmd":"command",
}

# ─── Helpers ────────────────────────────────────────────
def to_px(nx: float, ny: float) -> tuple[int, int]:
    """Coordonnées normalisées [0-1] → pixels écran"""
    x = max(0, min(SCREEN_W - 1, int(nx * SCREEN_W)))
    y = max(0, min(SCREEN_H - 1, int(ny * SCREEN_H)))
    return x, y

def paste_text(text: str):
    """Tape du texte Unicode via le presse-papier"""
    try:
        pyperclip.copy(text)
        if SYSTEM == "Darwin":
            pyautogui.hotkey("command", "v")
        elif SYSTEM == "Linux":
            pyautogui.hotkey("ctrl", "shift", "v")
        else:
            pyautogui.hotkey("ctrl", "v")
    except Exception:
        # Fallback ASCII
        safe = "".join(c for c in text if ord(c) < 128 and c.isprintable())
        pyautogui.typewrite(safe, interval=0.03)

# ─── Gestionnaire WebSocket ─────────────────────────────
active_clients: set = set()

async def handler(websocket):
    active_clients.add(websocket)
    addr = websocket.remote_address
    log.info(f"📱 Smartphone connecté : {addr[0]}:{addr[1]}")

    # Envoie info écran au client HTML
    await websocket.send(json.dumps({
        "type": "screen_info",
        "width": SCREEN_W,
        "height": SCREEN_H,
        "system": SYSTEM,
    }))

    try:
        async for raw in websocket:
            try:
                data = json.loads(raw)
                cmd  = data.get("type", "")

                # ── Déplacement souris ──────────────────
                if cmd == "move":
                    x, y = to_px(data["x"], data["y"])
                    pyautogui.moveTo(x, y, duration=0.02, _pause=False)

                # ── Clic ────────────────────────────────
                elif cmd == "click":
                    x, y  = to_px(data["x"], data["y"])
                    btn   = data.get("button", "left")   # left / right / middle
                    dbl   = data.get("double", False)
                    pyautogui.moveTo(x, y, duration=0.05, _pause=False)
                    if dbl:
                        pyautogui.doubleClick(x, y, _pause=False)
                    elif btn == "right":
                        pyautogui.rightClick(x, y, _pause=False)
                    elif btn == "middle":
                        pyautogui.middleClick(x, y, _pause=False)
                    else:
                        pyautogui.click(x, y, _pause=False)

                # ── Défilement ──────────────────────────
                elif cmd == "scroll":
                    x, y   = to_px(data.get("x", 0.5), data.get("y", 0.5))
                    amount = int(data.get("amount", 3))
                    pyautogui.moveTo(x, y, _pause=False)
                    if data.get("dir", "down") == "up":
                        pyautogui.scroll(amount, _pause=False)
                    else:
                        pyautogui.scroll(-amount, _pause=False)

                # ── Saisie texte ────────────────────────
                elif cmd == "keyboard":
                    text = data.get("text", "")
                    if text:
                        paste_text(text)

                # ── Touche spéciale ─────────────────────
                elif cmd == "key":
                    raw_key = data.get("key", "").lower()
                    mapped  = KEY_MAP.get(raw_key, raw_key)
                    if mapped:
                        pyautogui.press(mapped, _pause=False)

                # ── Raccourci clavier ───────────────────
                elif cmd == "hotkey":
                    keys = data.get("keys", [])
                    if keys:
                        pyautogui.hotkey(*keys, _pause=False)

                # ── Glisser-déposer ─────────────────────
                elif cmd == "drag_start":
                    x, y = to_px(data["x"], data["y"])
                    pyautogui.mouseDown(x, y, _pause=False)

                elif cmd == "drag_move":
                    x, y = to_px(data["x"], data["y"])
                    pyautogui.moveTo(x, y, duration=0.01, _pause=False)

                elif cmd == "drag_end":
                    x, y = to_px(data["x"], data["y"])
                    pyautogui.moveTo(x, y, _pause=False)
                    pyautogui.mouseUp(_pause=False)

                # ── Ping ────────────────────────────────
                elif cmd == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))

            except (json.JSONDecodeError, KeyError):
                pass
            except Exception as e:
                log.error(f"Erreur commande: {e}")

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        active_clients.discard(websocket)
        log.info(f"📴 Smartphone déconnecté : {addr[0]}:{addr[1]}")

# ─── Démarrage ──────────────────────────────────────────
async def main():
    print()
    print("  ╔═══════════════════════════════════════╗")
    print("  ║       RemoteLink Agent  v2.0          ║")
    print("  ╚═══════════════════════════════════════╝")
    print()
    log.info(f"Agent WebSocket → ws://{WS_HOST}:{WS_PORT}")
    log.info("Ouvrez remotelink.html dans Chrome/Edge sur ce PC")
    log.info("Ctrl+C pour arrêter\n")

    async with websockets.serve(
        handler,
        WS_HOST,
        WS_PORT,
        origins=None,           # Autorise toutes origines (file://, localhost…)
        ping_interval=20,
        ping_timeout=60,
        max_size=2**20,
    ):
        log.info("✅ Agent prêt — en attente de connexion…\n")
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n  Agent arrêté. À bientôt !\n")
