__author__ = 'leif'

from pyglet.window import mouse
import lib.context

class Editor(lib.context.Context):

    def on_draw(self):
        self.parent.clear()

    def on_mouse_press(self, x, y, button, modifiers):
        if button == mouse.LEFT:
            print('The left mouse button was pressed.')

    def on_key_press(self, key, modifier):
        print(key)