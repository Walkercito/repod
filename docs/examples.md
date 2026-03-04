# Examples

The `examples/` directory has working demos, each in its own folder:

| Example | Description |
|---|---|
| `chat/` | Multi-user chat room (terminal) |
| `lag_time/` | Ping/pong round-trip latency measurement |
| `whiteboard/` | Shared drawing canvas with color picker and smooth curves (pygame-ce) |
| `tag/` | Multiplayer tag game with obstacles (raylib) |
| `pong/` | Two-player pong with server-side physics (arcade) |

## Running the examples

Each example has a `server.py` and a `client.py`. Start the server first, then one or more clients:

```bash
# Terminal 1 -- start the server
python examples/chat/server.py

# Terminal 2 -- start a client
python examples/chat/client.py
```

### Whiteboard

Shared drawing canvas where each player picks their own color and stroke thickness. Strokes are rendered as smooth Catmull-Rom curves.

- **Color picker**: click a swatch in the sidebar
- **Stroke thickness**: press `1` (thin), `2` (medium), or `3` (thick)

```bash
python examples/whiteboard/server.py
python examples/whiteboard/client.py
```

!!! tip
    Requires `pygame-ce`. Install with `uv sync --group examples` or `pip install pygame-ce`.

### Tag

Multiplayer tag game with randomly generated obstacles. One player is "it" (shown in red) and must touch another player to transfer the role. Server is authoritative -- it runs physics and collision detection.

- **Move**: WASD or arrow keys

```bash
python examples/tag/server.py
python examples/tag/client.py
```

!!! tip
    Requires `raylib-python-cffi`. Install with `uv sync --group examples` or `pip install raylib`.

### Pong

Two-player pong with authoritative server-side physics. The server handles ball movement, paddle collision, bounce angles, scoring, and win conditions (first to 5). The client is built with arcade and features colored paddles, a glow effect on the ball, and a dashed center line.

- **Move**: W/S or Up/Down arrow keys

```bash
python examples/pong/server.py
python examples/pong/client.py
```

!!! tip
    Requires `arcade`. Install with `uv sync --group examples` or `pip install arcade`.
