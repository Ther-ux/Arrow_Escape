"""Live turning/recoil demo: python -m tools.rope_demo.

Use --frames-dir PATH for a deterministic 30 fps capture, without waiting.
"""

import argparse
import math
from pathlib import Path

import pygame

from ui.rope import Rope, rounded_path
from ui.rope_renderer import draw_rope


def head_at(t):
    if t < 0.8:
        return (220 + 160 * t, 160)
    if t < 1.6:
        angle = (t - 0.8) / 0.8 * math.pi / 2
        return (348 + 80 * math.sin(angle), 240 - 80 * math.cos(angle))
    return (428, 240 + 120 * min(0.8, t - 1.6))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames-dir", type=Path)
    args = parser.parse_args()
    pygame.init()
    surface = pygame.display.set_mode((720, 520))
    pygame.display.set_caption("Arrow Escape / flexible rope demo")
    font = pygame.font.Font(None, 26)
    clock = pygame.time.Clock()

    def make_rope():
        return Rope(rounded_path([(220, 160), (140, 160), (140, 300), (70, 300)]))

    rope = make_rope()
    t, frame, running = 0.0, 0, True
    if args.frames_dir:
        args.frames_dir.mkdir(parents=True, exist_ok=True)
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
            if not running:
                break
            surface.fill((13, 18, 36))
            stage = "PULL" if t < 0.8 else "TURN" if t < 1.6 else "FOLLOW" if t < 2.4 else "RECOIL / SETTLE"
            surface.blit(font.render(f"VERLET ROPE / {stage}", True, (234, 241, 252)), (36, 30))
            surface.blit(font.render("Pinned head / free tail / length constraints / smooth curve", True,
                                     (145, 162, 186)), (36, 64))
            draw_rope(surface, rope.positions,
                      (head_at(t + 0.001)[0] - head_at(t)[0], head_at(t + 0.001)[1] - head_at(t)[1])
                      if t < 2.4 else (0, 1), (94, 224, 163), width=4)
            surface.blit(font.render(f"t = {t:.2f}s    /    Esc to exit", True, (145, 162, 186)), (36, 472))
            pygame.display.flip()
            if args.frames_dir:
                pygame.image.save(surface, str(args.frames_dir / f"frame-{frame:03d}.png"))
                frame += 1
                if frame >= 121:
                    break
                dt = 1 / 30
            else:
                dt = min(clock.tick(60) / 1000, 0.05)
            rope.advance(dt, head_at)
            t += dt
            if t >= 4.5 and not args.frames_dir:
                t, rope = 0.0, make_rope()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
