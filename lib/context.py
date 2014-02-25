__author__ = 'leif'

class Context:
    def __init__(self, parent):
        self.parent = parent

    def on_draw(self):
        pass

    def on_mouse_press(self, x, y, button, modifiers):
        pass

    def on_key_press(self, key, modifier):
        pass
