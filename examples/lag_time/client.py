"""Lag-time client -- responds to pings and measures latency."""

from __future__ import annotations

import sys
import time

from repod import ConnectionListener


class LagTimeClient(ConnectionListener):
    """Client that responds to server pings."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5071) -> None:
        self.running = True
        self.pings_received = 0
        self.connect(host, port)
        print("LagTimeClient started")

    def run(self) -> None:
        """Synchronous main loop."""
        while self.running:
            self.pump()
            time.sleep(0.001)

    def Network_connected(self, data: dict) -> None:
        print("Connected to server!")

    def Network_ping(self, data: dict) -> None:
        print(f"Got ping #{data['count']}")
        self.pings_received += 1

        if self.pings_received >= 10:
            print("Received 10 pings, closing connection...")
            if self.connection is not None:
                self.connection.close()
        else:
            self.send(data)

    def Network_error(self, data: dict) -> None:
        print(f"Error: {data.get('error', 'Unknown error')}")
        self.running = False

    def Network_disconnected(self, data: dict) -> None:
        print("Disconnected from server")
        self.running = False


def main() -> None:
    host = "127.0.0.1"
    port = 5071

    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    client = LagTimeClient(host, port)

    try:
        client.run()
    except KeyboardInterrupt:
        print("\nDisconnecting...")


if __name__ == "__main__":
    main()
