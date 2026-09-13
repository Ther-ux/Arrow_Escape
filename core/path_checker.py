from typing import AbstractSet

from core.arrow import Arrow

Position = tuple[int, int]


def is_path_clear(
    arrow: Arrow,
    occupied: AbstractSet[Position],
    rows: int,
    cols: int,
) -> bool:
    """Return whether an arrow can travel forward to the board edge.

    Only cells strictly ahead of ``arrow`` on its row or column are checked.
    The input occupancy set is read but never changed; the caller owns game
    state updates such as removing an arrow after a successful move.
    """
    if isinstance(rows, bool) or not isinstance(rows, int) or rows <= 0:
        raise ValueError("rows must be a positive integer")
    if isinstance(cols, bool) or not isinstance(cols, int) or cols <= 0:
        raise ValueError("cols must be a positive integer")
    if not (0 <= arrow.row < rows and 0 <= arrow.col < cols):
        raise ValueError("arrow position must be inside the board")

    row_step, col_step = arrow.direction.delta
    row = arrow.row + row_step
    col = arrow.col + col_step

    while 0 <= row < rows and 0 <= col < cols:
        if (row, col) in occupied:
            return False
        row += row_step
        col += col_step

    return True
