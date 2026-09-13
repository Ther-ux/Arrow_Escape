import pytest

from core.arrow import Arrow, Direction
from core.path_checker import is_path_clear


BOARD_SIZE = 5


@pytest.mark.parametrize(
    "direction",
    [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT],
)
def test_clear_path_in_each_direction(direction):
    arrow = Arrow(row=2, col=2, direction=direction)

    assert is_path_clear(arrow, {(2, 2)}, BOARD_SIZE, BOARD_SIZE)


@pytest.mark.parametrize(
    ("direction", "blocker"),
    [
        (Direction.UP, (1, 2)),
        (Direction.DOWN, (3, 2)),
        (Direction.LEFT, (2, 1)),
        (Direction.RIGHT, (2, 3)),
    ],
)
def test_immediately_adjacent_arrow_blocks(direction, blocker):
    arrow = Arrow(row=2, col=2, direction=direction)

    assert not is_path_clear(arrow, {(2, 2), blocker}, BOARD_SIZE, BOARD_SIZE)


@pytest.mark.parametrize(
    ("direction", "blocker"),
    [
        (Direction.UP, (0, 2)),
        (Direction.DOWN, (4, 2)),
        (Direction.LEFT, (2, 0)),
        (Direction.RIGHT, (2, 4)),
    ],
)
def test_distant_arrow_blocks(direction, blocker):
    arrow = Arrow(row=2, col=2, direction=direction)

    assert not is_path_clear(arrow, {(2, 2), blocker}, BOARD_SIZE, BOARD_SIZE)


@pytest.mark.parametrize(
    ("arrow", "rows", "cols"),
    [
        (Arrow(0, 2, Direction.UP), 5, 5),
        (Arrow(4, 2, Direction.DOWN), 5, 5),
        (Arrow(2, 0, Direction.LEFT), 5, 5),
        (Arrow(2, 4, Direction.RIGHT), 5, 5),
    ],
)
def test_arrow_at_outward_edge_has_clear_path(arrow, rows, cols):
    occupied = {(arrow.row, arrow.col)}

    assert is_path_clear(arrow, occupied, rows, cols)


@pytest.mark.parametrize(
    "direction",
    [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT],
)
def test_arrow_off_the_ray_does_not_block(direction):
    arrow = Arrow(row=2, col=2, direction=direction)

    assert is_path_clear(arrow, {(2, 2), (0, 4)}, BOARD_SIZE, BOARD_SIZE)


@pytest.mark.parametrize(
    ("direction", "behind"),
    [
        (Direction.UP, (3, 2)),
        (Direction.DOWN, (1, 2)),
        (Direction.LEFT, (2, 3)),
        (Direction.RIGHT, (2, 1)),
    ],
)
def test_arrow_behind_does_not_block(direction, behind):
    arrow = Arrow(row=2, col=2, direction=direction)

    assert is_path_clear(arrow, {(2, 2), behind}, BOARD_SIZE, BOARD_SIZE)


def test_removing_blocker_opens_the_path_without_mutating_occupancy():
    arrow = Arrow(row=1, col=0, direction=Direction.RIGHT)
    blocker_position = (1, 2)
    occupied = {(1, 0), blocker_position}

    assert not is_path_clear(arrow, occupied, 4, 4)

    after_removal = occupied - {blocker_position}
    assert is_path_clear(arrow, after_removal, 4, 4)
    assert occupied == {(1, 0), blocker_position}


@pytest.mark.parametrize(
    ("rows", "cols"),
    [(0, 5), (5, 0), (-1, 5), (5, -1)],
)
def test_board_dimensions_must_be_positive(rows, cols):
    arrow = Arrow(row=0, col=0, direction=Direction.RIGHT)

    with pytest.raises(ValueError):
        is_path_clear(arrow, set(), rows, cols)


@pytest.mark.parametrize(
    ("arrow", "rows", "cols"),
    [
        (Arrow(-1, 2, Direction.UP), 5, 5),
        (Arrow(5, 2, Direction.DOWN), 5, 5),
        (Arrow(2, -1, Direction.LEFT), 5, 5),
        (Arrow(2, 5, Direction.RIGHT), 5, 5),
    ],
)
def test_arrow_must_be_inside_board(arrow, rows, cols):
    with pytest.raises(ValueError):
        is_path_clear(arrow, set(), rows, cols)


def test_arrow_model_is_immutable():
    arrow = Arrow(row=1, col=2, direction=Direction.LEFT)

    with pytest.raises(AttributeError):
        arrow.row = 3
