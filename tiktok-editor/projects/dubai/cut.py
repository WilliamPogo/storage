"""Cut segments.json from the source and join them into clip/assets/aroll.mp4.

Usage: python3 cut.py <proj_dir>

The iPhone source is HDR (HLG); each cut is tone-mapped to SDR here, because the
renderer freezes frames on HDR input and TikTok shows SDR more reliably.
"""
import json
import subprocess
import sys
from pathlib import Path

proj = Path(sys.argv[1])
build = proj / "build"
segs = json.loads((build / "segments.json").read_text())
VF = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=mobius:desat=0,"
      "zscale=t=bt709:m=bt709:r=tv,scale=1080:1920,fps=30,format=yuv420p")

for f in build.glob("seg_*.mp4"):
    f.unlink()
with open(build / "list.txt", "w") as lst:
    for i, s in enumerate(segs):
        d = round(s["out"] - s["in"], 3)
        out = build / f"seg_{i:02d}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s["in"]), "-i", str(proj / "src" / "input.mov"),
                        "-t", str(d), "-map", "0:v:0", "-map", "0:a:0", "-vf", VF,
                        "-af", f"afade=t=in:d=0.02,afade=t=out:st={d - 0.03}:d=0.03,aresample=48000",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14",
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                        "-c:a", "aac", "-b:a", "256k", str(out)], check=True)
        lst.write(f"file '{out.name}'\n")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(build / "list.txt"),
                "-c", "copy", "-movflags", "+faststart", str(proj / "clip" / "assets" / "aroll.mp4")], check=True)
print(f"{len(segs)} segments cut")
