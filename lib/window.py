__author__ = 'leif'

from pyglet.window import Window
import pyglet
import pymunk

class GameWindow(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context_stack = []

    @property
    def current_context(self):
        return self.context_stack[-1]

# =====  FOR CONTEXT USE  =======================================

    def on_draw(self):
        self.current_context.on_draw()

    def on_mouse_press(self, *args, **kwargs):
        self.current_context.on_mouse_press(*args, **kwargs)

    def on_key_press(self, *args, **kwargs):
        self.current_context.on_key_press(*args, **kwargs)
