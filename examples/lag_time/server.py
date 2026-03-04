"""Lag-time server -- measures round-trip ping latency."""

from __future__ import annotations

import sys
import time

from repod import Channel, Server


class LagTimeChannel(Channel):
    """Channel that measures round-trip latency via ping/pong."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.count: int = 0
        self.times: list[float] = []

    def on_close(self) -> None:
        print(f"Client {self.addr} disconnected")

    def Network_ping(self, data: dict) -> None:
        rtt = time.time() - self.times[data["count"]]
        print(f"Client {self.addr}: ping {data['count']} RTT was {rtt:.4f}s")
        self.ping()

    def ping(self) -> None:
        """Send a timestamped ping to the client."""
        self.times.append(time.time())
        self.send({"action": "ping", "count": self.count})
        self.count += 1


class LagTimeServer(Server[LagTimeChannel]):
    """Server that pings clients to measure latency."""

    channel_class = LagTimeChannel

    def __init__(self, host: str = "127.0.0.1", port: int = 5071) -> None:
        super().__init__(host, port)
        print("LagTimeServer started")

    def on_connect(self, channel: LagTimeChannel, addr: tuple[str, int]) -> None:
        print(f"Client {addr} connected")
        channel.ping()


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 5071

    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    print(f"Server running on {host}:{port}")
    LagTimeServer(host, port).launch()
