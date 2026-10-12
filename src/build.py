#!/usr/bin/env python3
"""Generates peonies/index.html and peonies/peonies.css (pure HTML + CSS output, no JS).

usage:  python3 build.py      (writes ../index.html and ../peonies.css)

The picture itself is traced from the watercolour the bouquet is modelled on: every
bloom, petal, leaf, the ribbon and the cut stems are stacks of flat washes whose outlines
(clip-path polygons) and pigments live in shapes.py. This file gives them their place in
the stack, their timing and their movement.

Timing is emitted on a coarse grid (see GRID): every one-shot animation is widened so it
starts and ends on a half-second, and holds still in the padding. The motion itself is
unchanged; what changes is that the browser's main thread only has to wake a few times a
second during the bloom, instead of on nearly every frame.
"""
import math, random, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True                        # (no __pycache__ left beside the sources)
import shapes                                         # noqa: E402

SRC_CSS = os.path.join(HERE, "peonies.src.css")
OUT_DIR = os.environ.get("OUT_DIR", os.path.dirname(HERE))      # the folder above src/
OUT_HTML = os.path.join(OUT_DIR, "index.html")
OUT_CSS = os.path.join(OUT_DIR, "peonies.css")

random.seed(11)

# bundle point (just under the top of the ribbon) where every stem starts, in stage em
BX, BY = 10.55, 14.7

# ---------------------------------------------------------------- flowers
# Shape, place and pigment of each bloom come from shapes.py. Here: when it happens.
#   d0   when the bud leaves the bundle on its stem
#   db   when it starts to open
# The blooms open front to back (the middle one first), so that each opens over, and so
# hides, the part of its neighbours that the painting never shows.
FLOWERS = {
    "f4": dict(d0=1.5, db=2.7),
    "f6": dict(d0=1.7, db=3.2),
    "f5": dict(d0=1.9, db=3.7),
    "f3": dict(d0=2.1, db=4.2),
    "f1": dict(d0=2.2, db=4.6),
    "f2": dict(d0=2.4, db=5.0),
    "f7": dict(d0=2.6, db=5.3),
    "f8": dict(d0=2.7, db=5.5),
}
for _k, _f in FLOWERS.items():
    _f.update(x=shapes.FLOWERS[_k]["x"], y=shapes.FLOWERS[_k]["y"])

BUD = .28                 # a bud is its bloom at this scale, with every petal folded:
FOLD = 44                 #   stood up from the page by this many degrees,
TWIST = -38               #   turned this far round the bloom,
TUCK = .8                 #   and drawn in to this size
PETAL_LAG = 1.3           # seconds between the outermost petal and the heart starting to open

# Once it is open, nothing in the bouquet stays quite still: every petal breathes on its own
# beat, every leaf wags and twists, every cut stem sways. That is what shows the picture to be
# made of separate pieces, and not one image being rocked from side to side.
FLUTTER_TURN = 2.4        # degrees a petal swings about the heart of its bloom (the outermost; less further in)
FLUTTER_SWELL = .026      # ...and how far it swells and draws in
FLUTTER_BEATS = (5.3, 6.1, 7.0, 7.9, 8.9)     # seconds: each petal keeps one of these
LEAF_WAG = 3.8            # degrees a leaf wags about the point it springs from
LEAF_WAG_OF = {"A": 2.6, "H3": 2.2}           # (these two lie along the rim of a bloom: gentler)
LEAF_TWIST = .09          # how far a leaf turns edge-on as it wags (share of its width)
NOD = 1.7                 # degrees a flower head nods about the top of its stem
BREATH = .016             # ...and how far it swells
STALK_SWAY = (1.2, 1.9)   # degrees a cut stem sways about the point it hangs from (each its own, in this range)

dice = random.Random(23)  # for all of the above, so that adding to it never reshuffles the rest


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


def washes(layers):
    """A stack of flat washes: one still box per wash, each cut to its outline. They sit
    inside the element that moves, so each outline is cut once, when that element is
    first painted, and never again."""
    return "".join(f'<b style="clip-path:polygon({poly});background:{col}"></b>' for col, poly in layers)


KEYFRAMES = []          # @keyframes blocks, one per petal, gust or padded one-shot (literal numbers only)


# ---------------------------------------------------------------- the grid
# Starting or finishing an animation is the one thing the compositor cannot do alone: the
# main thread has to wake, restyle every animation that is running, and commit the result,
# which stalls the compositor for most of a frame. With hundreds of one-shot animations each
# on its own delay that was happening on almost every frame of the bloom.
#
# So every one-shot is widened to the nearest half-second on both sides, and holds its
# first / last pose in the padding. All the starts and ends now land together on a few
# shared instants, and in between the whole bouquet runs on the compositor untouched.
GRID = .5


def window(delay, dur):
    """(start, total, a, b): the widened window, and where in it (0..1) the real motion
    begins and ends."""
    start = math.floor(delay / GRID + 1e-6) * GRID
    end = math.ceil((delay + dur) / GRID - 1e-6) * GRID
    total = end - start
    return start, total, (delay - start) / total, (delay + dur - start) / total


HELD = {}               # (base, a, b) -> keyframes name


def held(base, frames, delay, dur):
    """A one-shot animation, padded onto the grid by remapping its keyframes.
    frames = [(percent, declarations), ...]; the timing function stays on the element
    and so still shapes the real motion only (the padding sits between equal keyframes).
    Returns (keyframes name, start, total)."""
    start, total, a, b = window(delay, dur)
    key = (base, fmt(a * 100, 3), fmt(b * 100, 3))
    if key not in HELD:
        name = "%s-%d" % (base, sum(1 for k in HELD if k[0] == base))
        out = []
        if a > 1e-6:
            out.append("0%{" + frames[0][1] + "}")
        for pct, decl in frames:
            out.append(fmt((a + pct / 100 * (b - a)) * 100, 3) + "%{" + decl + "}")
        if b < 1 - 1e-6:
            out.append("100%{" + frames[-1][1] + "}")
        HELD[key] = name
        KEYFRAMES.append("@keyframes " + name + "{" + "".join(out) + "}")
    return HELD[key], start, total


def held_vars(base, frames, delay, dur):
    """The same, as the three custom properties the stylesheet's one-shot rules read."""
    name, start, total = held(base, frames, delay, dur)
    return "--kn:%s;--ks:%ss;--kd:%ss" % (name, fmt(start, 2), fmt(total, 2))


# The petals already have a keyframe block each, so they are padded the other way round:
# the spring itself is squeezed into the middle of a wider linear() easing. Petals whose
# delays sit at the same offset from the grid share one class.
BLOOM_DUR = 3.8
BLOOM_EASE = {}         # (a, b, total) -> class name


def bloom_class(delay):
    start, total, a, b = window(delay, BLOOM_DUR)
    key = (fmt(a * 100, 3), fmt(b * 100, 3), fmt(total, 2))
    if key not in BLOOM_EASE:
        BLOOM_EASE[key] = "t%d" % len(BLOOM_EASE)
    return BLOOM_EASE[key], start


# ---------------------------------------------------------------- leaves
# Outline, place and pigment of every leaf are traced from the painting (shapes.py).
# Each leaf belongs to the bloom it grows beside, and lives inside it, under its petals:
# it rides out of the bundle with that bud, grows as the bud grows, and flexes and nods
# with it in the breeze, so a leaf and its bloom can never drift apart. (Stacked like
# this, back to front, everything still overlaps exactly as it does in the painting.)
LEAVES_OF = {"f2": "C F", "f1": "A", "f3": "B H2 H3", "f5": "G1 G2", "f6": "I1 I2", "f4": "D E H1"}


def leaf(name, f, k):
    s = shapes.LEAVES[name]
    ls = round(random.uniform(4.6, 7.4), 1)                 # its own flutter period
    wag = (f'{wind_kf(GUST, LEAF_WAG_OF.get(name, LEAF_WAG), twist=LEAF_TWIST)} {fmt(ls, 2)}s '
           f'{fmt(wind_phase(s["x"]) - dice.uniform(0, ls), 2)}s linear infinite')
    # it unfurls as its bloom starts to open, swinging out from nearer the stem
    swing = -math.copysign(min(60, abs(s["dir"]) * .5), s["dir"])
    unfurl = held_vars("unfurl", [(0, f"scale:.05;rotate:{fmt(swing, 1)}deg"), (100, "scale:1;rotate:0deg")],
                       round(f["db"] - .5 + k * .3, 1), 2.6)
    return (f'          <i class="leaf" style="--x:{fmt(s["x"] - f["x"])};--y:{fmt(s["y"] - f["y"])};'
            f'--lw:{s["w"]}em;--lh:{s["h"]}em;--dir:{s["dir"]}deg;{unfurl}">'
            f'<i style="animation:{wag}">{washes(s["layers"])}</i></i>')


FLUTTER = {}            # (curve, strength) -> keyframes name
BEATS = set()           # (opening class, its padded length, beat) in use


def flutter_kf(curve, level):
    """A petal's breathing: a small turn about the heart of its bloom and a small swell, each
    following a gust of its own, so that the two never move in step. It animates `rotate` and
    `scale`, which leaves `transform` to the opening."""
    key = (curve, level)
    if key not in FLUTTER:
        turn, swell = (GUST, shifted(NODS, .4)) if curve == 0 else (NODS, shifted(GUST, .27))
        k = (.45, .72, 1.0)[level]
        n = 20
        step = (len(turn) - 1) // n
        frames = "".join(
            fmt(i / n * 100, 2) + "%{rotate:" + fmt(turn[i * step] * FLUTTER_TURN * k, 3) + "deg;scale:"
            + fmt(1 + swell[i * step] * FLUTTER_SWELL * k, 4) + "}" for i in range(n + 1))
        FLUTTER[key] = "fl%d" % len(FLUTTER)
        KEYFRAMES.append("@keyframes " + FLUTTER[key] + "{" + frames + "}")
    return FLUTTER[key]


def petal_html(f, q, p, far):
    """One petal: a box of washes that rests folded up into the bud, and is opened by a
    keyframe of its own. Every number is baked in, so the moving element is trivial to
    restyle."""
    # (to the tenth of a second, so that petals share a handful of padded easings)
    delay = round(f["db"] + (1 - p["dist"] / far) * PETAL_LAG + random.uniform(0, .12), 1)
    ease, begin = bloom_class(delay)
    # the fold is a turn about the line through the bloom's opening point that lies in the
    # page, square to the way the petal points: the petal stands up towards the eye
    axis = f'{fmt(-p["uy"])},{fmt(p["ux"])},0'
    name = f"k{len(KEYFRAMES)}"
    final = f"rotate(0deg) rotate3d({axis},0deg) scale(1)"
    start = f"rotate({TWIST}deg) rotate3d({axis},{-FOLD}deg) scale({fmt(TUCK)})"
    # The petal rests folded and the keyframe carries it open, which the animation then
    # keeps (fill: forwards). The other way round (resting open, held shut by the animation
    # until its turn) looks the same but costs: an animation that is holding a pose is
    # ticked on every frame, and every petal would be from the first.
    KEYFRAMES.append(f"@keyframes {name}{{to{{transform:{final}}}}}")
    # ...and from then on it breathes: the outer petals most, each on its own beat
    reach = p["dist"] / far
    flutter = flutter_kf(dice.randrange(2), 2 if reach > .66 else 1 if reach > .33 else 0)
    beat = dice.randrange(len(FLUTTER_BEATS))
    BEATS.add((ease, window(delay, BLOOM_DUR)[1], beat))
    style = (f'left:{fmt(p["x"] - f["x"])}em;top:{fmt(p["y"] - f["y"])}em;width:{p["w"]}em;height:{p["h"]}em;'
             f'transform-origin:{fmt(q[0] - p["x"])}em {fmt(q[1] - p["y"])}em;transform:{start};'
             f"animation-name:{name},{flutter};"
             f"animation-delay:{fmt(begin, 2)}s,{fmt(-dice.uniform(0, FLUTTER_BEATS[beat]), 2)}s")
    return f'          <i class="p {ease} b{beat}" style="{style}">{washes(p["layers"])}</i>'


def origin(f):
    """Where this flower's stem leaves the ribbon: stems fan across its width."""
    ox = BX + max(-.95, min(.95, (f["x"] - BX) * .13))
    return round(ox, 2), BY


def flower(fid, f):
    sh = shapes.FLOWERS[fid]
    q = (sh["qx"], sh["qy"])
    far = max(p["dist"] for p in sh["petals"])
    petals = "\n".join(petal_html(f, q, p, far) for p in sh["petals"])
    foliage = "".join(leaf(n, f, k) + "\n" for k, n in enumerate(LEAVES_OF.get(fid, "").split()))
    ox, oy = origin(f)
    # the head nods about the point where its stem holds it, and keeps its own time
    nod_period = round(random.uniform(7.4, 9.9), 1)
    nod = (f'{wind_kf(NODS, NOD, scale_amp=BREATH)} {nod_period}s '
           f'{fmt(wind_phase(f["x"]) * .6, 2)}s linear infinite')
    db = f["db"]
    # the bud rides out on its stem (same window as the stem, see arm()); not from 0: a
    # tiny bud is rasterised at load, a zero-size one only when it appears
    fly, fly_s, fly_t = held("fly", [(0, "scale:.01"), (100, "scale:1")], f["d0"], STEM_DUR)
    # a flare goes off as the bloom reaches full open
    halo = held_vars("halo", [(0, "opacity:0;scale:.45"), (30, "opacity:1"), (100, "opacity:0;scale:1.3")], db + 2.6, 2.8)
    grow = held_vars("peony-grow", [(0, f"scale:{fmt(BUD)}"), (100, "scale:1")], db - .2, 4.4)
    # under the open petals, a wash or two in the bloom's own tones (see .deep in the stylesheet)
    under = ""
    if sh.get("deep"):
        fade = held_vars("deep-in", [(0, "opacity:0"), (100, "opacity:1")], db + 2.6, 2.2)
        under = f'          <i class="deep" style="{fade}">{washes(sh["deep"])}</i>\n'
    s = sh["s"]
    at = f'{fmt(q[0] - f["x"])}em {fmt(q[1] - f["y"])}em'       # the opening point, from the middle of the bloom
    style = (
        f'--fx:{f["x"]};--fy:{f["y"]};--S:{s};--wind:{f["_wind"].split()[0]};'
        f'transform-origin:{fmt(ox - f["x"])}em {fmt(oy - f["y"])}em;'
        f'animation:{fly} {fmt(fly_t, 2)}s {fmt(fly_s, 2)}s cubic-bezier(.22,.75,.25,1) backwards,{f["_wind"]}'
    )
    return f'''    <div class="flower {fid}" style="{style}">
      <i class="halo" style="{halo}"></i>
      <div class="orient" style="transform-origin:{at};animation:{nod}">
        <div class="peony" style="transform-origin:{at};perspective-origin:{at};{grow}">
{foliage}          <i class="ball" style="--m:{sh["mid"]};clip-path:polygon({sh["body"]})"></i>
{under}{petals}
        </div>
      </div>
    </div>'''


STEM_DUR = 2.1            # how long a stem takes to grow (and its bud to ride out)


def stem_amp(ln):
    """A longer stem flexes further. Degrees at the ribbon. Kept modest: the blooms are
    packed against each other, as painted, and each runs on only so far under its
    neighbours (shapes.py), so they must not slide far over one another. The broad sway
    is the whole bunch leaning together (BOUQUET_WIND)."""
    return .45 + .07 * ln


def arm(fid, f):
    """Stem from the ribbon to the point the bloom opens from."""
    ox, oy = origin(f)
    bx, by = shapes.FLOWERS[fid]["qx"], shapes.FLOWERS[fid]["qy"]
    dx, dy = bx - ox, by - oy
    ln = math.hypot(dx, dy)
    ang = math.degrees(math.atan2(dx, -dy))
    f["_wind"] = wind_anim(GUST, stem_amp(ln), f["x"])      # shared with the flower
    # (from .01, like the bud that rides on it: see flower(). Unlike the bud, a stem that
    # short is still a visible dash, so it is kept out of sight until it sets out.)
    grow = held_vars("stem-grow", [(0, "scale:1 .01;opacity:0"), (5, "opacity:1"), (100, "scale:1 1;opacity:1")],
                     f["d0"], STEM_DUR)
    return (f'    <div class="arm" style="--bx:{ox};--by:{oy};--ang:{ang:.2f}deg;--len:{ln:.3f}em;'
            f'animation:{f["_wind"]}">'
            f'<i class="stem" style="{grow}"></i></div>')


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
NODS = samples(NOD_HARMONICS)


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


def wind_kf(curve, amp, scale_amp=None, sway_em=None, twist=None):
    """Emit one literal keyframe block for a gust and return its name.
    sway_em adds a sideways drift, so even a flower on a short, nearly horizontal
    stem (which rotation alone would mostly bob up and down) still travels across.
    twist narrows the element about its own axis out of step with the turn: a leaf
    showing more or less of its face."""
    drift = shifted(curve, .18) if sway_em else None
    turn = shifted(curve, .31) if twist else None
    frames = []
    n = len(curve) - 1
    for k, v in enumerate(curve):
        t = "" if drift is None else "translateX(" + fmt(drift[k] * sway_em, 3) + "em) "
        decl = "transform:" + t + "rotate(" + fmt(v * amp, 3) + "deg)"
        if turn is not None:
            decl += " scaleX(" + fmt(1 - twist * (turn[k] * .5 + .5), 4) + ")"
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


def flowers(keys):
    return "\n".join(flower(k, FLOWERS[k]) for k in keys.split())


def boxed(sh):
    return f'left:{sh["x"]}em;top:{sh["y"]}em;width:{sh["w"]}em;height:{sh["h"]}em'


# ---------------------------------------------------------------- the ribbon
def satin():
    """The ribbon's washes, and over them a soft light that travels up and down the satin.
    (The light is a blurred spot narrower than the ribbon, so it needs no outline cut for
    it: it has faded away before it reaches the ribbon's edge.)"""
    return washes(shapes.RIBBON["layers"]) + '<i class="sheen"></i>'


# ---------------------------------------------------------------- the cut stems
def stalks():
    """The cut stems below the ribbon, a strip for each (shapes.py): every one hangs from
    its own point under the ribbon and sways there on its own beat."""
    cut = shapes.STEMS
    x0, y0 = min(c["x"] for c in cut), min(c["y"] for c in cut)
    x1, y1 = max(c["x"] + c["w"] for c in cut), max(c["y"] + c["h"] for c in cut)
    out = []
    for k, c in enumerate(cut):
        beat = dice.uniform(5.2, 8.4)
        sway = (f'{wind_kf(GUST if k % 2 else NODS, dice.uniform(*STALK_SWAY))} {fmt(beat, 2)}s '
                f'{fmt(-dice.uniform(0, beat), 2)}s linear infinite')
        out.append(f'        <i class="stalk" style="left:{fmt(c["x"] - x0)}em;top:{fmt(c["y"] - y0)}em;'
                   f'width:{c["w"]}em;height:{c["h"]}em;'
                   f'transform-origin:{fmt(c["px"] - c["x"])}em {fmt(c["py"] - c["y"])}em;animation:{sway}">'
                   f'{washes(c["layers"])}</i>')
    box = f'left:{fmt(x0)}em;top:{fmt(y0)}em;width:{fmt(x1 - x0)}em;height:{fmt(y1 - y0)}em'
    return f'      <div class="bunch" style="{box};{STEMS_UP}">\n' + "\n".join(out) + "\n      </div>"


# ---------------------------------------------------------------- waves
# Behind the bouquet, washes with a rolling edge drift across the page, the nearer ones
# shorter, lower and quicker. Each is a strip one wavelength wider than the page with the
# swell cut along its top; it slides sideways by exactly one wavelength and starts again,
# which cannot be seen. Lengths across are in vw (the washes span the page), lengths down
# in stage em (they keep their place behind the bouquet).
#   top    where the crest lies (em from the top of the stage)    swell  its height (em)
#   span   one wavelength (vw)     beat  seconds to travel it     way  -1 leftwards, 1 rightwards
#   rise   when it wells up        tint, a  its pigment and strength
WAVES = [
    dict(top=11.2, swell=1.9,  span=62.0, beat=31, way=-1, rise=.3,  tint=(168, 200, 222), a=.36),
    dict(top=14.2, swell=1.6,  span=48.0, beat=25, way=1,  rise=.7,  tint=(140, 182, 214), a=.34),
    dict(top=17.2, swell=1.35, span=38.0, beat=19, way=-1, rise=1.1, tint=(118, 166, 206), a=.40),
    dict(top=20.2, swell=1.1,  span=30.0, beat=14, way=1,  rise=1.5, tint=(96, 148, 196), a=.36),
]
WAVE_DEPTH = 7.5          # em: how far down a wash runs before it has faded away
WAVE_RIM = .1             # em: the line of pooled pigment along its edge
WAVE_LIGHT = .55          # em: the paler band just under it, where the swell catches the light


def wave_edge(w, per=30):
    """The rolling edge as (x%, y em) along a strip: crests a little sharper than the troughs
    and leaning the way they travel, and exactly one `span` long per roll, so that the
    strip can slide by one span and start again unseen."""
    width = 100 + w["span"]
    n = math.ceil(width / w["span"] * per)
    pts = []
    for k in range(n + 1):
        x = min(width, k * w["span"] / per)
        th = math.tau * x / w["span"]
        lean = th + .28 * w["way"] * math.sin(th)              # (crests lean forward)
        roll = (.5 + .5 * math.sin(lean)) ** 1.5               # 0 trough .. 1 crest
        roll += .07 * math.sin(2 * th + 1.1) + .04 * math.sin(3 * th + 2.3)
        pts.append((x / width * 100, w["swell"] * (1 - roll) / 1.11))
    return pts


def waves():
    out = []
    for k, w in enumerate(WAVES):
        depth = WAVE_DEPTH + w["swell"]
        edge = wave_edge(w)
        pct = lambda pts: ",".join(f"{fmt(x, 2)}% {fmt(y / depth * 100, 2)}%" for x, y in pts)
        wash = pct(edge) + ",100% 100%,0 100%"
        rim = pct(edge) + "," + pct([(x, y + WAVE_RIM) for x, y in reversed(edge)])
        light = pct([(x, y + WAVE_RIM) for x, y in edge]) + "," + pct([(x, y + WAVE_RIM + WAVE_LIGHT) for x, y in reversed(edge)])
        drift = "drift-%d" % k
        KEYFRAMES.append("@keyframes %s{to{translate:%svw 0}}" % (drift, fmt(-w["span"], 3)))
        bob = dice.uniform(3.6, 5.2)
        rise = held_vars("wave-rise", [(0, "translate:0 62vh"), (100, "translate:0 0")], w["rise"], 3.4)
        r, g, b = w["tint"]
        out.append(
            f'      <div class="wave" style="top:{w["top"]}em;height:{fmt(depth)}em;{rise}">'
            f'<i style="width:{fmt(100 + w["span"], 3)}vw;'
            f'animation:{drift} {w["beat"]}s linear infinite{" reverse" if w["way"] > 0 else ""},'
            f'wave-bob {fmt(bob, 2)}s {fmt(-dice.uniform(0, bob), 2)}s ease-in-out infinite alternate">'
            f'<b style="clip-path:polygon({wash});'
            f'background:linear-gradient(rgb({r} {g} {b}/{w["a"]}),rgb({r} {g} {b}/{fmt(w["a"] * .5, 2)}) 38%,rgb({r} {g} {b}/0))"></b>'
            f'<b style="clip-path:polygon({light});background:rgb(255 255 255/.22)"></b>'
            f'<b style="clip-path:polygon({rim});background:rgb({round(r * .8)} {round(g * .82)} {round(b * .84)}/{fmt(min(1, w["a"] * 1.4), 2)})"></b>'
            f'</i></div>')
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
    cols = ["#e6c3cb", "#dcafba", "#efd9dd", "#c3d2b6", "#a8bda1", "#e4c9cd", "#b8cdd3"]
    for i in range(26):
        ang = random.uniform(0, math.tau)
        rad = random.uniform(7.4, 11.4)
        x = 10 + math.cos(ang) * rad * .95
        y = 11.8 + math.sin(ang) * rad * 1.1
        s = round(random.choice([.12, .18, .26, .34, .5, .7]) * random.uniform(.8, 1.2), 2)
        c = random.choice(cols)
        d = round(.9 + random.uniform(0, 5.2), 2)
        pop = held_vars("splat", [(0, "scale:0;opacity:0"), (100, "scale:1;opacity:.5")], d, .9)
        out.append(f'      <i style="--x:{x:.2f};--y:{y:.2f};--s:{s}em;--c:{c};{pop}"></i>')
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


LETTER_IN = [(0, "opacity:0;transform:translateY(.55em) rotate(-8deg) scale(.6)"),
             (100, "opacity:1;transform:translateY(0) rotate(0deg) scale(1)")]


def title_html():
    wave = title_wave_kf()
    glyphs = [ch for ch in TITLE if ch != " "]
    letters, idx = [], 0
    for ch in TITLE:
        if ch == " ":
            letters.append('<span class="gap"></span>')
            continue
        cls = ' class="cap"' if ch in "PY" else ""
        rise, rise_s, rise_t = held("letter-in", LETTER_IN, float("%.2f" % (.5 + idx * .075)), 1.5)
        letters.append(
            f'<span{cls} style="color:{title_color(idx / (len(glyphs) - 1))};'
            f'animation:{rise} {fmt(rise_t, 2)}s {fmt(rise_s, 2)}s cubic-bezier(.2,.9,.25,1.15) backwards,'
            f'{wave} 6.5s {fmt(-idx * .105, 3)}s linear infinite">{ch}</span>'
        )
        idx += 1
    sparks = [(3, -4, 1.9), (31, 96, 2.6), (60, -6, 3.3), (96, 88, 2.2)]
    spark_html = "".join(
        f'<i class="spark" style="--x:{x}%;--y:{y}%;animation-delay:{d}s"></i>' for x, y, d in sparks
    )
    draw = held_vars("rule-draw", [(0, "scale:0 1"), (100, "scale:1 1")], 1.6, 1.6)
    pop = held_vars("petal-pop", [(0, "scale:0;rotate:-90deg"), (100, "scale:1;rotate:45deg")], 1.5, 1.4)
    return f'''    <header class="title">
      <h1 aria-label="{TITLE}">
        {"".join(letters)}
        {spark_html}
      </h1>
      <div class="rule" aria-hidden="true"><i style="{draw}"></i><b style="{pop}"></b><i style="{draw}"></i></div>
    </header>'''


# The carrier: the whole bunch leans about the hand and drifts sideways with it.
# The drift is what gives the low, outer flowers a real left-right travel.
BOUQUET_WIND = "%s %ss 0s linear infinite" % (
    wind_kf(GUST, 1.45, sway_em=.42), fmt(WIND_PERIOD, 2))

WASHES = "".join(
    '<i style="%s"></i>' % held_vars("wash-in", [(0, "opacity:0;scale:.35"), (100, "opacity:1;scale:1")], d, 7)
    for d in (.3, 1.1, 1.6, 2.1))
# the cut stems grow up from their ends, the ribbon wraps round them, and only then do the
# buds set out (FLOWERS, d0)
STEMS_UP = held_vars("stems-up", [(0, "scale:1 .01"), (100, "scale:1 1")], .2, 1.5)
WRAP_IN = held_vars("wrap-in", [(0, "scale:1.22 1"), (100, "scale:1 1")], .8, 1.6)
WRAP_UP = held_vars("wrap-up", [(0, "translate:0 100%"), (100, "translate:0 0")], .8, 1.6)
CREDIT_IN = held_vars("credit-in", [(0, "opacity:0;transform:translateY(.8em)"), (100, "opacity:1;transform:translateY(0)")], 3.2, 2)

# ---------------------------------------------------------------- the loop clock
# The last .56s of each cycle is a pulse that resets the one-shot animations (see THE
# LOOP in the stylesheet). For the first CLOCK_PULSES cycles each pulse is its own
# one-shot animation with a delay, which costs nothing to wait for, unlike a repeating
# clock, which is ticked on the main thread on every frame. A waiting pulse is not quite
# free either, though: the browser looks at each one again whenever the main thread does
# wake (about 60 microseconds apiece here), so a list covering hours turned every such
# frame into a 50ms one. Hence a list of modest length, and a repeating clock after it.
LOOP = 28.0               # seconds per cycle
LOOP_PULSE = .56          # ...of which the last this-many are the reset
CLOCK_PULSES = 64         # half an hour


def clock():
    pulses = ["lp %ss %ss" % (fmt(LOOP_PULSE, 2), fmt(LOOP * k - LOOP_PULSE, 2))
              for k in range(1, CLOCK_PULSES + 1)]
    # ...then the flag that hands over to the repeating clock, a moment after the last
    # pulse, so that the two keep the same beat
    flag = "run-down .01s %ss forwards" % fmt(LOOP * CLOCK_PULSES + .1, 2)
    return ",\n    ".join([", ".join(pulses[i:i + 8]) for i in range(0, len(pulses), 8)] + [flag])


# ---------------------------------------------------------------- assemble HTML
# The stems come first, every one, so that they stay inside the bunch; each shares its
# keyframe with its flower (arm() makes it, flower() reuses it).
ARMS = "\n".join(arm(k, FLOWERS[k]) for k in FLOWERS)

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
  <!-- Pure HTML + CSS: no JavaScript, no images, no SVG. Everything you see is clip-paths, gradients, transforms and keyframes. -->
  <div class="paper"></div>

  <!-- (this wrapper holds the loop's spare clock: see THE LOOP in the stylesheet) -->
  <div class="loop">

  <main class="scene">
{title_html()}
    <div class="stage" role="img" aria-label="A bouquet of pink peonies blossoming against watercolour paper" style="--bx:{BX};--by:{BY}">

      <!-- behind everything: washes with a rolling edge, drifting across the page -->
      <div class="waves" aria-hidden="true">
{waves()}
      </div>

      <div class="wash">{WASHES}</div>
      <div class="splats">
{splats()}
      </div>

      <!-- everything that is actually held: it leans together in the breeze -->
      <div class="bouquet" style="animation:{BOUQUET_WIND}">

      <!-- the cut stems below the ribbon, the stems inside the bunch, and the ribbon round them -->
{stalks()}
{ARMS}
      <div class="ribbon" style="{boxed(shapes.RIBBON)};{WRAP_IN}"><div class="ribbon__band" style="{WRAP_UP}">{satin()}</div></div>

      <!-- the blooms, back to front as in the painting, each with its leaves -->
{flowers("f7 f8 f2 f1 f3 f5 f6 f4")}

      </div><!-- /.bouquet -->

      <div class="air">
{falls()}
{motes()}
      </div>
    </div>
  </main>

  <div class="curtain"><div class="veil"></div></div>

  </div>

  <p class="credit" style="{CREDIT_IN}">Made with <i class="heart" aria-hidden="true"></i> by <b>{CREDIT_NAME}</b></p>
</body>
</html>
'''


# ---------------------------------------------------------------- generated CSS pieces
def spring_points(zeta, n, settle=0.004):
    w0 = -math.log(settle) / zeta
    wd = w0 * math.sqrt(1 - zeta ** 2)
    pts = []
    for k in range(n):
        t = k / (n - 1)
        pts.append(1 - math.exp(-zeta * w0 * t) * (math.cos(wd * t) + (zeta * w0 / wd) * math.sin(wd * t)))
    pts[0], pts[-1] = 0, 1
    return [fmt(p) for p in pts]


def spring(zeta, n):
    return "linear(" + ", ".join(spring_points(zeta, n)) + ")"


def bloom_classes():
    """The petal spring, held still before and after so the animation spans whole grid
    steps. Stops with no position are spread evenly between their neighbours, so the
    spring keeps exactly the shape it has on its own. A petal runs two animations, the
    opening and then its breathing, so every list here has two entries: the lengths of the
    pair are set by the combination of its opening class and its beat."""
    pts = spring_points(.62, 120)
    rules = []
    for (a, b, total), cls in BLOOM_EASE.items():
        stops = ["0"] + (["0 %s%%" % a] if a != "0" else []) + pts[1:-1]
        stops += ["1 %s%%" % b, "1"] if b != "100" else ["1"]
        rules.append(".%s{animation-timing-function:linear(%s),linear}" % (cls, ", ".join(stops)))
    for cls, total, beat in sorted(BEATS):
        rules.append(".%s.b%d{animation-duration:%ss,%ss}" % (cls, beat, fmt(total, 2), fmt(FLUTTER_BEATS[beat], 2)))
    return "\n".join(rules)


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


css = open(SRC_CSS).read()
css = css.replace("/*@SOFT@*/", spring(.78, 100))
css = css.replace("/*@PETAL_KEYFRAMES@*/", "\n".join(KEYFRAMES))
css = css.replace("/*@BLOOM_CLASSES@*/", bloom_classes())
css = css.replace("/*@CLOCK@*/", "\n    " + clock())
# the reset rule is written once, for the pulses on <body>, and repeated for the
# repeating clock that takes over from them
begin, end = "/*@CLOCK_RESET_BEGIN@*/\n", "/*@CLOCK_RESET_END@*/\n"
head, rest = css.split(begin)
rule, tail = rest.split(end)
assert rule.count("@container clock ") == 1
css = head + rule + rule.replace("@container clock ", "@container spare-clock ") + tail
css = css.replace("/*@GRAIN_PAPER@*/", "\n    " + grain(5, 1000, "vw", "vh", 100, 100))
css = css.replace("/*@GRAIN_STAGE@*/", "\n    " + grain(9, 330, "em", "em", 20, 26.7))
assert "/*@" not in css

os.makedirs(OUT_DIR, exist_ok=True)
open(OUT_HTML, "w").write(html)
open(OUT_CSS, "w").write(css)
print("wrote", OUT_HTML, len(html), "bytes;", OUT_CSS, len(css), "bytes;",
      "petals:", html.count('<i class="p '), "washes:", html.count("<b style=\"clip-path") - 3 * len(WAVES), "elements:", html.count("<"),
      "keyframes:", len(KEYFRAMES), "bloom easings:", len(BLOOM_EASE))
