# Integrations

`ConnectionListener.pump()` is designed to drop into any game loop. Just call it once per frame -- repod handles the rest. Here are examples with the two most common Python game frameworks.

## Pygame

```python
import pygame as pg
from repod import ConnectionListener


class Game(ConnectionListener):

    def __init__(self) -> None:
        pg.init()
        self.screen = pg.display.set_mode((800, 600))
        self.clock = pg.time.Clock()
        self.running = True
        self.connect("localhost", 5071)

    def run(self) -> None:
        while self.running:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.running = False

            self.pump()  # process network messages

            self.screen.fill((0, 0, 0))
            # ... draw game state ...
            pg.display.flip()
            self.clock.tick(60)

        pg.quit()

    def Network_connected(self, data: dict) -> None:
        print("Connected to server!")

    def Network_state(self, data: dict) -> None:
        # Update game state from server
        pass


if __name__ == "__main__":
    Game().run()
```

## Raylib

```python
import pyray as rl
from repod import ConnectionListener


class Game(ConnectionListener):

    def __init__(self) -> None:
        rl.init_window(800, 600, "My Game")
        rl.set_target_fps(60)
        self.connect("localhost", 5071)

    def run(self) -> None:
        while not rl.window_should_close():
            self.pump()  # process network messages

            rl.begin_drawing()
            rl.clear_background(rl.BLACK)
            # ... draw game state ...
            rl.end_drawing()

        rl.close_window()

    def Network_connected(self, data: dict) -> None:
        print("Connected to server!")

    def Network_state(self, data: dict) -> None:
        # Update game state from server
        pass


if __name__ == "__main__":
    Game().run()
```

## Other frameworks

The pattern is the same for any framework with a main loop -- arcade, pyglet, Ursina, etc. Just call `pump()` once per frame:

```python
while game_running:
    client.pump()       # repod: process network events
    process_input()     # your framework's input handling
    update()            # your game logic
    render()            # your framework's draw call
```

!!! tip
    repod never calls `time.sleep()` inside `pump()`. It drains whatever messages are queued and returns immediately, so it won't stall your frame.
