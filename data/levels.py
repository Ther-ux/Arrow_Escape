import random
from dataclasses import dataclass
from enum import Enum

from core.arrow import Arrow, Direction
from core.path_checker import is_path_clear


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class GameMode(str, Enum):
    NORMAL = "normal"
    ENDLESS = "endless"


@dataclass(frozen=True)
class Level:
    name: str
    rows: int
    cols: int
    arrows: tuple[Arrow, ...]
    max_mistakes: int = 3


U, D, L, R = Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT

# The original three layouts are retained as normal-mode medium difficulty.
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


def generate_solvable_level(name: str, rows: int, cols: int, arrow_count: int,
                            rng: random.Random | None = None) -> Level:
    """Generate a random layout with a guaranteed legal removal sequence.

    Arrows are added in reverse solution order. Every new arrow is required to
    have a clear path through the arrows already placed, so removing the final
    list in reverse order is always a valid solution.
    """
    if arrow_count <= 0 or arrow_count > rows * cols:
        raise ValueError("arrow_count must fit on the board")
    source = rng or random.Random()
    directions = tuple(Direction)
    for _ in range(200):
        occupied: set[tuple[int, int]] = set()
        arrows: list[Arrow] = []
        for _ in range(arrow_count):
            candidates: list[Arrow] = []
            positions = [(row, col) for row in range(rows) for col in range(cols)
                         if (row, col) not in occupied]
            source.shuffle(positions)
            for row, col in positions:
                shuffled = list(directions)
                source.shuffle(shuffled)
                for direction in shuffled:
                    arrow = Arrow(row, col, direction)
                    if is_path_clear(arrow, occupied, rows, cols):
                        candidates.append(arrow)
            if not candidates:
                break
            selected = source.choice(candidates)
            arrows.append(selected)
            occupied.add((selected.row, selected.col))
        if len(arrows) == arrow_count:
            return Level(name, rows, cols, tuple(arrows))
    raise RuntimeError("could not generate a solvable level")


_DIFFICULTY_COUNTS = {
    Difficulty.EASY: (4, 6, 8),
    Difficulty.MEDIUM: (6, 9, 12),
    Difficulty.HARD: (8, 12, 16),
}


def levels_for_difficulty(difficulty: Difficulty) -> tuple[Level, ...]:
    """Return the three normal-mode levels for a selected difficulty."""
    if difficulty == Difficulty.MEDIUM:
        return LEVELS
    seed = {Difficulty.EASY: 2401, Difficulty.HARD: 2403}[difficulty]
    rng = random.Random(seed)
    rows, cols = (5, 5) if difficulty == Difficulty.EASY else (7, 7)
    label = "简单" if difficulty == Difficulty.EASY else "困难"
    return tuple(generate_solvable_level(
        f"{label}关卡 {index + 1}", rows, cols, count, rng)
        for index, count in enumerate(_DIFFICULTY_COUNTS[difficulty]))


def generate_endless_level(level_number: int,
                          rng: random.Random | None = None) -> Level:
    """Generate one random hard level for endless mode."""
    return generate_solvable_level(
        f"无尽关卡 {level_number}", 7, 7, 16, rng)


LEVELS_BY_DIFFICULTY = {
    difficulty: levels_for_difficulty(difficulty)
    for difficulty in Difficulty
}
