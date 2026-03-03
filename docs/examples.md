# Examples

The `examples/` directory has working demos:

| Example | Description |
|---|---|
| `chat_server.py` + `chat_client.py` | Multi-user chat room |
| `lag_time_server.py` + `lag_time_client.py` | Ping/pong round-trip latency |
| `whiteboard_server.py` + `whiteboard_client.py` | Shared drawing canvas (pygame-ce) |

## Running the examples

```bash
# Terminal 1
python examples/chat_server.py

# Terminal 2
python examples/chat_client.py
```

!!! tip
    The whiteboard example requires `pygame-ce`. Install it with `uv sync --group examples` or `pip install pygame-ce`.
