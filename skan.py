#!/usr/bin/env python3
"""
skan.py - 한글로 그리는 회전 3D 크리스마스 트리

    pip install numpy
    python3 skan.py          (Ctrl+C 로 종료)

진짜 터미널(iTerm2, Terminal.app, PyCharm 하단 Terminal 탭)에서 실행하세요.
창을 100x65 정도로 키우면 보기 좋습니다.

한글은 터미널에서 두 칸을 차지하므로, 화면 한 칸 = 터미널 두 칸 으로 그립니다.
잎은 숲/솔/ㅅ, 금색 띠는 반짝, 선물은 선물, 눈은 눈, 전구는 빛, 별은 별.
"""
import math
import os
import shutil
import sys
import time

import numpy as np

TAU = 2 * np.pi

# ---------------------------------------------------------------- scene layout
GROUND = -1.00          # floor height
Y0 = -0.78              # bottom of the foliage
Y1 = 1.15               # top of the foliage
BASE_R = 0.95           # foliage radius at the bottom

# ---------------------------------------------------------------- timeline (s)
T_TRUNK = (0.3, 1.8)    # trunk grows up; snow starts spreading over the ground from it
T_WRAP = (1.6, 8.0)     # a glowing ribbon winds up the tree, foliage appears behind it
WRAP_TURNS = 5.0
T_GSNOW = (0.5, 14.0)   # snow piles up on the ground
T_BAUBLE = (9.5, 11.5)
T_LIGHTS = (10.0, 12.5)
T_STAR = 13.0
T_GIFTS = (13.5, 14.5)
T_MSG = 14.8
T_TSNOW = (15.0, 25.0)  # after it has snowed a while, snow settles on the branches
# snowman, on the left of the tree
T_BALL1 = (15.0, 17.2)  # a snowball rolls in from the left, growing, and becomes the body
T_BALL2 = (17.4, 19.2)  # a second, smaller one rolls in beside it ...
T_LIFT = (19.2, 19.9)   # ... and hops up on top: the head
T_HAT = (20.2, 20.9)    # a black top hat drops onto the head and bounces
T_SPIN = (21.4, 23.2)   # the snowman turns round once
T_FACE = 23.3           # then eyes, nose, mouth, buttons and the scarf appear one after another
T_LOOP = 34.0           # restart the show
FPS = 60
SPIN = 0.45             # rad / s
SPIN_SLOW = 0.20        # the scene turns slower while the snowman is being built
T_SLOW = (14.0, 15.0)   # ... easing from SPIN to SPIN_SLOW in this window

MESSAGE = "MERRY CHRISTMAS 2026"
DETAIL = 1.0            # point density; the pygame version raises it for its finer grid

# 5-row pixel font for the big greeting (1 = lit pixel)
BIG_FONT = {
    "M": ["10001", "11011", "10101", "10001", "10001"],
    "E": ["111", "100", "110", "100", "111"],
    "R": ["110", "101", "110", "101", "101"],
    "Y": ["101", "101", "010", "010", "010"],
    "C": ["011", "100", "100", "100", "011"],
    "H": ["101", "101", "111", "101", "101"],
    "I": ["111", "010", "010", "010", "111"],
    "S": ["011", "100", "010", "001", "110"],
    "T": ["111", "010", "010", "010", "010"],
    "A": ["010", "101", "111", "101", "101"],
    "2": ["110", "001", "010", "100", "111"],
    "0": ["010", "101", "101", "101", "010"],
    "6": ["011", "100", "110", "101", "010"],
    " ": ["00", "00", "00", "00", "00"],
}
PAIR = 0x110000         # cell code holding two narrow pixels instead of one wide glyph
PAIR_STR = ["  ", " \u2588", "\u2588 ", "\u2588\u2588"]

# ---------------------------------------------------------------- colours
WHITE = (0.92, 0.95, 1.00)
SNOW_W = (0.88, 0.93, 1.00)
GOLD = (1.00, 0.78, 0.25)
RED = (0.92, 0.16, 0.14)
GREEN_BOX = (0.15, 0.62, 0.30)
BLUE = (0.30, 0.50, 1.00)
PURPLE = (0.62, 0.40, 0.95)
WRAP_C = (1.00, 0.93, 0.72)
MSG_RED = (1.00, 0.27, 0.25)
PINK = (1.00, 0.45, 0.75)
CYAN = (0.35, 0.90, 1.00)
ORANGE = (1.00, 0.55, 0.20)
TEAL = (0.20, 0.75, 0.70)
YELLOW = (1.00, 0.88, 0.30)
# foliage greens: mint, emerald, teal, lime, deep pine
GREENS = np.array([(0.45, 0.95, 0.68), (0.12, 0.74, 0.42), (0.10, 0.62, 0.58),
                   (0.42, 0.86, 0.32), (0.06, 0.45, 0.28)])
GREEN_W = np.array([0.24, 0.28, 0.18, 0.12, 0.18])
BAUBLE_COLS = [RED, GOLD, BLUE, PURPLE, PINK, CYAN, WHITE, ORANGE]
GOLDS = np.array([(1.00, 0.80, 0.25), (1.00, 0.66, 0.15), (1.00, 0.92, 0.50)])
SNOW_TINTS = np.array([(0.92, 0.95, 1.00), (0.80, 0.88, 1.00), (0.88, 0.84, 1.00), (0.82, 0.96, 1.00)])
LIGHT_COLS = [(0.95, 0.10, 0.08), (1.00, 0.68, 0.08)]          # fairy lights: deep red and gold only
# presents: deep red, yellow and green only
GIFT_RED, GIFT_YELLOW, GIFT_GREEN = (0.82, 0.08, 0.08), (0.98, 0.74, 0.06), (0.06, 0.52, 0.20)

# ---------------------------------------------------------------- part kinds
NEEDLE, SNOW, TRUNK, GARLAND, BAUBLE, LIGHT, GIFT, GSNOW, WRAP, STAR, SM_BODY, SM_HEAD, SM_HAT, SM_FACE = range(14)


def codes(s):
    return np.array([ord(c) for c in s], np.int32)


# glyphs, dark -> bright (every one is a two-cell wide character)
NEEDLE_CH = codes("ㆍㅅㅅ소솔솔숲숲")
# foliage: 4 brightness steps. Each cell keeps its own fixed pick inside a step, so a glyph
# only changes when the cell gets clearly brighter or darker (no flicker while turning).
NEEDLE_POOLS = np.array([codes("ㆍㅅㆍㅅ"), codes("ㅅ소ㅅ소"), codes("소솔솔소"), codes("숲솔숲숲")])
# one colour family for the foliage: deep -> mid -> mint -> pale mint, picked by the same step
FOLIAGE_TONES = np.array([(0.08, 0.38, 0.27), (0.13, 0.58, 0.40), (0.26, 0.78, 0.55), (0.48, 0.92, 0.68)])
SNOW_CH = codes("ㆍ눈눈")
GSNOW_CH = codes("ㆍㆍㅡ눈")
BAUBLE_CH = codes("ㅇㅇ공")
WRAP_CH = codes("ㆍ빛빛")
STAR_CH = codes("ㆍ별별별빛")
# the 3D star: amber in the shade -> gold -> pale gold where the light hits a facet
STAR_TONES = np.array([(0.62, 0.36, 0.08), (0.95, 0.62, 0.15), (1.00, 0.80, 0.30), (1.00, 0.93, 0.62)])
STAR_Y = Y1 + 0.19       # centre of the star; its two lower points rest on the tip
STAR_R, STAR_RIN, STAR_D = 0.33, 0.14, 0.10     # outer radius, inner radius, half thickness
SM_RB, SM_RH = 0.24, 0.16                       # snowman body and head radius
SM_X, SM_Z = -1.30, -0.80                       # where it stands (on screen at T_SM_REF): left of the tree
T_SM_REF = 20.0                                 # it turns with the scene, and is at that spot at this time
SM_SCALE = 0.9                                  # overall size of the snowman
SM_BODY_Y = GROUND + SM_RB
SM_HEAD_Y = GROUND + 2 * SM_RB + SM_RH * 0.75   # the two balls overlap a little: a figure 8
SM_ROLL_FROM = -1.7                             # the balls start this far to the left
SNOWMAN_CH = codes("ㆍ눈눈")
HAT_C = (0.30, 0.30, 0.36)                      # black hat (a little lifted so it shows on the night sky)
COAL = (0.10, 0.10, 0.14)                       # eyes, mouth, buttons: dark holes in the white snow
CARROT = (1.00, 0.52, 0.16)
SCARF_C = (0.92, 0.20, 0.22)
STAR_SWAY = 0.6          # the star sways +-35 degrees instead of spinning edge-on with the tree
WORD_GARLAND = "반짝"
WORD_GIFT = "선물"
WORD_TRUNK = "기둥"
RIBBON = ord("끈")
LIGHT_G = ord("빛")

CAM_D = 4.2             # camera distance
CAM_Y = 0.10
ASPECT = 1.0            # one screen cell = two terminal cells = roughly square
LIGHT_DIR = np.array([-0.45, 0.65, -0.62])
LIGHT_DIR /= np.linalg.norm(LIGHT_DIR)


# ================================================================= helpers
def unit(v):
    v = np.asarray(v, float)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def envelope(y):
    """Radius of the foliage cone at height y."""
    u = np.clip((np.asarray(y, float) - Y0) / (Y1 - Y0), 0, 1)
    return BASE_R * (1 - u) ** 1.1


def fib_sphere(n):
    """n points spread evenly on the unit sphere."""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.cos(phi), np.sin(th) * np.sin(phi)], 1)


def rotate_y(p, a):
    c, s = math.cos(a), math.sin(a)
    out = p.copy()
    out[:, 0] = p[:, 0] * c - p[:, 2] * s
    out[:, 2] = p[:, 0] * s + p[:, 2] * c
    return out


def project(p, cols, rows, aspect):
    zc = p[:, 2] + CAM_D
    f = min(rows * 1.05, cols * 1.44)
    sx = cols / 2 + p[:, 0] / zc * f * aspect
    sy = rows * 0.47 - (p[:, 1] - CAM_Y) / zc * f
    return sx, sy, zc


def wrap_time(y, a):
    """When the winding ribbon passes the point at height y, angle a (ribbon is just above it)."""
    u = np.clip((np.asarray(y, float) - Y0) / (Y1 - Y0), 0, 1)
    af = (np.asarray(a, float) / TAU) % 1.0
    n = np.maximum(np.ceil(u * WRAP_TURNS - af), 0)
    w = (af + n) / WRAP_TURNS                       # ribbon progress, 0 .. 1 + 1/TURNS
    s = np.clip(w / (1 + 1 / WRAP_TURNS), 0, 1)
    return T_WRAP[0] + (T_WRAP[1] - T_WRAP[0]) * s


def wide(c):
    """Make one character two cells wide: ASCII -> full-width form, space -> empty cell."""
    if c == " ":
        return 0
    o = ord(c)
    return o + 0xFEE0 if 0x21 <= o <= 0x7E else o


# ================================================================= point cloud
class Parts:
    def __init__(self):
        self.chunks = []

    def add(self, p, nrm, col, kind, t0, base=1.0, centre=None, phase=0.0, pop=False, glyph=0):
        p = np.atleast_2d(np.asarray(p, float))
        n = len(p)

        def vec(v):
            return np.array(np.broadcast_to(np.asarray(v, float), (n, 3)))

        def sca(v):
            return np.array(np.broadcast_to(np.asarray(v, float), (n,)))

        self.chunks.append(dict(
            p=p,
            n=unit(vec(nrm)),
            c=vec(col),
            k=sca(kind).astype(int),
            t0=sca(t0),
            base=sca(base),
            ctr=p.copy() if centre is None else vec(centre),
            ph=sca(phase),
            pop=sca(float(pop)),
            g=sca(glyph).astype(int),
        ))

    def finish(self):
        D = {k: np.concatenate([c[k] for c in self.chunks]) for k in self.chunks[0]}
        for k, v in D.items():                       # float32: less memory traffic per frame
            if v.dtype == np.float64:
                D[k] = v.astype(np.float32)
        k = D["k"]
        D["is_pop"] = D["pop"] > 0
        D["is_star"] = k == STAR
        D["is_snowman"] = (k == SM_BODY) | (k == SM_HEAD) | (k == SM_HAT) | (k == SM_FACE)
        D["is_grow"] = (k == NEEDLE) | (k == TRUNK)
        D["t_done"] = float(D["t0"].max()) + 0.5      # after this every part is fully grown
        return D


def build():
    rng = np.random.default_rng(7)
    q = Parts()
    tips = []
    snow_p, snow_n = [], []

    # needles: whorls of drooping branches, denser and longer at the bottom
    for i, y in enumerate(np.linspace(Y0 + 0.02, Y1 - 0.06, 24)):
        u = (y - Y0) / (Y1 - Y0)
        R = envelope(y) + 0.05
        nb = int(6 + 12 * (1 - u))
        for b in range(nb):
            a = TAU * (b + 0.5 * rng.random()) / nb + i * 0.77
            L = R * rng.uniform(0.85, 1.08)
            n = int((8 + 80 * L) * DETAIL)
            s = rng.random(n) ** 0.65                       # 0 trunk .. 1 tip
            d = np.array([np.cos(a), 0, np.sin(a)])
            side = np.array([-np.sin(a), 0, np.cos(a)])
            spread = (0.025 + 0.09 * s) * rng.normal(0, 1, n)
            sl = s * L
            p = d * sl[:, None] + side * spread[:, None]
            p[:, 1] = y + 0.06 * sl - 0.20 * sl ** 2 + 0.012 * rng.normal(0, 1, n)
            nrm = unit(d * 0.75 + np.array([0, 0.55, 0]) + 0.3 * rng.normal(0, 1, (n, 3)))
            ao = (0.30 + 0.70 * s ** 1.3) * rng.uniform(0.75, 1.1, n)
            green = GREENS[rng.choice(len(GREENS), n, p=GREEN_W)] * (0.75 + 0.35 * s[:, None])
            q.add(p, nrm, green, NEEDLE, wrap_time(p[:, 1], a) + 0.35 * s, base=ao)
            # spots where snow will settle later: upward-facing, towards the tips
            cand = (s > 0.35) & (nrm[:, 1] > 0.4) & (rng.random(n) < 0.12)
            snow_p.append(p[cand] + nrm[cand] * 0.02 + [0, 0.015, 0])
            snow_n.append(nrm[cand])
            tl = 0.93 * L
            tips.append(d * tl + [0, y + 0.06 * tl - 0.20 * tl ** 2, 0])

    # dark inner cone so nothing shows through the branches
    m = int(1800 * DETAIL)
    y = Y0 + (Y1 - 0.1 - Y0) * rng.random(m)
    phi = rng.random(m) * TAU
    out = np.stack([np.cos(phi), np.full(m, 0.3), np.sin(phi)], 1)
    r = 0.6 * envelope(y)
    q.add(np.stack([np.cos(phi) * r, y, np.sin(phi) * r], 1), out, GREENS[rng.integers(0, 5, m)] * 0.45, NEEDLE,
          wrap_time(y, phi), base=0.75)

    # leader shoot: a small dense cone at the very top, so the star does not float
    m = int(500 * DETAIL)
    ut = rng.random(m)
    yt = Y1 - 0.30 + 0.32 * ut
    at = rng.random(m) * TAU
    rt = (envelope(yt) + 0.03) * np.sqrt(rng.random(m))
    pt = np.stack([np.cos(at) * rt, yt, np.sin(at) * rt], 1)
    nt = unit(np.stack([np.cos(at), np.full(m, 0.6), np.sin(at)], 1))
    q.add(pt, nt, GREENS[rng.choice(len(GREENS), m, p=GREEN_W)], NEEDLE, wrap_time(yt, at),
          base=rng.uniform(0.6, 1.0, m))

    # trunk, growing up from the ground
    m = 800
    y, phi = GROUND + rng.random(m) * (Y0 + 0.1 - GROUND), rng.random(m) * TAU
    n = np.stack([np.cos(phi), np.zeros(m), np.sin(phi)], 1)
    bark = 0.75 + 0.25 * np.sign(np.sin(phi * 30 + y * 5))
    q.add(n * 0.08 + np.stack([np.zeros(m), y, np.zeros(m)], 1), n,
          np.array([0.50, 0.30, 0.15]) * bark[:, None], TRUNK,
          T_TRUNK[0] + (T_TRUNK[1] - T_TRUNK[0]) * (y - GROUND) / (Y0 + 0.1 - GROUND))

    # snow on the ground: spreads out from the trunk as it appears, then keeps piling up
    m = int(3500 * DETAIL)
    r = 0.12 + 2.5 * np.sqrt(rng.random(m))
    a = rng.random(m) * TAU
    gp = np.stack([np.cos(a) * r, GROUND + 0.004 + 0.01 * rng.random(m), np.sin(a) * r], 1)
    spread = 2.5 * r / 2.6
    t0 = T_GSNOW[0] + spread + rng.random(m) ** 1.6 * (T_GSNOW[1] - T_GSNOW[0] - spread)
    q.add(gp, (0, 1, 0), SNOW_TINTS[rng.integers(0, 4, m)], GSNOW, t0, base=rng.uniform(0.8, 1.15, m), phase=rng.random(m))

    # the glowing ribbon that winds up the tree
    wmax = 1 + 1 / WRAP_TURNS
    w = np.linspace(0, wmax, 2200)
    yw = Y0 + np.minimum(w, 1) * (Y1 - Y0)
    A = w * WRAP_TURNS * TAU
    rw = envelope(yw) + 0.09
    core = np.stack([np.cos(A) * rw, yw, np.sin(A) * rw], 1)
    line = np.concatenate([core + [0, dy, 0] for dy in (-0.025, 0.025)])
    line += 0.008 * rng.normal(0, 1, line.shape)
    wn = np.tile(unit(np.stack([np.cos(A), np.full_like(A, 0.3), np.sin(A)], 1)), (2, 1))
    q.add(line, wn, WRAP_C, WRAP, np.tile(T_WRAP[0] + (T_WRAP[1] - T_WRAP[0]) * w / wmax, 2), base=1.2)

    # tinsel garland: a thick gold spiral on the same path as the ribbon, left behind as it passes
    wg = np.linspace(0.02, 0.93, 2600)
    yg = Y0 + wg * (Y1 - Y0)
    ag = wg * WRAP_TURNS * TAU
    rg = envelope(yg) + 0.08
    core = np.stack([np.cos(ag) * rg, yg, np.sin(ag) * rg], 1)
    strands = [core + [0, dy, 0] for dy in (-0.03, 0.0, 0.03)]
    line = np.concatenate(strands) + 0.008 * rng.normal(0, 1, (3 * len(wg), 3))
    gn = np.tile(unit(np.stack([np.cos(ag), np.full_like(ag, 0.4), np.sin(ag)], 1)), (3, 1))
    gt = np.tile(T_WRAP[0] + (T_WRAP[1] - T_WRAP[0]) * wg / (1 + 1 / WRAP_TURNS) + 0.4, 3)
    q.add(line, gn, GOLDS[rng.integers(0, 3, len(line))], GARLAND, gt,
          base=1.15, phase=np.tile(wg * 9.0, 3))       # phase grows along the spiral

    # baubles: little shiny balls that pop in
    ball = fib_sphere(40)
    for k in range(40):
        yb = Y0 + 0.08 + (Y1 - Y0 - 0.35) * rng.random()
        a = rng.random() * TAU
        rb = envelope(yb) + 0.03
        c = np.array([np.cos(a) * rb, yb - 0.03, np.sin(a) * rb])
        size = 0.035 + 0.02 * rng.random()
        col = BAUBLE_COLS[k % len(BAUBLE_COLS)]
        t0 = T_BAUBLE[0] + rng.random() * (T_BAUBLE[1] - T_BAUBLE[0])
        q.add(c + ball * size, ball, col, BAUBLE, t0, base=1.15, centre=c, pop=True)

    # fairy lights on the branch tips
    tips = np.array(tips)
    pick = rng.choice(len(tips), min(45, len(tips)), replace=False)
    bulb = fib_sphere(24)
    light_t0 = T_LIGHTS[0] + rng.random(len(pick)) * (T_LIGHTS[1] - T_LIGHTS[0])
    for c, t0 in zip(tips[pick], light_t0):
        col = LIGHT_COLS[rng.integers(len(LIGHT_COLS))]
        q.add(c + bulb * 0.045, bulb, col, LIGHT, t0, centre=c, phase=rng.random())

    # presents: boxes with a crossed ribbon and a bow
    #        angle dist  w     h     d     rot  body       ribbon
    gifts = [(0.3, 1.14, 0.36, 0.29, 0.34, 0.4, GIFT_RED, GIFT_YELLOW), (1.5, 1.20, 0.32, 0.38, 0.32, 1.3, GIFT_GREEN, GIFT_RED),
             (2.6, 1.12, 0.40, 0.22, 0.32, 1.0, GIFT_YELLOW, GIFT_RED), (3.7, 1.20, 0.30, 0.25, 0.30, 0.7, GIFT_RED, GIFT_GREEN),
             (4.7, 1.14, 0.36, 0.27, 0.36, 0.1, GIFT_GREEN, GIFT_YELLOW), (5.6, 1.24, 0.28, 0.32, 0.28, 0.5, GIFT_YELLOW, GIFT_GREEN)]
    loop = fib_sphere(40)
    for g, (a, dist, w, h, d, rot, body, rib) in enumerate(gifts):
        areas = np.array([w * d, h * d, h * d, h * w, h * w])
        m = int(2500 * DETAIL * areas.sum())
        face = rng.choice(5, m, p=areas / areas.sum())
        r1, r2 = rng.random(m), rng.random(m)
        lp = np.zeros((m, 3))
        ln = np.zeros((m, 3))
        f = face == 0                                       # top
        lp[f] = np.stack([(r1[f] - 0.5) * w, np.full(f.sum(), h), (r2[f] - 0.5) * d], 1)
        ln[f] = [0, 1, 0]
        for fi, sgn in ((1, 1), (2, -1)):                   # +x / -x sides
            f = face == fi
            lp[f] = np.stack([np.full(f.sum(), sgn * w / 2), r1[f] * h, (r2[f] - 0.5) * d], 1)
            ln[f] = [sgn, 0, 0]
        for fi, sgn in ((3, 1), (4, -1)):                   # +z / -z sides
            f = face == fi
            lp[f] = np.stack([(r1[f] - 0.5) * w, r2[f] * h, np.full(f.sum(), sgn * d / 2)], 1)
            ln[f] = [0, 0, sgn]
        ribbon = (np.abs(lp[:, 0]) < 0.12 * w) | (np.abs(lp[:, 2]) < 0.12 * d)
        col = np.where(ribbon[:, None], rib, body)
        bow = np.concatenate([loop * [0.05, 0.035, 0.025] + [sx * 0.045, h + 0.03, 0] for sx in (-1, 1)])
        lp = np.concatenate([lp, bow])
        ln = np.concatenate([ln, loop, loop])
        col = np.concatenate([col, np.broadcast_to(rib, (len(bow), 3))])
        glyph = np.concatenate([np.where(ribbon, RIBBON, 0), np.full(len(bow), RIBBON)])
        base_pos = np.array([np.cos(a) * dist, GROUND, np.sin(a) * dist])
        wp = rotate_y(lp, rot) + base_pos
        wn = rotate_y(ln, rot)
        t0 = T_GIFTS[0] + g / len(gifts) * (T_GIFTS[1] - T_GIFTS[0])
        q.add(wp, wn, col, GIFT, t0, centre=base_pos + [0, h / 2, 0], pop=True, glyph=glyph)

    # 3D star: five points, every point made of two sloped facets on each side (front and back),
    # so it catches the light differently on each facet as the tree turns
    centre = np.array([0.0, STAR_Y, 0.0])
    corners = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rad = STAR_R if i % 2 == 0 else STAR_RIN
        corners.append(centre + [math.cos(a) * rad, math.sin(a) * rad, 0.0])
    per = int(260 * DETAIL)
    for side in (1, -1):
        apex = centre + [0, 0, side * STAR_D]
        for i in range(10):
            A, B = corners[i], corners[(i + 1) % 10]
            nrm = np.cross(A - apex, B - apex)
            nrm = nrm if nrm[2] * side > 0 else -nrm
            u, v = rng.random(per), rng.random(per)
            flip = u + v > 1
            u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
            pts = apex + u[:, None] * (A - apex) + v[:, None] * (B - apex)
            q.add(pts, nrm, GOLD, STAR, T_STAR, base=1.15, centre=centre, pop=True,
                  phase=rng.random(per))

    # snowman, in its own local coordinates (x = z = 0 under its middle, front = -z);
    # render() moves the parts (rolling, hopping, falling, turning) and puts it left of the tree
    sph = fib_sphere(int(700 * DETAIL))
    m = len(sph)
    q.add(sph * SM_RB + [0, SM_BODY_Y, 0], sph, SNOW_W, SM_BODY, T_BALL1[0],
          base=rng.uniform(1.0, 1.4, m), phase=rng.random(m))
    sph = fib_sphere(int(420 * DETAIL))
    m = len(sph)
    q.add(sph * SM_RH + [0, SM_HEAD_Y, 0], sph, SNOW_W, SM_HEAD, T_BALL2[0],
          base=rng.uniform(1.0, 1.4, m), phase=rng.random(m))

    # top hat: crown (side + top), red band, brim
    top = SM_HEAD_Y + SM_RH * 0.9
    m = int(420 * DETAIL)
    a, hh = rng.random(m) * TAU, rng.random(m) * 0.20
    side = np.stack([np.cos(a) * 0.11, top + 0.03 + hh, np.sin(a) * 0.11], 1)
    sn = np.stack([np.cos(a), np.zeros(m), np.sin(a)], 1)
    band = hh < 0.045
    word = np.where((a / TAU * 8).astype(int) % 2 == 0, ord("모"), ord("자"))
    q.add(side, sn, np.where(band[:, None], SCARF_C, HAT_C), SM_HAT, T_HAT[0], base=1.1,
          glyph=np.where(band, ord("띠"), word))
    m = int(160 * DETAIL)
    a, r = rng.random(m) * TAU, 0.11 * np.sqrt(rng.random(m))
    q.add(np.stack([np.cos(a) * r, np.full(m, top + 0.23), np.sin(a) * r], 1), (0, 1, 0), HAT_C, SM_HAT,
          T_HAT[0], base=1.1, glyph=ord("모"))
    m = int(320 * DETAIL)
    a, r = rng.random(m) * TAU, 0.11 + 0.08 * rng.random(m)
    q.add(np.stack([np.cos(a) * r, np.full(m, top + 0.03), np.sin(a) * r], 1), (0, 1, 0), HAT_C, SM_HAT,
          T_HAT[0], base=1.1, glyph=np.where((a / TAU * 8).astype(int) % 2 == 0, ord("모"), ord("자")))

    def on_ball(cx, cy, ry, rad, n, spread):
        """n points in a small patch on the front of a ball (front = -z)."""
        x = cx + spread * rng.normal(0, 1, n)
        y = cy + spread * rng.normal(0, 1, n)
        z = -np.sqrt(np.maximum(rad ** 2 - x ** 2 - (y - ry) ** 2, 0)) - 0.01
        return np.stack([x, y, z], 1)

    for ex in (-0.055, 0.055):                                      # eyes: 눈
        q.add(on_ball(ex, SM_HEAD_Y + 0.045, SM_HEAD_Y, SM_RH, 8, 0.004), (0, 0, -1), COAL, SM_FACE,
              T_FACE, base=1.0, glyph=ord("눈"))
    # carrot nose: a real cone sticking out (shaded by its own surface), with darker rings
    m = int(320 * DETAIL)
    sn_ = rng.random(m) ** 0.8                                      # 0 at the face .. 1 at the tip
    a = rng.random(m) * TAU
    L_n, r_n = 0.19, 0.038
    rad = r_n * (1 - sn_)
    nose = np.stack([rad * np.cos(a), SM_HEAD_Y - 0.01 + rad * np.sin(a) - 0.02 * sn_,
                     -SM_RH * 0.9 - L_n * sn_], 1)
    nose_n = unit(np.stack([np.cos(a), np.sin(a), np.full(m, -r_n / L_n)], 1))
    rings = 0.72 + 0.28 * (np.sin(sn_ * 34) > -0.4)                 # little grooves along the carrot
    q.add(nose, nose_n, CARROT, SM_FACE, T_FACE + 0.3 + 0.4 * sn_, base=1.15 * rings,
          glyph=np.where(sn_ < 0.5, ord("당"), ord("근")))
    for u in np.linspace(-1, 1, 5):                                 # mouth: a smile of dots
        q.add(on_ball(0.065 * u, SM_HEAD_Y - 0.065 + 0.025 * u * u, SM_HEAD_Y, SM_RH, 10, 0.006),
              (0, 0, -1), COAL, SM_FACE, T_FACE + 0.6, base=1.0, glyph=ord("ㆍ"))
    for i, dy in enumerate((0.11, 0.03, -0.05)):                    # buttons
        q.add(on_ball(0.0, SM_BODY_Y + dy, SM_BODY_Y, SM_RB, 5, 0.003), (0, 0, -1), COAL, SM_FACE,
              T_FACE + 0.8 + 0.15 * i, base=1.0, glyph=ord("ㅇ"))
    # twig arms: a stick out of each side, pointing up and out, with two little forks
    def twig(start, direction, length, t0, n):
        d = unit(np.asarray(direction, float))
        sv = rng.random(n)
        pts = np.asarray(start) + sv[:, None] * length * d + 0.006 * rng.normal(0, 1, (n, 3))
        return pts, t0 + 0.5 * sv, sv

    for side in (-1, 1):
        start = np.array([side * SM_RB * 0.92, SM_BODY_Y + 0.07, -0.02])
        main_d = np.array([side * 1.0, 0.55, -0.1])
        parts = [twig(start, main_d, 0.26, T_FACE + 1.0, int(75 * DETAIL))]
        tip = start + unit(main_d) * 0.26
        mid = start + unit(main_d) * 0.17
        parts.append(twig(mid, [side * 0.5, 1.0, -0.1], 0.075, T_FACE + 1.35, int(25 * DETAIL)))
        parts.append(twig(tip, [side * 1.0, -0.15, -0.1], 0.06, T_FACE + 1.5, int(20 * DETAIL)))
        parts.append(twig(tip, [side * 0.4, 1.0, 0.0], 0.05, T_FACE + 1.5, int(20 * DETAIL)))
        for pts, tt, sv in parts:
            q.add(pts, (0, 0.6, -1), (0.52, 0.33, 0.17), SM_FACE, tt, base=1.0,
                  glyph=np.where((sv * 6).astype(int) % 2 == 0, ord("가"), ord("지")))

    # scarf: a ring round the neck that wraps itself on, then a tail hanging down the front
    ny = GROUND + 2 * SM_RB - 0.005
    m = int(500 * DETAIL)
    a, b = rng.random(m) * TAU, rng.random(m) * TAU
    R_n, tube = 0.125, 0.035
    ring = np.stack([np.cos(a) * (R_n + tube * np.cos(b)), ny + tube * np.sin(b),
                     np.sin(a) * (R_n + tube * np.cos(b))], 1)
    rn = np.stack([np.cos(a) * np.cos(b), np.sin(b), np.sin(a) * np.cos(b)], 1)
    seg = (a / TAU * 12).astype(int)
    q.add(ring, rn, np.where((seg % 4 == 3)[:, None], WHITE, SCARF_C), SM_FACE,
          T_FACE + 1.3 + 0.6 * ((a - np.pi / 2) % TAU) / TAU, base=1.05,
          glyph=codes("목도리")[seg % 3])
    m = int(120 * DETAIL)
    hv = rng.random(m)
    tail = np.stack([0.07 + 0.03 * rng.random(m), ny - 0.02 - 0.17 * hv, -0.13 - 0.03 * hv], 1)
    q.add(tail, (0.2, 0, -1), SCARF_C, SM_FACE, T_FACE + 1.9 + 0.3 * hv, base=1.0,
          glyph=codes("목도리")[(hv * 6).astype(int) % 3])

    # snow settling on the branches, a little at a time
    sp = np.concatenate(snow_p)
    m = len(sp)
    t0 = T_TSNOW[0] + rng.random(m) ** 1.3 * (T_TSNOW[1] - T_TSNOW[0])
    q.add(sp, np.concatenate(snow_n), SNOW_TINTS[rng.integers(0, 4, m)], SNOW, t0, base=1.1, phase=rng.random(m))

    return q.finish()


# ================================================================= 2D drawing
def put(char, col, row, x, code, tint, b=1.0):
    rows, cols = char.shape
    if 0 <= row < rows and 0 <= x < cols:
        char[row, x] = code
        col[row, x] = np.clip(np.asarray(tint) * b, 0, 1)


class Backdrop:
    """Falling snow (눈 / ㆍ) + a dotted floor grid that turns with the tree."""

    def __init__(self, cols, rows):
        rng = np.random.default_rng(1)
        n = int(cols * rows * 0.05)
        self.x0 = rng.random(n) * cols
        self.y0 = rng.random(n) * rows
        self.sp = rng.uniform(1.5, 7.0, n)              # rows / s; fast flakes are closer
        self.ph = rng.random(n) * TAU
        self.ch = np.where(self.sp > 4.0, ord("눈"), ord("ㆍ"))
        self.bright = 0.35 + 0.1 * self.sp
        self.tint = SNOW_TINTS[rng.integers(0, 4, n)]
        self.front = self.sp > 5.6                      # drawn in front of the tree
        g = np.linspace(-5, 5, 70)
        gx, gz = np.meshgrid(g, g)
        self.gp = np.stack([gx.ravel(), np.full(gx.size, GROUND - 0.01), gz.ravel()], 1)
        self.gch = np.full(gx.size, ord("ㆍ"))     # one glyph: two kinds swapped cells while turning

    def _flakes(self, sel, clock, cols, rows, off=None):
        sp = self.sp[sel]
        fy = (self.y0[sel] + clock * sp) % rows
        fx = (self.x0[sel] + 0.15 * sp * np.sin(clock * 0.9 + self.ph[sel])) % cols
        x, y = fx.astype(int), fy.astype(int)
        if off is not None:                       # exact position inside the cell (pygame version)
            off[0][y, x] = fx - x
            off[1][y, x] = fy - y
        return x, y

    def draw(self, char, col, ang, clock, cols, rows, off=None):
        p = rotate_y(self.gp, ang)
        sx, sy, zc = project(p, cols, rows, ASPECT)
        ix, iy = np.round(sx).astype(int), np.round(sy).astype(int)
        ok = (zc > 0.5) & (ix >= 0) & (ix < cols) & (iy >= 0) & (iy < rows)
        ix, iy, zc, ch = ix[ok], iy[ok], zc[ok], self.gch[ok]
        b = np.clip(0.55 - (zc - CAM_D) * 0.05, 0.12, 0.45)
        char[iy, ix] = ch
        col[iy, ix] = np.array([0.55, 0.62, 0.75]) * b[:, None]
        back = ~self.front
        x, y = self._flakes(back, clock, cols, rows, off)
        char[y, x] = self.ch[back]
        col[y, x] = self.tint[back] * self.bright[back][:, None]

    def draw_front(self, char, col, clock, cols, rows, off=None):
        x, y = self._flakes(self.front, clock, cols, rows, off)
        char[y, x] = self.ch[self.front]
        col[y, x] = self.tint[self.front] * np.minimum(self.bright[self.front], 1.0)[:, None]


def spin_angle(t):
    """Scene rotation at time t: SPIN rad/s, easing down to SPIN_SLOW during T_SLOW."""
    a, b = T_SLOW
    if t <= a:
        return SPIN * t
    x = min((t - a) / (b - a), 1.0)
    eased = (b - a) * (x ** 3 - x ** 4 / 2)                # integral of smoothstep from 0 to x
    ang = SPIN * a + SPIN * (b - a) * x + (SPIN_SLOW - SPIN) * eased
    if t > b:
        ang += SPIN_SLOW * (t - b)
    return ang


_SM_SPOT = {}


def snowman_spot():
    """World position and facing of the snowman, so that at T_SM_REF it stands at (SM_X, SM_Z)
    on screen, and when its face appears it looks at the camera."""
    if not _SM_SPOT:
        ref = rotate_y(np.array([[SM_X, 0.0, SM_Z]]), -spin_angle(T_SM_REF))[0]
        at_face = rotate_y(ref[None], spin_angle(T_FACE + 0.8))[0]
        look = math.atan2(-at_face[0], -(-CAM_D - at_face[2]))   # direction to the camera
        _SM_SPOT.update(x=ref[0], z=ref[2], yaw=look - spin_angle(T_FACE + 0.8))
    return _SM_SPOT


def rot_z(p, a):
    c, s = math.cos(a), math.sin(a)
    out = p.copy()
    out[:, 0] = p[:, 0] * c - p[:, 1] * s
    out[:, 1] = p[:, 0] * s + p[:, 1] * c
    return out


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 2


def snowman_pose(pl, nl, kk, t):
    """Move the snowman parts for time t; returns world points and normals."""
    P, N = pl.astype(np.float64).copy(), nl.astype(np.float64).copy()

    # body: rolls in from the left, growing like a real snowball
    b = kk == SM_BODY
    e = ease_out((t - T_BALL1[0]) / (T_BALL1[1] - T_BALL1[0]))
    grow = 0.35 + 0.65 * e
    x = SM_ROLL_FROM * (1 - e)
    roll = -(x - SM_ROLL_FROM) / SM_RB                       # turned by distance / radius
    c0 = np.array([0, SM_BODY_Y, 0])
    P[b] = rot_z(P[b] - c0, roll) * grow + [x, GROUND + SM_RB * grow, 0]
    N[b] = rot_z(N[b], roll)

    # head: rolls in beside the body, then hops up on top of it
    h = kk == SM_HEAD
    e = ease_out((t - T_BALL2[0]) / (T_BALL2[1] - T_BALL2[0]))
    lift = smooth((t - T_LIFT[0]) / (T_LIFT[1] - T_LIFT[0]))
    grow = 0.35 + 0.65 * e
    side_x = -(SM_RB + SM_RH + 0.03)
    x = SM_ROLL_FROM + (side_x - SM_ROLL_FROM) * e
    roll = -(x - SM_ROLL_FROM) / SM_RH
    x = x * (1 - lift)
    y = (GROUND + SM_RH * grow) * (1 - lift) + SM_HEAD_Y * lift + 0.28 * math.sin(math.pi * lift)
    c0 = np.array([0, SM_HEAD_Y, 0])
    P[h] = rot_z(P[h] - c0, roll) * grow + [x, y, 0]
    N[h] = rot_z(N[h], roll)

    # hat: falls from above, then a small bounce
    ht = kk == SM_HAT
    e = min(max((t - T_HAT[0]) / (T_HAT[1] - T_HAT[0]), 0.0), 1.0)
    drop = 1.4 * (1 - e * e)
    if t > T_HAT[1]:
        drop = 0.06 * abs(math.sin((t - T_HAT[1]) * 11)) * math.exp(-(t - T_HAT[1]) * 5)
    P[ht, 1] += drop

    # one full turn, then it faces us again
    spot = snowman_spot()
    turn = TAU * smooth((t - T_SPIN[0]) / (T_SPIN[1] - T_SPIN[0])) + spot["yaw"]
    P, N = rotate_y(P, turn), rotate_y(N, turn)
    P[:, 1] = GROUND + (P[:, 1] - GROUND) * SM_SCALE        # a touch smaller, still standing on the ground
    P[:, 0] = P[:, 0] * SM_SCALE + spot["x"]
    P[:, 2] = P[:, 2] * SM_SCALE + spot["z"]
    return P, N                                             # world coordinates


_STATE = {}


def _cell_state(rows, cols):
    """What each screen cell showed last frame (used to avoid flicker)."""
    st = _STATE.get((rows, cols))
    if st is None:
        st = _STATE[(rows, cols)] = {"step": np.full((rows, cols), -1, np.int8)}
    return st


_HASH = {}


def _cell_hash(rows, cols):
    """A fixed random number 0..3 for every screen cell."""
    h = _HASH.get((rows, cols))
    if h is None:
        h = _HASH[(rows, cols)] = np.random.default_rng(11).integers(0, 4, (rows, cols))
    return h


# ================================================================= frame
def render(D, t, cols, rows, back, clock, draw_msg=True, subcell=False):
    """subcell=True also returns info["off"]: each glyph's exact position inside its cell,
    so a pixel renderer (pygame) can move glyphs smoothly instead of jumping cell to cell."""
    char = np.zeros((rows, cols), np.int32)
    col = np.zeros((rows, cols, 3))
    ang = spin_angle(t)
    info = {"rotation": math.degrees(ang) % 360}
    off = (np.zeros((rows, cols), np.float32), np.zeros((rows, cols), np.float32)) if subcell else None

    back.draw(char, col, ang, clock, cols, rows, off)

    k = D["k"]
    if t < D["t_done"]:
        g = smooth((t - D["t0"]) / 0.5).astype(np.float32)
        vis = g > 0.001
        p = D["p"].copy()
        # popping parts scale up from their centre
        sel = D["is_pop"] & vis
        p[sel] = D["ctr"][sel] + (p[sel] - D["ctr"][sel]) * g[sel, None]
        # needles and trunk extend outward from the middle
        grow = D["is_grow"] & (g < 1)
        p[grow, 0] *= 0.4 + 0.6 * g[grow]
        p[grow, 2] *= 0.4 + 0.6 * g[grow]
        p = p[vis]
    else:                                            # everything grown: skip the growth maths
        g = np.ones(len(k), np.float32)
        vis = slice(None)
        p = D["p"]

    P = rotate_y(p, ang)
    N = rotate_y(D["n"][vis], ang)
    sm_star = D["is_star"][vis]
    if sm_star.any():                    # undo the tree's spin for the star, then let it sway
        local = -ang + STAR_SWAY * math.sin(0.8 * t)
        P[sm_star] = rotate_y(P[sm_star], local)
        N[sm_star] = rotate_y(N[sm_star], local)
    kv, gv, base, ph = k[vis], g[vis], D["base"][vis], D["ph"][vis]
    cv = D["c"][vis]
    smv = D["is_snowman"][vis]
    if smv.any():                        # the snowman is animated, then turns with the scene
        Ps, Ns = snowman_pose(D["p"][vis][smv], D["n"][vis][smv], kv[smv], t)
        P[smv], N[smv] = rotate_y(Ps, ang), rotate_y(Ns, ang)

    diff = np.clip(N @ LIGHT_DIR, 0, 1)
    lum = base * (0.28 + 0.72 * diff) * gv
    sx, sy, zc = project(P, cols, rows, ASPECT)
    lum *= np.clip(1.25 - (zc - CAM_D) * 0.25, 0.55, 1.25)
    ix, iy = np.round(sx).astype(int), np.round(sy).astype(int)

    shimmer = kv == GARLAND
    lum[shimmer] = np.maximum(lum[shimmer], 0.9) * (1.0 + 0.25 * np.sin(ph[shimmer] * TAU - t * 5))  # always bright, light runs up the spiral
    lit = kv == LIGHT
    lum[lit] = (0.45 + 0.75 * diff[lit]) * (0.9 + 0.3 * np.sin(t * 3.0 + ph[lit] * TAU)) * gv[lit]  # round, glowing
    wrap = kv == WRAP                                # the ribbon glows, then fades away
    age = t - D["t0"][vis][wrap]
    lum[wrap] = np.where(age >= 0, 1.4 * np.exp(-np.maximum(age, 0) / 0.6), 0)

    # choose a Hangul glyph for every point
    def ramp(table, level):
        return table[np.clip(level.astype(int), 0, len(table) - 1)]

    chars = ramp(NEEDLE_CH, lum * len(NEEDLE_CH) * 0.85)
    nd = kv == NEEDLE                                # foliage: stable glyph + tone per brightness step
    cell_hash = _cell_hash(rows, cols)
    state = _cell_state(rows, cols)
    iyc, ixc = np.clip(iy, 0, rows - 1), np.clip(ix, 0, cols - 1)
    level = lum[nd] * 3.6
    step = np.clip(level.astype(int), 0, 3)
    before = state["step"][iyc[nd], ixc[nd]]
    # hysteresis: a cell keeps last frame's step unless the brightness clearly moved on
    keep = (before >= 0) & (np.abs(level - (before + 0.5)) < 0.85)
    step = np.where(keep, before, step)
    chars[nd] = NEEDLE_POOLS[step, cell_hash[iyc[nd], ixc[nd]]]
    step_of_point = np.full(len(kv), -1, np.int8)
    step_of_point[nd] = step
    cv = cv.copy()
    cv[nd] = FOLIAGE_TONES[step]
    chars[lit] = LIGHT_G
    bm = kv == BAUBLE
    chars[bm] = ramp(BAUBLE_CH, lum[bm] * 2.4)
    sm = kv == SNOW
    chars[sm] = ramp(SNOW_CH, lum[sm] * 2.0 + ph[sm])
    gs = kv == GSNOW
    chars[gs] = GSNOW_CH[cell_hash[iyc[gs], ixc[gs]]]   # fixed per cell, whichever flake lands there
    chars[wrap] = ramp(WRAP_CH, lum[wrap] * 2.2)
    snowball = (kv == SM_BODY) | (kv == SM_HEAD)
    chars[snowball] = ramp(SNOWMAN_CH, lum[snowball] * 2.2 + ph[snowball] * 0.5)
    st = kv == STAR                                  # star: facet shading + a flash when it appears
    if st.any():
        lum[st] *= 1.0 + 1.6 * math.exp(-((t - T_STAR - 0.15) / 0.3) ** 2)
        lum[st] *= 0.9 + 0.15 * np.sin(t * 3 + ph[st] * TAU)            # faint shimmer
        sstep = np.clip((lum[st] * 3.0).astype(int), 0, 3)
        chars[st] = ramp(STAR_CH, lum[st] * 3.4)
        cv[st] = STAR_TONES[sstep]
    for mask, word in ((shimmer, WORD_GARLAND), (kv == GIFT, WORD_GIFT), (kv == TRUNK, WORD_TRUNK)):
        chars[mask] = np.where(ix[mask] % 2 == 0, ord(word[0]), ord(word[1]))   # 반짝반짝 ...
    gv_glyph = D["g"][vis]
    over = gv_glyph > 0
    chars[over] = gv_glyph[over]
    shade = np.where((kv == GIFT) | lit, 0.22 + 1.05 * lum, 0.45 + 0.8 * lum)   # presents/lights: more contrast
    colours = np.clip(cv * shade[:, None], 0, 1)

    ok = (ix >= 0) & (ix < cols) & (iy >= 0) & (iy < rows) & (lum > 0.03)
    depth = zc - lit * 0.06 - wrap * 0.08 - shimmer * 0.03 - st * 0.05   # lights, ribbon, tinsel, star win ties
    order = np.argsort(-depth[ok])           # far first, near overwrites
    cell = (iy * cols + ix)[ok][order]
    char.reshape(-1)[cell] = chars[ok][order]
    col.reshape(-1, 3)[cell] = colours[ok][order]
    remembered = np.full(rows * cols, -1, np.int8)
    remembered[cell] = step_of_point[ok][order]
    state["step"] = remembered.reshape(rows, cols)
    if subcell:
        off[0].reshape(-1)[cell] = (sx - ix)[ok][order]
        off[1].reshape(-1)[cell] = (sy - iy)[ok][order]

    back.draw_front(char, col, clock, cols, rows, off)


    info["bold_row"] = -1
    if draw_msg and t > T_MSG:
        big_message(char, col, t, cols, rows)
    info["letters"] = int((char > 0).sum())
    info["off"] = off
    return char, col, info


def big_bitmap(text):
    """Pixel rows for text in the 5-row font, one pixel per terminal column."""
    rows = [""] * 5
    for ch in text:
        g = BIG_FONT.get(ch, BIG_FONT[" "])
        for r in range(5):
            rows[r] += g[r] + "0"
    return [r[:-1] for r in rows]


def big_message(char, col, t, cols, rows):
    """Big red greeting typed out letter by letter, pixels drawn with full blocks."""
    lines = [MESSAGE]
    if len(big_bitmap(MESSAGE)[0]) > 2 * cols - 4:          # too wide: split over two lines
        lines = MESSAGE.rsplit(" ", 1)
    shown = int((t - T_MSG) * 10)
    tint = np.clip(np.array(MSG_RED) * (1.0 + 0.1 * np.sin(t * 4)), 0, 1)
    top = rows - 2 - 6 * len(lines)
    for li, line in enumerate(lines):
        full = big_bitmap(line)
        part = big_bitmap(line[:max(0, shown)])
        shown -= len(line) + 1
        width = (len(full[0]) + 1) // 2                     # in screen cells (2 pixels each)
        x0 = (cols - width) // 2
        y0 = top + li * 6
        char[max(y0 - 1, 0):y0 + 6, max(x0 - 1, 0):x0 + width + 1] = 0
        for r, bits in enumerate(part):
            bits = bits.ljust(2 * width, "0")
            for cx in range(width):
                pair = (bits[2 * cx] == "1") * 2 + (bits[2 * cx + 1] == "1")
                if pair and 0 <= y0 + r < rows and 0 <= x0 + cx < cols:
                    char[y0 + r, x0 + cx] = PAIR + pair
                    col[y0 + r, x0 + cx] = tint


# ================================================================= terminal
_ESC = {}


def _esc(k):
    e = _ESC.get(k)
    if e is None:
        e = _ESC[k] = "\x1b[38;2;%d;%d;%dm" % ((k >> 10) * 8, ((k >> 5) & 31) * 8, (k & 31) * 8)
    return e


def _key(rgb):
    return (rgb[0] // 8) * 1024 + (rgb[1] // 8) * 32 + rgb[2] // 8


def to_ansi(char, col, info, t):
    rows, cols = char.shape
    q = np.clip((col * 31.99).astype(np.int32), 0, 31)             # 32 levels per channel
    key = q[..., 0] * 1024 + q[..., 1] * 32 + q[..., 2]
    char = char.copy()
    key[char == 0] = -1

    def hud(r, c0, text, rgb):
        for i, c in enumerate(text):
            if 0 <= r < rows and 0 <= c0 + i < cols:
                char[r, c0 + i] = wide(c)
                key[r, c0 + i] = _key(rgb) if c != " " else -1

    hud(1, 1, "한글 트리", (225, 228, 235))
    hud(2, 1, f"회전 {info['rotation']:.1f}도", (140, 148, 160))
    hud(3, 1, f"글자 {info['letters']:,}", (140, 148, 160))
    right = f"{t:04.1f}초"
    hud(1, cols - len(right) - 1, right, (230, 170, 80))

    keys, chs = key.tolist(), char.tolist()
    lines = []
    for r in range(rows):
        bold = r == info["bold_row"]
        parts = ["\x1b[1m"] if bold else []
        last = -2
        for k, c in zip(keys[r], chs[r]):
            if k < 0:
                parts.append("  ")                  # empty cell = two spaces
                continue
            if k != last:
                parts.append(_esc(k))
                last = k
            parts.append(PAIR_STR[c - PAIR] if c >= PAIR else chr(c))
        if bold:
            parts.append("\x1b[22m")
        lines.append("".join(parts))
    # synchronized update: the terminal shows the whole frame at once (no tearing)
    return "\x1b[?2026h\x1b[H" + "\n".join(lines) + "\x1b[?2026l"


def main():
    if not sys.stdout.isatty():
        print("터미널에서 실행하세요:  python3 skan.py")
        print("(PyCharm Run 콘솔은 화면이 계속 쌓여서 멈춥니다. 하단 Terminal 탭을 쓰세요.)")
        return
    if os.name == "nt":
        os.system("")                   # enable ANSI escapes on Windows
    D = build()
    out = sys.stdout.buffer
    out.write(b"\x1b[?1049h\x1b[?25l\x1b[48;2;8;10;20m\x1b[2J")
    start = time.perf_counter()
    next_frame = start
    size = None
    back = None
    try:
        while True:
            tc, tr = shutil.get_terminal_size((100, 65))
            cols, rows = (tc - 1) // 2, tr - 1   # one screen cell = two terminal columns
            if (cols, rows) != size:
                size = (cols, rows)
                back = Backdrop(cols, rows)
                out.write(b"\x1b[2J")
            clock = time.perf_counter() - start
            t = clock % T_LOOP
            char, col, info = render(D, t, cols, rows, back, clock)
            out.write(to_ansi(char, col, info, t).encode("utf-8"))
            out.flush()
            # steady pacing: aim at fixed frame times instead of "sleep a bit after each frame"
            next_frame += 1 / FPS
            delay = next_frame - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            else:
                next_frame = time.perf_counter()     # running behind: don't try to catch up
    except KeyboardInterrupt:
        pass
    finally:
        out.write(b"\x1b[0m\x1b[?25h\x1b[?1049l")
        out.flush()


if __name__ == "__main__":
    main()
