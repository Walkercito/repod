# How it works

There are three classes you need to know:

| Class | Side | What it does |
|---|---|---|
| `Server` | Server | Listens for TCP connections. Creates a `Channel` for each client that connects. |
| `Channel` | Server | Represents one connected client. You define `Network_{action}` methods here to handle messages from that client. |
| `ConnectionListener` | Client | Connects to a server. You define `Network_{action}` methods here to handle messages from the server. Call `pump()` every frame to process them. |

## Architecture

```
┌────────────────────┐            ┌───────────────────────┐
│      Client        │            │      Server           │
│                    │            │                       │
│ ConnectionListener │ ◄────────► │  Server               │
│  - pump()          │     TCP    │  - launch()           │
│  - send()          │            │  - on_connect()       │
│  - Network_*()     │            │  - on_disconnect()    │
│                    │            │                       │
│                    │            │  Channel (per client) │
│                    │            │  - send()             │
│                    │            │  - Network_*()        │
└────────────────────┘            └───────────────────────┘
```

## Message dispatch

The design philosophy is simple: **messages are Python dicts**. You send a dict with an `"action"` key, and repod automatically routes it to a method named `Network_{action}` on the other side.

```
Client sends:  {"action": "move", "x": 10, "y": 20}
                        │
                        ▼
Server calls:  channel.Network_move({"action": "move", "x": 10, "y": 20})
```

repod handles the TCP connection, serialization (msgpack), framing (length-prefix), and threading for you. You just define handler methods and send dicts.
