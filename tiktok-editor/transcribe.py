"""Word-level transcript for HyperFrames captions.

Usage: python3 transcribe.py <video> <out.json> [language]

Writes [{"id": "w0", "text": "...", "start": 0.0, "end": 0.5}, ...],
the format the /hyperframes captions reference works from.
"""
import json
import os
import subprocess
import sys

import numpy as np
from faster_whisper import WhisperModel

# Prefer the ivrit.ai Hebrew model (needs huggingface.co); fall back to Whisper small from npm.
IVRIT_DIR = os.path.expanduser("~/models/ivrit-large-v3-turbo-ct2")
SMALL_DIR = os.path.expanduser("~/models/whisper-small-ct2")
MODEL_DIR = os.environ.get("WHISPER_MODEL_DIR") or (
    IVRIT_DIR if os.path.exists(os.path.join(IVRIT_DIR, "model.bin")) else SMALL_DIR
)


def load_audio(path):
    # Decode with ffmpeg: the PyAV build bundled here can't open files directly.
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
        capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32)


def main():
    src, out = sys.argv[1], sys.argv[2]
    language = sys.argv[3] if len(sys.argv) > 3 else "he"
    model = WhisperModel(MODEL_DIR, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        load_audio(src), language=language, word_timestamps=True, vad_filter=True, beam_size=5
    )
    words = []
    for seg in segments:
        for w in seg.words:
            text = w.word.strip()
            if text:
                words.append({"id": f"w{len(words)}", "text": text,
                              "start": round(w.start, 3), "end": round(w.end, 3)})
    with open(out, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=1)
    print(f"{len(words)} words -> {out}")


if __name__ == "__main__":
    main()
