import math
import os

import pygame

from core.arrow import Arrow, Direction
from core.game import Game, Move, Screen

WIDTH, HEIGHT = 1000, 760
BG = (13, 18, 36)
PANEL = (22, 30, 51)
LINE = (41, 54, 78)
TEXT = (234, 241, 252)
MUTED = (145, 162, 186)
CYAN = (82, 213, 232)
GREEN = (94, 224, 163)
RED = (255, 121, 130)


class BoardLayout:
    """Drawing and mouse hit tests share the same grid geometry."""

    def __init__(self, rows: int, cols: int):
        self.rows, self.cols = rows, cols
        self.cell = min(76, 440 // max(rows, cols))
        self.rect = pygame.Rect(0, 0, cols * self.cell, rows * self.cell)
        self.rect.center = (365, 430)

    def cell_rect(self, row: int, col: int) -> pygame.Rect:
        return pygame.Rect(self.rect.x + col * self.cell,
                           self.rect.y + row * self.cell, self.cell, self.cell)

    def hit(self, point: tuple[int, int]) -> tuple[int, int] | None:
        if not self.rect.collidepoint(point):
            return None
        return ((point[1] - self.rect.y) // self.cell,
                (point[0] - self.rect.x) // self.cell)


class App:
    def __init__(self, game: Game | None = None):
        pygame.init()
        self.surface = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Arrow Escape · 箭境")
        font_path = pygame.font.match_font("microsoftyahei,simhei,notosanscjk")
        if font_path is None:
            candidate = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts", "msyh.ttc")
            font_path = candidate if os.path.isfile(candidate) else None
        self.fonts = {size: pygame.font.Font(font_path, size) for size in (14, 16, 18, 22, 28, 38, 52)}
        self.game = game or Game()
        self.running = True
        self.buttons: dict[str, pygame.Rect] = {}
        self.mouse = (-1, -1)
        self.result_age = 0.0
        self.message = "观察方向，寻找畅通的出口。"

    @property
    def layout(self) -> BoardLayout:
        return BoardLayout(self.game.board.rows, self.game.board.cols)

    def text(self, content: str, pos: tuple[int, int], size: int = 18,
             color: tuple[int, int, int] = TEXT, center: bool = False) -> None:
        rendered = self.fonts[size].render(content, True, color)
        self.surface.blit(rendered, rendered.get_rect(center=pos) if center else pos)

    def button(self, key: str, label: str, rect: pygame.Rect, primary: bool = False) -> None:
        self.buttons[key] = rect
        hover = rect.collidepoint(self.mouse)
        fill = CYAN if primary else ((42, 57, 80) if hover else PANEL)
        if primary and hover:
            fill = (115, 229, 244)
        pygame.draw.rect(self.surface, fill, rect, border_radius=12)
        if not primary:
            pygame.draw.rect(self.surface, LINE, rect, 1, border_radius=12)
        self.text(label, rect.center, 18, BG if primary else TEXT, center=True)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.home()
            elif event.key == pygame.K_r and self.game.screen != Screen.HOME:
                self.game.restart()
                self.message = "布局已恢复，重新寻找出口。"
        elif event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.mouse = event.pos
            allowed = {
                Screen.HOME: {"start"},
                Screen.PLAYING: {"restart", "home"},
                Screen.SUCCESS: {"next", "restart", "home"},
                Screen.FAILED: {"restart", "home"},
            }[self.game.screen]
            action = next((key for key, rect in self.buttons.items()
                           if key in allowed and rect.collidepoint(event.pos)), None)
            if action == "start":
                self.game.start()
                self.message = "观察方向，寻找畅通的出口。"
            elif action == "restart":
                self.game.restart()
                self.message = "布局已恢复，重新寻找出口。"
            elif action == "home":
                self.game.home()
            elif action == "next":
                self.game.next_level()
                self.message = "新的布局，新的出口。"
            elif self.game.screen == Screen.PLAYING:
                position = self.layout.hit(event.pos)
                if position is not None:
                    move = self.game.click(*position)
                    if move == Move.COLLISION:
                        self.message = "前方有箭头阻挡，失误机会 −1。"
                    elif move == Move.FLYING:
                        self.message = "路径畅通，箭头已释放。"

    def update(self, dt: float) -> None:
        before = self.game.screen
        self.game.update(dt)
        if before != self.game.screen:
            self.result_age = 0.0
        if self.game.screen in (Screen.SUCCESS, Screen.FAILED):
            self.result_age += dt

    def arrow(self, arrow: Arrow, center: tuple[float, float], scale: float,
              color: tuple[int, int, int], alpha: int = 255) -> None:
        sprite = pygame.Surface((80, 80), pygame.SRCALPHA)
        dy, dx = arrow.direction.delta
        perp_x, perp_y = -dy, dx
        length = 19 * scale
        tip = (40 + dx * length, 40 + dy * length)
        tail = (40 - dx * length, 40 - dy * length)
        neck = (40 + dx * 5 * scale, 40 + dy * 5 * scale)
        pygame.draw.line(sprite, color, tail, neck, max(3, round(5 * scale)))
        pygame.draw.polygon(sprite, color, [tip,
            (neck[0] + perp_x * 10 * scale, neck[1] + perp_y * 10 * scale),
            (neck[0] - perp_x * 10 * scale, neck[1] - perp_y * 10 * scale)])
        sprite.set_alpha(max(0, min(255, alpha)))
        self.surface.blit(sprite, sprite.get_rect(center=center))

    def draw_board(self) -> None:
        layout = self.layout
        hovered = layout.hit(self.mouse) if self.game.screen == Screen.PLAYING else None
        for row in range(layout.rows):
            for col in range(layout.cols):
                rect = layout.cell_rect(row, col).inflate(-8, -8)
                position = (row, col)
                is_hover = position == hovered and position in self.game.board.arrows
                pygame.draw.rect(self.surface, (29, 47, 67) if is_hover else PANEL, rect, border_radius=12)
                pygame.draw.rect(self.surface, CYAN if is_hover else LINE, rect, 1, border_radius=12)
                arrow = self.game.board.arrow_at(row, col)
                if arrow and position not in self.game.animations:
                    self.arrow(arrow, rect.center, 1.1 if is_hover else 1, CYAN)
        # Flight is clipped to the board region, disappearing at its boundary.
        previous_clip = self.surface.get_clip()
        self.surface.set_clip(layout.rect.inflate(12, 12))
        for animation in self.game.animations.values():
            rect = layout.cell_rect(animation.arrow.row, animation.arrow.col)
            dy, dx = animation.arrow.direction.delta
            p = animation.progress
            if animation.kind == Move.FLYING:
                if dx > 0:
                    distance = layout.rect.right - rect.centerx + 50
                elif dx < 0:
                    distance = rect.centerx - layout.rect.left + 50
                elif dy > 0:
                    distance = layout.rect.bottom - rect.centery + 50
                else:
                    distance = rect.centery - layout.rect.top + 50
                offset = distance * p * p
                color, alpha = GREEN, int(255 * (1 - p * p))
            else:
                offset = 14 * math.sin(p * math.pi) * math.cos(p * math.pi * 2)
                color, alpha = RED, 255
            self.arrow(animation.arrow, (rect.centerx + dx * offset, rect.centery + dy * offset), 1, color, alpha)
        self.surface.set_clip(previous_clip)

    def draw(self) -> None:
        self.buttons.clear()
        self.surface.fill(BG)
        pygame.draw.circle(self.surface, (17, 25, 45), (950, 30), 300)
        self.text("AE / ARROW ESCAPE", (48, 28), 16, CYAN)
        self.text("箭境", (48, 65), 28)
        self.text("找到出口，一箭破局", (WIDTH - 275, 38), 16, MUTED)
        pygame.draw.line(self.surface, LINE, (48, 115), (952, 115))
        if self.game.screen == Screen.HOME:
            self.text("只需一点，顺序由你决定。", (500, 232), 38, center=True)
            self.text("观察箭头的前方，让每一支箭头找到出口。", (500, 298), 18, MUTED, True)
            self.text("畅通 · 释放     /     受阻 · 消耗一次失误", (500, 337), 18, MUTED, True)
            for i, direction in enumerate(Direction):
                rect = pygame.Rect(322 + i * 94, 387, 74, 74)
                pygame.draw.rect(self.surface, PANEL, rect, border_radius=16)
                self.arrow(Arrow(0, 0, direction), rect.center, 1, CYAN)
            self.button("start", "开始游戏", pygame.Rect(370, 510, 260, 56), True)
            self.text(f"{len(self.game.levels)} 个练习布局  ·  每关 {self.game.level.max_mistakes} 次失误机会",
                      (500, 601), 16, MUTED, True)
        else:
            self.text(f"关卡 {self.game.level_index + 1:02d} / {len(self.game.levels):02d}", (80, 147), 16, CYAN)
            self.text(self.game.level.name, (80, 177), 28)
            self.draw_board()
            panel = pygame.Rect(665, 230, 265, 373)
            pygame.draw.rect(self.surface, PANEL, panel, border_radius=18)
            self.text("本关进度", (691, 253), 16, MUTED)
            self.text(f"{len(self.game.board.arrows):02d}", (690, 286), 52)
            self.text("剩余箭头", (788, 316), 16, MUTED)
            pygame.draw.line(self.surface, LINE, (691, 370), (904, 370))
            self.text(f"剩余失误机会  {self.game.mistakes_left} / {self.game.level.max_mistakes}",
                      (691, 393), 16, MUTED)
            for i in range(self.game.level.max_mistakes):
                pygame.draw.circle(self.surface, RED if i < self.game.mistakes_left else LINE,
                                   (706 + i * 36, 444), 9)
            self.text("前方有箭头时，请先释放阻挡者。", (691, 481), 14, MUTED)
            if self.game.screen == Screen.PLAYING:
                self.button("restart", "重新开始  /  R", pygame.Rect(691, 529, 213, 48))
                self.button("home", "返回首页", pygame.Rect(782, 147, 148, 44))
            self.text(self.message, (365, 672), 16, MUTED, True)
            if self.game.screen in (Screen.SUCCESS, Screen.FAILED):
                self.draw_result()
        self.text("单击箭头  /  R 重开  /  Esc 返回首页", (500, 727), 14, MUTED, True)
        pygame.display.flip()

    def draw_result(self) -> None:
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((6, 10, 22, round(190 * min(1, self.result_age / 0.2))))
        self.surface.blit(veil, (0, 0))
        pygame.draw.rect(self.surface, PANEL, (275, 225, 450, 310), border_radius=22)
        success = self.game.screen == Screen.SUCCESS
        title = ("全部练习完成" if self.game.final_level else "本关通关") if success else "本关失败"
        self.text(title, (500, 292), 38, GREEN if success else RED, True)
        self.text("每一支箭头都找到了出口。" if success else "失误机会已耗尽，再观察一次顺序。",
                  (500, 354), 18, MUTED, True)
        if success and not self.game.final_level:
            self.button("next", "下一关", pygame.Rect(321, 411, 171, 50), True)
        else:
            self.button("restart", "再次挑战", pygame.Rect(321, 411, 171, 50), True)
        self.button("home", "返回首页", pygame.Rect(508, 411, 171, 50))

    def run(self) -> None:
        clock = pygame.time.Clock()
        try:
            while self.running:
                dt = clock.tick(60) / 1000
                for event in pygame.event.get():
                    self.handle_event(event)
                self.update(dt)
                self.draw()
        finally:
            pygame.quit()
