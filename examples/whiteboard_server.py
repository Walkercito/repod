"""Whiteboard server -- shared drawing canvas."""

from __future__ import annotations

import sys

from repod import Channel, Server


class WhiteboardChannel(Channel["WhiteboardServer"]):
    """Channel representing a connected drawing client."""

    id: str
    color: list[int]
    lines: list[list[tuple[int, int]]]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.id = str(self.server.next_id())
        color_index = int(self.id)
        self.color = [
            (color_index + 1) % 3 * 84,
            (color_index + 2) % 3 * 84,
            (color_index + 3) % 3 * 84,
        ]
        self.lines = []

    def _relay(self, data: dict) -> None:
        """Relay data to all clients, tagging it with this channel's id."""
        data["id"] = self.id
        self.server.relay(data)

    def on_close(self) -> None:
        self.server.del_player(self)

    def Network_startline(self, data: dict) -> None:
        self.lines.append([data["point"]])
        self._relay(data)

    def Network_drawpoint(self, data: dict) -> None:
        if not self.lines:
            self.lines.append([data["point"]])
        else:
            self.lines[-1].append(data["point"])
        self._relay(data)


class WhiteboardServer(Server[WhiteboardChannel]):
    """Server managing a shared whiteboard canvas."""

    channel_class = WhiteboardChannel

    def __init__(self, host: str = "127.0.0.1", port: int = 5071) -> None:
        super().__init__(host, port)
        self.id_counter: int = 0
        self.players: dict[WhiteboardChannel, bool] = {}
        print("WhiteboardServer started")

    def next_id(self) -> int:
        """Return a monotonically increasing player id."""
        self.id_counter += 1
        return self.id_counter

    def on_connect(self, channel: WhiteboardChannel, addr: tuple[str, int]) -> None:
        self._add_player(channel)

    def _add_player(self, player: WhiteboardChannel) -> None:
        print(f"New player: {player.addr} (ID: {player.id})")
        self.players[player] = True

        player.send(
            {
                "action": "initial",
                "lines": {p.id: {"color": p.color, "lines": p.lines} for p in self.players},
            }
        )
        self._send_players()

    def del_player(self, player: WhiteboardChannel) -> None:
        """Remove a player from the whiteboard session."""
        print(f"Deleting player: {player.addr} (ID: {player.id})")
        if player in self.players:
            del self.players[player]
            self._send_players()

    def _send_players(self) -> None:
        self.relay(
            {
                "action": "players",
                "players": {p.id: p.color for p in self.players},
            }
        )

    def relay(self, data: dict) -> None:
        """Send data to all connected players."""
        for player in self.players:
            player.send(data)


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 5071

    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    print(f"Server running on {host}:{port}")
    WhiteboardServer(host, port).launch()
