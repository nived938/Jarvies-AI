# JARVIES AI

A local Windows voice assistant inspired by Iron Man's JARVIS.

## What it does

- 🎙️ Local speech recognition with Faster-Whisper
- 🧠 Local AI reasoning through Ollama
- 🔊 Local text-to-speech with Windows SAPI via pyttsx3
- 🖥️ Take a screenshot and ask JARVIES what is on your screen or where to click
- 🌐 Open websites and search the web by voice
- 🚀 Launch common Windows applications by voice
- ⌨️ Type text and press keyboard keys with voice commands
- 🖱️ Move/click the mouse when explicitly requested
- 🔒 Confirmation required for potentially destructive system actions
- 🌐 No cloud API key is required for the core assistant

## Requirements

Windows 10/11, Python 3.11+, Ollama, and a microphone.

Install Ollama, then pull a local model:

```powershell
ollama pull llama3.2:3b
```

For screen understanding, use a vision model such as:

```powershell
ollama pull llama3.2-vision:11b
```

The vision model is optional. JARVIES will still work for voice commands without it.

## Install

```powershell
cd Jarvies-AI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The first Faster-Whisper run downloads the selected speech model. After that, transcription runs locally.

## Run

Start Ollama first, then:

```powershell
python jarvies.py
```

Say **"JARVIES"** to activate a command. Say **"JARVIES, watch my screen"** to get a screen description.

You can also use push-to-talk with `Ctrl+Space` when the assistant is running.

## Example commands

- "JARVIES, open YouTube"
- "JARVIES, search YouTube for Minecraft survival"
- "JARVIES, open Discord"
- "JARVIES, take a look at my screen"
- "JARVIES, where do I click to change this setting?"
- "JARVIES, type hello world"
- "JARVIES, press Enter"
- "JARVIES, move the mouse to 500 400"

The assistant is intentionally conservative around file deletion, shutdown, reboot, formatting, and other destructive operations.

## Configuration

Environment variables:

- `JARVIES_MODEL`, default `llama3.2:3b`
- `JARVIES_VISION_MODEL`, default `llama3.2-vision:11b`
- `JARVIES_WHISPER_MODEL`, default `base.en`
- `JARVIES_WAKE_WORD`, default `jarvies`

Copy `.env.example` to `.env` to customize them.

## Privacy

The core application sends AI requests only to the local Ollama server at `127.0.0.1`. Screenshots are processed locally when using a local Ollama vision model.
