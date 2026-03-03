# Pygame integration

`ConnectionListener.pump()` is designed to drop into any game loop. Here's a pygame example:

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

!!! tip
    This works with any framework that has a main loop: pygame, raylib, arcade, pyglet, etc. Just call `pump()` once per frame.
