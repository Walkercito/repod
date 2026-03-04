# Logging

```python
from repod import configure_logging
```

repod uses Python's standard `logging` module. By default it is **completely silent** -- a `NullHandler` is attached so no output appears unless your application opts in.

## Quick start

```python
from repod import configure_logging

configure_logging()          # INFO and above to stderr
configure_logging("DEBUG")   # everything, including message dispatch
```

## Output format

```
HH:MM:SS [+] server_started                     |  host=0.0.0.0  port=5071
HH:MM:SS [+] client_connected                   |  addr=127.0.0.1:52340
HH:MM:SS [*] message_dispatched                  |  action=chat
HH:MM:SS [!] slow_client                         |  addr=10.0.0.5:49100  bytes=102400
HH:MM:SS [-] connection_failed                   |  host=example.com  error=Connection refused
HH:MM:SS [x] fatal_crash                         |  error=Out of memory
```

### Bracket tags

| Tag | Level | Color |
|---|---|---|
| `[*]` | `DEBUG` | Gray |
| `[+]` | `INFO` | Green |
| `[!]` | `WARNING` | Yellow |
| `[-]` | `ERROR` | Red |
| `[x]` | `CRITICAL` | Bold red |

## Events emitted by repod

These are the structured log events the library produces internally:

### Server (`repod.server`)

| Event | Level | Context keys |
|---|---|---|
| `server_started` | INFO | `host`, `port` |
| `server_stopped` | INFO | -- |
| `client_connected` | INFO | `addr`, `clients` |
| `client_disconnected` | INFO | `addr`, `clients` |
| `background_server_error` | ERROR | `error` |

### Channel (`repod.channel`)

| Event | Level | Context keys |
|---|---|---|
| `channel_error` | ERROR | `error`, `addr` |
| `message_dispatched` | DEBUG | `action` |
| `message_unhandled` | DEBUG | `action` |

### Client (`repod.client`)

| Event | Level | Context keys |
|---|---|---|
| `connecting` | INFO | `host`, `port` |
| `connected` | INFO | `host`, `port` |
| `connection_failed` | ERROR | `host`, `port`, `error` |
| `network_thread_error` | ERROR | `error` |
| `message_dispatched` | DEBUG | `action` |
| `message_unhandled` | DEBUG | `action` |

---

## `configure_logging()`

```python
configure_logging(level="INFO", stream=None)
```

Enable colored structured logging for the `"repod"` logger.

Call once at application startup **before** creating any server or client. If never called, repod remains silent.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `level` | `int \| str` | `logging.INFO` | Minimum log level. Accepts `logging.DEBUG`, `"DEBUG"`, etc. |
| `stream` | file-like | `sys.stderr` | Output stream. |

---

## `get_logger()`

```python
from repod.logconfig import get_logger

log = get_logger(__name__)
```

Returns a `StructuredLogger` bound to the given name. Accepts `**kwargs` on every call which are rendered as structured key-value context after the `|` separator.

```python
log.info("player_joined", name="Alice", team="blue")
# HH:MM:SS [+] player_joined                     |  name=Alice  team=blue
```

---

## `RepodFormatter`

```python
from repod.logconfig import RepodFormatter
```

A `logging.Formatter` subclass that produces the colored wide-event output. You can use it with your own handler if you want repod-style formatting for other loggers:

```python
import logging
from repod.logconfig import RepodFormatter

handler = logging.StreamHandler()
handler.setFormatter(RepodFormatter())

my_logger = logging.getLogger("myapp")
my_logger.addHandler(handler)
```
