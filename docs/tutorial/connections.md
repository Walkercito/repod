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

## Limiting connections

repod does not enforce a maximum number of connections at the transport level. Every TCP connection is accepted and handed a channel. This is intentional -- the "right" limit depends on your game: a pong match needs 2 players, a battle royale needs 100, and a chat room might have no cap at all.

Handle it in `on_connect` by checking your own count and rejecting the client with a message:

```python
MAX_PLAYERS = 2


class GameServer(Server):
    channel_class = GameChannel

    def __init__(self, host: str = "127.0.0.1", port: int = 5071) -> None:
        super().__init__(host, port)
        self.players: list[GameChannel] = []

    def on_connect(self, channel: GameChannel, addr: tuple[str, int]) -> None:
        if len(self.players) >= MAX_PLAYERS:
            channel.send({"action": "full"})
            return

        self.players.append(channel)
        channel.send({"action": "welcome", "slot": len(self.players) - 1})
```

On the client side, handle the rejection:

```python
class GameClient(ConnectionListener):

    def Network_full(self, data: dict) -> None:
        print("Server is full, try again later.")
```

This pattern gives you full control -- you can reject with a reason, put players in a spectator queue, or allow reconnection to an existing slot.
