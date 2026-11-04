"""Track only the green car's yellow number plate; keep the parked car's plate box.

Usage: python3 track_yellow.py <proj_dir>   -> blur_boxes_yellow.json
"""
import json
import sys
from pathlib import Path

import cv2

proj = Path(sys.argv[1])
d = json.loads((proj / "blur_boxes.json").read_text())
fps = d["fps"]
S = 4
cap = cv2.VideoCapture(str(proj / "src" / "input.mov"))
small = []
while True:
    ok, img = cap.read()
    if not ok:
        break
    small.append(cv2.resize(img, (img.shape[1] // S, img.shape[0] // S), interpolation=cv2.INTER_AREA))
N = len(small)


def fi(t):
    return min(N - 1, int(round(t * fps)))


# Parked car (first seconds): keep its existing boxes.
out = [list(d["frames"][i]) if i < fi(3.4) else [] for i in range(N)]
for i in range(fi(3.4), fi(4.3) + 1):  # its plate sliding out on the right: a tight box, not the wide hold
    out[i].append([2010, 1880, 2160, 2100])


def track(t0, box, t_from, t_to):
    for step, t_end in ((1, t_to), (-1, t_from)):
        tr = cv2.TrackerCSRT_create()
        x0, y0, x1, y1 = [v / S for v in box]
        tr.init(small[fi(t0)], (int(x0), int(y0), int(x1 - x0), int(y1 - y0)))
        for i in range(fi(t0), fi(t_end) + step, step):
            ok, (x, y, w, h) = tr.update(small[i])
            if ok:
                w_, h_ = w * S, h * S
                out[i].append([x * S - 0.12 * w_, y * S - 0.3 * h_, (x + w) * S + 0.12 * w_, (y + h) * S + 0.3 * h_])


track(6.6, (370, 1290, 470, 1385), 5.6, 7.2)      # side view, plate at the left of the grille
track(10.6, (710, 1790, 1180, 2020), 9.8, 11.4)   # head-on approach

# Entering from the left edge just before 9.8 s: slide the 9.8 s box back along its own motion, clipped at
# the frame edge, so it never reaches the white "זהות" plate to its right.
a, b = out[fi(9.8)][-1], out[fi(9.95)][-1]
vx = (a[2] - b[2]) / (fi(9.95) - fi(9.8))  # px per frame, negative going back in time
for i in range(fi(9.62), fi(9.8)):
    k = fi(9.8) - i
    x1 = a[2] + vx * k
    if x1 > 0:
        out[i].append([0, a[1], x1, a[3]])

(proj / "blur_boxes_yellow.json").write_text(json.dumps({"fps": fps, "frames": out}))
print(f"{N} frames, {sum(1 for f in out if f)} with boxes")
