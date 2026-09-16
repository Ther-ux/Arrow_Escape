"""Antialiased rope curves and a head oriented along travel direction."""

import math

import pygame

from ui.rope import Point, smooth_curve


def draw_rope(surface: pygame.Surface, nodes: list[Point], heading: Point,
              color: tuple[int, int, int], alpha: int = 255, width: int = 3) -> None:
    points = smooth_curve(nodes)
    if len(points) < 2:
        return
    dx, dy = heading
    magnitude = math.hypot(dx, dy)
    dx, dy = (dx / magnitude, dy / magnitude) if magnitude > 1e-8 else (1, 0)
    min_x, min_y = min(x for x, _ in points), min(y for _, y in points)
    max_x, max_y = max(x for x, _ in points), max(y for _, y in points)
    bounds = pygame.Rect(math.floor(min_x) - 24, math.floor(min_y) - 24,
                         math.ceil(max_x - min_x) + 49, math.ceil(max_y - min_y) + 49)
    bounds = bounds.clip(surface.get_rect())
    if not bounds.width or not bounds.height:
        return
    # Draw at 2x and downsample; this smooths both curve edges and arrow tips.
    scale = 2
    size = (bounds.width * scale, bounds.height * scale)
    local = [((x - bounds.x) * scale, (y - bounds.y) * scale) for x, y in points]
    glow = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.lines(glow, (*color, min(alpha, 28)), False, local, (width + 5) * scale)
    layer = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.lines(layer, (*color, alpha), False, local, width * scale)
    pygame.draw.circle(layer, (*color, alpha), local[-1], width * scale // 2)
    tip = local[0]
    neck = (tip[0] - dx * 22 * scale, tip[1] - dy * 22 * scale)
    head = [tip, (neck[0] - dy * 10 * scale, neck[1] + dx * 10 * scale),
            (neck[0] + dy * 10 * scale, neck[1] - dx * 10 * scale)]
    pygame.draw.polygon(layer, (*color, alpha), head)
    surface.blit(pygame.transform.smoothscale(glow, bounds.size), bounds.topleft)
    surface.blit(pygame.transform.smoothscale(layer, bounds.size), bounds.topleft)
