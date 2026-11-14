#!/usr/bin/env python3
"""
skan_pygame.py - 한글 크리스마스 트리를 pygame 창에 그리는 버전

    pip install pygame-ce numpy
    python3 skan_pygame.py            전체 화면  (ESC 종료, F 창/전체 화면 전환, G 빛 번짐 끄기/켜기, R 처음부터)
    python3 skan_pygame.py --window   창 모드로 시작
    python3 skan_pygame.py --fps 60   빠른 컴퓨터에서 60fps

트리 계산은 skan.py 를 그대로 쓰고, 화면만 pygame 으로 그립니다.
터미널보다 칸이 촘촘하고, 글자 빛 번짐(glow)과 큰 영어 인사말이 들어갑니다.
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pygame

import skan

COLS, ROWS = 90, 78             # window grid: wide enough for the snowman left of the tree
BG = (14, 18, 34)               # a slightly lifted navy instead of near-black
FPS = 30                        # steady 30 looks smoother than an uneven 40-60 (videos are 30 too)
GLOW_NEAR = 0.70                # tight glow right around bright glyphs
GLOW_FAR = 0.45                 # wide, faint haze
COLOR_SMOOTH = 0.5              # how much of last frame's colour each cell keeps (less flicker)
HOLD_FRAMES = 2                 # an emptied cell keeps fading its glyph this many frames
SOFTEN = 0.10                   # 0 = original colours, higher = paler, pastel-like
TRAIL = 0.45                    # how much of the previous frame lingers (soft motion), 0 = none

KOREAN_FONTS = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/Library/Fonts/NanumGothic.ttf",
    "C:/Windows/Fonts/malgun.ttf",
]


def korean_font(size, bold=False):
    for path in KOREAN_FONTS:
        if os.path.exists(path):
            f = pygame.font.Font(path, size)
            f.bold = bold
            return f
    return pygame.font.SysFont("applesdgothicneo,applegothic,nanumgothic,malgungothic", size, bold=bold)


class GlyphCache:
    """Pre-rendered coloured glyphs, centred in their cell."""

    def __init__(self, font, cell):
        self.font, self.cell, self.cache = font, cell, {}

    def get(self, code, key):
        item = self.cache.get((code, key))
        if item is None:
            rgb = ((key >> 10) * 8 + 4, ((key >> 5) & 31) * 8 + 4, (key & 31) * 8 + 4)
            # soft tone: pull each colour towards its own brightness (less saturated) and lift it
            m = max(rgb)
            rgb = tuple(min(255, int(c * (1 - SOFTEN) + m * SOFTEN * 0.8 + 14)) for c in rgb)
            surf = self.font.render(chr(code), True, rgb)
            ox = (self.cell - surf.get_width()) // 2
            oy = (self.cell - surf.get_height()) // 2
            item = self.cache[(code, key)] = (surf, ox, oy)
        return item


def make_icon():
    """Small Christmas-tree icon: a green triangle, trunk and a gold star."""
    icon = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.polygon(icon, (60, 190, 120), [(32, 10), (8, 52), (56, 52)])
    pygame.draw.polygon(icon, (110, 225, 160), [(32, 10), (20, 32), (44, 32)])
    pygame.draw.rect(icon, (140, 90, 50), (28, 52, 8, 9))
    pygame.draw.circle(icon, (255, 210, 90), (32, 9), 6)
    for x, y, c in ((24, 40, (255, 90, 90)), (40, 44, (120, 170, 255)), (34, 28, (255, 140, 210))):
        pygame.draw.circle(icon, c, (x, y), 3)
    return icon


def _soften(surf, k):
    """Cheap blur: shrink by k and grow back (smoothscale averages neighbours both ways)."""
    w, h = surf.get_size()
    return pygame.transform.smoothscale(pygame.transform.smoothscale(surf, (max(1, w // k), max(1, h // k))), (w, h))


def two_layer_glow(src, W, H):
    """Tight glow + wide haze, both blurred at low resolution and added together."""
    quarter = pygame.transform.smoothscale(pygame.transform.scale(src, (W // 2, H // 2)), (W // 4, H // 4))
    near = _soften(quarter, 2)                                       # tight glow
    far = _soften(pygame.transform.smoothscale(quarter, (W // 12, H // 12)), 2)   # wide haze
    far = pygame.transform.smoothscale(far, (W // 4, H // 4))
    near.fill((int(255 * GLOW_NEAR),) * 3, special_flags=pygame.BLEND_RGB_MULT)
    far.fill((int(255 * GLOW_FAR),) * 3, special_flags=pygame.BLEND_RGB_MULT)
    near.blit(far, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    return pygame.transform.smoothscale(near, (W, H))


def set_mode_vsync(size, flags):
    """Open the window synced to the display refresh (no tearing); fall back if not supported."""
    try:
        return pygame.display.set_mode(size, flags, vsync=1)
    except (pygame.error, TypeError):
        return pygame.display.set_mode(size, flags)


def make_layout(fullscreen):
    """Window or full screen. Rows are fixed so the tree keeps its size; columns fill the width."""
    if fullscreen:
        screen = set_mode_vsync((0, 0), pygame.FULLSCREEN)
    else:
        info = pygame.display.Info()
        cell = max(8, min(16, int(info.current_h * 0.86 / ROWS), int(info.current_w * 0.95 / COLS)))
        screen = set_mode_vsync((COLS * cell, ROWS * cell), 0)
    pygame.mouse.set_visible(not fullscreen)
    W, H = screen.get_size()
    cell = max(6, H // ROWS)
    cols = W // cell
    return dict(
        screen=screen, W=W, H=H, cell=cell, cols=cols,
        ox=(W - cols * cell) // 2, oy=(H - ROWS * cell) // 2,
        back=skan.Backdrop(cols, ROWS),
        glyphs=GlyphCache(korean_font(int(cell * 0.9)), cell),      # a little gap between glyphs
        hud_big=korean_font(max(12, cell * 2), bold=True),
        hud_small=korean_font(max(10, int(cell * 1.4))),
        title=pygame.font.SysFont("avenirnext,helveticaneue,arial", int(cell * 3.6), bold=True),
        layer=pygame.Surface((W, H)),                                # everything that glows, on black
        accum=pygame.Surface((W, H)),                                # layer + fading trail of earlier frames
        small=(max(1, W // 8), max(1, H // 8)),
    )


def main():
    pygame.init()
    pygame.display.set_caption("한글 크리스마스 트리")
    pygame.display.set_icon(make_icon())     # tree icon in the Dock / title bar instead of the default
    skan.DETAIL = 1.15                      # slightly finer grid than the terminal -> a few more points
    D = skan.build()
    fullscreen = "--window" not in sys.argv
    global FPS
    if "--fps" in sys.argv:                 # e.g.  --fps 60  on a fast machine
        FPS = int(sys.argv[sys.argv.index("--fps") + 1])
    L = make_layout(fullscreen)
    timer = pygame.time.Clock()
    anim = 0.0                              # animation time: advances by the frame time, at most 1/15 s
    glow_on = True
    prev_col, prev_on, prev_char, prev_off, hold = None, None, None, None, None
    glow, frame_no = None, 0

    # the tree maths (numpy) runs in a worker thread for the NEXT frame while this frame is drawn
    worker = ThreadPoolExecutor(max_workers=1)

    def compute(clock, lay):
        t = clock % skan.T_LOOP
        return (t,) + skan.render(D, t, lay["cols"], ROWS, lay["back"], clock, draw_msg=False, subcell=True)

    pending = worker.submit(compute, 0.0, L)

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                worker.shutdown(wait=True)
                pygame.quit()
                return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                pending.result()
                anim = 0.0
                L["accum"].fill((0, 0, 0))
                pending = worker.submit(compute, anim, L)
            if e.type == pygame.KEYDOWN and e.key == pygame.K_g:        # glow on/off (faster when off)
                glow_on = not glow_on
            if e.type == pygame.KEYDOWN and e.key == pygame.K_f:        # toggle full screen
                pending.result()
                fullscreen = not fullscreen
                L = make_layout(fullscreen)
                pending = worker.submit(compute, anim, L)

        t, char, col, inf = pending.result()
        if char.shape[1] != L["cols"]:                                   # frame from the old layout
            pending = worker.submit(compute, anim, L)
            continue
        # next frame: step by the real frame time, but never more than 1/15 s,
        # so a hiccup slows the show down for a moment instead of making it jump
        step = min(timer.get_time() / 1000 or 1 / FPS, 1 / 15)
        anim += step
        pending = worker.submit(compute, anim, L)

        # colour of each cell eases from the previous frame (like a slow fade, no flicker)
        on = char > 0
        if prev_col is not None and prev_col.shape == col.shape:
            both = (on & prev_on)[..., None]
            col = np.where(both, col * (1 - COLOR_SMOOTH) + prev_col * COLOR_SMOOTH, col)
            # a cell that just went empty keeps its glyph for up to 2 frames, fading,
            # so cells do not blink on and off while the tree turns
            gone = ~on & prev_on & (hold < HOLD_FRAMES)
            if gone.any():
                char, col = char.copy(), col.copy()
                char[gone] = prev_char[gone]
                col[gone] = prev_col[gone] * 0.7
                offx, offy = inf["off"][0].copy(), inf["off"][1].copy()
                offx[gone], offy[gone] = prev_off[0][gone], prev_off[1][gone]
                inf["off"] = (offx, offy)
            hold = np.where(gone, hold + 1, 0)
            on = char > 0
        else:
            hold = np.zeros(char.shape, np.int8)
        prev_col, prev_on, prev_char, prev_off = col, on, char, inf["off"]

        screen, W, H, cell, layer = L["screen"], L["W"], L["H"], L["cell"], L["layer"]
        ox, oy, glyphs = L["ox"], L["oy"], L["glyphs"]

        # glyph grid -> one batch of blits
        q = np.clip((col * 31.99).astype(np.int32), 0, 31)
        key = q[..., 0] * 1024 + q[..., 1] * 32 + q[..., 2]
        ys, xs = np.nonzero(char > 0)
        codes, keys = char[ys, xs].tolist(), key[ys, xs].tolist()
        # exact pixel position of every glyph (sub-cell), so motion is smooth instead of cell steps
        px = (ox + (xs + inf["off"][0][ys, xs]) * cell).astype(int).tolist()
        py = (oy + (ys + inf["off"][1][ys, xs]) * cell).astype(int).tolist()
        batch = []
        for x, y, c, k in zip(px, py, codes, keys):
            surf, gx, gy = glyphs.get(c, k)
            batch.append((surf, (x + gx, y + gy)))
        layer.fill((0, 0, 0))
        layer.fblits(batch)

        # big greeting, typed out, also glowing
        if t > skan.T_MSG:
            title = L["title"]
            shown = min(len(skan.MESSAGE), int((t - skan.T_MSG) * 10))
            full = title.size(skan.MESSAGE)
            pulse = 1.0 + 0.08 * np.sin(t * 4)
            red = tuple(int(min(255, v * 255 * pulse)) for v in skan.MSG_RED)
            text = title.render(skan.MESSAGE[:shown], True, red)
            tx = (W - full[0]) // 2
            ty = H - full[1] - cell * 3
            pygame.draw.rect(layer, (0, 0, 0), (tx - cell, ty, full[0] + 2 * cell, full[1]))
            layer.blit(text, (tx, ty))

        # glow: blurred copy of the bright layer added on top
        # soft motion: keep a fading copy of earlier frames under the new one
        accum = L["accum"]
        dt = max(timer.get_time(), 1) / 1000                          # same trail length at any fps
        fade = int(255 * TRAIL ** (dt * 60))
        accum.fill((fade, fade, fade), special_flags=pygame.BLEND_RGB_MULT)
        accum.blit(layer, (0, 0), special_flags=pygame.BLEND_RGB_MAX)

        screen.fill(BG)
        screen.blit(accum, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        if glow_on:
            # the blur is soft anyway, so it is refreshed only every other frame (saves ~40% time)
            frame_no += 1
            if glow is None or frame_no % 2 == 0 or glow.get_size() != (W, H):
                glow = two_layer_glow(accum, W, H)
            screen.blit(glow, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # HUD
        hud_big, hud_small = L["hud_big"], L["hud_small"]
        screen.blit(hud_big.render("한글 트리", True, (225, 228, 235)), (cell * 2, cell * 2))
        y = cell * 2 + hud_big.get_height()
        for line in (f"회전 {inf['rotation']:.1f}도", f"글자 {inf['letters']:,}",
                     f"{timer.get_fps():.0f} fps"):
            screen.blit(hud_small.render(line, True, (140, 148, 160)), (cell * 2, y))
            y += hud_small.get_height()
        tsurf = hud_small.render(f"{t:04.1f}초", True, (230, 170, 80))
        screen.blit(tsurf, (W - tsurf.get_width() - cell * 2, cell * 2))

        pygame.display.flip()
        timer.tick(FPS)


if __name__ == "__main__":
    if sys.version_info < (3, 8):
        sys.exit("Python 3.8 이상이 필요합니다.")
    main()
