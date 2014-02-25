__author__ = 'leif'

import pyglet
import pymunk

class Level:
    def __init__(self):
        self.space = pymunk.Space()