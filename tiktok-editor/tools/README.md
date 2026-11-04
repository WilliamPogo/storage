# tools

Scripts from the night-drive edit, kept as a starting point for the next plate-blur job.
The time ranges and boxes inside `track_yellow.py` belong to that video: change them per video.

1. `detect_plates.py <video> <out.json>` — YOLO plate detections for every frame.
2. `track_yellow.py <proj_dir>` — CSRT tracking from hand-picked boxes, plus edge boxes.
3. `verify.py <proj_dir> <t0> <t1> <step> <out.jpg>` — draws the boxes on frames to check by eye.
4. `blur_master.py <proj_dir> [boxes.json]` — blurs the boxes and writes a 1080x1920 master.
