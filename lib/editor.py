__author__ = 'leif'

from pyglet.window import mouse
import pymunk
import pyglet
import itertools
import lib.context


class MouseTool:
    pass


class PolygonTool(MouseTool):
    def __init__(self):
        super().__init__()
        self.is_editing = False
        self.points = []
        self.triangles = []

    def collect_batch(self, batch):
        pass

    def on_draw(self):
        if self.triangles:
            pyglet.graphics.draw(int(len(self.triangles)/2), pyglet.gl.GL_TRIANGLES,
                                 ('v2i', self.triangles))

    def on_mouse_press(self, x, y, button, modifiers):
        if button == mouse.LEFT:
            self.points.append((x, y))

        self.triangles = tuple(itertools.chain(*itertools.chain(*pymunk.util.triangulate(self.points))))

    def on_key_press(self, key, modifier):
        print(key)


class Editor(lib.context.Context):
    def __init__(self, parent):
        super().__init__(parent)
        self.current_context = PolygonTool()

    def on_draw(self):
        self.parent.clear()
        self.current_context.on_draw()

    def on_mouse_press(self, *args, **kwargs):
        self.current_context.on_mouse_press(*args, **kwargs)

    def on_key_press(self, *args, **kwargs):
        self.current_context.on_key_press(*args, **kwargs)