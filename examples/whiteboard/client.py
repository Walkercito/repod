"""Whiteboard client -- shared drawing canvas with color picker and smooth curves."""

from __future__ import annotations

import math
import sys

import pygame as pg

from repod import ConnectionListener

# --- Color palette -----------------------------------------------------------

PALETTE: list[tuple[int, int, int]] = [
    (0, 0, 0),  # Black
    (255, 255, 255),  # White (eraser)
    (200, 40, 40),  # Red
    (40, 160, 40),  # Green
    (40, 80, 200),  # Blue
    (255, 200, 0),  # Yellow
    (255, 120, 0),  # Orange
    (160, 40, 200),  # Purple
    (0, 200, 200),  # Cyan
    (255, 100, 150),  # Pink
    (120, 80, 40),  # Brown
    (140, 140, 140),  # Gray
]

THICKNESS_OPTIONS: list[int] = [2, 5, 10]
THICKNESS_LABELS: list[str] = ["Thin", "Medium", "Thick"]


# --- Smooth curve helpers ----------------------------------------------------


def _catmull_rom(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    segments: int = 8,
) -> list[tuple[int, int]]:
    """Return interpolated points on a Catmull-Rom spline segment."""
    points: list[tuple[int, int]] = []
    for i in range(segments + 1):
        t = i / segments
        t2 = t * t
        t3 = t2 * t

        x = 0.5 * (
            (2 * p1[0])
            + (-p0[0] + p2[0]) * t
            + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
            + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
        )
        y = 0.5 * (
            (2 * p1[1])
            + (-p0[1] + p2[1]) * t
            + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
            + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
        )
        points.append((int(x), int(y)))
    return points


def smooth_points(raw: list[tuple[int, int]], segments: int = 8) -> list[tuple[int, int]]:
    """Convert raw input points into a smooth Catmull-Rom curve."""
    if len(raw) < 3:
        return list(raw)

    result: list[tuple[int, int]] = []
    pts = [raw[0], *raw, raw[-1]]

    for i in range(1, len(pts) - 2):
        seg = _catmull_rom(pts[i - 1], pts[i], pts[i + 1], pts[i + 2], segments)
        if result:
            seg = seg[1:]
        result.extend(seg)

    return result


def draw_smooth_line(
    surface: pg.Surface,
    color: tuple[int, int, int],
    points: list[tuple[int, int]],
    thickness: int,
) -> None:
    """Draw a smooth line with round joints from a list of points."""
    smooth = smooth_points(points)
    if len(smooth) < 2:
        if smooth:
            pg.draw.circle(surface, color, smooth[0], thickness // 2)
        return

    for i in range(len(smooth) - 1):
        pg.draw.line(surface, color, smooth[i], smooth[i + 1], thickness)

    for pt in smooth:
        pg.draw.circle(surface, color, pt, thickness // 2)


# --- UI components -----------------------------------------------------------


class ColorPicker:
    """Sidebar color picker widget."""

    SWATCH_SIZE = 28
    PADDING = 4

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
        self.selected = 0
        self.rects: list[pg.Rect] = []

        for i, _color in enumerate(PALETTE):
            row = i // 2
            col = i % 2
            rect = pg.Rect(
                x + col * (self.SWATCH_SIZE + self.PADDING),
                y + row * (self.SWATCH_SIZE + self.PADDING),
                self.SWATCH_SIZE,
                self.SWATCH_SIZE,
            )
            self.rects.append(rect)

    def draw(self, surface: pg.Surface) -> None:
        for i, (rect, color) in enumerate(zip(self.rects, PALETTE, strict=True)):
            pg.draw.rect(surface, color, rect)
            border_color = (255, 255, 0) if i == self.selected else (80, 80, 80)
            border_width = 3 if i == self.selected else 1
            pg.draw.rect(surface, border_color, rect, border_width)

    def handle_click(self, pos: tuple[int, int]) -> bool:
        """Return True if a swatch was clicked."""
        for i, rect in enumerate(self.rects):
            if rect.collidepoint(pos):
                self.selected = i
                return True
        return False

    @property
    def color(self) -> tuple[int, int, int]:
        return PALETTE[self.selected]


class ThicknessPicker:
    """Thickness selector widget."""

    def __init__(self, x: int, y: int, font: pg.font.Font) -> None:
        self.x = x
        self.y = y
        self.font = font
        self.selected = 0
        self.rects: list[pg.Rect] = []

        for i in range(len(THICKNESS_OPTIONS)):
            rect = pg.Rect(x, y + i * 32, 60, 26)
            self.rects.append(rect)

    def draw(self, surface: pg.Surface) -> None:
        for i, (rect, label) in enumerate(zip(self.rects, THICKNESS_LABELS, strict=True)):
            bg = (220, 220, 255) if i == self.selected else (230, 230, 230)
            pg.draw.rect(surface, bg, rect, border_radius=4)
            pg.draw.rect(surface, (80, 80, 80), rect, 1, border_radius=4)
            text = self.font.render(label, True, (0, 0, 0))
            surface.blit(text, (rect.x + 4, rect.y + 4))

    def handle_click(self, pos: tuple[int, int]) -> bool:
        for i, rect in enumerate(self.rects):
            if rect.collidepoint(pos):
                self.selected = i
                return True
        return False

    @property
    def thickness(self) -> int:
        return THICKNESS_OPTIONS[self.selected]


# --- Whiteboard surface ------------------------------------------------------


class Whiteboard:
    """Drawing surface."""

    def __init__(self, width: int, height: int) -> None:
        self.surface = pg.Surface((width, height))
        self.surface.fill((255, 255, 255))
        self.bounds = self.surface.get_rect()
        self.drawing = False
        self.current_line: list[tuple[int, int]] = []

    def pen_down(
        self, pos: tuple[int, int], color: tuple[int, int, int], thickness: int
    ) -> None:
        self.drawing = True
        self.current_line = [pos]
        pg.draw.circle(self.surface, color, pos, thickness // 2)

    def pen_move(
        self, pos: tuple[int, int], color: tuple[int, int, int], thickness: int
    ) -> None:
        if self.drawing and self.current_line:
            prev = self.current_line[-1]
            dist = math.hypot(pos[0] - prev[0], pos[1] - prev[1])
            if dist > 1.5:
                self.current_line.append(pos)
                self._draw_tail(color, thickness)

    def pen_up(self) -> None:
        self.drawing = False
        self.current_line = []

    def _draw_tail(self, color: tuple[int, int, int], thickness: int) -> None:
        """Draw only the tail of the current stroke for smooth incremental rendering."""
        tail = self.current_line[max(0, len(self.current_line) - 6) :]
        if len(tail) >= 2:
            draw_smooth_line(self.surface, color, tail, thickness)
        elif tail:
            pg.draw.circle(self.surface, color, tail[0], thickness // 2)


# --- Network client ----------------------------------------------------------


class WhiteboardClient(ConnectionListener):
    """Client that connects to a whiteboard server."""

    SIDEBAR_W = 80

    def __init__(self, host: str = "127.0.0.1", port: int = 5071) -> None:
        self.connect(host, port)
        self.players: dict[str, dict] = {}

        pg.init()
        self.screen = pg.display.set_mode((880, 620))
        pg.display.set_caption("Whiteboard - repod")
        self.clock = pg.time.Clock()
        self.font = pg.font.Font(None, 20)

        canvas_x = self.SIDEBAR_W + 10
        canvas_w = 880 - canvas_x - 10
        self.whiteboard = Whiteboard(canvas_w, 560)
        self.whiteboard.bounds.topleft = (canvas_x, 50)

        self.color_picker = ColorPicker(10, 50)
        self.thickness_picker = ThicknessPicker(10, 260, self.font)

        self.status = "connecting..."
        self.players_label = "0 players"
        self.running = True

    def run(self) -> None:
        while self.running:
            self._process_events()
            self.pump()
            self._draw()
            self.clock.tick(60)
        pg.quit()

    def _process_events(self) -> None:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False

            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_1:
                    self.thickness_picker.selected = 0
                elif event.key == pg.K_2:
                    self.thickness_picker.selected = 1
                elif event.key == pg.K_3:
                    self.thickness_picker.selected = 2

            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                pos = pg.mouse.get_pos()
                if self.color_picker.handle_click(pos):
                    continue
                if self.thickness_picker.handle_click(pos):
                    continue
                self._handle_pen_down()

            elif event.type == pg.MOUSEMOTION and pg.mouse.get_pressed()[0]:
                self._handle_pen_move()

            elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                self._handle_pen_up()

    def _local_pos(self) -> tuple[int, int] | None:
        pos = pg.mouse.get_pos()
        if self.whiteboard.bounds.collidepoint(pos):
            return (
                pos[0] - self.whiteboard.bounds.x,
                pos[1] - self.whiteboard.bounds.y,
            )
        return None

    def _handle_pen_down(self) -> None:
        local = self._local_pos()
        if local is not None:
            color = self.color_picker.color
            thickness = self.thickness_picker.thickness
            self.whiteboard.pen_down(local, color, thickness)
            self.send(
                {
                    "action": "startline",
                    "point": local,
                    "color": list(color),
                    "thickness": thickness,
                }
            )

    def _handle_pen_move(self) -> None:
        local = self._local_pos()
        if local is not None:
            color = self.color_picker.color
            thickness = self.thickness_picker.thickness
            self.whiteboard.pen_move(local, color, thickness)
            self.send({"action": "drawpoint", "point": local})

    def _handle_pen_up(self) -> None:
        self.whiteboard.pen_up()

    def _draw(self) -> None:
        self.screen.fill((240, 240, 240))

        # Sidebar background
        pg.draw.rect(
            self.screen,
            (225, 225, 225),
            pg.Rect(0, 0, self.SIDEBAR_W, 620),
        )

        # Labels
        color_label = self.font.render("Color", True, (0, 0, 0))
        self.screen.blit(color_label, (10, 30))
        thick_label = self.font.render("Size (1/2/3)", True, (0, 0, 0))
        self.screen.blit(thick_label, (10, 242))

        self.color_picker.draw(self.screen)
        self.thickness_picker.draw(self.screen)

        # Canvas
        self.screen.blit(self.whiteboard.surface, self.whiteboard.bounds)
        pg.draw.rect(self.screen, (0, 0, 0), self.whiteboard.bounds, 2)

        # Status bar
        status_surf = self.font.render(
            f"{self.status}  |  {self.players_label}", True, (60, 60, 60)
        )
        self.screen.blit(status_surf, (self.SIDEBAR_W + 10, 10))

        pg.display.flip()

    def _rebuild_canvas(self) -> None:
        """Redraw every stroke from network state."""
        self.whiteboard.surface.fill((255, 255, 255))
        for player_info in self.players.values():
            for stroke in player_info["lines"]:
                color = tuple(stroke["color"])
                thickness = stroke.get("thickness", 3)
                pts = [tuple(p) for p in stroke["points"]]
                if len(pts) >= 2:
                    draw_smooth_line(self.whiteboard.surface, color, pts, thickness)
                elif pts:
                    pg.draw.circle(self.whiteboard.surface, color, pts[0], thickness // 2)

    # --- Network handlers ----------------------------------------------------

    def Network_connected(self, data: dict) -> None:
        self.status = "connected"

    def Network_error(self, data: dict) -> None:
        self.status = f"error: {data.get('error', 'unknown')}"

    def Network_disconnected(self, data: dict) -> None:
        self.status = "disconnected"
        self.running = False

    def Network_initial(self, data: dict) -> None:
        self.players = {}
        for player_id, player_info in data["lines"].items():
            self.players[player_id] = {"lines": player_info["lines"]}
        self._rebuild_canvas()

    def _ensure_player(self, player_id: str) -> dict:
        """Return the player entry, creating it if missing."""
        if player_id not in self.players:
            self.players[player_id] = {"lines": []}
        return self.players[player_id]

    def Network_drawpoint(self, data: dict) -> None:
        player_id = data["id"]
        point = tuple(data["point"])
        info = self._ensure_player(player_id)
        if not info["lines"]:
            info["lines"].append(
                {
                    "points": [point],
                    "color": data.get("color", [0, 0, 0]),
                    "thickness": data.get("thickness", 3),
                }
            )
            return

        stroke = info["lines"][-1]
        stroke["points"].append(point)
        color = tuple(stroke["color"])
        thickness = stroke.get("thickness", 3)

        # Incremental draw: only re-render the tail of the current
        # stroke instead of rebuilding the entire canvas.
        pts = [tuple(p) for p in stroke["points"]]
        # We need a small window of recent points for Catmull-Rom
        # continuity.  Using the last ~6 raw points is enough to
        # produce a smooth tail that blends with the previously drawn
        # portion of this stroke.
        tail = pts[max(0, len(pts) - 6) :]
        if len(tail) >= 2:
            draw_smooth_line(self.whiteboard.surface, color, tail, thickness)
        elif tail:
            pg.draw.circle(self.whiteboard.surface, color, tail[0], thickness // 2)

    def Network_startline(self, data: dict) -> None:
        player_id = data["id"]
        point = tuple(data["point"])
        color = data.get("color", [0, 0, 0])
        thickness = data.get("thickness", 3)
        info = self._ensure_player(player_id)
        info["lines"].append(
            {
                "points": [point],
                "color": color,
                "thickness": thickness,
            }
        )
        # Incremental draw: just the starting dot.
        pg.draw.circle(self.whiteboard.surface, tuple(color), point, thickness // 2)

    def Network_players(self, data: dict) -> None:
        count = data.get("count", 0)
        self.players_label = f"{count} players"


def main() -> None:
    host = "127.0.0.1"
    port = 5071

    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    client = WhiteboardClient(host, port)
    client.run()


if __name__ == "__main__":
    main()
