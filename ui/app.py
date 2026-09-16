import ctypes
import math
import os
from pathlib import Path

import pygame

from core.arrow import Arrow, Direction
from core.game import Game, Move, Screen
from core.progress import DEFAULT_PROGRESS_PATH, load_endless_level, save_endless_level
from data.levels import Difficulty, GameMode, generate_endless_level, levels_for_difficulty
from ui.rope import Rope, resample
from ui.rope_renderer import draw_rope
from ui.routes import plan_routes

WIDTH, HEIGHT = 1000, 760
BG = (13, 18, 36)
PANEL = (22, 30, 51)
LINE = (41, 54, 78)
TEXT = (234, 241, 252)
MUTED = (145, 162, 186)
CYAN = (82, 213, 232)
GREEN = (94, 224, 163)
RED = (255, 121, 130)
ROUTE_COLORS = (
    (82, 213, 232),
    (190, 128, 255),
    (169, 230, 101),
    (255, 118, 191),
    (255, 205, 91),
)


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
    def __init__(self, game: Game | None = None, progress_path: Path | None = None):
        self.enable_dpi_awareness()
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
        self.auto_solving = False
        self.selected_mode = GameMode.NORMAL
        self.selected_difficulty = Difficulty.MEDIUM
        self.progress_path = progress_path or DEFAULT_PROGRESS_PATH
        self.saved_endless_level = load_endless_level(self.progress_path)
        self.ropes: dict[tuple[int, int], Rope] = {}
        self._rope_board = self.game.board
        self._route_board = None
        self._paths = {}

    @staticmethod
    def enable_dpi_awareness() -> None:
        """Prevent Windows from bitmap-scaling the native-resolution window."""
        if os.name != "nt":
            return
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except (AttributeError, OSError):
                pass

    def sync_ropes(self) -> None:
        # A board object changes on restart/next level, even at the same index.
        if self._rope_board is not self.game.board or self.game.screen == Screen.HOME:
            self.ropes.clear()
            self._rope_board = self.game.board
        for position in set(self.ropes) - self.game.animations.keys():
            del self.ropes[position]
        for position, animation in self.game.animations.items():
            if position not in self.ropes:
                rope = Rope(self.rope_points(animation.arrow))
                self.ropes[position] = rope
                if animation.kind == Move.FLYING:
                    # Include tail length: the result must wait for the rope,
                    # rather than discarding a long body when its head exits.
                    animation.visual_duration = max(0.45, min(1.15, 0.45 + rope.length / 650))

    def rope_points(self, arrow: Arrow) -> list[tuple[float, float]]:
        if self._route_board is not self.game.board:
            layout = self.layout
            self._paths = plan_routes(self.game.level.arrows, layout.rows, layout.cols,
                                      layout.cell, layout.rect.topleft)
            self._route_board = self.game.board
        return self._paths[(arrow.row, arrow.col)]

    def head_at(self, animation, rope: Rope, elapsed: float) -> tuple[float, float]:
        arrow = animation.arrow
        rect, bounds = self.layout.cell_rect(arrow.row, arrow.col), self.layout.rect
        dy, dx = arrow.direction.delta
        p = min(1.0, elapsed / animation.duration)
        if animation.kind == Move.FLYING:
            edge_distance = ((bounds.right - rect.centerx) if dx > 0 else
                             (rect.centerx - bounds.left) if dx < 0 else
                             (bounds.bottom - rect.centery) if dy > 0 else
                             (rect.centery - bounds.top))
            offset = (edge_distance + rope.length + 90) * p * p
        else:
            offset = 14 * math.sin(p * math.pi) * math.cos(p * math.pi * 2)
        return (rect.centerx + dx * (18 + offset), rect.centery + dy * (18 + offset))

    @property
    def layout(self) -> BoardLayout:
        return BoardLayout(self.game.board.rows, self.game.board.cols)

    def start_selected_game(self) -> None:
        if self.selected_mode == GameMode.ENDLESS:
            first_level = generate_endless_level(self.saved_endless_level)
            self.game.start((first_level,), endless=True,
                            level_factory=generate_endless_level,
                            endless_level_number=self.saved_endless_level)
        else:
            self.game.start(levels_for_difficulty(self.selected_difficulty))

    def save_endless_progress(self, next_level: int) -> None:
        self.saved_endless_level = max(self.saved_endless_level, next_level)
        save_endless_level(self.saved_endless_level, self.progress_path)

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
                self.auto_solving = False
            elif event.key == pygame.K_r and self.game.screen != Screen.HOME:
                self.game.restart()
                self.auto_solving = False
                self.message = "布局已恢复，重新寻找出口。"
        elif event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.mouse = event.pos
            allowed = {
                Screen.HOME: {"start", "mode_normal", "mode_endless"},
                Screen.PLAYING: {"restart", "home", "hint", "undo", "ai"},
                Screen.SUCCESS: {"next", "restart", "home"},
                Screen.FAILED: {"restart", "home"},
            }[self.game.screen]
            if self.game.screen == Screen.HOME and self.selected_mode == GameMode.NORMAL:
                allowed |= {"difficulty_easy", "difficulty_medium", "difficulty_hard"}
            action = next((key for key, rect in self.buttons.items()
                           if key in allowed and rect.collidepoint(event.pos)), None)
            if action == "start":
                self.start_selected_game()
                self.auto_solving = False
                self.message = "观察方向，寻找畅通的出口。"
            elif action == "mode_normal":
                self.selected_mode = GameMode.NORMAL
            elif action == "mode_endless":
                self.selected_mode = GameMode.ENDLESS
                self.selected_difficulty = Difficulty.HARD
            elif action == "difficulty_easy":
                self.selected_difficulty = Difficulty.EASY
            elif action == "difficulty_medium":
                self.selected_difficulty = Difficulty.MEDIUM
            elif action == "difficulty_hard":
                self.selected_difficulty = Difficulty.HARD
            elif action == "restart":
                self.game.restart()
                self.auto_solving = False
                self.message = "布局已恢复，重新寻找出口。"
            elif action == "home":
                self.game.home()
                self.auto_solving = False
            elif action == "hint":
                position = self.game.hint()
                if position is None:
                    self.message = "当前没有可提示的箭头，先观察路径。"
                else:
                    self.message = "提示：高亮箭头可以直接释放。"
            elif action == "undo":
                if self.game.undo():
                    self.message = "已撤销上一步，可以重新选择。"
                else:
                    self.message = "暂时没有可以撤销的操作。"
            elif action == "ai":
                self.auto_solving = not self.auto_solving
                self.message = ("AI 正在自动求解当前关卡。"
                                if self.auto_solving else "已停止 AI 自动求解。")
            elif action == "next":
                self.game.next_level()
                if self.game.endless:
                    self.save_endless_progress(self.game.endless_level_number)
                self.auto_solving = False
                self.message = "新的布局，新的出口。"
            elif self.game.screen == Screen.PLAYING:
                position = self.layout.hit(event.pos)
                if position is not None:
                    if self.auto_solving:
                        self.message = "AI 正在求解，请点击 AI 按钮停止。"
                        return
                    if any(a.kind == Move.FLYING for a in self.game.animations.values()):
                        self.message = "尾线正在离场，稍等一下再释放下一支。"
                        return
                    move = self.game.click(*position)
                    if move == Move.COLLISION:
                        self.message = "前方有箭头阻挡，失误机会 −1。"
                    elif move == Move.FLYING:
                        self.message = "路径畅通，箭头已释放。"
        self.sync_ropes()

    def update(self, dt: float) -> None:
        self.sync_ropes()
        for position, rope in self.ropes.items():
            animation = self.game.animations[position]
            rope.advance(min(dt, max(0.0, animation.duration - animation.elapsed)),
                         lambda elapsed, a=animation, r=rope: self.head_at(a, r, elapsed))
        before = self.game.screen
        self.game.update(dt)
        self.sync_ropes()
        if before != self.game.screen:
            self.result_age = 0.0
            if self.game.endless and self.game.screen == Screen.SUCCESS:
                self.save_endless_progress(self.game.endless_level_number + 1)
        if self.game.screen in (Screen.SUCCESS, Screen.FAILED):
            self.result_age += dt
        if self.auto_solving:
            if self.game.screen != Screen.PLAYING:
                self.auto_solving = False
            elif not self.game.animations:
                position = self.game.ai_step()
                if position is None:
                    self.auto_solving = False
                    self.message = "AI 暂时找不到可行的下一步。"
                else:
                    self.message = "AI 正在自动释放箭头。"

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

    def route(self, arrow: Arrow, color: tuple[int, int, int], alpha: int = 255,
              highlighted: bool = False, nodes=None) -> None:
        """Render a continuous curve, with the arrow tip at the pinned head."""
        dy, dx = arrow.direction.delta
        draw_rope(self.surface, nodes if nodes is not None else resample(self.rope_points(arrow)),
                  (dx, dy), color, alpha, 5 if highlighted else 3)

    def draw_map_backdrop(self, layout: BoardLayout) -> None:
        """Give the board a map-like boundary without drawing a grid."""
        map_rect = layout.rect.inflate(18, 18)
        pygame.draw.rect(self.surface, (18, 28, 49), map_rect, border_radius=24)
        pygame.draw.rect(self.surface, (37, 57, 79), map_rect, 1, border_radius=24)
        for x in range(map_rect.left + 14, map_rect.right - 13, 14):
            pygame.draw.circle(self.surface, (61, 83, 105), (x, map_rect.top - 5), 2)
            pygame.draw.circle(self.surface, (61, 83, 105), (x, map_rect.bottom + 5), 2)
        for y in range(map_rect.top + 14, map_rect.bottom - 13, 14):
            pygame.draw.circle(self.surface, (61, 83, 105), (map_rect.left - 5, y), 2)
            pygame.draw.circle(self.surface, (61, 83, 105), (map_rect.right + 5, y), 2)

    def draw_board(self) -> None:
        self.sync_ropes()
        layout = self.layout
        hovered = layout.hit(self.mouse) if self.game.screen == Screen.PLAYING else None
        self.draw_map_backdrop(layout)

        # Draw the map routes first, then place the arrowheads on top. There
        # are deliberately no cell tiles or grid lines in this layer.
        for position, arrow in self.game.board.arrows.items():
            if position not in self.game.animations:
                color = CYAN if position == self.game.hinted_position else \
                    ROUTE_COLORS[(position[0] * layout.cols + position[1]) % len(ROUTE_COLORS)]
                self.route(arrow, color, highlighted=position == hovered or
                           position == self.game.hinted_position)

        # Allow the head to cross the map border without covering HUD/buttons.
        previous_clip = self.surface.get_clip()
        self.surface.set_clip(pygame.Rect(48, 215, 585, 450))
        for position, animation in self.game.animations.items():
            p = animation.progress
            if animation.kind == Move.FLYING:
                color, alpha = GREEN, int(255 * (1 - max(0, (p - 0.8) / 0.2)))
            else:
                color, alpha = RED, 255
            self.route(animation.arrow, color, alpha, nodes=self.ropes[position].positions)
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
            self.text("只需一点，顺序由你决定。", (500, 185), 38, center=True)
            self.text("观察箭头的前方，让每一支箭头找到出口。", (500, 241), 18, MUTED, True)
            self.text("游戏模式", (500, 290), 16, MUTED, True)
            self.button("mode_normal", "普通模式",
                        pygame.Rect(295, 310, 180, 48),
                        primary=self.selected_mode == GameMode.NORMAL)
            self.button("mode_endless", "无尽模式",
                        pygame.Rect(525, 310, 180, 48),
                        primary=self.selected_mode == GameMode.ENDLESS)
            self.text("难度设置", (500, 390), 16, MUTED, True)
            if self.selected_mode == GameMode.NORMAL:
                difficulty_buttons = (
                    ("difficulty_easy", "简单", Difficulty.EASY),
                    ("difficulty_medium", "中等", Difficulty.MEDIUM),
                    ("difficulty_hard", "困难", Difficulty.HARD),
                )
                for index, (key, label, difficulty) in enumerate(difficulty_buttons):
                    self.button(key, label, pygame.Rect(260 + index * 160, 410, 140, 48),
                                primary=self.selected_difficulty == difficulty)
            else:
                self.button("difficulty_hard", "困难（无尽固定）",
                            pygame.Rect(390, 410, 220, 48), primary=True)
            self.button("start", "开始游戏", pygame.Rect(370, 510, 260, 56), True)
            if self.selected_mode == GameMode.NORMAL:
                difficulty_label = {
                    Difficulty.EASY: "简单",
                    Difficulty.MEDIUM: "中等",
                    Difficulty.HARD: "困难",
                }[self.selected_difficulty]
                mode_info = f"普通模式 · {difficulty_label}难度 · 3 个关卡"
            else:
                mode_info = (f"无尽模式 · 困难难度 · 继续第 {self.saved_endless_level} 关"
                             if self.saved_endless_level > 1 else
                             "无尽模式 · 困难难度 · 关卡持续生成")
            self.text(f"{mode_info}  ·  每关 {self.game.level.max_mistakes} 次失误机会",
                      (500, 601), 16, MUTED, True)
        else:
            total_levels = "∞" if self.game.endless else f"{len(self.game.levels):02d}"
            current_level = (self.game.endless_level_number if self.game.endless
                             else self.game.level_index + 1)
            self.text(f"关卡 {current_level:02d} / {total_levels}",
                      (80, 147), 16, CYAN)
            self.text(self.game.level.name, (80, 177), 28)
            self.draw_board()
            panel = pygame.Rect(665, 230, 265, 420)
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
                self.button("hint", f"提示 {self.game.hints_left}", pygame.Rect(691, 529, 68, 48))
                self.button("undo", "撤销", pygame.Rect(766, 529, 68, 48))
                self.button("restart", "重开", pygame.Rect(841, 529, 63, 48))
                self.button("ai", "停止 AI" if self.auto_solving else "AI 求解",
                            pygame.Rect(691, 585, 213, 48), primary=self.auto_solving)
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
