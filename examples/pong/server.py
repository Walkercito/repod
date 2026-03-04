"""Pong server -- authoritative two-player pong with server-side physics."""

from __future__ import annotations

import math
import random
import sys
import time

from repod import Channel, Server

# --- Constants ---------------------------------------------------------------

FIELD_W = 800
FIELD_H = 600

PADDLE_W = 12
PADDLE_H = 90
PADDLE_SPEED = 380.0
PADDLE_MARGIN = 30

BALL_SIZE = 10
BALL_SPEED_INITIAL = 320.0
BALL_SPEED_INCREMENT = 18.0
BALL_SPEED_MAX = 600.0
BALL_MAX_ANGLE = math.pi / 3

TICK_RATE = 1 / 60
WIN_SCORE = 5


# --- Game state --------------------------------------------------------------


def _initial_ball() -> dict:
    """Return ball state launching from center at a random angle."""
    angle = random.uniform(-math.pi / 5, math.pi / 5)
    direction = random.choice([-1, 1])
    return {
        "x": FIELD_W / 2,
        "y": FIELD_H / 2,
        "vx": math.cos(angle) * BALL_SPEED_INITIAL * direction,
        "vy": math.sin(angle) * BALL_SPEED_INITIAL,
        "speed": BALL_SPEED_INITIAL,
    }


# --- Server ------------------------------------------------------------------


class PongChannel(Channel["PongServer"]):
    """Channel representing one pong player."""

    slot: int
    paddle_y: float
    direction: int  # -1 up, 0 still, 1 down
    score: int

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.slot = -1
        self.paddle_y = FIELD_H / 2
        self.direction = 0
        self.score = 0

    def on_close(self) -> None:
        self.server.remove_player(self)

    def Network_input(self, data: dict) -> None:
        self.direction = int(data.get("direction", 0))


class PongServer(Server[PongChannel]):
    """Authoritative pong server for two players."""

    channel_class = PongChannel

    def __init__(self, host: str = "127.0.0.1", port: int = 5071) -> None:
        super().__init__(host, port)
        self.slots: list[PongChannel | None] = [None, None]
        self.ball = _initial_ball()
        self.state: str = "waiting"  # waiting | playing | scored | finished
        self.pause_until: float = 0.0
        print("PongServer started")

    def on_connect(self, channel: PongChannel, addr: tuple[str, int]) -> None:
        slot = self._assign_slot(channel)
        if slot is None:
            channel.send({"action": "full"})
            return

        channel.slot = slot
        channel.paddle_y = FIELD_H / 2
        channel.score = 0
        print(f"Player {slot + 1} connected from {addr}")

        channel.send(
            {
                "action": "setup",
                "slot": slot,
                "field": {"w": FIELD_W, "h": FIELD_H},
                "paddle": {"w": PADDLE_W, "h": PADDLE_H, "margin": PADDLE_MARGIN},
                "ball_size": BALL_SIZE,
                "win_score": WIN_SCORE,
            }
        )

        if self.slots[0] is not None and self.slots[1] is not None:
            self._start_round()

    def remove_player(self, channel: PongChannel) -> None:
        if 0 <= channel.slot <= 1 and self.slots[channel.slot] is channel:
            print(f"Player {channel.slot + 1} disconnected")
            self.slots[channel.slot] = None
            self.state = "waiting"
            self._broadcast({"action": "opponent_left"})

    def on_tick(self) -> None:
        """Run one server tick: physics + broadcast."""
        now = time.time()

        if self.state == "playing":
            self._update_paddles()
            self._update_ball()
            self._check_score()

        elif self.state == "scored" and now >= self.pause_until:
            self._start_round()

        self._broadcast_state()

    # -- Slot management ------------------------------------------------------

    def _assign_slot(self, channel: PongChannel) -> int | None:
        for i in range(2):
            if self.slots[i] is None:
                self.slots[i] = channel
                return i
        return None

    # -- Round management -----------------------------------------------------

    def _start_round(self) -> None:
        self.ball = _initial_ball()
        self.state = "playing"
        self._broadcast({"action": "round_start"})

    def _score_point(self, scorer: int) -> None:
        player = self.slots[scorer]
        if player is None:
            return

        player.score += 1
        print(f"Player {scorer + 1} scores! ({self._score_str()})")

        if player.score >= WIN_SCORE:
            self.state = "finished"
            self._broadcast(
                {
                    "action": "game_over",
                    "winner": scorer,
                }
            )
        else:
            self.state = "scored"
            self.pause_until = time.time() + 1.0

    def _score_str(self) -> str:
        s0 = self.slots[0].score if self.slots[0] else 0
        s1 = self.slots[1].score if self.slots[1] else 0
        return f"{s0} - {s1}"

    # -- Physics --------------------------------------------------------------

    def _update_paddles(self) -> None:
        dt = TICK_RATE
        half = PADDLE_H / 2
        for slot in self.slots:
            if slot is None:
                continue
            slot.paddle_y += slot.direction * PADDLE_SPEED * dt
            slot.paddle_y = max(half, min(FIELD_H - half, slot.paddle_y))

    def _update_ball(self) -> None:
        dt = TICK_RATE
        b = self.ball
        b["x"] += b["vx"] * dt
        b["y"] += b["vy"] * dt

        # Top / bottom wall bounce
        half = BALL_SIZE / 2
        if b["y"] - half <= 0:
            b["y"] = half
            b["vy"] = abs(b["vy"])
        elif b["y"] + half >= FIELD_H:
            b["y"] = FIELD_H - half
            b["vy"] = -abs(b["vy"])

        # Paddle collision
        self._check_paddle_hit(0)
        self._check_paddle_hit(1)

    def _check_paddle_hit(self, slot_idx: int) -> None:
        player = self.slots[slot_idx]
        if player is None:
            return

        b = self.ball
        bx, by = b["x"], b["y"]
        half_bw = BALL_SIZE / 2
        half_ph = PADDLE_H / 2

        if slot_idx == 0:
            # Left paddle
            paddle_x = PADDLE_MARGIN
            if (
                bx - half_bw <= paddle_x + PADDLE_W / 2
                and b["vx"] < 0
                and abs(by - player.paddle_y) < half_ph + half_bw
            ):
                self._bounce(player.paddle_y, 1)
        else:
            # Right paddle
            paddle_x = FIELD_W - PADDLE_MARGIN
            if (
                bx + half_bw >= paddle_x - PADDLE_W / 2
                and b["vx"] > 0
                and abs(by - player.paddle_y) < half_ph + half_bw
            ):
                self._bounce(player.paddle_y, -1)

    def _bounce(self, paddle_y: float, x_dir: int) -> None:
        b = self.ball
        offset = (b["y"] - paddle_y) / (PADDLE_H / 2)
        offset = max(-1.0, min(1.0, offset))
        angle = offset * BALL_MAX_ANGLE

        b["speed"] = min(b["speed"] + BALL_SPEED_INCREMENT, BALL_SPEED_MAX)
        b["vx"] = math.cos(angle) * b["speed"] * x_dir
        b["vy"] = math.sin(angle) * b["speed"]

    def _check_score(self) -> None:
        b = self.ball
        if b["x"] <= 0:
            self._score_point(1)  # Right player scores
        elif b["x"] >= FIELD_W:
            self._score_point(0)  # Left player scores

    # -- Broadcasting ---------------------------------------------------------

    def _broadcast_state(self) -> None:
        p0 = self.slots[0]
        p1 = self.slots[1]
        msg = {
            "action": "state",
            "ball": {
                "x": round(self.ball["x"], 1),
                "y": round(self.ball["y"], 1),
            },
            "paddles": [
                round(p0.paddle_y, 1) if p0 else FIELD_H / 2,
                round(p1.paddle_y, 1) if p1 else FIELD_H / 2,
            ],
            "scores": [
                p0.score if p0 else 0,
                p1.score if p1 else 0,
            ],
            "game_state": self.state,
        }
        self._broadcast(msg)

    def _broadcast(self, msg: dict) -> None:
        for slot in self.slots:
            if slot is not None:
                slot.send(msg)


# --- Entry point -------------------------------------------------------------


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 5071

    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    print(f"Server running on {host}:{port}")

    server = PongServer(host, port)
    server.start_background()

    try:
        while True:
            server.on_tick()
            time.sleep(TICK_RATE)
    except KeyboardInterrupt:
        print("\nShutting down...")
