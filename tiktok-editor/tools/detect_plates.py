"""Detect license plates in every frame of a video.

Usage: python3 detect_plates.py <video> <out.json>
Writes {"fps":..., "w":..., "h":..., "frames": [[[x0,y0,x1,y1,conf], ...], ...]} in display orientation.
"""
import json
import sys

import cv2
from ultralytics import YOLO

src, out = sys.argv[1], sys.argv[2]
model = YOLO("/root/models/plate/plate-m.onnx", task="detect")
cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS)
frames = []
w = h = 0
while True:
    ok, img = cap.read()
    if not ok:
        break
    h, w = img.shape[:2]
    r = model.predict(img, imgsz=1280, conf=0.15, verbose=False)[0]
    frames.append([[*map(float, b.xyxy[0].tolist()), float(b.conf[0])] for b in r.boxes])
    if len(frames) % 60 == 0:
        print(f"{len(frames)} frames", flush=True)
json.dump({"fps": fps, "w": w, "h": h, "frames": frames}, open(out, "w"))
print(f"done: {len(frames)} frames, {w}x{h}, {sum(1 for f in frames if f)} with plates")
