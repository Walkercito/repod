"""Chat client example using repod."""

from __future__ import annotations

import sys
import threading
import time

from repod import ConnectionListener


class ChatClient(ConnectionListener):
    """Chat client that connects to a chat server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5071) -> None:
        self.running = True
        self.connect(host, port)
        print("Chat client started")

    def set_nickname(self, nickname: str) -> None:
        """Send the chosen nickname to the server."""
        self.send({"action": "nickname", "nickname": nickname})

    def send_message(self, text: str) -> None:
        """Send a chat message to the server."""
        self.send({"action": "message", "text": text})

    def run(self) -> None:
        """Synchronous main loop (ideal for game loops like pygame)."""
        while self.running:
            self.pump()
            time.sleep(0.01)

    def Network_connected(self, data: dict) -> None:
        print("Connected to server!")

    def Network_system(self, data: dict) -> None:
        print(f"SYSTEM: {data['text']}")

    def Network_message(self, data: dict) -> None:
        print(f"{data['nickname']}: {data['text']}")

    def Network_players(self, data: dict) -> None:
        print(f"Players: {', '.join(data['list'])}")

    def Network_error(self, data: dict) -> None:
        print(f"Error: {data.get('error', 'Unknown error')}")
        self.running = False

    def Network_disconnected(self, data: dict) -> None:
        print("Disconnected from server")
        self.running = False


def input_thread(client: ChatClient) -> None:
    """Read user input in a separate thread to avoid blocking the pump loop."""
    nickname = input("Enter your nickname: ")
    client.set_nickname(nickname)
    print("Type your messages (Ctrl+C to quit):")

    while client.running:
        try:
            msg = input()
            if msg and client.running:
                client.send_message(msg)
        except (EOFError, KeyboardInterrupt):
            client.running = False
            break


def main() -> None:
    host = "127.0.0.1"
    port = 5071

    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    client = ChatClient(host, port)

    t = threading.Thread(target=input_thread, args=(client,), daemon=True)
    t.start()

    try:
        client.run()
    except KeyboardInterrupt:
        print("\nDisconnecting...")
        client.running = False


if __name__ == "__main__":
    main()
