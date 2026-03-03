# Broadcasting messages

From inside a Channel, you can access the server via `self.server` and all connected channels via `self.server.channels`:

```python
class ChatChannel(Channel):

    def Network_message(self, data: dict) -> None:
        # Send to ALL connected clients (including sender)
        self.server.send_to_all({"action": "message", "text": data["text"]})
```

`send_to_all()` is a built-in convenience method. You can also loop manually:

```python
def Network_message(self, data: dict) -> None:
    for channel in self.server.channels:
        if channel is not self:  # skip the sender
            channel.send({"action": "message", "text": data["text"]})
```
