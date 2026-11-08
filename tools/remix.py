"""Remix-Builder: baut neue Craftamico-Videos aus vorhandenem Material.
Alte Text-Pillen werden mit neuen Pillen in derselben Zone überdeckt.
Aufruf: python3 remix.py <spec.json>
spec: {"out": "...mp4", "voice": "...mp3", "end": {"title": "...", "sub": ["..",".."], "cta": "..."},
       "segs": [{"src": "...", "start": 0.3, "dur": 4, "zone": "top|mid|none", "lines": ["..."], "tag": "...", "speed": 1, "zoom": 1.0}]}
"""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
NAVY = (27, 35, 64, 255)
BLUE = (70, 85, 229)
FS = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
FB = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FM = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
MEDIA = "/home/claude/media"
MUSIC = f"{MEDIA}/audio/craftamico-standard.mp3"
LOGO = f"{MEDIA}/raw/logo-gross.png"
# Zonen, in denen die alten Pillen sitzen (inkl. Rand)
ZONES = {"top": (130, 296, 950, 512), "mid": (80, 1136, 1000, 1342)}


def run(c):
    subprocess.run(c, check=True)


def overlay(seg, path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FS, 50)
    lines = seg.get("lines", [])
    zone = seg.get("zone", "none")
    lh = 64
    tw = max([d.textlength(l, font=f) for l in lines] or [0])
    pw, ph = int(tw + 80), lh * len(lines) + 48
    if zone in ZONES:
        x0, y0, x1, y1 = ZONES[zone]
        z = seg.get("zoom", 1.0)
        if z != 1.0:
            x0, x1 = (x0 - W/2)*z + W/2 - 10, (x1 - W/2)*z + W/2 + 10
            y0, y1 = (y0 - H/2)*z + H/2 - 10, (y1 - H/2)*z + H/2 + 10
        pw, ph = max(pw, x1 - x0), max(ph, y1 - y0)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        bx0, by0 = cx - pw / 2, cy - ph / 2
    else:
        bx0, by0 = (W - pw) / 2, seg.get("y", 330)
    if lines:
        d.rounded_rectangle([bx0, by0, bx0 + pw, by0 + ph], radius=28, fill=NAVY)
        ty = by0 + (ph - lh * len(lines)) / 2 + 2
        for i, l in enumerate(lines):
            lw = d.textlength(l, font=f)
            d.text(((W - lw) / 2 if zone == "none" else bx0 + (pw - lw) / 2, ty + i * lh), l, font=f, fill="white")
    tag = seg.get("tag")
    if tag:
        ft = ImageFont.truetype(FM, 30)
        t2 = d.textlength(tag, font=ft)
        tx0 = bx0 + (pw - t2 - 36) / 2
        ty0 = by0 + ph + 16
        d.rounded_rectangle([tx0, ty0, tx0 + t2 + 36, ty0 + 50], radius=25, fill=(255, 255, 255, 230))
        d.text((tx0 + 18, ty0 + 8), tag, font=ft, fill=(60, 60, 70))
    im.save(path)


def endcard(spec, path):
    e = spec["end"]
    im = Image.new("RGB", (W, H), "white")
    lg = Image.open(LOGO).convert("RGBA")
    lw = 820
    lg = lg.resize((lw, round(lg.height * lw / lg.width)), Image.LANCZOS)
    im.paste(lg, ((W - lw) // 2, 560), lg)
    d = ImageDraw.Draw(im)

    def ct(t, font, y, fill):
        w = d.textlength(t, font=font)
        d.text(((W - w) / 2, y), t, font=font, fill=fill)
    ct(e["title"], ImageFont.truetype(FB, 54), 1060, (20, 21, 26))
    for i, s in enumerate(e.get("sub", [])):
        ct(s, ImageFont.truetype(FM, 38), 1150 + i * 50, (90, 95, 105))
    ct(e["cta"], ImageFont.truetype(FS, 44), 1170 + 50 * len(e.get("sub", [])) + 30, BLUE)
    im.save(path)


def main(spec_path):
    spec = json.load(open(spec_path))
    tmp = os.path.splitext(spec["out"])[0] + "_tmp"
    os.makedirs(tmp, exist_ok=True)
    parts = []
    for i, s in enumerate(spec["segs"]):
        ov = f"{tmp}/o{i}.png"
        overlay(s, ov)
        sp = s.get("speed", 1)
        z = s.get("zoom", 1.0)
        zf = f",scale={int(W*z)}:{int(H*z)},crop={W}:{H}" if z != 1.0 else ""
        base = f"scale={W}:-2,crop={W}:{H}:0:{s['crop_top']}" if "crop_top" in s else f"scale={W}:{H}"
        vf = (f"[0:v]{base}{zf},setpts=(PTS-STARTPTS)/{sp},fps={FPS}[b];"
              f"[b][1:v]overlay=0:0,format=yuv420p")
        p = f"{tmp}/s{i}.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-ss", str(s["start"]), "-t", str(s["dur"] * sp), "-i", s["src"] if s["src"].startswith("/") else f"{MEDIA}/{s['src']}",
             "-i", ov, "-filter_complex", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", p])
        parts.append(p)
    endcard(spec, f"{tmp}/end.png")
    p = f"{tmp}/s_end.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", f"{tmp}/end.png", "-vf", f"fps={FPS},format=yuv420p,fade=in:st=0:d=0.4",
         "-t", str(spec.get("end_dur", 4)), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", p])
    parts.append(p)
    with open(f"{tmp}/list.txt", "w") as fh:
        fh.writelines(f"file '{x}'\n" for x in parts)
    silent = f"{tmp}/silent.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{tmp}/list.txt", "-c", "copy", silent])
    total = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", silent]))
    af = (f"[1:a]adelay=300|300[v];[2:a]volume=0.12,afade=t=out:st={total-1.5}:d=1.5[m];"
          f"[v][m]amix=inputs=2:duration=longest:normalize=0,atrim=0:{total}[a]")
    run(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", spec["voice"], "-i", MUSIC, "-filter_complex", af,
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", spec["out"]])
    print(spec["out"], round(total, 2))


if __name__ == "__main__":
    main(sys.argv[1])
