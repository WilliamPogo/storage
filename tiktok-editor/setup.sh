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

echo "tiktok-editor: ready"
