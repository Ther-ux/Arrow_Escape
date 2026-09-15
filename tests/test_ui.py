import pygame
import pytest

from core.game import Screen
from ui.app import App, BoardLayout


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    result = App()
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
