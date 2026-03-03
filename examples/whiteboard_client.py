"""Whiteboard client -- shared drawing canvas with pygame-ce."""

from __future__ import annotations

import sys
from typing import ClassVar

import pygame as pg

from repod import ConnectionListener


class Whiteboard:
    """Drawing surface widget."""

    COLORS: ClassVar[dict[int, tuple[int, int, int]]] = {
        0: (0, 0, 0),
        1: (255, 0, 0),
        2: (0, 255, 0),
        3: (0, 0, 255),
        4: (255, 255, 0),
        5: (255, 0, 255),
        6: (0, 255, 255),
    }

    def __init__(self, width: int, height: int) -> None:
        self.surface = pg.Surface((width, height))
        self.surface.fill((255, 255, 255))
        self.bounds = self.surface.get_rect()
        self.drawing = False
        self.current_line: list[tuple[int, int]] = []

    @property
    def my_color(self) -> tuple[int, int, int]:
        """Return the local user's drawing color."""
        return self.COLORS.get(0, (0, 0, 0))

    def pen_down(self, pos: tuple[int, int]) -> None:
        """Start a new stroke at *pos*."""
        self.drawing = True
        self.current_line = [pos]

    def pen_move(self, pos: tuple[int, int]) -> None:
        """Continue the current stroke to *pos*."""
        if self.drawing and self.current_line:
            pg.draw.line(self.surface, self.my_color, self.current_line[-1], pos, 2)
            self.current_line.append(pos)

    def pen_up(self, _pos: tuple[int, int]) -> None:
        """Finish the current stroke."""
        self.drawing = False
        self.current_line = []


class WhiteboardClient(ConnectionListener):
    """Client that connects to a whiteboard server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5071) -> None:
        self.connect(host, port)
        self.players: dict[str, dict] = {}

        pg.init()
        self.screen = pg.display.set_mode((800, 600))
        pg.display.set_caption("Whiteboard - Repod")
        self.clock = pg.time.Clock()

        self.whiteboard = Whiteboard(780, 520)
        self.whiteboard.bounds.topleft = (10, 50)

        self.font = pg.font.Font(None, 24)
        self.status = "connecting..."
        self.players_label = "0 players"
        self.running = True

    def run(self) -> None:
        """Main game loop."""
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
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_pen_down()
            elif event.type == pg.MOUSEMOTION and pg.mouse.get_pressed()[0]:
                self._handle_pen_move()
            elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                self._handle_pen_up()

    def _local_pos(self) -> tuple[int, int] | None:
        """Return mouse position relative to the whiteboard, or None."""
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
            self.whiteboard.pen_down(local)
            self.send({"action": "startline", "point": local})

    def _handle_pen_move(self) -> None:
        local = self._local_pos()
        if local is not None:
            self.whiteboard.pen_move(local)
            self.send({"action": "drawpoint", "point": local})

    def _handle_pen_up(self) -> None:
        local = self._local_pos()
        if local is not None:
            self.whiteboard.pen_up(local)
            self.send({"action": "drawpoint", "point": local})

    def _draw(self) -> None:
        self.screen.fill((240, 240, 240))
        self.screen.blit(self.whiteboard.surface, self.whiteboard.bounds)
        pg.draw.rect(self.screen, (0, 0, 0), self.whiteboard.bounds, 2)

        status_surf = self.font.render(f"Status: {self.status}", True, (0, 0, 0))
        self.screen.blit(status_surf, (10, 10))

        players_surf = self.font.render(self.players_label, True, (0, 0, 0))
        self.screen.blit(players_surf, (10, 30))

        pg.display.flip()

    def _update_whiteboard(self) -> None:
        self.whiteboard.surface.fill((255, 255, 255))
        for player_info in self.players.values():
            color = player_info["color"]
            for line in player_info["lines"]:
                if len(line) >= 2:
                    pg.draw.lines(self.whiteboard.surface, color, False, line, 2)

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
            self.players[player_id] = {
                "color": tuple(player_info["color"]),
                "lines": player_info["lines"],
            }
        self._update_whiteboard()

    def Network_drawpoint(self, data: dict) -> None:
        player_id = data["id"]
        point = tuple(data["point"])
        if player_id in self.players:
            if not self.players[player_id]["lines"]:
                self.players[player_id]["lines"].append([point])
            else:
                self.players[player_id]["lines"][-1].append(point)
        self._update_whiteboard()

    def Network_startline(self, data: dict) -> None:
        player_id = data["id"]
        point = tuple(data["point"])
        if player_id in self.players:
            self.players[player_id]["lines"].append([point])
        self._update_whiteboard()

    def Network_players(self, data: dict) -> None:
        self.players_label = f"{len(data['players'])} players"

        to_remove = [pid for pid in self.players if pid not in data["players"]]
        for pid in to_remove:
            del self.players[pid]

        for player_id, color in data["players"].items():
            if player_id not in self.players:
                self.players[player_id] = {
                    "color": tuple(color),
                    "lines": [],
                }


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
