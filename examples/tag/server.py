"""Tag game server -- one player is 'it' and must tag others."""

from __future__ import annotations

import math
import random
import sys
import time

from repod import Channel, Server

# --- Constants ---------------------------------------------------------------

ARENA_W = 800
ARENA_H = 600
PLAYER_RADIUS = 14
PLAYER_SPEED = 200.0
TAG_DISTANCE = PLAYER_RADIUS * 2 + 4
TAG_COOLDOWN = 1.5
TICK_RATE = 1 / 60

PLAYER_COLORS: list[list[int]] = [
    [60, 180, 80],
    [60, 120, 220],
    [240, 200, 40],
    [200, 80, 200],
    [40, 200, 200],
    [255, 140, 60],
    [180, 180, 180],
    [140, 80, 40],
]


def _generate_obstacles(count: int = 7) -> list[dict]:
    """Generate random rectangular obstacles inside the arena."""
    obstacles: list[dict] = []
    for _ in range(count):
        w = random.randint(40, 120)
        h = random.randint(40, 120)
        x = random.randint(60, ARENA_W - w - 60)
        y = random.randint(60, ARENA_H - h - 60)
        obstacles.append({"x": x, "y": y, "w": w, "h": h})
    return obstacles


def _spawn_position(obstacles: list[dict]) -> tuple[float, float]:
    """Find a random spawn position not overlapping obstacles."""
    for _ in range(200):
        x = random.uniform(PLAYER_RADIUS + 10, ARENA_W - PLAYER_RADIUS - 10)
        y = random.uniform(PLAYER_RADIUS + 10, ARENA_H - PLAYER_RADIUS - 10)
        ok = True
        for obs in obstacles:
            if (
                obs["x"] - PLAYER_RADIUS < x < obs["x"] + obs["w"] + PLAYER_RADIUS
                and obs["y"] - PLAYER_RADIUS < y < obs["y"] + obs["h"] + PLAYER_RADIUS
            ):
                ok = False
                break
        if ok:
            return (x, y)
    return (ARENA_W / 2, ARENA_H / 2)


def _clamp_position(x: float, y: float, obstacles: list[dict]) -> tuple[float, float]:
    """Clamp position to arena bounds and resolve obstacle collisions."""
    x = max(PLAYER_RADIUS, min(ARENA_W - PLAYER_RADIUS, x))
    y = max(PLAYER_RADIUS, min(ARENA_H - PLAYER_RADIUS, y))

    for obs in obstacles:
        ox, oy, ow, oh = obs["x"], obs["y"], obs["w"], obs["h"]
        # Expanded obstacle rect by player radius
        left = ox - PLAYER_RADIUS
        right = ox + ow + PLAYER_RADIUS
        top = oy - PLAYER_RADIUS
        bottom = oy + oh + PLAYER_RADIUS

        if left < x < right and top < y < bottom:
            # Push out to nearest edge
            distances = [
                ("left", x - left),
                ("right", right - x),
                ("top", y - top),
                ("bottom", bottom - y),
            ]
            edge, _dist = min(distances, key=lambda d: d[1])
            if edge == "left":
                x = left
            elif edge == "right":
                x = right
            elif edge == "top":
                y = top
            elif edge == "bottom":
                y = bottom

    return (x, y)


# --- Server ------------------------------------------------------------------


class TagChannel(Channel["TagServer"]):
    """Channel representing one player in the tag game."""

    player_id: int
    x: float
    y: float
    dx: float
    dy: float
    color: list[int]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.player_id = self.server.next_id()
        self.color = PLAYER_COLORS[self.player_id % len(PLAYER_COLORS)]
        sx, sy = _spawn_position(self.server.obstacles)
        self.x = sx
        self.y = sy
        self.dx = 0.0
        self.dy = 0.0

    def on_close(self) -> None:
        self.server.del_player(self)

    def Network_input(self, data: dict) -> None:
        """Receive movement input from the client."""
        self.dx = float(data.get("dx", 0))
        self.dy = float(data.get("dy", 0))


class TagServer(Server[TagChannel]):
    """Server that manages a tag game with obstacles."""

    channel_class = TagChannel

    def __init__(self, host: str = "127.0.0.1", port: int = 5071) -> None:
        super().__init__(host, port)
        self.id_counter: int = 0
        self.players: dict[int, TagChannel] = {}
        self.it_id: int | None = None
        self.last_tag_time: float = 0.0
        self.obstacles: list[dict] = _generate_obstacles()
        print("TagServer started")

    def next_id(self) -> int:
        self.id_counter += 1
        return self.id_counter

    def on_connect(self, channel: TagChannel, addr: tuple[str, int]) -> None:
        print(f"Player {channel.player_id} connected from {addr}")
        self.players[channel.player_id] = channel

        if self.it_id is None:
            self.it_id = channel.player_id
            self.last_tag_time = time.time()

        channel.send(
            {
                "action": "setup",
                "your_id": channel.player_id,
                "obstacles": self.obstacles,
                "arena": {"w": ARENA_W, "h": ARENA_H},
                "radius": PLAYER_RADIUS,
            }
        )

    def del_player(self, channel: TagChannel) -> None:
        print(f"Player {channel.player_id} disconnected")
        if channel.player_id in self.players:
            del self.players[channel.player_id]

        if self.it_id == channel.player_id and self.players:
            self.it_id = next(iter(self.players))
            self.last_tag_time = time.time()

    def on_tick(self) -> None:
        """Called every server tick -- update physics and broadcast state."""
        dt = TICK_RATE

        for ch in self.players.values():
            # Normalize diagonal movement
            mag = math.hypot(ch.dx, ch.dy)
            if mag > 0:
                nx = ch.dx / mag * PLAYER_SPEED * dt
                ny = ch.dy / mag * PLAYER_SPEED * dt
            else:
                nx = ny = 0

            new_x = ch.x + nx
            new_y = ch.y + ny
            ch.x, ch.y = _clamp_position(new_x, new_y, self.obstacles)

        self._check_tags()
        self._broadcast_state()

    def _check_tags(self) -> None:
        if self.it_id is None or len(self.players) < 2:
            return

        now = time.time()
        if now - self.last_tag_time < TAG_COOLDOWN:
            return

        it_player = self.players.get(self.it_id)
        if it_player is None:
            return

        for pid, ch in self.players.items():
            if pid == self.it_id:
                continue
            dist = math.hypot(it_player.x - ch.x, it_player.y - ch.y)
            if dist < TAG_DISTANCE:
                print(f"Player {self.it_id} tagged player {pid}!")
                self.it_id = pid
                self.last_tag_time = now
                self._broadcast_event(
                    "tagged",
                    {"tagger": it_player.player_id, "tagged": pid},
                )
                break

    def _broadcast_state(self) -> None:
        state = {
            "action": "state",
            "it": self.it_id,
            "players": {
                pid: {
                    "x": round(ch.x, 1),
                    "y": round(ch.y, 1),
                    "color": ch.color,
                }
                for pid, ch in self.players.items()
            },
        }
        for ch in self.players.values():
            ch.send(state)

    def _broadcast_event(self, action: str, data: dict) -> None:
        msg = {"action": action, **data}
        for ch in self.players.values():
            ch.send(msg)


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 5071

    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    print(f"Server running on {host}:{port}")

    server = TagServer(host, port)
    server.start_background()

    try:
        while True:
            server.on_tick()
            time.sleep(TICK_RATE)
    except KeyboardInterrupt:
        print("\nShutting down...")
