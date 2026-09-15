"""Verlet rope simulation and curve sampling, independent of Pygame."""

import math
from collections.abc import Callable, Sequence

Point = tuple[float, float]


def distance(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def nearest_on_path(point: Point, path: Sequence[Point]) -> Point:
    best, squared_distance = path[0], float("inf")
    for a, b in zip(path, path[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy)
                          / max(dx * dx + dy * dy, 1e-12)))
        candidate = (a[0] + dx * t, a[1] + dy * t)
        d = (point[0] - candidate[0]) ** 2 + (point[1] - candidate[1]) ** 2
        if d < squared_distance:
            best, squared_distance = candidate, d
    return best


def rounded_path(points: Sequence[Point], radius: float = 20) -> list[Point]:
    """Round layout corners with quadratic curves before rope resampling."""
    result = [points[0]]
    for before, corner, after in zip(points, points[1:], points[2:]):
        incoming, outgoing = distance(before, corner), distance(corner, after)
        if min(incoming, outgoing) < 1e-8:
            continue
        cut = min(radius, incoming * 0.35, outgoing * 0.35)
        entry = tuple(corner[i] + (before[i] - corner[i]) * cut / incoming for i in range(2))
        exit_point = tuple(corner[i] + (after[i] - corner[i]) * cut / outgoing for i in range(2))
        result.append(entry)
        for step in range(1, 9):
            t = step / 8
            result.append(tuple((1 - t) ** 2 * entry[i] + 2 * (1 - t) * t * corner[i]
                                + t * t * exit_point[i] for i in range(2)))
    result.append(points[-1])
    return result


def resample(points: Sequence[Point], spacing: float = 10) -> list[Point]:
    """Equally space nodes by arc length, retaining both endpoints."""
    if len(points) < 2 or spacing <= 0:
        raise ValueError("a rope needs two points and positive spacing")
    lengths = [distance(a, b) for a, b in zip(points, points[1:])]
    total = sum(lengths)
    if total < 1e-8:
        raise ValueError("a rope cannot have zero length")
    count = max(1, math.ceil(total / spacing))
    result, segment, traversed = [tuple(points[0])], 0, 0.0
    for index in range(1, count):
        target = total * index / count
        while segment < len(lengths) - 1 and traversed + lengths[segment] < target:
            traversed += lengths[segment]
            segment += 1
        t = (target - traversed) / max(lengths[segment], 1e-8)
        a, b = points[segment], points[segment + 1]
        result.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    result.append(tuple(points[-1]))
    return result


def smooth_curve(points: Sequence[Point], samples: int = 5) -> list[Point]:
    """Catmull–Rom interpolation; render samples, never the constraint polygon."""
    if samples < 1:
        raise ValueError("samples must be positive")
    if len(points) < 2:
        return list(points)
    result = [tuple(points[0])]
    for i in range(len(points) - 1):
        p1, p2 = points[i], points[i + 1]
        p0 = points[i - 1] if i else tuple(2 * p1[j] - p2[j] for j in range(2))
        p3 = points[i + 2] if i + 2 < len(points) else tuple(2 * p2[j] - p1[j] for j in range(2))
        for step in range(1, samples + 1):
            t = step / samples
            result.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t
                                + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3)
                                for j in range(2)))
    return result


class Rope:
    """A pinned moving head and free inertial tail with distance constraints.

    The head trajectory is sampled at a fixed 240 Hz so turn/acceleration
    impulses are consistent across render frame rates. Finite constraint
    iterations permit slight elastic stretch. Strong damping and a soft
    historical-path guide keep the tail controlled instead of whipping.
    """

    STEP = 1 / 240

    def __init__(self, points: Sequence[Point]):
        self.positions = resample(points)
        self.previous = list(self.positions)
        self.lengths = [distance(a, b) for a, b in zip(self.positions, self.positions[1:])]
        self.length = sum(self.lengths)
        self.time = 0.0
        self.accumulator = 0.0
        self.trail = list(reversed(self.positions))

    def _guide_targets(self, head: Point) -> list[Point]:
        if distance(self.trail[-1], head) > 1e-8:
            self.trail.append(head)
        # A single backward walk samples the stored path by each node's
        # distance behind the head. This is a soft guide, not a rigid offset.
        segment, traversed = len(self.trail) - 1, 0.0
        targets, target_distance = [head], 0.0
        for rest in self.lengths:
            target_distance += rest
            while segment > 1:
                length = distance(self.trail[segment], self.trail[segment - 1])
                if traversed + length >= target_distance:
                    break
                traversed += length
                segment -= 1
            a, b = self.trail[segment], self.trail[segment - 1]
            t = min(1.0, (target_distance - traversed) / max(1e-8, distance(a, b)))
            targets.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        if segment > 8:
            del self.trail[:segment - 8]
        return targets

    def advance(self, dt: float, head_at: Callable[[float], Point]) -> None:
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("dt must be finite and nonnegative")
        self.accumulator += dt
        while self.accumulator + 1e-10 >= self.STEP:
            self.time += self.STEP
            self._step(head_at(self.time))
            self.accumulator -= self.STEP

    def _step(self, head: Point) -> None:
        targets = self._guide_targets(head)
        for i in range(1, len(self.positions)):
            x, y = self.positions[i]
            old_x, old_y = self.previous[i]
            self.previous[i] = (x, y)
            predicted = (x + (x - old_x) * 0.96, y + (y - old_y) * 0.96)
            guidance = 0.10 / (1 + i * 0.12)
            self.positions[i] = tuple(predicted[j] + (targets[i][j] - predicted[j]) * guidance
                                      for j in range(2))
        self.positions[0] = head
        for _ in range(18):
            for i, rest in enumerate(self.lengths):
                a, b = self.positions[i], self.positions[i + 1]
                dx, dy = b[0] - a[0], b[1] - a[1]
                length = math.hypot(dx, dy)
                if length < 1e-8:
                    continue
                correction = (length - rest) / length * 0.95
                if i == 0:
                    self.positions[1] = (b[0] - dx * correction, b[1] - dy * correction)
                else:
                    self.positions[i] = (a[0] + dx * correction * 0.5, a[1] + dy * correction * 0.5)
                    self.positions[i + 1] = (b[0] - dx * correction * 0.5, b[1] - dy * correction * 0.5)
        # Keep elastic deviations small: the prior path remains a corridor,
        # while Verlet inertia supplies subtle lag and recoil inside it.
        for i in range(1, len(self.positions)):
            point = self.positions[i]
            target = nearest_on_path(point, self.trail)
            offset = distance(target, point)
            if offset > 4:
                self.positions[i] = tuple(target[j] + (point[j] - target[j]) * 4 / offset
                                          for j in range(2))
