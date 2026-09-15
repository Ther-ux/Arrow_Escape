from dataclasses import dataclass
from enum import Enum

from core.arrow import Arrow
from core.board import Board
from core.path_checker import is_path_clear
from data.levels import LEVELS, Level


class Screen(str, Enum):
    HOME = "home"
    PLAYING = "playing"
    SUCCESS = "success"
    FAILED = "failed"


class Move(str, Enum):
    FLYING = "flying"
    COLLISION = "collision"
    IGNORED = "ignored"


@dataclass
class Animation:
    arrow: Arrow
    kind: Move
    elapsed: float = 0.0

    @property
    def duration(self) -> float:
        return 0.45 if self.kind == Move.FLYING else 0.32

    @property
    def progress(self) -> float:
        return min(1.0, self.elapsed / self.duration)


class Game:
    """Gameplay and animation timing; no Pygame calls or blocking waits."""

    def __init__(self, levels: tuple[Level, ...] = LEVELS):
        if not levels:
            raise ValueError("at least one level is required")
        self.levels = levels
        self.level_index = 0
        self.screen = Screen.HOME
        self.animations: dict[tuple[int, int], Animation] = {}
        self.elapsed = 0.0
        self._load()

    @property
    def level(self) -> Level:
        return self.levels[self.level_index]

    @property
    def final_level(self) -> bool:
        return self.level_index == len(self.levels) - 1

    def _load(self) -> None:
        self.board = Board(self.level.rows, self.level.cols, self.level.arrows)
        self.mistakes_left = self.level.max_mistakes
        self.animations.clear()
        self.elapsed = 0.0

    def start(self) -> None:
        self.level_index = 0
        self.restart()

    def restart(self) -> None:
        self._load()
        self.screen = Screen.PLAYING

    def home(self) -> None:
        self.animations.clear()
        self.screen = Screen.HOME

    def next_level(self) -> bool:
        if self.screen != Screen.SUCCESS or self.final_level:
            return False
        self.level_index += 1
        self.restart()
        return True

    def click(self, row: int, col: int) -> Move:
        position = (row, col)
        if self.screen != Screen.PLAYING or self.mistakes_left == 0:
            return Move.IGNORED
        arrow = self.board.arrow_at(row, col)
        if arrow is None or position in self.animations:
            return Move.IGNORED
        if is_path_clear(arrow, self.board.occupied, self.board.rows, self.board.cols):
            del self.board.arrows[position]
            kind = Move.FLYING
        else:
            self.mistakes_left -= 1
            kind = Move.COLLISION
        self.animations[position] = Animation(arrow, kind)
        return kind

    def update(self, dt: float) -> None:
        if dt < 0:
            raise ValueError("dt cannot be negative")
        if self.screen != Screen.PLAYING:
            return
        self.elapsed += dt
        for position, animation in list(self.animations.items()):
            animation.elapsed += dt
            if animation.progress >= 1:
                del self.animations[position]
        # Let the final fly-out/collision finish before showing the result.
        if not self.animations:
            if self.mistakes_left == 0:
                self.screen = Screen.FAILED
            elif not self.board.arrows:
                self.screen = Screen.SUCCESS
