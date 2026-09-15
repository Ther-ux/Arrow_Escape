from dataclasses import dataclass

from core.arrow import Arrow, Direction


@dataclass(frozen=True)
class Level:
    name: str
    rows: int
    cols: int
    arrows: tuple[Arrow, ...]
    max_mistakes: int = 3


U, D, L, R = Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT

# Small original MVP layouts. Formal difficulty tuning belongs to M3.
LEVELS = (
    Level("初见出口", 5, 5, (
        Arrow(0, 1, U), Arrow(1, 1, U), Arrow(2, 0, L),
        Arrow(2, 2, R), Arrow(2, 4, U), Arrow(4, 3, D),
    )),
    Level("逐步释放", 5, 5, (
        Arrow(0, 0, L), Arrow(0, 2, L), Arrow(0, 4, U),
        Arrow(2, 0, U), Arrow(2, 2, U), Arrow(2, 4, R),
        Arrow(4, 0, L), Arrow(4, 2, D), Arrow(4, 4, L),
    )),
    Level("交错方向", 6, 6, (
        Arrow(0, 1, U), Arrow(0, 4, R), Arrow(1, 1, U),
        Arrow(1, 4, U), Arrow(2, 0, L), Arrow(2, 2, L),
        Arrow(2, 4, U), Arrow(3, 1, D), Arrow(3, 3, R),
        Arrow(3, 5, R), Arrow(5, 1, D), Arrow(5, 4, L),
    )),
)
