"""Exercise real Pygame drawing and synthetic mouse events; save evidence.

Run from the project root: python -m tools.smoke_ui
This is automated UI verification, not a record of human play.
"""

from pathlib import Path
import argparse

import pygame

from core.game import Screen
from core.path_checker import is_path_clear
from ui.app import App


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("docs/screenshots"))
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    app = App()
    print(f"SDL video driver: {pygame.display.get_driver()}")

    def save(name):
        app.draw()
        pygame.image.save(app.surface, str(output / f"{name}.png"))

    def click(point):
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
        for event in pygame.event.get():
            app.handle_event(event)
        app.draw()

    def advance(seconds):
        for _ in range(round(seconds * 60)):
            for event in pygame.event.get():
                app.handle_event(event)
            app.update(1 / 60)
            app.draw()

    try:
        save("home")
        click(app.buttons["start"].center)
        assert app.game.screen == Screen.PLAYING
        app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=app.layout.cell_rect(0, 1).center))
        save("game")
        click(app.layout.cell_rect(1, 1).center)
        assert app.game.mistakes_left == 2
        advance(0.1)
        save("collision")
        # Restart while feedback is running, then verify the original board.
        click(app.buttons["restart"].center)
        assert app.game.mistakes_left == 3 and not app.game.animations
        click(app.layout.cell_rect(0, 1).center)
        advance(0.15)
        save("flight")
        click(app.buttons["restart"].center)
        for _ in range(3):
            click(app.layout.cell_rect(1, 1).center)
            advance(0.35)
        assert app.game.screen == Screen.FAILED
        advance(0.2)
        save("failed")
        click(app.buttons["restart"].center)
        for level_index in range(len(app.game.levels)):
            assert app.game.level_index == level_index
            sequence = []
            while app.game.board.arrows:
                level = app.game.level
                arrow = next((a for a in app.game.board.arrows.values()
                              if is_path_clear(a, app.game.board.occupied, level.rows, level.cols)), None)
                assert arrow is not None, "layout has a deadlock"
                sequence.append((arrow.row, arrow.col))
                click(app.layout.cell_rect(arrow.row, arrow.col).center)
                advance(app.game.animations[(arrow.row, arrow.col)].duration + 0.02)
            assert app.game.screen == Screen.SUCCESS
            advance(0.2)
            save(f"success-l{level_index + 1}")
            print(f"L{level_index + 1}: UI mouse sequence {sequence} -> SUCCESS")
            if not app.game.final_level:
                click(app.buttons["next"].center)
                assert app.game.mistakes_left == 3
        click(app.buttons["home"].center)
        assert app.game.screen == Screen.HOME
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        app.run()
        assert not app.running
        print("UI smoke passed: home, hover, collision, flight, failure, restart, 3 levels, next, quit")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
