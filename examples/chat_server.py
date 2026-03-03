"""Chat server example using repod."""

from __future__ import annotations

import sys

from repod import Channel, Server


class ClientChannel(Channel["ChatServer"]):
    """Server-side channel for a connected chat client."""

    nickname: str

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.nickname = "Anonymous"

    def on_close(self) -> None:
        self.server.del_player(self)

    def Network_message(self, data: dict) -> None:
        self.server.broadcast(
            {
                "action": "message",
                "text": data["text"],
                "nickname": self.nickname,
            }
        )

    def Network_nickname(self, data: dict) -> None:
        self.nickname = data["nickname"]
        self.server.send_players()


class ChatServer(Server[ClientChannel]):
    """Chat server that manages connected clients."""

    channel_class = ClientChannel

    def __init__(self, host: str = "127.0.0.1", port: int = 5071) -> None:
        super().__init__(host, port)
        self.players: dict[ClientChannel, str] = {}

    def on_connect(self, channel: ClientChannel, addr: tuple[str, int]) -> None:
        self._add_player(channel)

    def _add_player(self, player: ClientChannel) -> None:
        self.players[player] = player.nickname
        print(f"Player connected: {player.addr}")
        self.broadcast(
            {
                "action": "system",
                "text": f"{player.nickname} joined the chat",
            }
        )
        self.send_players()

    def del_player(self, player: ClientChannel) -> None:
        """Remove a player and notify others."""
        if player in self.players:
            nickname = self.players.pop(player)
            print(f"Player disconnected: {player.addr}")
            self.broadcast(
                {
                    "action": "system",
                    "text": f"{nickname} left the chat",
                }
            )
            self.send_players()

    def send_players(self) -> None:
        """Broadcast the current player list."""
        self.broadcast(
            {
                "action": "players",
                "list": [p.nickname for p in self.players],
            }
        )

    def broadcast(self, data: dict) -> None:
        """Send a message to all connected players."""
        for player in self.players:
            player.send(data)


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 5071

    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    print(f"Chat server running on {host}:{port}")
    print("Press Ctrl+C to stop")
    ChatServer(host, port).launch()
