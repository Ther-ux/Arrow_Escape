from collections.abc import Callable
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
    visual_duration: float | None = None

    @property
    def duration(self) -> float:
        return self.visual_duration or (0.45 if self.kind == Move.FLYING else 0.32)

    @property
    def progress(self) -> float:
        return min(1.0, self.elapsed / self.duration)


@dataclass(frozen=True)
class Action:
    position: tuple[int, int]
    arrow: Arrow
    kind: Move


class Game:
    """Gameplay and animation timing; no Pygame calls or blocking waits."""

    HINTS_PER_GAME = 3

    def __init__(self, levels: tuple[Level, ...] = LEVELS):
        if not levels:
            raise ValueError("at least one level is required")
        self.levels = tuple(levels)
        self.level_index = 0
        self.screen = Screen.HOME
        self.animations: dict[tuple[int, int], Animation] = {}
        self.actions: list[Action] = []
        self.elapsed = 0.0
        self.hints_left = self.HINTS_PER_GAME
        self.hinted_position: tuple[int, int] | None = None
        self.endless = False
        self.level_factory: Callable[[int], Level] | None = None
        self.endless_level_number = 1
        self._load()

    @property
    def level(self) -> Level:
        return self.levels[self.level_index]

    @property
    def final_level(self) -> bool:
        return not self.endless and self.level_index == len(self.levels) - 1

    def _load(self) -> None:
        self.board = Board(self.level.rows, self.level.cols, self.level.arrows)
        self.mistakes_left = self.level.max_mistakes
        self.animations.clear()
        self.actions.clear()
        self.hinted_position = None
        self.elapsed = 0.0

    def start(self, levels: tuple[Level, ...] | None = None, *, endless: bool = False,
              level_factory: Callable[[int], Level] | None = None,
              endless_level_number: int = 1) -> None:
        if levels is not None:
            if not levels:
                raise ValueError("at least one level is required")
            self.levels = tuple(levels)
        if endless and level_factory is None:
            raise ValueError("endless mode requires a level factory")
        if endless_level_number < 1:
            raise ValueError("endless level number must be positive")
        self.endless = endless
        self.level_factory = level_factory
        self.endless_level_number = endless_level_number if endless else 1
        self.level_index = 0
        self.hints_left = self.HINTS_PER_GAME
        self.restart()

    def restart(self) -> None:
        self._load()
        self.screen = Screen.PLAYING

    def home(self) -> None:
        self.animations.clear()
        self.hinted_position = None
        self.screen = Screen.HOME

    def next_level(self) -> bool:
        if self.screen != Screen.SUCCESS:
            return False
        if self.endless:
            if self.level_factory is None:
                return False
            self.endless_level_number += 1
            self.levels = (*self.levels, self.level_factory(self.endless_level_number))
        elif self.final_level:
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
        if position == self.hinted_position:
            self.hinted_position = None
        if is_path_clear(arrow, self.board.occupied, self.board.rows, self.board.cols):
            del self.board.arrows[position]
            kind = Move.FLYING
        else:
            self.mistakes_left -= 1
            kind = Move.COLLISION
        self.animations[position] = Animation(arrow, kind)
        self.actions.append(Action(position, arrow, kind))
        return kind

    def hint(self) -> tuple[int, int] | None:
        """Highlight one currently clear arrow without changing the board."""
        if self.screen != Screen.PLAYING or self.hints_left <= 0:
            return None
        position = self.next_clear_position()
        if position is not None:
            self.hints_left -= 1
            self.hinted_position = position
            return position
        return None

    def next_clear_position(self) -> tuple[int, int] | None:
        """Return a currently legal arrow position, without changing state."""
        for position, arrow in self.board.arrows.items():
            if is_path_clear(arrow, self.board.occupied, self.board.rows, self.board.cols):
                return position
        return None

    def ai_step(self) -> tuple[int, int] | None:
        """Release one legal arrow for the automatic solver."""
        if self.screen != Screen.PLAYING or self.animations:
            return None
        position = self.next_clear_position()
        if position is None:
            return None
        self.click(*position)
        return position

    @property
    def can_undo(self) -> bool:
        return bool(self.actions)

    def undo(self) -> bool:
        """Undo the most recent accepted click and cancel its animation."""
        if self.screen not in (Screen.PLAYING, Screen.SUCCESS, Screen.FAILED) or not self.actions:
            return False
        action = self.actions.pop()
        self.animations.pop(action.position, None)
        if action.kind == Move.FLYING:
            self.board.arrows[action.position] = action.arrow
        elif action.kind == Move.COLLISION:
            self.mistakes_left = min(self.level.max_mistakes, self.mistakes_left + 1)
        self.hinted_position = None
        self.screen = Screen.PLAYING
        return True

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
