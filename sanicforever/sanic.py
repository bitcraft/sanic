import itertools
import pygame
import pymunk
import math
from . import collisions
from . import config
from . import resources
from . import models
from .sprite import SanicForeverSprite
from .sprite import BoxSprite
from .sprite import make_body
from .sprite import make_feet
from .sprite import make_hitbox
import logging

logger = logging.getLogger('sanicforever.sprite')

from pygame.locals import *
from .buttons import *

###   CONFIGURE YOUR KEYS HERE   ###
KEY_MAP = {
    K_LEFT: P1_LEFT,
    K_RIGHT: P1_RIGHT,
    K_UP: P1_UP,
    K_DOWN: P1_DOWN,
    K_q: P1_ACTION1,
    K_w: P1_ACTION2,
}

INV_KEY_MAP = {v: k for k, v in KEY_MAP.items()}
#####################################


class Model(models.UprightModel):
    """
    CBS contain animations, a simple state machine, and references to the pymunk
    objects that they represent.
    """
    def __init__(self):
        super(Model, self).__init__()

        # the weight is used to give sanic more inertia while crouched
        self.weight = None

        self.legs = []

        self.air_move = 0
        self.air_move_speed = config.getfloat('hero', 'air-move')

        self.on_stairs = False

        # this is the normal hitbox
        self.normal_rect = pygame.Rect(0, 0, 50, 60)
        self.normal_feet_offset = (0, .7)

        # this is the hitbox for the crouched state
        self.crouched_rect = pygame.Rect(0, 0, 24, 32)
        self.crouched_feet_offset = (0, 0)

        # detect if player wants to use stairs
        self.wants_stairs = False

        # input fluidity
        self.ignore_buttons = set()

        self.move_power = config.getint('hero', 'move_power')
        self.move_speed = config.getint('hero', 'move_speed')
        self.brake_power = config.getint('hero', 'brake_power')
        self.jump_power = config.getint('hero', 'jump_power')
        self.jump_mod = 1.0

        # crouching is kinda like a toggle
        self.crouched = False

        # used for the interal action state machine
        self.state = set()
        self.sprite_direction = self.RIGHT
        self._sprites = []

    @property
    def sprites(self):
        return iter(self._sprites)

    def process(self, cmd):
        """ process player input

        big ugly bunch of if statements... poor man's state machine
        """

        input_class, button, state = cmd

        # ignoring an input means the 'up' state won't be handled
        # prevent the same input from being 'mashed'
        ignore = self.ignore_buttons.add

        if state == BUTTONUP:
            try:
                self.ignore_buttons.remove(button)
            except KeyError:
                pass
        else:
            if button in self.ignore_buttons:
                return

        # stairs?
        if button == P1_UP:
            if state == BUTTONDOWN:
                self.wants_stairs = True
            elif state == BUTTONUP:
                self.wants_stairs = False

        if state == BUTTONDOWN or state == BUTTONHELD:
            if self.grounded:
                if button == P1_LEFT:
                    self.sprite_direction = self.LEFT
                    self.process2('move')

                elif button == P1_RIGHT:
                    self.sprite_direction = self.RIGHT
                    self.process2('move')

                elif button == P1_DOWN:
                    ignore(P1_DOWN)
                    self.process2('crouch')

        if state == BUTTONUP:
            if button == P1_LEFT or button == P1_RIGHT:
                self.process2('brake')

    def process2(self, state):
        """
        the other state machine.

        accepts following:
            move      # when wants to run or air move
            slide     # when pushed or sliding
            stop      # has come to a stop
            brake     # wants to stop
            landed    # when touching solid ground
            crouch    # crouch if able, or spin if running
            spin      # make ball and spin
            jump
            hurt
            fall
            idle
            die
        """

        pymunk_body = self.sprite.shape.body

        # make sure we have the most up to date information
        velocity = pymunk_body.velocity
        running = bool(abs(velocity.x) >= 100)
        grounded = self.grounded

        def remove(*args):
            for arg in args:
                try:
                    self.state.remove(arg)
                except KeyError:
                    pass

        if 'hurt' == state:
            self.sprite.play('hurt')
            resources.sounds['hurt'].stop()
            resources.sounds['hurt'].play()

        elif 'spin' == state:
            remove('move')
            if 'spin' not in self.state:
                self.make_ball()
                self.state.add('spin')
                self.sprite.play('spinning')

        elif 'crouch' == state:
            if running:
                self.process2('spin')

            elif 'idle' in self.state:
                remove('idle')
                self.state.add('crouching')
                self.sprite.play('crouching')

        elif 'slide' == state:
            if 'idle' in self.state:
                remove('idle')
                self.state.add('slide')
                self.sprite.play('running')

        elif 'stop' == state:
            if 'spin' in self.state:
                remove('spin')
                self.unmake_ball()

            remove('move', 'brake')
            self.state.add('idle')
            self.sprite.play('idle')
            self.feet.shape.body.angle = math.pi

        elif 'brake' == state:
            self.state.add(state)
            self.brake()

        elif 'move' == state:
            if 'jumping' in self.state:
                pass
            if 'spin' in self.state:
                flip = self.sprite_direction == self.LEFT
                for sprite in self.sprites:
                    sprite.flip = flip
                self.accelerate(self.sprite_direction)
            elif grounded:
                do_run = False
                if 'idle' in self.state:
                    do_run = True
                    remove('idle')
                    self.state.add(state)
                    self.sprite.play('running')
                if 'move' in self.state:
                    do_run = True
                if 'slide' in self.state:
                    do_run = True
                if do_run:
                    flip = self.sprite_direction == self.LEFT
                    for sprite in self.sprites:
                        sprite.flip = flip
                    self.accelerate(self.sprite_direction)

        elif 'jump' == state:
            if grounded:
                self.state.add(state)
                self.sprite.play('jumping')

    def update(self, dt):
        super(Model, self).update(dt)
        if not self.air_move == 0:
            vel_x = self.air_move * self.air_move_speed
            if abs(self.sprite.shape.body.velocity.x) < abs(vel_x):
                self.sprite.shape.body.velocity.x = vel_x

        vel_x = abs(self.sprite.shape.body.velocity.x)

        try:
            m = (vel_x / 700.0)
        except ZeroDivisionError:
            m = 1.0
        m += .35
        if m > 1.2: m = 1.2
        self.sprite.speed_modifier = m

        # this should be a velocity callback
        if vel_x > .15:
            self.process2('slide')

        if 'idle' not in self.state:
            if vel_x < .15:
                self.process2('stop')

    def kill(self):
        space = self.sprite.shape.body._space
        for i in (collisions.geometry, collisions.boundary,
                  collisions.trap, collisions.enemy,
                  collisions.stairs):
            space.remove_collision_handler(collisions.hero, i)

        for leg in self.legs:
            space.remove(leg.shape)
            space.remove(leg.shape.body)
            space.remove(leg.joint)

        super(Model, self).kill()

    def on_collision(self, space, arbiter):
        shape0, shape1 = arbiter.shapes

        logger.info('hero collision %s, %s, %s, %s, %s, %s',
                    shape0.collision_type,
                    shape1.collision_type,
                    arbiter.elasticity,
                    arbiter.friction,
                    arbiter.is_first_contact,
                    arbiter.total_impulse)

        if shape1.collision_type == collisions.trap:
            self.alive = False
            self.sprite.play('die')
            return False

        elif shape1.collision_type == collisions.enemy:
            if shape1.model.alive:
                self.alive = False
                self.sprite.play('die')
                return False

        elif shape1.collision_type == collisions.boundary:
            self.alive = False
            return False

        return True

    def on_stairs_begin(self, space, arbiter):
        shape0, shape1 = arbiter.shapes

        logger.info('stairs begin %s, %s, %s, %s, %s, %s',
                    shape0.collision_type,
                    shape1.collision_type,
                    arbiter.elasticity,
                    arbiter.friction,
                    arbiter.is_first_contact,
                    arbiter.total_impulse)

        if self.wants_stairs:
            c = arbiter.contacts
            shape1.collision_type = collisions.geometry
            self.on_stairs = shape1
            return True
        else:
            return False

    def on_stairs_separate(self, space, arbiter):
        shape0, shape1 = arbiter.shapes

        logger.info('stairs seperate %s, %s, %s, %s, %s, %s',
                    shape0.collision_type,
                    shape1.collision_type,
                    arbiter.elasticity,
                    arbiter.friction,
                    arbiter.is_first_contact,
                    arbiter.total_impulse)

        return False

    def drop_from_stairs(self):
        self.on_stairs.collision_type = collisions.stairs
        self.on_stairs = None

    def on_grounded(self, space, arbiter):
        self.air_move = 0
        self.grounded = True
        return True

    def on_ungrounded(self, space, arbiter):
        self.air_move = 0
        self.grounded = False
        if self.on_stairs:
            self.drop_from_stairs()
        return True

    @staticmethod
    def normal_feet_position(position, feet_shape):
        return (position.x,
                position.y - feet_shape.radius * .7)

    @staticmethod
    def crouched_feet_position(position, feet_shape):
        return (position.x,
                position.y + feet_shape.radius * 1.5)

    def make_ball(self):
        pymunk_body = self.sprite.shape.body
        space = pymunk_body._space

        # make the body a small circle
        old_shape = self.sprite.shape
        new_shape = pymunk.Circle(pymunk_body, 1)
        new_shape.friction = old_shape.friction
        new_shape.elasticity = old_shape.elasticity
        new_shape.layers = old_shape.layers
        new_shape.collision_type = old_shape.collision_type
        self.sprite.shape = new_shape

        # make the feet a little slippery
        self.feet.shape.friction = 0.6
        self.move_mod = .5
        self.speed_mod = .5

        # make the game more 'fun', crouching adds a body with a large mass
        # to the player, so as the player is crouched, it carries more inertia
        # and more importantly, it goes fast
        weight = pymunk.Body(20, pymunk.inf)
        weight.velocity = pymunk_body.velocity * 1.7
        weight.position = pymunk_body.position
        w_joint = pymunk.PivotJoint(weight, pymunk_body, (0, 0))
        self.weight = (weight, w_joint)

        space.remove(old_shape)
        space.add(weight, w_joint, new_shape)

        if self.on_stairs:
            self.drop_from_stairs()

    def unmake_ball(self):
        pymunk_body = self.sprite.shape.body
        pymunk_feet = self.feet.shape.body
        space = pymunk_body._space

        # remake the body shape
        old_shape = self.sprite.shape
        new_shape = make_hitbox(pymunk_body, self.normal_rect)
        new_shape.friction = old_shape.friction
        new_shape.elasticity = old_shape.elasticity
        new_shape.layers = old_shape.layers
        new_shape.collision_type = old_shape.collision_type

        # hack to get the body pinned back together properly
        # -move bodies to unused part of map
        # -rebuild the shape
        # -place back in the same place
        old_position = pymunk.Vec2d(pymunk_feet.position)
        pymunk_body.position = 0, 0

        # set the feet to the right spot
        pymunk_feet.position = self.normal_feet_position(
            pymunk_body.position,
            self.feet.shape
        )

        # make the feet sticky again
        self.feet.shape.friction = pymunk.inf
        self.move_mod = 1.0
        self.speed_mod = 1.0

        diff = pymunk.Vec2d(pymunk_feet.position)

        # put back in old position
        pymunk_feet.position = old_position
        pymunk_body.position = pymunk_feet.position - diff

        # kill the weight
        for i in self.weight:
            space.remove(i)

        self.weight = None

        space.remove(old_shape)
        space.add(new_shape)

        self.sprite.shape = new_shape

    def attack(self):
        pass

class BodySprite(SanicForeverSprite):
    sprite_sheet = 'sanic-spritesheet'
    name = 'sanic'
    """ animation def:
        (animation name, interval, func, ((x, y, w, h, x offset, y offset)...

    the frames are passed to fun to create a generator
    """
    image_animations = [
        ('idle',      100, itertools.repeat, ((  0,   0, 32, 50,  0,  0), )),
        ('spinning',  100, itertools.repeat, ((590, 112, 40, 40,  0,  0), )),
        ('crouching', 100, itertools.repeat, ((522, 170, 40, 40,  0,  0), )),
        ('standup',    50, itertools.repeat, ((189,  19, 35, 37,  0,  0), )),
        ('jumping',   100, itertools.repeat, ((185, 160, 40, 50,  0,  0), )),
        ('attacking',  40, itertools.repeat, ((16,  188, 49, 50,  3,  0),
                                             (207, 190, 42, 48,  6,  0),
                                             ( 34, 250, 52, 54, 15,  0),
                                             (194, 256, 50, 46, -6,  0))),
        ('running',   80, itertools.cycle, ((  0,   0, 32, 50,  0,  0),
                                             (  33,   0, 32, 50,  0,  0),
                                             (  65,   0, 46, 50,  0,  0),
                                             ( 107,  0, 36, 50,  0,  0))),
        ('walking',   60, itertools.repeat, ((   5, 122, 50, 50,  0,  0),
                                             ( 62, 122, 50, 50,  0,  0),
                                             (119, 122, 50, 50,  0,  0),
                                             (176, 122, 50, 50,  0,  0),
                                             (233, 122, 50, 50,  0,  0),
                                             (290, 122, 50, 50,  0,  0),
                                             (347, 122, 50, 50,  0,  0),
                                             (404, 122, 50, 50,  0,  0))),
        ('hurt',      50, itertools.repeat, ((307,   4, 50, 50,  0,  0),
                                             (365,   4, 50, 50,  0,  0))),
    ]

    def __init__(self, shape):
        super(BodySprite, self).__init__(shape)
        self.load_animations()
        self.play('idle')

class SanicSprite(SanicForeverSprite):
    sprite_sheet = 'parts-spritesheet'
    name = 'sanic'
    """ animation def:
        (animation name, interval, func, ((x, y, w, h, x offset, y offset)...

    the frames are passed to fun to create a generator
    """
    image_animations = [
        ('idle',      100, itertools.repeat, (( 90,   0, 50, 60,  0,  0), )),
    ]

    def __init__(self, shape):
        super(SanicSprite, self).__init__(shape)
        self.load_animations()
        self.play('idle')

class LegSprite(SanicForeverSprite):
    sprite_sheet = 'parts-spritesheet'
    name = 'leg'
    """ animation def:
        (animation name, interval, func, ((x, y, w, h, x offset, y offset)...

    the frames are passed to fun to create a generator
    """
    image_animations = [
        ('idle',      100, itertools.repeat, ((  0,   0, 32, 50,  0,  0), )),
    ]

    def __init__(self, shape):
        super(LegSprite, self).__init__(shape)
        self.load_animations()
        self.play('idle')


def build(space):
    logger.info('building hero model')

    model = Model()

    # build body
    layers = 1
    body_body, body_shape = make_body(model.normal_rect)
    body_body.collision_type = collisions.hero
    body_shape.layers = layers
    body_shape.friction = 1.0
    body_shape.elasticity = 0.0
    body_sprite = SanicSprite(body_shape)
    space.add(body_body, body_shape)

    # build feet
    layers = 2
    feet_body, feet_shape = make_feet(model.normal_rect)
    feet_shape.collision_type = collisions.hero
    feet_shape.layers = layers
    feet_shape.friction = pymunk.inf
    feet_shape.elasticity = 0.0
    feet_sprite = SanicForeverSprite(feet_shape)
    space.add(feet_body, feet_shape)

    # jump/collision sensor
    #layers = 2
    #size = body_rect.width, body_rect.height * 1.05
    #offset = 0, -body_rect.height * .05
    #sensor = pymunk.Poly.create_box(body_body, size, offset)
    #sensor.sensor = True
    #sensor.layers = layers
    #sensor.collision_type = collisions.hero
    #space.add(sensor)

    # attach feet to body
    feet_body.position = model.normal_feet_position(
        body_body.position,
        feet_shape)

    # motor and joint for feet
    motor = pymunk.SimpleMotor(body_body, feet_body, 0.0)
    joint = pymunk.PivotJoint(
        body_body, feet_body, feet_body.position, (0, 0))
    space.add(motor, joint)

    # the following are cosmetic embellishments
    def make_leg(offset=(0,0)):
        w, h = 10, model.normal_rect.height/2
        leg_mass = .01
        box_offset = (0, 0)
        moment = pymunk.inf
        #moment = pymunk.moment_for_box(10, w,h)
        leg_body = pymunk.Body(leg_mass, moment)
        leg_body.position = feet_body.position + (0, 5)
        leg_shape = pymunk.Poly.create_box(leg_body, (w, h),
                                           offset=box_offset)
        leg_shape.layers = 0
        leg_joint = pymunk.PivotJoint(leg_body, feet_body, offset)
        space.add(leg_body, leg_shape, leg_joint)
        sprite = LegSprite(leg_shape)
        sprite.joint = leg_joint
        return sprite

    # the model is used with gameplay logic
    model.sprite = body_sprite
    model._sprites.append(make_leg((-5, -10)))
    model._sprites.append(make_leg((5, -10)))
    model._sprites.append(body_sprite)
    model.feet = feet_sprite
    model.joint = joint
    model.motor = motor

    # define the collision handlers
    for i in (collisions.boundary, collisions.trap, collisions.enemy):
        space.add_collision_handler(collisions.hero, i,
                                    pre_solve=model.on_collision)

    space.add_collision_handler(collisions.hero, collisions.geometry,
                                post_solve=model.on_grounded,
                                separate=model.on_ungrounded)

    space.add_collision_handler(collisions.hero, collisions.stairs,
                                pre_solve=model.on_stairs_begin,
                                separate=model.on_stairs_separate)
    return model