import pytest

from core.arrow import Arrow, Direction
from core.board import Board
from core.game import Game, Move, Screen
from data.levels import (Difficulty, LEVELS, LEVELS_BY_DIFFICULTY, Level,
                         generate_endless_level)


@pytest.fixture
def game():
    layout = Level("test", 3, 3, (Arrow(1, 0, Direction.RIGHT), Arrow(1, 2, Direction.UP)))
    result = Game((layout, layout))
    result.start()
    return result


def test_t01_clear_arrow_is_removed_and_has_flight(game):
    assert game.click(1, 2) == Move.FLYING
    assert game.board.arrow_at(1, 2) is None
    assert game.animations[(1, 2)].kind == Move.FLYING
    assert game.mistakes_left == 3


def test_hint_highlights_clear_arrow_without_moving_it(game):
    assert game.hint() == (1, 2)
    assert game.hints_left == 2
    assert game.hinted_position == (1, 2)
    assert len(game.board.arrows) == 2

    assert game.click(1, 2) == Move.FLYING
    assert game.hinted_position is None


def test_hints_are_limited_to_three_per_game_and_reset_for_new_game(game):
    assert [game.hint(), game.hint(), game.hint()] == [(1, 2), (1, 2), (1, 2)]
    assert game.hints_left == 0
    assert game.hint() is None

    game.home()
    game.start()
    assert game.hints_left == 3


def test_restart_clears_hint_but_does_not_restore_game_hints(game):
    game.hint()
    game.restart()
    assert game.hints_left == 2
    assert game.hinted_position is None


def test_undo_flying_move_restores_arrow_and_cancels_animation(game):
    assert game.click(1, 2) == Move.FLYING
    assert game.can_undo
    assert game.undo()
    assert game.board.arrow_at(1, 2) is not None
    assert not game.animations
    assert game.screen == Screen.PLAYING
    assert not game.can_undo


def test_undo_collision_restores_mistake_and_allows_retry(game):
    assert game.click(1, 0) == Move.COLLISION
    assert game.mistakes_left == 2
    assert game.undo()
    assert game.mistakes_left == 3
    assert game.board.arrow_at(1, 0) is not None
    assert not game.animations


def test_undo_can_recover_from_failure(game):
    for _ in range(3):
        assert game.click(1, 0) == Move.COLLISION
        game.update(0.33)
    assert game.screen == Screen.FAILED
    assert game.undo()
    assert game.screen == Screen.PLAYING
    assert game.mistakes_left == 1


@pytest.mark.parametrize("level", LEVELS, ids=lambda level: level.name)
def test_ai_steps_solve_each_level_without_mistakes(level):
    game = Game((level,))
    game.start()
    steps = 0
    while game.board.arrows:
        position = game.ai_step()
        assert position is not None
        assert game.mistakes_left == level.max_mistakes
        game.update(2)
        steps += 1
    assert steps == len(level.arrows)
    assert game.screen == Screen.SUCCESS


@pytest.mark.parametrize("difficulty, counts", [
    (Difficulty.EASY, (4, 6, 8)),
    (Difficulty.MEDIUM, (6, 9, 12)),
    (Difficulty.HARD, (8, 12, 16)),
])
def test_normal_difficulty_levels_have_increasing_arrow_counts(difficulty, counts):
    assert tuple(len(level.arrows) for level in LEVELS_BY_DIFFICULTY[difficulty]) == counts


@pytest.mark.parametrize("difficulty", list(Difficulty))
def test_all_normal_difficulty_levels_are_ai_solvable(difficulty):
    for level in LEVELS_BY_DIFFICULTY[difficulty]:
        game = Game((level,))
        game.start()
        while game.board.arrows:
            assert game.ai_step() is not None
            game.update(2)
        assert game.screen == Screen.SUCCESS


def test_endless_mode_generates_a_new_hard_level_after_success():
    factory = lambda number: generate_endless_level(number)
    game = Game((factory(1),))
    game.start(endless=True, level_factory=factory)
    while game.board.arrows:
        assert game.ai_step() is not None
        game.update(2)
    assert game.screen == Screen.SUCCESS
    assert not game.final_level
    assert game.next_level()
    assert game.level_index == 1
    assert len(game.level.arrows) == 16
    assert game.level.name == "无尽关卡 2"


def test_endless_mode_preserves_global_level_number_when_resuming():
    factory = lambda number: generate_endless_level(number)
    game = Game((factory(5),))
    game.start(endless=True, level_factory=factory, endless_level_number=5)
    assert game.endless_level_number == 5
    while game.board.arrows:
        assert game.ai_step() is not None
        game.update(2)
    assert game.next_level()
    assert game.endless_level_number == 6
    assert game.level.name == "无尽关卡 6"


def test_t02_collision_keeps_arrow_and_costs_exactly_one(game):
    assert game.click(1, 0) == Move.COLLISION
    assert game.board.arrow_at(1, 0) is not None
    assert game.mistakes_left == 2
    game.update(0.1)
    assert game.mistakes_left == 2


def test_t03_outward_edge_exits_without_index_error():
    game = Game((Level("edge", 1, 1, (Arrow(0, 0, Direction.LEFT),)),))
    game.start()
    assert game.click(0, 0) == Move.FLYING
    game.update(0.45)
    assert game.screen == Screen.SUCCESS


def test_t04_and_t11_result_waits_for_last_flight(game):
    game.click(1, 2)
    game.click(1, 0)
    game.update(0.44)
    assert not game.board.arrows
    assert game.screen == Screen.PLAYING
    game.update(0.02)
    assert game.screen == Screen.SUCCESS
    assert game.next_level()
    assert game.level_index == 1
    assert len(game.board.arrows) == 2
    assert game.mistakes_left == 3


def test_t05_failure_freezes_clicks_and_restart_works(game):
    for _ in range(3):
        assert game.click(1, 0) == Move.COLLISION
        game.update(0.33)
    assert game.screen == Screen.FAILED
    assert game.mistakes_left == 0
    assert game.click(1, 2) == Move.IGNORED
    game.restart()
    assert game.screen == Screen.PLAYING
    assert game.mistakes_left == 3


def test_t06_restart_restores_layout_and_cancels_animations(game):
    original = game.board.arrows.copy()
    game.click(1, 0)
    game.click(1, 2)
    game.update(0.1)
    game.restart()
    assert game.board.arrows == original
    assert game.mistakes_left == 3
    assert not game.animations
    assert game.elapsed == 0


def test_rapid_clicks_during_collision_are_ignored(game):
    game.click(1, 0)
    for _ in range(10):
        assert game.click(1, 0) == Move.IGNORED
    assert game.mistakes_left == 2
    game.update(0.33)
    assert game.click(1, 0) == Move.COLLISION
    assert game.mistakes_left == 1


def test_empty_cells_and_outside_board_do_not_cost_mistakes(game):
    for position in ((0, 0), (-1, 0), (3, 3)):
        assert game.click(*position) == Move.IGNORED
    assert game.mistakes_left == 3


def test_final_level_does_not_advance_past_end():
    game = Game((Level("final", 1, 1, (Arrow(0, 0, Direction.UP),)),))
    game.start()
    game.click(0, 0)
    game.update(1)
    assert game.final_level
    assert not game.next_level()
    assert game.level_index == 0


def test_home_and_pending_failure_ignore_input(game):
    for _ in range(2):
        game.click(1, 0)
        game.update(1)
    game.click(1, 0)
    assert game.click(1, 2) == Move.IGNORED
    game.home()
    assert game.click(1, 2) == Move.IGNORED
    assert not game.animations


def test_board_rejects_duplicate_and_outside_arrows():
    arrow = Arrow(0, 0, Direction.UP)
    with pytest.raises(ValueError):
        Board(2, 2, (arrow, arrow))
    with pytest.raises(ValueError):
        Board(2, 2, (Arrow(2, 0, Direction.UP),))


@pytest.mark.parametrize("level", LEVELS, ids=lambda level: level.name)
def test_mvp_layouts_have_legal_complete_removal_sequence(level):
    from core.path_checker import is_path_clear

    game = Game((level,))
    game.start()
    while game.board.arrows:
        arrow = next((a for a in game.board.arrows.values()
                      if is_path_clear(a, game.board.occupied, level.rows, level.cols)), None)
        assert arrow is not None, "deadlock found"
        assert game.click(arrow.row, arrow.col) == Move.FLYING
        game.update(0.5)
    assert game.screen == Screen.SUCCESS
