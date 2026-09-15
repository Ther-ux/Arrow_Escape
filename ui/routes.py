"""Plan decorative tails together so their resting curves do not overlap."""

from collections.abc import Sequence

from core.arrow import Arrow
from ui.rope import Point, rounded_path


def plan_routes(arrows: Sequence[Arrow], rows: int, cols: int, cell: float,
                origin: Point) -> dict[tuple[int, int], list[Point]]:
    spacing = cell / 4
    anchors = {(a.row, a.col): (a.row * 4 + 2, a.col * 4 + 2) for a in arrows}
    head_masks = {}
    departure = set()
    for arrow in arrows:
        row, col = anchors[(arrow.row, arrow.col)]
        head_masks[(arrow.row, arrow.col)] = {(row + r, col + c)
                                            for r in (-1, 0, 1) for c in (-1, 0, 1)}
        dy, dx = arrow.direction.delta
        r, c = row + dy, col + dx
        while 0 < r < rows * 4 and 0 < c < cols * 4:
            departure.add((r, c))
            r, c = r + dy, c + dx
    occupied, result = set(), {}
    for arrow in sorted(arrows, key=lambda a: (a.row, a.col)):
        position = (arrow.row, arrow.col)
        start = anchors[position]
        blocked_heads = set().union(*(mask for p, mask in head_masks.items() if p != position))
        dy, dx = arrow.direction.delta
        back, left, right = (-dy, -dx), (-dx, dy), (dx, -dy)
        chain, heading, run = [start], back, 0
        for _ in range(14):
            # Small bends in a separate lane, rather than sharing long grid edges.
            side = left if (arrow.row + arrow.col) % 2 else right
            candidates = [heading, side, (-side[0], -side[1]), back]
            if run >= 3:
                candidates = [side, (-side[0], -side[1]), heading, back]
            if len(chain) == 1:
                candidates = [back]
            chosen = None
            for step in candidates:
                point = (chain[-1][0] + step[0], chain[-1][1] + step[1])
                if not (0 < point[0] < rows * 4 and 0 < point[1] < cols * 4):
                    continue
                if point in chain or point in occupied or point in blocked_heads:
                    continue
                if (point in head_masks[position] and
                        (point[0] - start[0]) * dy + (point[1] - start[1]) * dx > 0):
                    continue
                # Keep straight departure corridors free of other resting tails.
                if point in departure and point not in head_masks[position]:
                    continue
                chosen = point, step
                break
            if chosen is None:
                break
            point, step = chosen
            run = run + 1 if step == heading else 1
            heading = step
            chain.append(point)
        occupied.update(chain)
        center = (origin[0] + start[1] * spacing, origin[1] + start[0] * spacing)
        points = [(center[0] + dx * 18, center[1] + dy * 18)]
        points.extend((origin[0] + c * spacing, origin[1] + r * spacing) for r, c in chain)
        result[position] = rounded_path(points, radius=spacing * 0.4)
    return result
