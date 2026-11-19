"""Build LinkedIn images for the Agentic Pilot paper from real assets in this repository.

Run:  python make_images.py      (needs Pillow; reads ../report/fig/cad and ../report/fig)
Output: 2400x1254 PNGs (LinkedIn's 1.91:1 link-image ratio, at 2x).
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).parent
FIG = HERE.parent / "report" / "fig"
CAD = FIG / "cad"
OUT = HERE
W, H = 2400, 1254

NAVY = (14, 47, 92)
BLUE = (18, 65, 127)
GOLD = (201, 162, 39)
LIGHT = (215, 224, 240)
WHITE = (255, 255, 255)
INK = (34, 34, 34)
GREY = (107, 107, 107)
BG = (244, 246, 250)
ORANGE = (208, 122, 28)

FD = "/usr/share/fonts/opentype/inter/"


def font(size, weight="Regular"):
    return ImageFont.truetype(f"{FD}Inter-{weight}.otf", size)


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def para(draw, xy, text, fnt, fill, width, spacing=1.3):
    x, y = xy
    for ln in wrap(draw, text, fnt, width):
        draw.text((x, y), ln, font=fnt, fill=fill)
        y += int(fnt.size * spacing)
    return y


def centered(draw, cx, y, text, fnt, fill):
    draw.text((cx - draw.textlength(text, font=fnt) / 2, y), text, font=fnt, fill=fill)


def shadowed(canvas, img, xy, border=6):
    """Paste img with a white border and soft shadow."""
    x, y = xy
    w, h = img.size
    sh = Image.new("RGBA", (w + 2 * border + 60, h + 2 * border + 60), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((30, 40, 30 + w + 2 * border, 40 + h + 2 * border), fill=(0, 0, 0, 90))
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    canvas.paste(sh, (x - 30, y - 30), sh)
    framed = Image.new("RGB", (w + 2 * border, h + 2 * border), WHITE)
    framed.paste(img, (border, border))
    canvas.paste(framed, (x, y))
    return framed.size


def fit(img, box_w, box_h):
    s = min(box_w / img.width, box_h / img.height)
    return img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)


def arrow(d, p0, p1, fill, width=8, head=22):
    d.line([p0, p1], fill=fill, width=width)
    import math
    a = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    pts = [p1,
           (p1[0] - head * math.cos(a - 0.45), p1[1] - head * math.sin(a - 0.45)),
           (p1[0] - head * math.cos(a + 0.45), p1[1] - head * math.sin(a + 0.45))]
    d.polygon(pts, fill=fill)


def footer(d, text, dark=False):
    d.text((90, H - 78), text, font=font(30), fill=LIGHT if dark else GREY)
    r = "Sudesh P  |  Dr. Kanchana M  |  SRM Institute of Science and Technology"
    d.text((W - 90 - d.textlength(r, font=font(30)), H - 78), r, font=font(30), fill=LIGHT if dark else GREY)


# ---------------------------------------------------------------- 1. Agentic loop cover
def cover():
    im = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 24, H), fill=GOLD)
    d.text((90, 70), "RESEARCH PAPER  |  AGENTIC AI", font=font(34, "Bold"), fill=GOLD)
    d.text((90, 130), "Agentic Pilot", font=font(150, "ExtraBold"), fill=WHITE)
    para(d, (94, 322), "An evidence-driven local AI agent: it reports “done” only when the page proves it.",
         font(54, "Medium"), LIGHT, 1750)

    # the loop
    nodes = [("Goal", "your request"), ("Plan", "local model"), ("Act", "browser or CAD"),
             ("Observe", "the page"), ("Gate Φ", "rule over the page"), ("Done", "+ stored evidence")]
    bw, bh, gap = 300, 170, 78
    total = len(nodes) * bw + (len(nodes) - 1) * gap
    x0, y0 = (W - total) // 2, 560
    centers = []
    for i, (t, s) in enumerate(nodes):
        x = x0 + i * (bw + gap)
        gate = t.startswith("Gate")
        done = t == "Done"
        fill = GOLD if gate else (WHITE if done else BLUE)
        txt = NAVY if (gate or done) else WHITE
        d.rounded_rectangle((x, y0, x + bw, y0 + bh), radius=26, fill=fill, outline=WHITE if not (gate or done) else None, width=3)
        centered(d, x + bw / 2, y0 + 34, t, font(56, "Bold"), txt)
        centered(d, x + bw / 2, y0 + 108, s, font(30), txt)
        centers.append(x + bw / 2)
        if i:
            arrow(d, (x - gap + 8, y0 + bh / 2), (x - 6, y0 + bh / 2), WHITE)
    # return path: gate fails -> back to plan
    gx, px = centers[4], centers[1]
    yb = y0 + bh + 95
    d.line([(gx, y0 + bh), (gx, yb), (px, yb)], fill=ORANGE, width=8)
    arrow(d, (px, yb), (px, y0 + bh + 6), ORANGE)
    centered(d, (gx + px) / 2, yb + 18, "gate fails: keep working or re-plan", font(36, "Medium"), (255, 200, 120))
    centered(d, (centers[4] + centers[5]) / 2, y0 - 52, "holds", font(32, "Medium"), (160, 230, 170))

    # stats
    stats = [("9 of 22", "premature “done” claims withheld\n(frozen held-out states)"),
             ("1 of 20", "good states rejected by mistake"),
             ("27 ms", "median cost per check,\nno model call")]
    sw, sx0, sy = 640, 160, 930
    for i, (big, small) in enumerate(stats):
        x = sx0 + i * (sw + 70)
        d.text((x, sy), big, font=font(84, "ExtraBold"), fill=GOLD)
        yy = sy + 106
        for ln in small.split("\n"):
            d.text((x, yy), ln, font=font(32), fill=LIGHT)
            yy += 42
    footer(d, "Component-level results on constructed test states.", dark=True)
    im.save(OUT / "1_agentic_loop_cover.png")


# ---------------------------------------------------------------- 2. CAD
def cad():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 190), fill=NAVY)
    d.text((90, 38), "One sentence in, a CAD model out", font=font(78, "ExtraBold"), fill=WHITE)
    d.text((90, 132), "The agent plans, builds step by step in FreeCAD, and exports the part", font=font(38), fill=LIGHT)

    prompt = Image.open(CAD / "02-sprocket-prompt.png").convert("RGB").crop((0, 0, 1250, 420))
    partial = Image.open(CAD / "06-freecad-partial-build.png").convert("RGB").crop((0, 40, 1920, 790))
    result = Image.open(CAD / "08-results-drawings-and-metrics.png").convert("RGB").crop((820, 110, 1900, 760))
    final = Image.open(CAD / "09-freecad-final-sprocket.png").convert("RGB").crop((0, 40, 1920, 790))
    tiles = [("1  Prompt", prompt), ("2  Builds in FreeCAD", partial), ("3  Drawings, metrics, exports", result), ("4  Finished model", final)]
    tw, th = 1060, 380
    xs = [90, 90 + tw + 100]
    ys = [215, 215 + 455]
    for i, (label, img) in enumerate(tiles):
        x, y = xs[i % 2], ys[i // 2]
        d.text((x, y - 6), label, font=font(40, "Bold"), fill=BLUE)
        pic = fit(img, tw, th)
        shadowed(im, pic, (x + (tw - pic.width) // 2, y + 52), border=5)
    footer(d, "Illustrative demonstration run, 17 Nov 2026. Not an evaluated result of the paper.")
    im.save(OUT / "2_agent_builds_cad_model.png")


# ---------------------------------------------------------------- 3. Browser task
def browser():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 190), fill=NAVY)
    d.text((90, 38), "The agent drives a real browser", font=font(78, "ExtraBold"), fill=WHITE)
    d.text((90, 132), "Recorded task: search the web for “Agentic AI”, no human clicks", font=font(38), fill=LIGHT)
    frames = [("1  Opens the page", FIG / "demo_a.png"), ("2  Types the query", FIG / "demo_b.png"), ("3  Reads the results", FIG / "demo_c.png")]
    tw = 700
    for i, (label, p) in enumerate(frames):
        x = 60 + i * (tw + 90)
        img = Image.open(p).convert("RGB")
        img = img.crop((0, 0, 1500, 806))
        d.text((x, 300), label, font=font(42, "Bold"), fill=BLUE)
        pic = fit(img, tw, 520)
        shadowed(im, pic, (x, 375), border=5)
        if i < 2:
            arrow(d, (x + tw + 14, 570), (x + tw + 80, 570), GOLD, width=10, head=26)
    d.rounded_rectangle((90, 900, W - 90, 1080), radius=24, fill=WHITE)
    para(d, (130, 935), "Every action is followed by a check of what the page actually shows. The agent may report the task done "
         "only when that check holds, and each decision is stored as evidence.", font(40), INK, W - 300)
    footer(d, "Frames from the recorded demo in the repo.")
    im.save(OUT / "3_agent_browser_task.png")


# ---------------------------------------------------------------- 4. Numbers
def numbers():
    im = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 24, H), fill=GOLD)
    d.text((90, 70), "WHY A COMPLETION GATE?", font=font(34, "Bold"), fill=GOLD)
    d.text((90, 125), "Don’t trust an agent’s “done”", font=font(120, "ExtraBold"), fill=WHITE)
    para(d, (94, 290), "A successful action is not a finished task. Agentic Pilot checks the page before it says so.",
         font(50, "Medium"), LIGHT, 2000)
    cards = [("9 / 22", "premature “done” claims withheld", "frozen held-out states"),
             ("1 / 20", "good states wrongly rejected", "95% interval 0.01–0.24"),
             ("27 ms", "median time per decision", "no model call, zero tokens"),
             ("555 / 555", "connections stayed on 127.0.0.1", "70 episodes, agent’s Python processes")]
    cw, ch, gap = 500, 440, 60
    x0 = (W - (4 * cw + 3 * gap)) // 2
    for i, (big, mid, small) in enumerate(cards):
        x = x0 + i * (cw + gap)
        d.rounded_rectangle((x, 520, x + cw, 520 + ch), radius=30, fill=BLUE)
        d.text((x + 36, 560), big, font=font(92, "ExtraBold"), fill=GOLD)
        para(d, (x + 36, 700), mid, font(42, "Bold"), WHITE, cw - 72)
        para(d, (x + 36, 840), small, font(32), LIGHT, cw - 72)
    d.text((90, 1020), "Better than accepting every claim (exact McNemar p = 0.021); not yet clearly better than an error check alone (p = 0.070).",
           font=font(36), fill=LIGHT)
    d.text((90, 1075), "Checks are tied to request wording: 20 of 23 on design states, 9 of 22 on new ones.", font=font(36), fill=LIGHT)
    footer(d, "Constructed states; component-level results.", dark=True)
    im.save(OUT / "4_the_numbers.png")


if __name__ == "__main__":
    cover(); cad(); browser(); numbers()
    print("done")
