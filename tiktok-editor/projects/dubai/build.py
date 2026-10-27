"""Generate clip/index.html from segments.json + words.json.

Usage: python3 build.py <proj_dir>
"""
import json
import math
import subprocess
import sys
from pathlib import Path

proj = Path(sys.argv[1])
build = proj / "build"
segs = json.loads((build / "segments.json").read_text())
words = json.loads((proj / "words.json").read_text())

WORDS_PER_GROUP = 3
MAX_CHARS = 14
CAPTION_TOP = 1110
W_ = 1080
FLAVOR_COLORS = {"פקאן": "#C47A3A", "מנגו": "#FFB000", "דובאי": "#3FA34D", "פסיפלורה": "#9B4DFF"}


def dur(f):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                         capture_output=True, text=True).stdout
    return float(out)


def clean(w):
    return w.strip().rstrip(".,")


# Timeline: each segment's real encoded length.
t = 0.0
for i, s in enumerate(segs):
    s["start"] = round(t, 3)
    s["len"] = dur(build / f"seg_{i:02d}.mp4")
    t += s["len"]
TOTAL = round(t, 3)

# Word timings: transcript words inside the segment window, matched by position to the
# corrected caption words; when counts differ, spread the corrected words evenly.
for s in segs:
    cap = s["words"].split()
    src = [w for w in words if s["in"] - 0.1 <= w["start"] < s["out"]]
    if len(src) == len(cap) and not s.get("spread"):
        times = [(w["start"], w["end"]) for w in src]
    else:
        a = src[0]["start"] if src else s["in"] + 0.05
        b = src[-1]["end"] if src else s["out"] - 0.05
        step = (b - a) / len(cap)
        times = [(a + k * step, a + (k + 1) * step) for k in range(len(cap))]
    s["timed"] = []
    for text, (a, b) in zip(cap, times):
        a = max(a, s["in"]) - s["in"] + s["start"]
        b = min(b, s["out"]) - s["in"] + s["start"]
        s["timed"].append({"text": text, "start": round(a, 3), "end": round(max(b, a + 0.08), 3)})

html = []
js = []
gid = 0

sys.path.insert(0, str(Path(__file__).parent))
from place import Detector, pick  # noqa: E402

det = Detector(proj / "clip" / "assets" / "aroll.mp4")
LINE_H = 118
SAFE_BOTTOM = 1330  # TikTok's caption/handle area starts below this


def caption_box(text, top):
    width = min(900, len(text) * 50 + 40 * text.count(" ") + 60)
    lines = math.ceil((len(text) * 50 + 40 * text.count(" ")) / 900) or 1
    return (540 - width / 2, top, 540 + width / 2, top + LINE_H * lines), lines


busy_top = []  # windows when a title or chips own the top of the frame
prev_top = None
cap_boxes = []  # (start, end, box) of every placed caption, so emojis avoid them


def el(tag, id_, start, duration, track, cls="", style="", body="", extra=""):
    html.append(f'<{tag} id="{id_}" class="clip {cls}" data-start="{start:.3f}" data-duration="{duration:.3f}" '
                f'data-track-index="{track}" style="{style}" {extra}>{body}</{tag}>')


# Caption groups: break at the group size or at sentence punctuation.
cap_html = []
for si, s in enumerate(segs):
    hl = {clean(h) for h in s.get("hl", [])}
    group = []
    groups = []
    for w in s["timed"]:
        # Keep every group on one line: start a new group when this word would overflow it.
        if group and len(" ".join(x["text"] for x in group + [w])) > MAX_CHARS:
            groups.append(group)
            group = []
        group.append(w)
        if len(group) >= WORDS_PER_GROUP or w["text"][-1] in ".?":
            groups.append(group)
            group = []
    if group:
        groups.append(group)
    for gi, g in enumerate(groups):
        start = g[0]["start"] - 0.04 if gi else s["start"] + 0.02
        end = groups[gi + 1][0]["start"] - 0.04 if gi + 1 < len(groups) else s["start"] + s["len"] - 0.02
        start = max(start, s["start"] + 0.02)
        gid_ = f"cap{gid}"
        text_all = " ".join(w["text"] for w in g)
        _, lines = caption_box(text_all, 0)
        h = LINE_H * lines
        tops = [(SAFE_BOTTOM - h, 0), (1110, 6000)]
        if not (si == 0 or si == len(segs) - 1 or s.get("flavors")):
            tops.append((250, 60000))
        # Jumping between top and bottom is hard to read: changing position costs extra.
        top = pick(det, [(caption_box(text_all, y)[0], pen + (40000 if prev_top and abs(y - prev_top) > 300 else 0), y)
                         for y, pen in tops], start, end)
        prev_top = top
        cap_boxes.append((start, end, caption_box(text_all, top)[0]))
        spans = []
        for wi, w in enumerate(g):
            wid = f"{gid_}w{wi}"
            text = clean(w["text"]) if w["text"][-1] in ".," else w["text"]
            k = "hl" if clean(w["text"]) in hl else ""
            spans.append(f'<span id="{wid}" class="w {k}">{text}</span>')
            js.append(f'tl.to("#{wid}", {{ color: "#FFE600", scale: {1.22 if k else 1.1}, duration: 0.08, ease: "power3.out" }}, {w["start"]:.3f});')
            if wi + 1 < len(g):
                js.append(f'tl.to("#{wid}", {{ color: "{"#FFE600" if k else "#FFFFFF"}", scale: 1, duration: 0.1 }}, {g[wi + 1]["start"]:.3f});')
        cap_html.append(f'<div id="{gid_}" class="clip cap" dir="rtl" data-start="{start:.3f}" data-duration="{end - start:.3f}" '
                        f'data-track-index="2" style="top: {top}px;"><div class="capin" id="{gid_}i">{" ".join(spans)}</div></div>')
        js.append(f'tl.fromTo("#{gid_}i", {{ scale: 0.6, y: 30, opacity: 0 }}, {{ scale: 1, y: 0, opacity: 1, duration: 0.16, ease: "back.out(2.5)" }}, {start:.3f});')
        gid += 1

# Video: one wrapper per segment so each cut gets its own framing (jump-cut zoom) and punch-ins.
vid_wrap_js = []
for si, s in enumerate(segs):
    base = 1.0
    st = s["start"]
    vid_wrap_js.append(f'tl.set("#frame", {{ scale: {base}, x: 0, rotation: 0 }}, {st:.3f});')
    if s.get("punch"):
        w = next(w for w in s["timed"] if w["text"] == s["punch"])
        vid_wrap_js.append(f'tl.to("#frame", {{ scale: 1.15, duration: 0.18, ease: "expo.out" }}, {w["start"]:.3f});')
        if w["start"] + 1.3 < st + s["len"]:
            vid_wrap_js.append(f'tl.to("#frame", {{ scale: {base}, duration: 0.35, ease: "power2.inOut" }}, {w["start"] + 0.9:.3f});')
    if s.get("shake"):
        w = next(w for w in s["timed"] if w["text"] == s["shake"])
        vid_wrap_js.append(f'tl.to("#frame", {{ keyframes: [{{x: -28, rotation: -1.5}}, {{x: 24, rotation: 1.2}}, {{x: -16, rotation: -0.8}}, {{x: 10, rotation: 0.5}}, {{x: 0, rotation: 0}}], duration: 0.4, ease: "none" }}, {w["start"]:.3f});')

# Emojis: pop beside the caption at the segment's first highlighted word, with a pop sound.
sfx = []
for si, s in enumerate(segs):
    if not s.get("emoji"):
        continue
    hl = [clean(h) for h in s.get("hl", [])]
    at = next((w["start"] for w in s["timed"] if clean(w["text"]) in hl), s["timed"][0]["start"])
    end = s["start"] + s["len"]
    eid = f"emo{si}"
    cands = []
    for side in ("left", "right"):
        x0 = 70 if side == "left" else W_ - 270
        for y, pen in ((860, 0), (700, 2000), (560, 6000), (1000, 6000), (420, 12000)):
            box = (x0, y, x0 + 200, y + 200)
            clash = sum(5 * max(0, min(box[2], b[2]) - max(box[0], b[0])) * max(0, min(box[3], b[3]) - max(box[1], b[1]))
                        for cs, ce, b in cap_boxes if cs < end and ce > at)
            cands.append((box, pen + clash + (0 if (side == "left") == (si % 2 == 0) else 1500), (side, y)))
    side, ey = pick(det, cands, at, end)
    left = side == "left"
    pos = "left: 70px;" if left else "right: 70px;"
    el("div", eid, at, end - at, 3, "emo", f"{pos} top: {ey}px;", f'<div class="emoin" id="{eid}i">{s["emoji"]}</div>')
    js.append(f'tl.fromTo("#{eid}i", {{ scale: 0, rotation: {-25 if left else 25} }}, {{ scale: 1, rotation: {-8 if left else 8}, duration: 0.35, ease: "back.out(3)" }}, {at:.3f});')
    js.append(f'tl.to("#{eid}i", {{ y: -14, duration: 0.5, ease: "sine.inOut", yoyo: true, repeat: {max(0, int((end - at - 0.5) / 0.5))} }}, {at + 0.35:.3f});')
    sfx.append((f"pop{si}", "assets/sfx/pop.wav", at, 0.35))

# Whoosh on punch-ins.
for si, s in enumerate(segs):
    if s.get("punch"):
        w = next(w for w in s["timed"] if w["text"] == s["punch"])
        sfx.append((f"wh{si}", "assets/sfx/whoosh.wav", max(0, w["start"] - 0.12), 0.25))

# Hook title over the opening segment.
s0 = segs[0]
el("div", "hook", 0.0, s0["len"], 4, "hook", "", '<div id="hooki" class="hookin">דובי כי זה דובאי 🧸</div>', 'dir="rtl"')
js.append('tl.fromTo("#hooki", { scale: 1.6, opacity: 0, rotation: -8 }, { scale: 1, opacity: 1, rotation: -3, duration: 0.3, ease: "back.out(2)" }, 0.0);')

# Flavor chips during the flavor list.
fs = next(s for s in segs if s.get("flavors"))
seen = []
for w in fs["timed"]:
    name = clean(w["text"])
    if name in seen:
        continue
    seen.append(name)
for k, name in enumerate(seen):
    w = next(w for w in fs["timed"] if clean(w["text"]) == name)
    cid = f"chip{k}"
    end = fs["start"] + fs["len"]
    top = 230 + k * 120
    el("div", cid, w["start"], end - w["start"], 4, "chip",
       f"top: {top}px; right: 80px; background: {FLAVOR_COLORS.get(name, '#FF2D55')};", name, 'dir="rtl"')
    js.append(f'tl.fromTo("#{cid}", {{ x: 400, opacity: 0 }}, {{ x: 0, opacity: 1, duration: 0.25, ease: "expo.out" }}, {w["start"]:.3f});')
    sfx.append((f"cp{k}", "assets/sfx/pop.wav", w["start"], 0.25))

# Closing badge on the final line.
last = segs[-1]
el("div", "outro", last["start"], last["len"], 4, "hook", "", '<div id="outroi" class="hookin pink">⭐ עקבו לעוד טעימות ⭐</div>', 'dir="rtl"')
js.append(f'tl.fromTo("#outroi", {{ scale: 0, rotation: 6 }}, {{ scale: 1, rotation: 2, duration: 0.35, ease: "back.out(2.5)" }}, {last["start"]:.3f});')

audio_html = "\n".join(
    f'<audio id="{i}" class="clip" src="{src}" data-start="{st:.3f}" data-duration="{d}" data-track-index="5" data-volume="{0.35 if i.startswith("wh") else 0.5}"></audio>'
    for i, src, st, d in sfx)

page = f"""<!doctype html>
<html lang="he">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="assets/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Rubik"; font-weight: 900; src: url(assets/fonts/rubik-hebrew-900-normal.woff2) format("woff2"); unicode-range: U+0590-05FF, U+200C-2010, U+20AA, U+25CC, U+FB1D-FB4F; }}
      @font-face {{ font-family: "Rubik"; font-weight: 900; src: url(assets/fonts/rubik-latin-900-normal.woff2) format("woff2"); unicode-range: U+0000-00FF, U+2000-206F; }}
      @font-face {{ font-family: "Noto Color Emoji"; src: url(assets/fonts/NotoColorEmoji.ttf) format("truetype"); }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
      body {{ font-family: "Rubik", "Noto Color Emoji", sans-serif; }}
      #stage {{ position: absolute; inset: 0; overflow: hidden; }}
      #frame {{ position: absolute; inset: 0; transform-origin: 50% 30%; }}
      #aroll {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
      #captions {{ position: absolute; inset: 0; }}
      .cap {{ position: absolute; left: 0; right: 0; top: {CAPTION_TOP}px; padding: 0 90px; text-align: center; overflow: visible; }}
      .capin {{ display: inline-block; font-weight: 900; font-size: 96px; line-height: 1.15; color: #fff;
               -webkit-text-stroke: 14px #000; paint-order: stroke fill; text-shadow: 0 8px 0 rgba(0,0,0,.55); }}
      .w {{ display: inline-block; margin: 0 20px; }}
      .w.hl {{ color: #FFE600; }}
      .emo {{ position: absolute; width: 200px; height: 200px; }}
      .emoin {{ font-family: "Noto Color Emoji"; font-size: 150px; line-height: 200px; text-align: center; filter: drop-shadow(0 8px 10px rgba(0,0,0,.4)); }}
      .hook {{ position: absolute; left: 0; right: 0; top: 230px; text-align: center; }}
      .hookin {{ display: inline-block; font-weight: 900; font-size: 84px; color: #000; background: #FFE600;
                 padding: 18px 44px 24px; border-radius: 28px; box-shadow: 0 10px 0 #000; }}
      .hookin.pink {{ background: #FF2D78; color: #fff; }}
      .chip {{ position: absolute; font-weight: 900; font-size: 64px; color: #fff; padding: 10px 36px 16px; border-radius: 999px;
               -webkit-text-stroke: 8px #000; paint-order: stroke fill; border: 6px solid #000; box-shadow: 0 8px 0 #000; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL:.3f}" data-width="1080" data-height="1920">
      <div id="stage">
        <div id="frame">
          <video id="aroll" class="clip" src="assets/aroll.mp4" playsinline data-has-audio="true" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="0"></video>
        </div>
      </div>
      <div id="captions" data-track-kind="captions">
{chr(10).join(cap_html)}
      </div>
{chr(10).join(html)}
{audio_html}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
{chr(10).join(vid_wrap_js)}
{chr(10).join(js)}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
(proj / "clip" / "index.html").write_text(page, encoding="utf-8")
print(f"total {TOTAL}s, {gid} caption groups, {len(sfx)} sfx")
