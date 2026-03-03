# Type-safe generics

!!! note
    This is **optional**. If you don't use generics, everything works fine -- `self.server` is typed as a generic `Server`.

If you want your IDE to autocomplete custom methods on `self.server`, pass your server class as a type parameter:

```python
class GameChannel(Channel["GameServer"]):

    def Network_chat(self, data: dict) -> None:
        # IDE knows self.server is GameServer, not generic Server
        self.server.broadcast(data)  # autocompletes!


class GameServer(Server[GameChannel]):
    channel_class = GameChannel

    def broadcast(self, data: dict) -> None:
        for ch in self.channels:
            ch.send(data)
```

Use it when you want the IDE help. Skip it when you just want to get something working.
