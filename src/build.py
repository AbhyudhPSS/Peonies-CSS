#!/usr/bin/env python3
"""Generates peonies/index.html and peonies/peonies.css (pure HTML + CSS output, no JS).

usage:  python3 build.py      (writes ../index.html and ../peonies.css)

Petals are emitted already sorted back-to-front for each flower, so the browser never
has to depth-sort a 3D context.
"""
import math, random, re, os

SCRATCH = os.path.dirname(os.path.abspath(__file__))
SRC_CSS = os.path.join(SCRATCH, "peonies.src.css")
OUT_DIR = os.environ.get("OUT_DIR", os.path.dirname(SCRATCH))   # the folder above src/
OUT_HTML = os.path.join(OUT_DIR, "index.html")
OUT_CSS = os.path.join(OUT_DIR, "peonies.css")

random.seed(11)

# bundle point (top of the ribbon) where every stem starts, in stage em
BX, BY = 10.5, 14.75

# ---------------------------------------------------------------- flowers
# x,y   centre of the bloom on the stage (em, stage is 20 x 26.7)
# R     radius of the open bloom (em)
# open  0..1  how far the petals unfurl (round ball -> wide open)
# tilt  rotateX of the whole bloom (negative = looks up into the cup)
# roll  lean of the bloom   yaw: spin of the petal pattern
# d0    when the bud leaves the bundle   db: when the petals start opening
FLOWERS = {
    "f7": dict(x=3.35, y=11.7, R=2.05, open=.62, tilt=-22, roll=-30, yaw=10,  d0=2.2, db=3.7, kb=-.1,  rings="1 2 3 5", sy=.30),
    "f8": dict(x=16.9, y=11.0, R=1.55, open=.55, tilt=-20, roll=28,  yaw=40,  d0=2.5, db=4.4, kb=-.1,  rings="1 2 3 5", sy=.30),
    "f2": dict(x=14.1, y=6.55, R=3.25, open=.52, tilt=-16, roll=14,  yaw=70,  d0=2.0, db=3.4, kb=-.15, rings="1 2 3 4 5", sy=.30),
    "f1": dict(x=9.0,  y=4.05, R=3.45, open=.58, tilt=-16, roll=-4,  yaw=130, d0=1.5, db=2.7, kb=-.2,  rings="1 2 3 4 5 6", sy=.30),
    "f3": dict(x=4.75, y=7.45, R=2.90, open=.55, tilt=-18, roll=-18, yaw=200, d0=1.8, db=3.1, kb=-.1,  rings="1 2 3 4 5", sy=.30),
    "f6": dict(x=6.75, y=13.4, R=3.15, open=.78, tilt=-34, roll=-8,  yaw=260, d0=2.5, db=4.8, kb=.1,   rings="1 2 3 4 5 6", sy=.30),
    "f5": dict(x=13.9, y=11.6, R=3.00, open=.74, tilt=-30, roll=12, yaw=320, d0=2.2, db=4.2, kb=0,    rings="1 2 3 4 5 6", sy=.30),
    "f4": dict(x=9.2,  y=8.9,  R=3.20, open=.62, tilt=-24, roll=-3,  yaw=40,  d0=2.8, db=5.5, kb=.12,  rings="1 2 3 4 5 6", sy=.30),
}

RING_N = {"s": 5, "1": 8, "2": 8, "3": 7, "4": 6, "5": 5, "6": 4}


# ---------------------------------------------------------------- ring recipes (read from the CSS so they can't drift)
def parse_recipes(css):
    out = {}
    for m in re.finditer(r"^\.(r[1-6]|rs)\s*\{(.*?)\}", css, re.S | re.M):
        d = {}
        for k, v in re.findall(r"--([\w]+):\s*([^;]+);", m.group(2)):
            d[k] = float(re.sub(r"[a-z]+$", "", v.strip()))
        out[m.group(1)[1:]] = d
    return out


SRC = open(SRC_CSS).read()
RECIPES = parse_recipes(SRC)
assert set(RECIPES) == {"1", "2", "3", "4", "5", "6", "s"}, RECIPES.keys()


# ---------------------------------------------------------------- painter's order
def rx(v, d):
    x, y, z = v; c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return (x, y * c - z * s, y * s + z * c)


def ry(v, d):
    x, y, z = v; c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return (x * c + z * s, y, -x * s + z * c)


def depths(ring, i, n, j, f):
    """View-space depth (bigger = nearer the viewer) of a petal's lower and upper panel at full bloom."""
    rc = RECIPES[ring]
    a = 360 * i / n + rc["off"] + j * 8
    to = rc["t0"] + (rc["t1"] - rc["t0"]) * f["open"] + j * 4
    hl = rc["ph"] * .5
    hu = hl * 1.2
    hinge = (0, -hl + .03, 0)
    up = rx((0, -hu / 2, 0), rc["curl"])
    lower = (0, -hl / 2, 0)
    upper = (hinge[0] + up[0], hinge[1] + up[1], hinge[2] + up[2])

    def place(p):
        p = rx(p, to)
        p = (p[0], p[1], p[2] - rc["r"])
        p = ry(p, a)
        p = (p[0], p[1] - rc["y"], p[2])
        p = ry(p, f["yaw"])
        p = rx(p, f["tilt"])
        return p

    return place(lower)[2], place(upper)[2]


def fmt(x, nd=3):
    s = ("%." + str(nd) + "f") % x
    s = s.rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    if s.startswith("0."):
        s = s[1:]
    elif s.startswith("-0."):
        s = "-" + s[2:]
    return s


KEYFRAMES = []          # @keyframes blocks, one per panel (literal numbers only)


def petals_for(f):
    """Every panel (lower .p and upper .q of every petal), farthest first."""
    items = []
    for ring in ["s"] + f["rings"].split():
        n = RING_N[ring]
        for i in range(n):
            j = round(random.uniform(-1, 1), 2)
            m = round(random.uniform(-1, 1), 2)
            zl, zu = depths(ring, i, n, j, f)
            items.append((zl, "p", ring, i, n, j, m))
            items.append((zu, "q", ring, i, n, j, m))
    items.sort(key=lambda t: t[0])           # farthest first
    return items


def panel_html(f, panel, ring, i, n, j, m):
    """One petal panel with every number baked in, so the moving element is trivial to restyle."""
    rc = RECIPES[ring]
    a = 360 * i / n + rc["off"] + j * 8
    to = rc["t0"] + (rc["t1"] - rc["t0"]) * f["open"] + j * 4
    w = rc["pw"] * (1 + m * .09)
    ph = rc["ph"]
    delay = f["db"] + rc["rd"] + i * .07
    pose = f'rotateZ({fmt(f["roll"])}deg) rotateX({fmt(f["tilt"])}deg) rotateY({fmt(f["yaw"])}deg)'
    pose0 = f'rotateZ({fmt(f["roll"])}deg) rotateX({fmt(f["tilt"])}deg) rotateY({fmt(f["yaw"] - 50)}deg)'
    chain = f'translateY({fmt(-rc["y"])}em) rotateY({fmt(a)}deg) translateZ({fmt(-rc["r"])}em) rotateX({fmt(to)}deg)'
    chain0 = f'translateY({fmt(-rc["y0"])}em) rotateY({fmt(a - 45)}deg) translateZ({fmt(-rc["r0"])}em) rotateX({fmt(rc["t0"])}deg)'
    name = f"k{len(KEYFRAMES)}"
    if panel == "p":
        geom = f"left:{fmt(-w / 2)}em;width:{fmt(w)}em;height:{fmt(ph * .5)}em"
        final = f"{pose} {chain} scale(1)"
        start = f"{pose0} {chain0} scale(.72,1)"
    else:
        hinge = -ph * .5 + .03
        geom = f"left:{fmt(-w * .55)}em;width:{fmt(w * 1.1)}em;height:{fmt(ph * .6)}em"
        final = f"{pose} {chain} translateY({fmt(hinge)}em) scale(1,1) rotateX({fmt(rc['curl'])}deg)"
        start = f"{pose0} {chain0} translateY({fmt(hinge)}em) scale(.62,1) rotateX({fmt(rc['curl0'])}deg)"
    KEYFRAMES.append(f"@keyframes {name}{{from{{transform:{start}}}}}")
    style = (f"--i:{i};--n:{n};--j:{fmt(j, 2)};--m:{fmt(m, 2)};{geom};transform:{final};"
             f"animation-name:{name};animation-delay:{fmt(delay, 2)}s")
    return f'          <i class="{panel} r{ring}" style="{style}"><i class="s"></i></i>'


def origin(f):
    """Where this flower's stem leaves the ribbon: stems fan across its width."""
    ox = BX + max(-.95, min(.95, (f["x"] - BX) * .13))
    return round(ox, 2), BY


def flower(fid, f):
    petals = "\n".join(panel_html(f, panel, ring, i, n, j, m) for _, panel, ring, i, n, j, m in petals_for(f))
    ox, oy = origin(f)
    nod_period = round(random.uniform(7.4, 9.9), 1)        # each head keeps its own time
    nod = (f'{wind_kf(NOD, 1.7, scale_amp=.022)} {nod_period}s '
           f'{fmt(wind_phase(f["x"]) * .6, 2)}s linear infinite')
    style = (
        f'--fx:{f["x"]};--fy:{f["y"]};--bx:{ox};--by:{oy};--R:{f["R"]};--open:{f["open"]};'
        f'--tilt:{f["tilt"]}deg;--roll:{f["roll"]}deg;--yaw:{f["yaw"]}deg;'
        f'--d0:{f["d0"]}s;--db:{f["db"]}s;--sy:{f["sy"]};--kb:{f["kb"]};'
        f'transform-origin:{fmt(ox - f["x"])}em {fmt(oy - f["y"])}em;'
        f'animation:fly 2.1s {f["d0"]}s cubic-bezier(.22,.75,.25,1) backwards,{f["_wind"]}'
    )
    return f'''    <div class="flower {fid}" style="{style}">
      <i class="halo"></i>
      <div class="orient" style="animation:{nod}">
        <div class="peony">
          <i class="core"></i>
{petals}
        </div>
      </div>
    </div>'''


def stem_amp(ln):
    """A longer stem flexes further. Degrees at the ribbon."""
    return 1.1 + .22 * ln


def arm(f):
    """Stem from the ribbon top to the flower's base (where the calyx sits)."""
    ox, oy = origin(f)
    bx, by = f["x"], f["y"] + f["R"] * f["sy"]
    dx, dy = bx - ox, by - oy
    ln = math.hypot(dx, dy)
    ang = math.degrees(math.atan2(dx, -dy))
    f["_armlen"] = ln
    f["_wind"] = wind_anim(GUST, stem_amp(ln), f["x"])      # shared with the flower
    return (f'    <div class="arm" style="--bx:{ox};--by:{oy};--ang:{ang:.1f}deg;--len:{ln:.2f}em;'
            f'--d0:{f["d0"]}s;animation:{f["_wind"]}">'
            f'<i class="stem"></i></div>')


def stemmed(keys):
    return "\n".join(arm(FLOWERS[k]) + "\n" + flower(k, FLOWERS[k]) for k in keys)


# ---------------------------------------------------------------- the breeze
# One gust shape shared by everything that moves, so the whole bouquet reads as a
# single wind rather than a crowd of separate wobbles. Three harmonics of one period:
# the loop is therefore seamless (every harmonic closes exactly at t = 1) and the
# motion never settles into an obvious back-and-forth.
WIND_PERIOD = 11.0        # seconds for one full gust
WIND_LAG = 1.9            # seconds the gust takes to travel across the bouquet
WIND_X0, WIND_X1 = 3.0, 17.2      # the x range the lag is spread over

GUST_HARMONICS = ((1, .70, 0.0), (2, .22, 0.8), (3, .08, 2.1))
NOD_HARMONICS = ((1, .62, 1.9), (2, .26, 4.4), (3, .12, 0.3))


def samples(harmonics, n=40):
    """One normalised cycle, sampled evenly. 40 points keeps the straight line between
    samples well under a tenth of a degree, so it reads as a smooth curve."""
    vals = [sum(a * math.sin(h * math.tau * k / n + ph) for h, a, ph in harmonics)
            for k in range(n + 1)]
    peak = max(abs(v) for v in vals) or 1
    out = [v / peak for v in vals]
    out[-1] = out[0]                      # close the loop exactly
    return out


GUST = samples(GUST_HARMONICS)
NOD = samples(NOD_HARMONICS)


def wind_phase(x):
    """Negative delay = further through the gust. The left of the bouquet leads."""
    t = min(1.0, max(0.0, (x - WIND_X0) / (WIND_X1 - WIND_X0)))
    return -(1 - t) * WIND_LAG


def shifted(curve, frac):
    """The same gust, started part-way through -- used to keep two parts of one
    element's motion from moving in lockstep."""
    n = len(curve) - 1
    off = int(round(frac * n)) % n
    return [curve[(k + off) % n] for k in range(n)] + [curve[off % n]]


def wind_kf(curve, amp, scale_amp=None, sway_em=None):
    """Emit one literal keyframe block for a gust and return its name.
    sway_em adds a sideways drift, so even a flower on a short, nearly horizontal
    stem (which rotation alone would mostly bob up and down) still travels across."""
    drift = shifted(curve, .18) if sway_em else None
    frames = []
    n = len(curve) - 1
    for k, v in enumerate(curve):
        t = "" if drift is None else "translateX(" + fmt(drift[k] * sway_em, 3) + "em) "
        decl = "transform:" + t + "rotate(" + fmt(v * amp, 3) + "deg)"
        if scale_amp is not None:
            decl += ";scale:" + fmt(1 + (v * .5 + .5) * scale_amp, 4)
        frames.append(fmt(k / n * 100, 2) + "%{" + decl + "}")
    name = "w%d" % len(KEYFRAMES)
    KEYFRAMES.append("@keyframes " + name + "{" + "".join(frames) + "}")
    return name


def wind_anim(curve, amp, x, **kw):
    """The full literal animation shorthand for one breeze-driven element."""
    return "%s %ss %ss linear infinite" % (
        wind_kf(curve, amp, **kw), fmt(WIND_PERIOD, 2), fmt(wind_phase(x), 2))


# ---------------------------------------------------------------- leaves
# base (x,y) in em, dir = direction of the tip in degrees clockwise from "up",
# L length, W width, d = delay, tone 0 (very dark) .. 1 (lighter)
LEAVES = {
    1: [  # behind everything
        dict(x=5.85, y=5.15, dir=-31, L=3.0, W=1.45, d=3.2, tone=.35),   # A top-left
        dict(x=12.3, y=4.15, dir=33,  L=3.1, W=1.5,  d=3.0, tone=.25),   # C top-right
        dict(x=16.4, y=6.3,  dir=63,  L=1.5, W=.75,  d=4.2, tone=.7),    # F small right
    ],
    2: [  # between back and front flowers
        dict(x=6.7, y=6.55, dir=-6,  L=2.7, W=1.0,  d=3.5, tone=.5),     # B
        dict(x=11.5, y=7.1, dir=-17, L=2.9, W=1.25, d=3.9, tone=.3),     # D
        dict(x=11.9, y=7.55, dir=50, L=3.5, W=1.8,  d=4.1, tone=.2),     # E
        dict(x=6.4, y=9.85, dir=-124, L=3.7, W=1.7, d=4.3, tone=.3),     # I left big
        dict(x=3.8, y=9.65, dir=-100, L=2.15, W=.7, d=4.6, tone=.15),    # I2 small
    ],
    3: [
        dict(x=15.4, y=8.75, dir=66,  L=3.2, W=1.25, d=5.0, tone=.45),   # G
        dict(x=15.6, y=8.9,  dir=108, L=3.1, W=1.35, d=5.2, tone=.2),    # H
    ],
    4: [  # in front of everything
        dict(x=10.25, y=12.9, dir=98, L=2.2, W=.95, d=5.6, tone=.25),    # J
        dict(x=11.5, y=15.7, dir=-30, L=2.45, W=1.15, d=5.8, tone=.4),   # K
    ],
}


def leaf(l):
    f = l.get("f", 1)
    ls = round(random.uniform(4.6, 7.4), 1)                 # its own flutter period
    wag = (f'{wind_kf(GUST, 3.6 + l["L"] * .35)} {fmt(ls * 1.45, 2)}s '
           f'{fmt(wind_phase(l["x"]), 2)}s linear infinite')
    return (f'    <i class="leaf" style="--x:{l["x"]};--y:{l["y"]};--lw:{l["W"]*1.15:.2f}em;--lh:{l["L"]*1.12:.2f}em;'
            f'--dir:{l["dir"]}deg;--f:{f};--d:{l["d"]}s;--tone:{l["tone"]}">'
            f'<i style="animation:{wag}"></i></i>')


def leaves(layer):
    return "\n".join(leaf(l) for l in LEAVES[layer])


# ---------------------------------------------------------------- bunch below ribbon
def stalks():
    out = []
    n = 10
    for i in range(n):
        t = i / (n - 1)
        x = 9.55 + t * 1.85 + random.uniform(-.1, .1)
        ang = -5 + t * 15 + random.uniform(-2.5, 2.5)
        ln = 4.3 + random.uniform(-.4, .9) + (1 - abs(t - .55)) * .5
        hue = random.choice(["#7d8d3e", "#6b8441", "#76876a", "#5f7d55", "#8a9748", "#677f74", "#72863f"])
        out.append(
            f'      <i class="stalk" style="--x:{x:.2f};--ang:{ang:.1f}deg;--len:{ln:.2f}em;--c:{hue};--d:{.2 + i * .07:.2f}s"></i>'
        )
    return "\n".join(out)


# ---------------------------------------------------------------- ambience
def falls():
    out = []
    cfg = [
        (9.0, 4.5), (14.0, 7.0), (4.8, 8.0), (9.2, 9.5), (13.8, 12.0), (7.0, 14.0),
        (11.0, 6.0), (6.5, 6.0), (15.5, 10.5), (3.5, 11.5),
    ]
    for i, (x, y) in enumerate(cfg):
        dur = round(random.uniform(9.5, 14), 1)
        dly = round(9.5 + i * 1.15 + random.uniform(0, .6), 2)
        dx = round(random.uniform(-3.2, 3.2), 2)
        sz = round(random.uniform(.34, .55), 2)
        rot = random.randint(0, 360)
        out.append(
            f'      <i class="fall" style="--x:{x};--y:{y};--dx:{dx}em;--s:{sz}em;--dur:{dur}s;--del:{dly}s;--r:{rot}deg"></i>'
        )
    return "\n".join(out)


def motes():
    out = []
    for i in range(22):
        x = round(random.uniform(1.5, 18.5), 2)
        y = round(random.uniform(6, 23), 2)
        s = round(random.uniform(.14, .42), 2)
        dur = round(random.uniform(7, 13), 1)
        dly = round(3 + random.uniform(0, 9), 2)
        dx = round(random.uniform(-1.2, 1.2), 2)
        out.append(
            f'      <i class="mote" style="--x:{x};--y:{y};--s:{s}em;--dur:{dur}s;--del:{dly}s;--dx:{dx}em"></i>'
        )
    return "\n".join(out)


def splats():
    out = []
    cols = ["#f3b8c8", "#eaa0b6", "#f7d0da", "#c9d9b8", "#a9c2a0", "#f0c2cc", "#b8cdd3"]
    for i in range(26):
        ang = random.uniform(0, math.tau)
        rad = random.uniform(6.2, 11.2)
        x = 10 + math.cos(ang) * rad * .95
        y = 11.8 + math.sin(ang) * rad * 1.1
        s = round(random.choice([.12, .18, .26, .34, .5, .7]) * random.uniform(.8, 1.2), 2)
        c = random.choice(cols)
        d = round(.9 + random.uniform(0, 5.2), 2)
        out.append(f'      <i style="--x:{x:.2f};--y:{y:.2f};--s:{s}em;--c:{c};--d:{d}s"></i>')
    return "\n".join(out)


# ---------------------------------------------------------------- heading + credit
TITLE = "Peonies for You."
CREDIT_NAME = "Abhyudh"         # <- the name shown in the credit line at the bottom

TITLE_STOPS = [(0.0, (122, 38, 80)), (0.5, (178, 63, 108)), (1.0, (201, 87, 127))]   # deep rose -> soft rose


def title_color(t):
    for (t0, c0), (t1, c1) in zip(TITLE_STOPS, TITLE_STOPS[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            return "#%02x%02x%02x" % tuple(round(a + (b2 - a) * k) for a, b2 in zip(c0, c1))
    return "#%02x%02x%02x" % TITLE_STOPS[-1][1]


def title_wave_kf():
    """One gentle elliptical sway shared by every letter. Letters differ only by
    delay, so the wave travels through the word instead of moving it as a block.
    It animates `translate`, leaving `transform` free for the entrance."""
    cx, cy = GUST, shifted(GUST, .25)
    n = len(cx) - 1
    frames = "".join(
        fmt(k / n * 100, 2) + "%{translate:" + fmt(cx[k] * .055, 3) + "em "
        + fmt(cy[k] * .04, 3) + "em}" for k in range(n + 1))
    name = "w%d" % len(KEYFRAMES)
    KEYFRAMES.append("@keyframes " + name + "{" + frames + "}")
    return name


def title_html():
    wave = title_wave_kf()
    glyphs = [ch for ch in TITLE if ch != " "]
    letters, idx = [], 0
    for ch in TITLE:
        if ch == " ":
            letters.append('<span class="gap"></span>')
            continue
        cls = ' class="cap"' if ch in "PY" else ""
        letters.append(
            f'<span{cls} style="color:{title_color(idx / (len(glyphs) - 1))};'
            f'animation:letter-in 1.5s {.5 + idx * .075:.2f}s cubic-bezier(.2,.9,.25,1.15) backwards,'
            f'{wave} 6.5s {fmt(-idx * .105, 3)}s linear infinite">{ch}</span>'
        )
        idx += 1
    sparks = [(3, -4, 1.9), (31, 96, 2.6), (60, -6, 3.3), (96, 88, 2.2)]
    spark_html = "".join(
        f'<i class="spark" style="--x:{x}%;--y:{y}%;animation-delay:{d}s"></i>' for x, y, d in sparks
    )
    return f'''    <header class="title">
      <h1 aria-label="{TITLE}">
        {"".join(letters)}
        {spark_html}
      </h1>
      <div class="rule" aria-hidden="true"><i></i><b></b><i></i></div>
    </header>'''


# The carrier: the whole bunch leans about the hand and drifts sideways with it.
# The drift is what gives the low, outer flowers a real left-right travel.
BOUQUET_WIND = "%s %ss 0s linear infinite" % (
    wind_kf(GUST, 1.45, sway_em=.42), fmt(WIND_PERIOD, 2))

# ---------------------------------------------------------------- assemble HTML
html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Peonies for You</title>
  <link rel="stylesheet" href="peonies.css">
</head>
<body>
  <!-- Pure HTML + CSS: no JavaScript, no images, no SVG. Everything you see is gradients, transforms and keyframes. -->
  <div class="paper"></div>

  <main class="scene">
{title_html()}
    <div class="stage" role="img" aria-label="A bouquet of pink peonies blossoming against watercolour paper" style="--bx:{BX};--by:{BY}">

      <div class="wash"><i></i><i></i><i></i><i></i></div>
      <div class="splats">
{splats()}
      </div>

      <!-- everything that is actually held: it leans together in the breeze -->
      <div class="bouquet" style="animation:{BOUQUET_WIND}">

      <!-- the bunch below the ribbon + the ribbon itself -->
      <div class="bunch">
{stalks()}
      </div>
      <div class="ribbon"><div class="ribbon__band"></div></div>

      <div class="leaves leaves--1">
{leaves(1)}
      </div>

      <!-- every flower is preceded by its own stem, so stems pass over the blooms behind
           them and tuck under the bloom they belong to -->
{stemmed(["f7", "f8"])}
{stemmed(["f2", "f1", "f3"])}

      <div class="leaves leaves--2">
{leaves(2)}
      </div>

{stemmed(["f6", "f5"])}

      <div class="leaves leaves--3">
{leaves(3)}
      </div>

{stemmed(["f4"])}

      <div class="leaves leaves--4">
{leaves(4)}
      </div>

      </div><!-- /.bouquet -->

      <div class="air">
{falls()}
{motes()}
      </div>
    </div>
  </main>

  <div class="veil"></div>

  <p class="credit">Made with <i class="heart" aria-hidden="true"></i> by <b>{CREDIT_NAME}</b></p>
</body>
</html>
'''


# ---------------------------------------------------------------- generated CSS pieces
def spring(zeta, n, settle=0.004):
    w0 = -math.log(settle) / zeta
    wd = w0 * math.sqrt(1 - zeta ** 2)
    pts = []
    for k in range(n):
        t = k / (n - 1)
        pts.append(1 - math.exp(-zeta * w0 * t) * (math.cos(wd * t) + (zeta * w0 / wd) * math.sin(wd * t)))
    pts[0], pts[-1] = 0, 1
    return "linear(" + ", ".join(("%.3f" % p).rstrip("0").rstrip(".") or "0" for p in pts) + ")"


def leaf_polygon():
    pts_l, pts_r = [], []
    steps = 22
    for k in range(steps + 1):
        u = k / steps
        h = 50 * (math.sin(math.pi * u ** 0.66) ** 0.92)
        y = 100 - 100 * u
        pts_l.append((50 - h, y))
        pts_r.append((50 + h, y))
    pts = pts_l + pts_r[::-1]
    return "polygon(" + ", ".join(f"{x:.1f}% {y:.1f}%" for x, y in pts) + ")"


def grain(seed, n, unit_x, unit_y, xmax, ymax):
    rnd = random.Random(seed)
    sizes = [0, 0, 0, 0, .1, .1, .2, .2, .35]
    shadows = []
    for _ in range(n):
        x, y = rnd.uniform(0, xmax), rnd.uniform(0, ymax)
        sp = rnd.choice(sizes)
        a = rnd.uniform(.05, .15)
        shadows.append(f"{x:.1f}{unit_x} {y:.1f}{unit_y} 0 {sp}px rgba(70,80,92,{a:.2f})")
    return ",\n    ".join(shadows)


css = SRC
css = css.replace("/*@SOFT@*/", spring(.78, 100))
css = css.replace("/*@BLOOM@*/", spring(.62, 120))
css = css.replace("/*@LEAF_POLY@*/", leaf_polygon())
css = css.replace("/*@PETAL_KEYFRAMES@*/", "\n".join(KEYFRAMES))
css = css.replace("/*@GRAIN_PAPER@*/", "\n    " + grain(5, 1000, "vw", "vh", 100, 100))
css = css.replace("/*@GRAIN_STAGE@*/", "\n    " + grain(9, 330, "em", "em", 20, 26.7))
assert "/*@" not in css

os.makedirs(OUT_DIR, exist_ok=True)
open(OUT_HTML, "w").write(html)
open(OUT_CSS, "w").write(css)
print("wrote", OUT_HTML, len(html), "bytes;", OUT_CSS, len(css), "bytes;",
      "petals:", html.count('class="p r'), "elements:", html.count("<"))
