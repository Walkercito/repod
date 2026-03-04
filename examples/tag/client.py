"""Tag game client -- raylib-based multiplayer tag with obstacles."""

from __future__ import annotations

import sys
import time

import pyray as rl

from repod import ConnectionListener

# --- Constants ---------------------------------------------------------------

IT_COLOR = rl.Color(220, 50, 50, 255)
OBSTACLE_COLOR = rl.Color(60, 60, 70, 255)
OBSTACLE_BORDER = rl.Color(90, 90, 100, 255)
BG_COLOR = rl.Color(30, 30, 35, 255)
ARENA_BG = rl.Color(45, 45, 52, 255)
HUD_COLOR = rl.Color(220, 220, 220, 255)
COOLDOWN_COLOR = rl.Color(255, 255, 100, 200)


# --- Client ------------------------------------------------------------------


class TagClient(ConnectionListener):
    """Raylib-based tag game client."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5071) -> None:
        self.connect(host, port)

        self.my_id: int | None = None
        self.arena_w: int = 800
        self.arena_h: int = 600
        self.radius: int = 14
        self.obstacles: list[dict] = []
        self.players: dict[int, dict] = {}
        self.it_id: int | None = None
        self.status: str = "connecting..."
        self.running: bool = True
        self.last_tag_msg: str = ""
        self.last_tag_time: float = 0.0

    def run(self) -> None:
        rl.init_window(860, 660, "Tag - repod")
        rl.set_target_fps(60)

        while self.running and not rl.window_should_close():
            self._send_input()
            self.pump()
            self._draw()

        rl.close_window()

    def _send_input(self) -> None:
        dx = 0.0
        dy = 0.0
        if rl.is_key_down(rl.KeyboardKey.KEY_W) or rl.is_key_down(rl.KeyboardKey.KEY_UP):
            dy -= 1
        if rl.is_key_down(rl.KeyboardKey.KEY_S) or rl.is_key_down(rl.KeyboardKey.KEY_DOWN):
            dy += 1
        if rl.is_key_down(rl.KeyboardKey.KEY_A) or rl.is_key_down(rl.KeyboardKey.KEY_LEFT):
            dx -= 1
        if rl.is_key_down(rl.KeyboardKey.KEY_D) or rl.is_key_down(rl.KeyboardKey.KEY_RIGHT):
            dx += 1

        if dx != 0 or dy != 0:
            self.send({"action": "input", "dx": dx, "dy": dy})
        else:
            self.send({"action": "input", "dx": 0, "dy": 0})

    def _draw(self) -> None:
        rl.begin_drawing()
        rl.clear_background(BG_COLOR)

        # Offset to center arena
        ox = (860 - self.arena_w) // 2
        oy = 50

        # Arena background
        rl.draw_rectangle(ox, oy, self.arena_w, self.arena_h, ARENA_BG)
        rl.draw_rectangle_lines(ox, oy, self.arena_w, self.arena_h, rl.WHITE)

        # Obstacles
        for obs in self.obstacles:
            rx = ox + obs["x"]
            ry = oy + obs["y"]
            rl.draw_rectangle(rx, ry, obs["w"], obs["h"], OBSTACLE_COLOR)
            rl.draw_rectangle_lines(rx, ry, obs["w"], obs["h"], OBSTACLE_BORDER)

        # Players
        for pid, info in self.players.items():
            px = ox + int(info["x"])
            py = oy + int(info["y"])
            c = info["color"]

            if pid == self.it_id:
                # "It" player: red ring + glow
                rl.draw_circle(px, py, self.radius + 4, rl.Color(220, 50, 50, 80))
                rl.draw_circle(px, py, self.radius, IT_COLOR)
                rl.draw_circle_lines(px, py, self.radius + 3, rl.Color(255, 80, 80, 200))
                label = "IT!"
                rl.draw_text(label, px - 8, py - self.radius - 18, 14, IT_COLOR)
            else:
                player_color = rl.Color(c[0], c[1], c[2], 255)
                rl.draw_circle(px, py, self.radius, player_color)

            # Highlight self
            if pid == self.my_id:
                rl.draw_circle_lines(px, py, self.radius + 2, rl.WHITE)

        # HUD
        player_count = len(self.players)
        rl.draw_text(f"Players: {player_count}", 10, 10, 20, HUD_COLOR)
        rl.draw_text(f"Status: {self.status}", 10, 32, 16, HUD_COLOR)

        if self.my_id is not None:
            role = "YOU ARE IT!" if self.my_id == self.it_id else "Run!"
            role_color = IT_COLOR if self.my_id == self.it_id else rl.GREEN
            rl.draw_text(role, 860 - 160, 10, 24, role_color)

        # Tag notification
        if self.last_tag_msg and time.time() - self.last_tag_time < 3.0:
            rl.draw_text(
                self.last_tag_msg,
                860 // 2 - 100,
                oy + self.arena_h + 10,
                20,
                COOLDOWN_COLOR,
            )

        # Controls hint
        rl.draw_text(
            "WASD / Arrow keys to move", 10, 660 - 22, 14, rl.Color(120, 120, 120, 255)
        )

        rl.end_drawing()

    # --- Network handlers ----------------------------------------------------

    def Network_connected(self, data: dict) -> None:
        self.status = "connected"

    def Network_error(self, data: dict) -> None:
        self.status = f"error: {data.get('error', 'unknown')}"

    def Network_disconnected(self, data: dict) -> None:
        self.status = "disconnected"
        self.running = False

    def Network_setup(self, data: dict) -> None:
        self.my_id = data["your_id"]
        self.obstacles = data["obstacles"]
        self.arena_w = data["arena"]["w"]
        self.arena_h = data["arena"]["h"]
        self.radius = data["radius"]
        self.status = f"joined as player {self.my_id}"

    def Network_state(self, data: dict) -> None:
        self.it_id = data["it"]
        self.players = {int(k): v for k, v in data["players"].items()}

    def Network_tagged(self, data: dict) -> None:
        tagger = data["tagger"]
        tagged = data["tagged"]
        self.last_tag_msg = f"Player {tagger} tagged player {tagged}!"
        self.last_tag_time = time.time()


def main() -> None:
    host = "127.0.0.1"
    port = 5071

    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    client = TagClient(host, port)
    client.run()


if __name__ == "__main__":
    main()
