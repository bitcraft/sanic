__author__ = 'leif'

import pyglet
import pymunk


class Entity:
    def __init__(self):
        self.body = pymunk.Body()
        self.sprites = []

    def model_shape(self):
        pass