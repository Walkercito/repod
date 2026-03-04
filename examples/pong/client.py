"""Pong client -- two-player pong rendered with arcade."""

from __future__ import annotations

import sys

import arcade

from repod import ConnectionListener

# --- Constants ---------------------------------------------------------------

WINDOW_W = 800
WINDOW_H = 600

COLOR_BG = (15, 15, 25)
COLOR_LINE = (60, 60, 80)
COLOR_BALL = (255, 255, 255)
COLOR_PADDLE_L = (80, 180, 255)
COLOR_PADDLE_R = (255, 120, 80)
COLOR_LABEL = (140, 140, 160)
COLOR_FLASH = (255, 255, 100)
COLOR_OVERLAY = (255, 255, 255)


# --- Network client ----------------------------------------------------------


class PongClient(ConnectionListener):
    """Handles network communication for the pong game."""

    def __init__(self, game: PongGame, host: str, port: int) -> None:
        self.game = game
        self.connect(host, port)

    def Network_connected(self, data: dict) -> None:
        self.game.set_status("waiting for other player...")

    def Network_disconnected(self, data: dict) -> None:
        self.game.set_status("disconnected")

    def Network_error(self, data: dict) -> None:
        self.game.set_status(f"error: {data.get('error', '?')}")

    def Network_setup(self, data: dict) -> None:
        self.game.my_slot = data["slot"]
        self.game.field_w = data["field"]["w"]
        self.game.field_h = data["field"]["h"]
        self.game.paddle_w = data["paddle"]["w"]
        self.game.paddle_h = data["paddle"]["h"]
        self.game.paddle_margin = data["paddle"]["margin"]
        self.game.ball_size = data["ball_size"]
        self.game.win_score = data["win_score"]
        side = "LEFT" if data["slot"] == 0 else "RIGHT"
        self.game.set_status(f"you are player {data['slot'] + 1} ({side})")

    def Network_state(self, data: dict) -> None:
        self.game.ball_x = data["ball"]["x"]
        self.game.ball_y = data["ball"]["y"]
        self.game.paddle_y[0] = data["paddles"][0]
        self.game.paddle_y[1] = data["paddles"][1]
        self.game.scores[0] = data["scores"][0]
        self.game.scores[1] = data["scores"][1]
        self.game.game_state = data["game_state"]
        self.game._update_score_labels()

    def Network_round_start(self, data: dict) -> None:
        self.game.set_flash("GO!")

    def Network_game_over(self, data: dict) -> None:
        winner = data["winner"]
        if winner == self.game.my_slot:
            self.game.set_overlay("YOU WIN!")
        else:
            self.game.set_overlay("YOU LOSE")
        self.game.game_state = "finished"

    def Network_opponent_left(self, data: dict) -> None:
        self.game.set_status("opponent disconnected")
        self.game.set_overlay("")
        self.game.game_state = "waiting"

    def Network_full(self, data: dict) -> None:
        self.game.set_status("server full (2 players max)")


# --- Arcade game window ------------------------------------------------------


class PongGame(arcade.Window):
    """Arcade window that renders and controls the pong game."""

    def __init__(self, host: str, port: int) -> None:
        super().__init__(WINDOW_W, WINDOW_H, "Pong - repod")

        # Game config (set by server via setup message)
        self.my_slot: int = -1
        self.field_w: int = WINDOW_W
        self.field_h: int = WINDOW_H
        self.paddle_w: int = 12
        self.paddle_h: int = 90
        self.paddle_margin: int = 30
        self.ball_size: int = 10
        self.win_score: int = 5

        # Game state (updated by server)
        self.ball_x: float = WINDOW_W / 2
        self.ball_y: float = WINDOW_H / 2
        self.paddle_y: list[float] = [WINDOW_H / 2, WINDOW_H / 2]
        self.scores: list[int] = [0, 0]
        self.game_state: str = "waiting"

        # Input
        self.direction: int = 0

        # Flash timer
        self.flash_timer: float = 0.0

        # Pre-built Text objects (arcade 3.x, avoids draw_text)
        cx = WINDOW_W / 2
        quarter = WINDOW_W / 4

        self._txt_score_l = arcade.Text(
            "0",
            quarter,
            WINDOW_H - 50,
            COLOR_PADDLE_L,
            font_size=36,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )
        self._txt_score_r = arcade.Text(
            "0",
            WINDOW_W - quarter,
            WINDOW_H - 50,
            COLOR_PADDLE_R,
            font_size=36,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )
        self._txt_status = arcade.Text(
            "connecting...",
            cx,
            16,
            COLOR_LABEL,
            font_size=12,
            anchor_x="center",
            anchor_y="center",
        )
        self._txt_flash = arcade.Text(
            "",
            cx,
            WINDOW_H / 2 + 40,
            COLOR_FLASH,
            font_size=32,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )
        self._txt_overlay = arcade.Text(
            "",
            cx,
            WINDOW_H / 2,
            COLOR_OVERLAY,
            font_size=48,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )
        self._txt_waiting = arcade.Text(
            "waiting for other player...",
            cx,
            WINDOW_H / 2,
            COLOR_LABEL,
            font_size=20,
            anchor_x="center",
            anchor_y="center",
        )

        # Network (connect last so callbacks can use text objects)
        self.client = PongClient(self, host, port)

    # -- Text helpers ---------------------------------------------------------

    def set_status(self, text: str) -> None:
        self._txt_status.text = text

    def set_flash(self, text: str) -> None:
        self._txt_flash.text = text
        self.flash_timer = 1.0

    def set_overlay(self, text: str) -> None:
        self._txt_overlay.text = text

    def _update_score_labels(self) -> None:
        self._txt_score_l.text = str(self.scores[0])
        self._txt_score_r.text = str(self.scores[1])

    # -- Arcade callbacks -----------------------------------------------------

    def on_update(self, delta_time: float) -> None:
        self.client.pump()

        if self.flash_timer > 0:
            self.flash_timer -= delta_time
            if self.flash_timer <= 0:
                self._txt_flash.text = ""

    def on_draw(self) -> None:
        self.clear(COLOR_BG)

        self._draw_court()
        self._draw_paddles()
        self._draw_ball()

        self._txt_score_l.draw()
        self._txt_score_r.draw()
        self._txt_status.draw()

        if self.game_state == "waiting":
            self._txt_waiting.draw()

        if self._txt_overlay.text:
            self._txt_overlay.draw()

        if self._txt_flash.text:
            self._txt_flash.draw()

    def on_key_press(self, key: int, modifiers: int) -> None:
        if key in (arcade.key.W, arcade.key.UP):
            self.direction = -1
            self._send_input()
        elif key in (arcade.key.S, arcade.key.DOWN):
            self.direction = 1
            self._send_input()

    def on_key_release(self, key: int, modifiers: int) -> None:
        if (key in (arcade.key.W, arcade.key.UP) and self.direction == -1) or (
            key in (arcade.key.S, arcade.key.DOWN) and self.direction == 1
        ):
            self.direction = 0
            self._send_input()

    def _send_input(self) -> None:
        self.client.send({"action": "input", "direction": self.direction})

    # -- Drawing helpers ------------------------------------------------------

    def _draw_court(self) -> None:
        # Center dashed line
        cx = self.field_w / 2
        dash_h = 12
        gap = 10
        y = gap
        while y < self.field_h:
            arcade.draw_line(
                cx,
                y,
                cx,
                min(y + dash_h, self.field_h),
                COLOR_LINE,
                2,
            )
            y += dash_h + gap

        # Top and bottom borders
        arcade.draw_line(0, 0, self.field_w, 0, COLOR_LINE, 2)
        arcade.draw_line(
            0,
            self.field_h,
            self.field_w,
            self.field_h,
            COLOR_LINE,
            2,
        )

    def _draw_paddles(self) -> None:
        # Left paddle (player 1)
        lx = self.paddle_margin
        ly = self.field_h - self.paddle_y[0]
        color_l = COLOR_PADDLE_L
        if self.my_slot == 0:
            color_l = _brighten(color_l)
        paddle_rect = arcade.XYWH(lx, ly, self.paddle_w, self.paddle_h)
        arcade.draw_rect_filled(paddle_rect, color_l)
        outline_rect = arcade.XYWH(
            lx,
            ly,
            self.paddle_w + 2,
            self.paddle_h + 2,
        )
        arcade.draw_rect_outline(outline_rect, (255, 255, 255, 40))

        # Right paddle (player 2)
        rx = self.field_w - self.paddle_margin
        ry = self.field_h - self.paddle_y[1]
        color_r = COLOR_PADDLE_R
        if self.my_slot == 1:
            color_r = _brighten(color_r)
        paddle_rect = arcade.XYWH(rx, ry, self.paddle_w, self.paddle_h)
        arcade.draw_rect_filled(paddle_rect, color_r)
        outline_rect = arcade.XYWH(
            rx,
            ry,
            self.paddle_w + 2,
            self.paddle_h + 2,
        )
        arcade.draw_rect_outline(outline_rect, (255, 255, 255, 40))

    def _draw_ball(self) -> None:
        if self.game_state not in ("playing", "scored", "finished"):
            return

        bx = self.ball_x
        by = self.field_h - self.ball_y
        arcade.draw_circle_filled(bx, by, self.ball_size / 2, COLOR_BALL)

        # Glow effect
        arcade.draw_circle_filled(
            bx,
            by,
            self.ball_size,
            (*COLOR_BALL[:3], 25),
        )


def _brighten(color: tuple, amount: int = 50) -> tuple:
    return tuple(min(255, c + amount) for c in color[:3])


# --- Entry point -------------------------------------------------------------


def main() -> None:
    host = "127.0.0.1"
    port = 5071

    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    PongGame(host, port)
    arcade.run()


if __name__ == "__main__":
    main()
