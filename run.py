__author__ = 'leif'

import pyglet
import lib.game

screen_width = 800
screen_height = 600

game = lib.game.new_game(width=screen_width, height=screen_height)
pyglet.app.run()