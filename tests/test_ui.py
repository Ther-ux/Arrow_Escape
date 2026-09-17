import pygame
import pytest

from core.game import Screen
from ui.app import App, BoardLayout


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    result = App(progress_path=tmp_path / "endless_progress.json")
    result.draw()
    yield result
    pygame.quit()


def click(app, point):
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
    app.draw()


def test_cell_centers_match_hit_and_edges_stay_outside():
    for rows, cols in ((5, 5), (6, 6), (3, 7)):
        layout = BoardLayout(rows, cols)
        for row in range(rows):
            for col in range(cols):
                assert layout.hit(layout.cell_rect(row, col).center) == (row, col)
        assert layout.hit((layout.rect.right, layout.rect.top)) is None
        assert layout.hit((layout.rect.left, layout.rect.bottom)) is None


def test_start_collision_restart_and_home_mouse_events(app):
    click(app, app.buttons["start"].center)
    assert app.game.screen == Screen.PLAYING
    click(app, app.layout.cell_rect(1, 1).center)
    assert app.game.mistakes_left == 2
    click(app, app.buttons["restart"].center)
    assert app.game.mistakes_left == 3
    assert not app.game.animations
    click(app, app.buttons["home"].center)
    assert app.game.screen == Screen.HOME


def test_hint_button_uses_one_game_hint_and_highlights_arrow(app):
    click(app, app.buttons["start"].center)
    assert app.game.hints_left == 3
    assert "hint" in app.buttons

    click(app, app.buttons["hint"].center)
    assert app.game.hints_left == 2
    assert app.game.hinted_position is not None
    assert "提示" in app.message


def test_undo_button_restores_collision(app):
    click(app, app.buttons["start"].center)
    click(app, app.layout.cell_rect(1, 1).center)
    assert app.game.mistakes_left == 2
    assert "undo" in app.buttons

    click(app, app.buttons["undo"].center)
    assert app.game.mistakes_left == 3
    assert app.game.board.arrow_at(1, 1) is not None
    assert "撤销" in app.message


def test_ai_button_solves_current_level_with_animation(app):
    click(app, app.buttons["start"].center)
    click(app, app.buttons["ai"].center)
    for _ in range(200):
        app.update(0.1)
        app.draw()
        if app.game.screen == Screen.SUCCESS:
            break
    assert app.game.screen == Screen.SUCCESS
    assert app.game.mistakes_left == app.game.level.max_mistakes
    assert not app.auto_solving


def test_home_difficulty_and_endless_mode_selection(app):
    click(app, app.buttons["difficulty_hard"].center)
    click(app, app.buttons["start"].center)
    assert not app.game.endless
    assert len(app.game.level.arrows) == 8

    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    app.draw()
    click(app, app.buttons["mode_endless"].center)
    assert "difficulty_hard" in app.buttons
    click(app, app.buttons["start"].center)
    assert app.game.endless
    assert len(app.game.level.arrows) == 16


def test_basic_playstyle_has_only_fixed_levels_and_no_advanced_selectors(app):
    click(app, app.buttons["play_basic"].center)
    assert set(app.buttons) == {"play_basic", "play_advanced", "start"}

    click(app, app.buttons["start"].center)
    assert not app.game.endless
    assert len(app.game.levels) == 3
    assert app.layout.cell < BoardLayout(app.game.board.rows, app.game.board.cols).cell

    click(app, app.buttons["ai"].center)
    for _ in range(200):
        app.update(0.1)
        app.draw()
        if app.game.screen == Screen.SUCCESS:
            break
    assert app.game.screen == Screen.SUCCESS


def test_endless_completion_saves_next_level_and_resumes(app):
    click(app, app.buttons["mode_endless"].center)
    click(app, app.buttons["start"].center)
    click(app, app.buttons["ai"].center)
    for _ in range(150):
        app.update(0.2)
        if app.game.screen == Screen.SUCCESS:
            break
    assert app.game.screen == Screen.SUCCESS
    assert app.saved_endless_level == 2

    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    app.draw()
    click(app, app.buttons["start"].center)
    assert app.game.endless
    assert app.game.endless_level_number == 2


def test_failure_result_restart_and_keyboard_escape(app):
    click(app, app.buttons["start"].center)
    for _ in range(3):
        click(app, app.layout.cell_rect(1, 1).center)
        app.update(0.33)
        app.draw()
    assert app.game.screen == Screen.FAILED
    assert set(app.buttons) == {"restart", "home"}
    click(app, app.buttons["restart"].center)
    assert app.game.screen == Screen.PLAYING
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert app.game.screen == Screen.HOME


def test_quit_event_stops_main_loop(app):
    app.handle_event(pygame.event.Event(pygame.QUIT))
    assert not app.running


def test_stale_buttons_cannot_restart_after_returning_home(app):
    click(app, app.buttons["start"].center)
    restart_center = app.buttons["restart"].center
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=restart_center))
    assert app.game.screen == Screen.HOME


def test_flight_nodes_follow_head_and_restart_clears_rope(app):
    click(app, app.buttons["start"].center)
    click(app, app.layout.cell_rect(2, 4).center)
    rope = app.ropes[(2, 4)]
    original_tail = rope.positions[-1]
    app.update(0.1)
    assert rope.positions[0] != original_tail
    assert rope.positions[-1] != original_tail
    assert app.game.animations[(2, 4)].duration > 0.45
    app.draw()
    # Rendering is pure: additional draw calls do not advance physics.
    snapshot = list(rope.positions)
    app.draw()
    assert rope.positions == snapshot
    click(app, app.buttons["restart"].center)
    assert not app.ropes
    assert not app.game.animations


def test_last_rope_keeps_result_pending_until_tail_finishes(app):
    click(app, app.buttons["start"].center)
    app.game.board.arrows = {(4, 3): app.game.board.arrow_at(4, 3)}
    click(app, app.layout.cell_rect(4, 3).center)
    duration = app.game.animations[(4, 3)].duration
    app.update(duration - 0.01)
    assert app.game.screen == Screen.PLAYING
    assert app.ropes
    app.update(0.02)
    assert app.game.screen == Screen.SUCCESS
    assert not app.ropes


def test_next_release_waits_for_rope_to_avoid_overlapping_departures(app):
    click(app, app.buttons["start"].center)
    click(app, app.layout.cell_rect(0, 1).center)
    duration = app.game.animations[(0, 1)].duration
    click(app, app.layout.cell_rect(1, 1).center)
    assert app.game.board.arrow_at(1, 1) is not None
    assert app.game.mistakes_left == 3
    assert set(app.ropes) == {(0, 1)}
    app.update(duration + 0.01)
    click(app, app.layout.cell_rect(1, 1).center)
    assert app.game.board.arrow_at(1, 1) is None
