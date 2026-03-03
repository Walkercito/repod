# Background server (Host + Play)

For "Host Game" scenarios where the player who hosts also plays, run the server in a background thread:

```python
from repod import Server, ConnectionListener


class GameServer(Server):
    channel_class = GameChannel


class GameClient(ConnectionListener):
    ...


# Start server in background (doesn't block)
server = GameServer(host="0.0.0.0", port=5071)
thread = server.start_background()

# Connect as a regular client
client = GameClient()
client.connect("localhost", 5071)

# Normal game loop
while True:
    client.pump()
    time.sleep(0.01)
```

`start_background()` spawns a daemon thread, so it dies automatically when the main program exits.
