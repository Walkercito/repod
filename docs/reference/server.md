# Server

```python
class Server[C: Channel]
```

TCP server that manages client channels. Subclass it and set `channel_class`.

## Class attributes

| Attribute | Type | Description |
|---|---|---|
| `channel_class` | `type[C]` | The Channel subclass to instantiate per connection. **Required.** |

## Constructor

```python
Server(host: str = "127.0.0.1", port: int = 5071)
```

| Parameter | Default | Description |
|---|---|---|
| `host` | `"127.0.0.1"` | IP to bind to. Use `"0.0.0.0"` for all interfaces. |
| `port` | `5071` | Port to listen on. |

## Instance attributes

| Attribute | Type | Description |
|---|---|---|
| `host` | `str` | Bound hostname. |
| `port` | `int` | Bound port. |
| `channels` | `list[C]` | Currently connected channels. |

## Properties

| Property | Type | Description |
|---|---|---|
| `address` | `tuple[str, int]` | `(host, port)` tuple. |

## Methods

| Method | Description |
|---|---|
| `launch()` | Start the server and block forever. Hides asyncio. Handles `Ctrl+C`. |
| `send_to_all(data)` | Send a dict to every connected channel. |
| `start_background()` | Start in a daemon background thread. Returns the `Thread`. |
| `await start()` | Bind and start accepting connections. |
| `await run()` | Block until stopped. |
| `await stop()` | Disconnect all clients and shut down. |

## Callbacks

Override these in your subclass:

| Callback | Signature | When |
|---|---|---|
| `on_connect` | `(channel: C, addr: tuple[str, int])` | A new client connected. |
| `on_disconnect` | `(channel: C)` | A client disconnected. |
