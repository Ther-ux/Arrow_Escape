from dataclasses import dataclass
from enum import Enum


class Direction(str, Enum):
    """The four orthogonal directions an arrow can travel."""

    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"

    @property
    def delta(self) -> tuple[int, int]:
        """Return the row and column offset for one step in this direction."""
        return {
            Direction.UP: (-1, 0),
            Direction.DOWN: (1, 0),
            Direction.LEFT: (0, -1),
            Direction.RIGHT: (0, 1),
        }[self]


@dataclass(frozen=True, slots=True)
class Arrow:
    """An arrow's grid position and travel direction."""

    row: int
    col: int
    direction: Direction

    def __post_init__(self) -> None:
        if isinstance(self.row, bool) or not isinstance(self.row, int):
            raise TypeError("row must be an integer")
        if isinstance(self.col, bool) or not isinstance(self.col, int):
            raise TypeError("col must be an integer")
        if not isinstance(self.direction, Direction):
            raise TypeError("direction must be a Direction")
