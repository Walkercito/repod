# Handling connections and disconnections

## Server side

Override `on_connect` and `on_disconnect` on your **Server** subclass:

```python
class GameServer(Server):
    channel_class = GameChannel

    def __init__(self, host: str = "127.0.0.1", port: int = 5071) -> None:
        super().__init__(host, port)
        self.players: list[GameChannel] = []

    def on_connect(self, channel: GameChannel, addr: tuple[str, int]) -> None:
        """Called when a new client connects."""
        print(f"New player from {addr}")
        self.players.append(channel)

    def on_disconnect(self, channel: GameChannel) -> None:
        """Called when a client disconnects."""
        print(f"Player left")
        if channel in self.players:
            self.players.remove(channel)
```

On the **Channel**, override `on_connect` and `on_close`:

```python
class GameChannel(Channel):

    def on_connect(self) -> None:
        """Called when this channel's connection is established."""
        print(f"Client connected: {self.addr}")

    def on_close(self) -> None:
        """Called when this channel's connection is closed."""
        print(f"Client disconnected: {self.addr}")
```

## Client side

On the client, these are just regular `Network_*` handlers:

```python
class GameClient(ConnectionListener):

    def Network_connected(self, data: dict) -> None:
        print("Connected to server!")

    def Network_disconnected(self, data: dict) -> None:
        print("Lost connection.")

    def Network_error(self, data: dict) -> None:
        print(f"Connection error: {data.get('error')}")
```
