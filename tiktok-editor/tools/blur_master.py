"""Blur plates and write a 1080x1920 master at the source frame rate.

Usage: python3 blur_master.py <proj_dir>
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

proj = Path(sys.argv[1])
d = json.loads((proj / (sys.argv[2] if len(sys.argv) > 2 else "blur_boxes.json")).read_text())
cap = cv2.VideoCapture(str(proj / "src" / "input.mov"))
fps = cap.get(cv2.CAP_PROP_FPS)
OW, OH = 1080, 1920
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}",
                        "-r", f"{fps}", "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "10",
                        "-pix_fmt", "yuv420p", str(proj / "master.mp4")], stdin=subprocess.PIPE)
i = 0
while True:
    ok, img = cap.read()
    if not ok:
        break
    img = cv2.resize(img, (OW, OH), interpolation=cv2.INTER_AREA)
    boxes = d["frames"][i] if i < len(d["frames"]) else []
    if boxes:
        # Heavy blur inside each box, blended through a feathered mask so the edit doesn't show a hard square.
        mask = np.zeros((OH, OW), np.float32)
        for b in boxes:
            x0, y0, x1, y1 = [int(v / 2) for v in b]
            cv2.rectangle(mask, (x0, y0), (x1, y1), 1.0, -1)
        mask = cv2.GaussianBlur(mask, (0, 0), 6)[..., None]
        small = cv2.resize(img, (OW // 16, OH // 16), interpolation=cv2.INTER_AREA)
        blurred = cv2.GaussianBlur(cv2.resize(small, (OW, OH), interpolation=cv2.INTER_LINEAR), (0, 0), 6)
        img = (img * (1 - mask) + blurred * mask).astype(np.uint8)
    enc.stdin.write(img.tobytes())
    i += 1
enc.stdin.close()
enc.wait()
print(f"{i} frames at {fps:.3f} fps")
