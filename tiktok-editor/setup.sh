#!/usr/bin/env bash
# Installs everything needed to edit TikTok clips with HyperFrames in a fresh cloud session.
# Safe to re-run: each step skips work that is already done.
set -euo pipefail

MODEL_DIR="${WHISPER_MODEL_DIR:-$HOME/models/whisper-small-ct2}"

# 1. HyperFrames skills for Claude (/hyperframes, /hyperframes-cli, /hyperframes-registry, /media-use)
if [ ! -d "$HOME/.claude/skills/hyperframes" ]; then
  npx -y hyperframes@latest skills update
fi

# 2. Headless Chrome used by HyperFrames to render HTML into MP4
npx -y hyperframes@latest browser ensure >/dev/null

# 3. Local transcription (faster-whisper). huggingface.co is blocked here,
#    so the Whisper "small" multilingual model is pulled from npm instead.
python3 -c "import faster_whisper" 2>/dev/null || pip install -q faster-whisper
if [ ! -f "$MODEL_DIR/model.bin" ]; then
  tmp="$(mktemp -d)"
  for i in 0 1 2 3; do
    (cd "$tmp" && npm pack -q "@skillninja/shortmovie-telop-model-p$i" >/dev/null)
    mkdir -p "$tmp/p$i" && tar xzf "$tmp"/skillninja-shortmovie-telop-model-p$i-*.tgz -C "$tmp/p$i"
  done
  mkdir -p "$MODEL_DIR"
  cp "$tmp"/p0/package/{config.json,preprocessor_config.json,tokenizer.json,vocabulary.json,model.sha256} "$MODEL_DIR/"
  cat "$tmp"/p0/package/model.bin.part0 "$tmp"/p1/package/model.bin.part1 \
      "$tmp"/p2/package/model.bin.part2 "$tmp"/p3/package/model.bin.part3 > "$MODEL_DIR/model.bin"
  (cd "$MODEL_DIR" && echo "$(cat model.sha256)  model.bin" | sha256sum -c --quiet)
  rm -rf "$tmp"
fi

# 3b. ivrit.ai Hebrew model: much more accurate for Hebrew. Needs huggingface.co
#     in the environment's allowed domains; skipped quietly when it is blocked.
IVRIT_DIR="$HOME/models/ivrit-large-v3-turbo-ct2"
if [ ! -f "$IVRIT_DIR/model.bin" ]; then
  python3 -c "from huggingface_hub import snapshot_download; snapshot_download('ivrit-ai/whisper-large-v3-turbo-ct2', local_dir='$IVRIT_DIR')" \
    >/dev/null 2>&1 || echo "note: huggingface.co unreachable, using Whisper small"
fi

# 4. GSAP and Hebrew fonts, vendored locally: cdn.jsdelivr.net is blocked here.
#    Copy vendor/ into each video project and reference vendor/gsap.min.js.
here="$(cd "$(dirname "$0")" && pwd)"
if [ ! -f "$here/vendor/gsap.min.js" ]; then
  (cd "$here" && npm install --silent --no-save gsap@3.14.2 @fontsource/rubik @fontsource/heebo @fontsource/secular-one)
  mkdir -p "$here/vendor/fonts"
  cp "$here/node_modules/gsap/dist/gsap.min.js" "$here/vendor/"
  cp "$here"/node_modules/@fontsource/{rubik,heebo,secular-one}/files/*-hebrew-*-normal.woff2 "$here/vendor/fonts/"
fi

# 5. Plate blurring and caption placement: detection, tracking, Drive downloads.
python3 -c "import cv2; cv2.TrackerCSRT_create" 2>/dev/null || {
  pip uninstall -y -q opencv-python opencv-python-headless 2>/dev/null || true
  pip install -q opencv-contrib-python-headless
}
python3 -c "import ultralytics, onnxruntime, mediapipe, gdown" 2>/dev/null || pip install -q ultralytics onnxruntime mediapipe gdown
mkdir -p "$HOME/models/plate" "$HOME/models/mp"
[ -f "$HOME/models/plate/plate-m.onnx" ] || curl -sSfL -o "$HOME/models/plate/plate-m.onnx" \
  https://huggingface.co/morsetechlab/yolov11-license-plate-detection/resolve/main/license-plate-finetune-v1m.onnx || true
[ -f "$HOME/models/mp/hand_landmarker.task" ] || curl -sSfL -o "$HOME/models/mp/hand_landmarker.task" \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task || true
[ -f "$HOME/models/mp/blaze_face_short_range.tflite" ] || curl -sSfL -o "$HOME/models/mp/blaze_face_short_range.tflite" \
  https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite || true

echo "tiktok-editor: ready"
