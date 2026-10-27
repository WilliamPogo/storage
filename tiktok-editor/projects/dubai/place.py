"""Keep captions and emojis off the face and hands.

Samples frames from the cut a-roll, finds the face and hands with MediaPipe, and for each
overlay picks the candidate position whose box overlaps them least.
"""
import os

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

MODELS = os.path.expanduser("~/models/mp")
W, H = 1080, 1920


class Detector:
    def __init__(self, video):
        self.cap = cv2.VideoCapture(str(video))
        self.face = vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(
            base_options=BaseOptions(model_asset_path=f"{MODELS}/blaze_face_short_range.tflite"),
            min_detection_confidence=0.4))
        self.hands = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=f"{MODELS}/hand_landmarker.task"),
            num_hands=2, min_hand_detection_confidence=0.3))
        self.cache = {}

    def boxes(self, t):
        """Face and hand boxes (x0, y0, x1, y1, weight) in 1080x1920 frame pixels at time t."""
        key = round(t, 2)
        if key in self.cache:
            return self.cache[key]
        self.cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = self.cap.read()
        out = []
        if ok:
            img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            for d in self.face.detect(img).detections:
                b = d.bounding_box
                # Pad: the detector box is tight; include forehead, chin and glasses.
                out.append((b.origin_x - 60, b.origin_y - 140, b.origin_x + b.width + 60,
                            b.origin_y + b.height + 90, 4.0))
            for lm in self.hands.detect(img).hand_landmarks:
                xs = [p.x * W for p in lm]
                ys = [p.y * H for p in lm]
                out.append((min(xs) - 40, min(ys) - 40, max(xs) + 40, max(ys) + 40, 2.0))
        self.cache[key] = out
        return out


def overlap(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(0, w) * max(0, h)


def cost(det, box, start, end):
    times = [start + (end - start) * k for k in (0.15, 0.5, 0.85)]
    total = 0.0
    for t in times:
        for b in det.boxes(t):
            total += overlap(box, b[:4]) * b[4]
    return total / len(times)


def pick(det, candidates, start, end):
    """candidates: [(box, preference_penalty, value)]; returns the value with the lowest cost."""
    return min(candidates, key=lambda c: cost(det, c[0], start, end) + c[1])[2]
