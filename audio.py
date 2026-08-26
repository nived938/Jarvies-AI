import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 4


def listen_once(seconds: int = RECORD_SECONDS):
    """Capture a short microphone segment for local Whisper transcription."""
    try:
        recording = sd.rec(
            int(seconds * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
        )
        sd.wait()
        audio = np.squeeze(recording)
        if np.max(np.abs(audio)) < 0.008:
            return None
        return audio
    except Exception as exc:
        print(f"Microphone error: {exc}")
        return None
