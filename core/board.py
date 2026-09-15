from collections.abc import Iterable

from core.arrow import Arrow


class Board:
    """Grid occupancy, without any dependency on drawing coordinates."""

    def __init__(self, rows: int, cols: int, arrows: Iterable[Arrow]):
        if rows <= 0 or cols <= 0:
            raise ValueError("board dimensions must be positive")
        self.rows, self.cols = rows, cols
        self.arrows: dict[tuple[int, int], Arrow] = {}
        for arrow in arrows:
            position = (arrow.row, arrow.col)
            if not (0 <= arrow.row < rows and 0 <= arrow.col < cols):
                raise ValueError("arrow must be inside the board")
            if position in self.arrows:
                raise ValueError("two arrows cannot occupy the same cell")
            self.arrows[position] = arrow

    @property
    def occupied(self) -> set[tuple[int, int]]:
        return set(self.arrows)

    def arrow_at(self, row: int, col: int) -> Arrow | None:
        return self.arrows.get((row, col))
