import base64
import io
import json
import os
import re
import time

import pyautogui
import requests
from PIL import ImageGrab

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
VISION_MODEL = os.getenv("JARVIES_VISION_MODEL", "llama3.2-vision:11b")

# Actions that can change files, send messages, purchase things, or power off the PC
# are intentionally never executed automatically.
BLOCKED_WORDS = {
    "delete", "remove", "uninstall", "format", "shutdown", "restart", "reboot",
    "purchase", "buy", "pay", "send message", "send email", "post", "publish",
}


def screenshot_for_vision():
    image = ImageGrab.grab(all_screens=True)
    original_size = image.size
    max_w, max_h = 1800, 1100
    scale = min(max_w / image.width, max_h / image.height, 1.0)
    if scale < 1:
        image = image.resize((int(image.width * scale), int(image.height * scale)))
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=82)
    return base64.b64encode(buf.getvalue()).decode("ascii"), original_size, image.size


def _json_from_response(text):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise ValueError("Vision model did not return JSON")
        return json.loads(match.group(0))


def plan_actions(command):
    image_b64, screen_size, image_size = screenshot_for_vision()
    prompt = f"""You are JARVIES controlling a Windows PC. Look at the screenshot and plan only the actions needed for this user request.
User request: {command}

Return ONLY valid JSON in this exact shape:
{{"message":"short explanation","actions":[{{"type":"click","x":123,"y":456}}]}}

Allowed action types: click, double_click, type, key, hotkey, scroll, wait.
Coordinates MUST be in the screenshot coordinate system, width={image_size[0]}, height={image_size[1]}.
For type use {{"type":"type","text":"..."}}.
For key use {{"type":"key","key":"enter"}}.
For hotkey use {{"type":"hotkey","keys":["ctrl","l"]}}.
For scroll use {{"type":"scroll","amount":-5}}.
For wait use {{"type":"wait","seconds":1}}.
Never invent an element that is not visible. If the request cannot safely be completed from this screenshot, return an empty actions list and explain why.
Do not plan deletion, file destruction, purchases, payments, sending messages/emails, publishing, shutdown, restart, or other destructive actions.
"""
    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": VISION_MODEL,
            "messages": [{"role": "user", "content": prompt, "images": [image_b64]}],
            "stream": False,
            "options": {"temperature": 0.1},
        },
        timeout=240,
    )
    response.raise_for_status()
    data = response.json()["message"]["content"]
    plan = _json_from_response(data)
    plan["_screen_size"] = screen_size
    plan["_image_size"] = image_size
    return plan


def dangerous_request(command):
    lower = command.lower()
    return any(word in lower for word in BLOCKED_WORDS)


def execute_actions(plan, confirm=False):
    actions = plan.get("actions", [])
    if not isinstance(actions, list):
        return "The vision model returned an invalid action plan."
    screen_w, screen_h = plan["_screen_size"]
    image_w, image_h = plan["_image_size"]
    sx = screen_w / image_w
    sy = screen_h / image_h

    for action in actions:
        kind = action.get("type")
        if kind in {"click", "double_click"}:
            x = max(0, min(screen_w - 1, int(action["x"] * sx)))
            y = max(0, min(screen_h - 1, int(action["y"] * sy)))
            if kind == "double_click":
                pyautogui.doubleClick(x, y, interval=0.12)
            else:
                pyautogui.click(x, y)
        elif kind == "type":
            pyautogui.write(str(action.get("text", "")), interval=0.01)
        elif kind == "key":
            pyautogui.press(str(action.get("key", "enter")))
        elif kind == "hotkey":
            keys = action.get("keys", [])
            pyautogui.hotkey(*[str(k) for k in keys])
        elif kind == "scroll":
            pyautogui.scroll(int(action.get("amount", 0)))
        elif kind == "wait":
            time.sleep(max(0, min(float(action.get("seconds", 1)), 5)))
        else:
            return f"I stopped because I do not recognize the action {kind}."
        time.sleep(0.25)
    return "Actions completed."
