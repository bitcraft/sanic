Level Design
============

Sanic forever can use a tile based map, but I'm simply using an image layer for
the background and shapes to provide level geometry.


Layers
======

The level loader recognizes the following layer names and treats them
differently.

## Traps
Any objects in this layer will kill the player

## Boundaries
Kills the player, used if player moves off map or falls into pit

## Physics
Special treatment to objects that begin with the following words:
- moving: springboard

All other geometry will collide with the player.


Sanic
=====

Set start position by creating object of type 'hero'

