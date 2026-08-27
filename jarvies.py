import base64
import io
import os
import re
import subprocess
import threading
import time
import webbrowser
from queue import Queue

import pyautogui
import pyttsx3
import requests
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from PIL import ImageGrab

from audio import listen_once
from computer_control import dangerous_request, execute_actions, plan_actions

load_dotenv()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.getenv("JARVIES_MODEL", "llama3.2:3b")
VISION_MODEL = os.getenv("JARVIES_VISION_MODEL", "llama3.2-vision:11b")
WHISPER_MODEL = os.getenv("JARVIES_WHISPER_MODEL", "base.en")
WAKE_WORD = os.getenv("JARVIES_WAKE_WORD", "jarvies").lower()

APP_ALIASES = {
    "youtube": "https://www.youtube.com", "google": "https://www.google.com",
    "gmail": "https://mail.google.com", "github": "https://github.com",
    "discord": "https://discord.com/app", "spotify": "https://open.spotify.com",
    "chatgpt": "https://chatgpt.com", "whatsapp": "https://web.whatsapp.com",
    "instagram": "https://www.instagram.com", "facebook": "https://www.facebook.com",
    "reddit": "https://www.reddit.com", "netflix": "https://www.netflix.com",
}

engine = pyttsx3.init()
engine.setProperty("rate", 175)
print("Loading local speech model...")
whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
print("JARVIES is ready.")


def speak(text):
    text = re.sub(r"\s+", " ", str(text)).strip()
    if text:
        print(f"JARVIES: {text}")
        engine.say(text)
        engine.runAndWait()


def ollama_chat(prompt, model=MODEL):
    response = requests.post(f"{OLLAMA_URL}/api/chat", json={
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.2},
    }, timeout=120)
    response.raise_for_status()
    return response.json()["message"]["content"].strip()


def open_target(target):
    target = target.strip().strip('"\'').lower()
    if target in APP_ALIASES:
        webbrowser.open(APP_ALIASES[target])
        return f"Opening {target}."
    known_apps = {
        "notepad": "notepad.exe", "calculator": "calc.exe", "paint": "mspaint.exe",
        "file explorer": "explorer.exe", "explorer": "explorer.exe",
        "command prompt": "cmd.exe", "cmd": "cmd.exe", "powershell": "powershell.exe",
        "settings": "ms-settings:", "task manager": "taskmgr.exe",
    }
    if target in known_apps:
        try:
            if known_apps[target].endswith(":"):
                os.startfile(known_apps[target])
            else:
                subprocess.Popen(known_apps[target], shell=True)
            return f"Opening {target}."
        except Exception as exc:
            return f"I could not open {target}: {exc}"
    if target.startswith(("http://", "https://")):
        webbrowser.open(target)
        return "Opening it."
    webbrowser.open("https://www.google.com/search?q=" + requests.utils.quote(target))
    return f"I searched for {target}."


def search_web(query, service="google"):
    query = query.strip()
    if service == "youtube":
        url = "https://www.youtube.com/results?search_query=" + requests.utils.quote(query)
    else:
        url = "https://www.google.com/search?q=" + requests.utils.quote(query)
    webbrowser.open(url)
    return f"Searching {service} for {query}."


def take_screenshot():
    image = ImageGrab.grab(all_screens=True)
    image.thumbnail((1800, 1100))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=78)
    return buffer.getvalue()


def inspect_screen(question):
    image_b64 = base64.b64encode(take_screenshot()).decode("ascii")
    try:
        response = requests.post(f"{OLLAMA_URL}/api/chat", json={
            "model": VISION_MODEL,
            "messages": [{
                "role": "user",
                "content": (
                    "You are JARVIES, a helpful Windows screen assistant. Describe only what "
                    "is visible. If asked where to click, give precise guidance using visible "
                    "labels and approximate position. Never invent UI. Keep it concise.\n\n"
                    "Question: " + question
                ),
                "images": [image_b64],
            }],
            "stream": False,
        }, timeout=240)
        response.raise_for_status()
        return response.json()["message"]["content"].strip()
    except requests.RequestException as exc:
        return f"My local vision model is unavailable: {exc}"


def control_screen(command):
    if dangerous_request(command):
        return "I will not perform destructive or sensitive actions automatically."
    try:
        speak("Scanning the screen and planning the action.")
        plan = plan_actions(command)
        message = plan.get("message", "I found an action plan.")
        actions = plan.get("actions", [])
        if not actions:
            return message
        print("JARVIES plan:", actions)
        speak(message + " I can perform the safe actions now.")
        return execute_actions(plan)
    except requests.RequestException:
        return f"I could not reach the local vision model. Make sure Ollama is running and {VISION_MODEL} is installed."
    except Exception as exc:
        return f"I could not safely control the screen: {exc}"


def type_text(text):
    pyautogui.write(text, interval=0.01)
    return "Done."


def press_key(key):
    key = key.strip().lower().replace(" ", "_")
    key = {"return": "enter", "escape": "esc", "control": "ctrl", "windows": "win"}.get(key, key)
    allowed = {"enter", "esc", "tab", "space", "backspace", "delete", "home", "end",
               "up", "down", "left", "right", "ctrl", "shift", "alt", "win",
               "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12"}
    if key not in allowed and len(key) != 1:
        return "I do not recognize that key."
    pyautogui.press(key)
    return f"Pressed {key.replace('_', ' )')}".replace(" )", " ").strip() + "."


def parse_command(command):
    text = command.strip()
    lower = text.lower()
    if lower in {"stop", "quit", "exit", "goodbye", "shutdown jarvies"}:
        return "exit", None
    if re.search(r"(watch|look at|see|check|inspect|analy[sz]e).*(screen|display)", lower) or re.search(r"(where|what).*(click|button).*(screen|here)", lower):
        return "screen", text
    if re.search(r"\b(click|press|tap|select|type|enter|scroll|move).*(on|in|the)\b", lower) and any(w in lower for w in ["screen", "browser", "page", "button", "box", "website"]):
        return "control", text
    if lower.startswith(("do it", "do that", "perform it", "click it", "go ahead")):
        return "control", text
    m = re.match(r"(?:search|find)\s+(?:youtube|on youtube)\s+(?:for\s+)?(.+)$", text, re.I)
    if m:
        return "youtube", m.group(1)
    m = re.match(r"(?:open|launch|start)\s+(.+)$", text, re.I)
    if m:
        return "open", m.group(1)
    m = re.match(r"(?:search|google)\s+(?:for\s+)?(.+)$", text, re.I)
    if m:
        return "search", m.group(1)
    m = re.match(r"(?:type|write)\s+(.+)$", text, re.I)
    if m:
        return "type", m.group(1)
    m = re.match(r"(?:press|hit)\s+(.+)$", text, re.I)
    if m:
        return "key", m.group(1)
    m = re.match(r"(?:move|put)\s+(?:the\s+)?mouse\s+(?:to\s+)?(\d+)\s*[ ,]\s*(\d+)$", text, re.I)
    if m:
        return "mouse", (int(m.group(1)), int(m.group(2)))
    return "ai", text


def ai_fallback(command):
    try:
        return ollama_chat(
            f"You are JARVIES, a concise local Windows voice assistant. The user said: {command}\n"
            "Answer naturally in one or two sentences. Never claim you performed an action unless the program did it."
        )
    except Exception:
        return "My local AI model is not available. Please make sure Ollama is running."


def handle(command):
    action, value = parse_command(command)
    if action == "exit":
        speak("Goodbye. Standing by.")
        return False
    if action == "open": speak(open_target(value))
    elif action == "search": speak(search_web(value))
    elif action == "youtube": speak(search_web(value, "youtube"))
    elif action == "screen":
        speak("One moment. I'm looking at your screen.")
        speak(inspect_screen(value))
    elif action == "control": speak(control_screen(value))
    elif action == "type": speak(type_text(value))
    elif action == "key": speak(press_key(value))
    elif action == "mouse":
        pyautogui.moveTo(*value, duration=0.2)
        speak(f"Moving to {value[0]}, {value[1]}.")
    else: speak(ai_fallback(value))
    return True


def voice_loop(running):
    while running.is_set():
        try:
            audio = listen_once()
            if audio is None:
                continue
            segments, _ = whisper.transcribe(audio, beam_size=1, vad_filter=True)
            transcript = " ".join(s.text.strip() for s in segments).strip()
            if not transcript:
                continue
            print(f"You (voice): {transcript}")
            if WAKE_WORD not in transcript.lower():
                continue
            command = re.sub(r"\b" + re.escape(WAKE_WORD) + r"\b[,:]?\s*", "", transcript, count=1, flags=re.I).strip()
            if not command:
                speak("Yes, sir. How can I help?")
                continue
            if not handle(command):
                running.clear()
                break
        except Exception as exc:
            print(f"Voice error: {exc}")
            time.sleep(1)


def main():
    running = threading.Event()
    running.set()
    speak("JARVIES online. Local systems are ready.")
    print("Voice mode: say 'JARVIES' followed by a command.")
    print("Typing mode: type a command below without the wake word.")
    print("Examples: open YouTube | search Minecraft | look at my screen | exit")
    print("Press Ctrl+C to stop.\n")

    voice_thread = threading.Thread(target=voice_loop, args=(running,), daemon=True)
    voice_thread.start()

    while running.is_set():
        try:
            command = input("You (type): ").strip()
            if not command:
                continue
            if not handle(command):
                running.clear()
                break
        except (KeyboardInterrupt, EOFError):
            running.clear()
            print("\nJARVIES stopped.")
            break


if __name__ == "__main__":
    main()
