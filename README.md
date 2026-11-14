# ChrismasTrees

A rotating 3D Christmas tree drawn entirely with Hangul characters.

Leaves are written with `ㆍ ㅅ 소 솔 숲`, the gold tinsel spiral with `반짝`, presents with `선물`,
lights with `빛`, the star with `별` and the snow with `눈`.

## The show (30 s loop)

1. The trunk grows up and snow starts spreading over the ground.
2. A glowing ribbon winds up the tree five times; the foliage appears behind it and a gold `반짝` spiral is left in its place.
3. Baubles, fairy lights, the star and presents pop in, then **MERRY CHRISTMAS 2026** is typed out.
4. After it has snowed for a while, snow settles on the branches.

## Two versions

| File | Runs in | Notes |
|---|---|---|
| `skan_pygame.py` | pygame window | Full screen, soft glow, smooth sub-cell motion, fading trails |
| `skan.py` | Terminal | 24-bit colour ANSI output; best in iTerm2 or another GPU terminal |

`skan_pygame.py` imports `skan.py` for the scene, so keep both files together.

## Run

```bash
pip install -r requirements.txt
python3 skan_pygame.py              # full screen
python3 skan_pygame.py --window     # windowed
python3 skan_pygame.py --fps 60     # on a fast machine
python3 skan.py                     # terminal version (make the window about 100x65)
```

Keys in the pygame version: `F` window / full screen, `G` glow on/off, `R` restart, `Esc` quit.

Run the terminal version in a real terminal. IDE run consoles (for example PyCharm's Run panel) cannot
handle cursor-control codes, so the frames pile up and the IDE freezes; the script refuses to start there.

## How it works

- The scene is a point cloud (needles, ribbon, garland, baubles, lights, presents, snow) rotated and projected every frame.
- Each screen cell keeps the nearest point. Hangul is two terminal columns wide, so one screen cell = two columns.
- Foliage uses four brightness steps; inside a step every cell keeps a fixed glyph and tone, so the tree does not flicker while it turns.
- The pygame version draws each glyph at its exact sub-cell position, eases cell colours between frames, keeps a fading trail and adds a two-layer glow.

The flicker-free glyph choice and the two-layer glow were inspired by the approach in
[JIN2's BLACK-HOLE ASCII art](https://github.com/JIN2-ASCII/-JIN2-ASCII/tree/main/BLACK-HOLE) (@jin_22ee). No code was copied.
