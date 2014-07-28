# -*- coding: utf-8; -*-
"""
PyMunkTMX provides an easy to use method for designing and importing pymunk
shapes from a Tiled Mapeditor Map file (tmx). It is designed to provide this
functionality as an extension to the excellent PyTMX library which is a
dependency of PyMunkTMX.

The only function a developer would most likely need from this module is
load_shapes. The other functions are documented in the case that some special
functionality is required.


.. py:data:: PYMUNK_TYPES

   This dict represents both the list of supported
   pymunk shapes as well as a mapping of the shape type to the function
   that can load it.

.. moduleauthor:: William Kevin Manire <williamkmanire@gmail.com>
"""

from functools import partial
from uuid import uuid4
from xml.etree import ElementTree
import logging
import re

logger = logging.getLogger("pymunktmx.shapeloader")

import pymunk
import pymunk.util

GLOBAL_DEFAULTS = {"pymunktmx_box": dict(),
                   "pymunktmx_poly": dict(),
                   "pymunktmx_circle": dict(),
                   "pymunktmx_segment": dict()}


def load_defaults(objects_xml_data):
    defaults = dict(GLOBAL_DEFAULTS)
    parse = ElementTree.fromstring
    node = parse(objects_xml_data).find("pymunktmx_defaults")
    for shape_node in node:
        logger.debug(shape_node.tag)
        if shape_node.tag in defaults:
            d = defaults[shape_node.tag]
            for default in shape_node.findall("default"):
                d[default.get("key")] = default.get("value")

    return defaults


def load_tmxdata_defaults(tmxdata):
    defaults = dict(GLOBAL_DEFAULTS)
    for key, value in tmxdata.__dict__.items():
        logger.debug(key)
        for prefix in GLOBAL_DEFAULTS:
            if key.startswith(prefix):
                parts = key.split(".")
                defaults[parts[0]][".".join(parts[1:])] = value
    return defaults

def set_attrs(attrs, obj, skip_keys=[]):
    """
    Given a set of attributes as a dict, set those attributes on an object.

    :param dict attrs: A dict of attribute names and values.
    :param object obj: An object to set the attributes on
    :param list skip_keys: A list, set or tuple of keys to skip.
    :rtype: None
    :return: None
    :raises AttributeError: If the attribute cannot be set.
    """
    for key, value in attrs.items():
        if key in skip_keys:
            continue
        try:
            setattr(obj, key, value)
        except AttributeError as ex:
            logger.error("Could not set %s to %s on object %s"
                         % (str(key), str(value), str(obj)))
            raise ex


def get_attrs(attrs_type, tmxobject, defaults):
    """
    Parse properties from a TiledObject and return them as a dict.

    :param str attrs_type: A prefix used to filter which object properties \
    to return. It must be one of 'shape', 'body', 'circle' or 'segment'.
    :param TiledObject tmxobject: The pytmx TiledObject instance that \
    contains the properties to be parsed.

    :rtype: dict
    :return: A dict of property keys and values.
    :raises ValueError: If the attrs_type param is not one of the \
    supported prefixes.
    """
    attr_types = set([u"shape", u"body", u"circle", u"segment"])
    if attrs_type not in attr_types:
        raise ValueError(u"attrs_type must be one of %s" % unicode(attr_types))

    attrs = dict(defaults)
    attrs.update(tmxobject.__dict__)
    out_attrs = dict()
    for key, value in attrs.items():
        parts = key.split(u".")
        if len(parts) != 2:
            continue
        cat, prop = parts
        if cat == attrs_type:
            out_attrs[prop] = value
    return out_attrs


def uint(n):
    """
    This is an internal utility function that is intended to correct negative
    bitmask values for pymunk.

    :param int n: An integral number.
    :return: A positive integer.
    :rtype: int
    """
    return abs(int(n))

# flexible regexp for matching coordinate pairs
COORDS_RE = re.compile(
    r"^\(?\s*([-+]?[0-9]*\.?[0-9]+)\s*,\s*([-+]?[0-9]*\.?[0-9]+)\s*\)?$")


def parse_coordinates(coord_string):
    """
    Parses a coordinate tuple of floats from a string. It can handle any
    combination of the following formats:

    - (x, y)
    - x, y
    - x,y
    - x.0, y.0
    - (x.0, y.0)

    :param str coord_string: A string containing a coordinate expression.

    :rtype: tuple
    :return: A tuple of floats representing the x and y axis. (1.0, 2.0)
    :raises ValueError: If a coordinate tuple cannot be parsed from the string.
    """
    if coord_string is None:
        return None

    match = COORDS_RE.match(coord_string)
    if not match:
        raise ValueError("Invalid coordinate string")

    return (float(match.group(1)), float(match.group(2)))


def get_body_attrs(tmxobject, defaults):
    """
    Parses all body properties (body.xxx) from the TiledObject.

    :param TiledObject tmxobject: The TiledObject instance to parse body \
    properties from.

    :rtype: dict
    :return: A dict of parsed body properties with sane defaults applied.
    """
    attrs = get_attrs(u"body", tmxobject, defaults)
    body_attrs = {
        u"angle": float(attrs.get(u"angle", 0.0)),
        u"angular_velocity_limit": float(
            attrs.get(u"angular_velocity_limit", pymunk.inf)),
        u"mass": float(attrs.get(u"mass", 1.0)),
        u"position": parse_coordinates(attrs.get("position")),
        u"offset": parse_coordinates(attrs.get("offset", "(0, 0)")),
        u"velocity_limit": float(attrs.get(u"velocity_limit", pymunk.inf)),
        u"sensor": attrs.get(u"sensor", u"false").lower() == u"true",
        u"static": attrs.get(u"static", u"true").lower() == u"true",
    }

    return body_attrs


def get_shape_attrs(tmxobject, defaults):
    """
    Parses all shape properties (shape.xxx) from the TiledObject.

    :param TiledObject tmxobject: The TiledObject instance to parse shape \
    properties from.

    :rtype: dict
    :return: A dict of parsed shape properties with sane defaults applied.
    """
    attrs = get_attrs(u"shape", tmxobject, defaults)
    shape_attrs = {
        u"collision_type": uint(attrs.get(u"collision_type", 0)),
        u"elasticity": float(attrs.get(u"elasticity", 0.0)),
        u"friction": float(attrs.get(u"friction", 0.0)),
        u"layers": int(attrs.get(u"layers", -1)),
        u"sensor": attrs.get(u"sensor", u"false").lower() == u"true",
        u"radius": int(attrs.get(u"radius", 0.0))
    }
    return shape_attrs


def get_circle_attrs(tmxobject, defaults):
    """
    Parses all circle properties (circle.xxx) from the TiledObject.

    :param TiledObject tmxobject: The TiledObject instance to parse circle \
    properties from.

    :rtype: dict
    :return: A dict of parsed circle properties with sane defaults applied.
    """
    attrs = get_attrs(u"circle", tmxobject, defaults)
    shape_attrs = {
        u"inner_radius": float(attrs.get(u"inner_radius", 0.0))
    }
    return shape_attrs


def get_segment_attrs(tmxobject, defaults):
    """
    Parses all segment properties (segment.xxx) from the TiledObject.

    :param TiledObject tmxobject: The TiledObject instance to parse segment \
    properties from.

    :rtype: dict
    :return: A dict of parsed segment properties with sane defaults applied.
    """
    attrs = get_attrs(u"segment", tmxobject, defaults)
    segment_attrs = {
        u"radius": float(attrs.get(u"radius", 1.0))
    }
    return segment_attrs


def get_shape_name(tmxobject, suffix_fn=uuid4):
    """
    Returns the name of a TiledObject if it has one, otherwise it generates a
    name using the type and the return value of the suffix_fn. By default the
    suffix function is uuid.uuid4() but any function which returns a unique
    string can be used in its place.

    Example Auto Generated Name:
        "pymunk_circle_39869097-98fd-473d-b513-f0ad0cf2f368"

    :param TiledObject tmxobject: The TiledObject instance to get the name \
    from.
    :param function suffix_fn: A function that returns a unique string.
    :rtype: string
    :return: The original, or new name of the TiledObject.
    """
    if tmxobject.name is None:
        return tmxobject.type + u"_" + unicode(suffix_fn())
    return tmxobject.name


def load_box(tmxobject, map_height, static_body, defaults):
    """
    Creates a pymunk.Poly in the shape of a box from a TiledObject instance and
    orients it relative to the height of a TiledMap.

    :param TiledObject tmxobject: A TiledObject instance that represents a box.
    :param int map_height: The height of the TiledMap that the TiledObject \
    was loaded from in pixels.

    :rtype: pymunk.Poly
    :return: A pymunk.Poly shape instance.
    """
    box_defaults = defaults["pymunktmx_box"]
    shape_attrs = get_shape_attrs(tmxobject, box_defaults)
    body_attrs = get_body_attrs(tmxobject, box_defaults)
    offset = body_attrs[u"offset"]
    radius = shape_attrs[u"radius"]

    shape = None
    if body_attrs[u"static"]:
        tl = tmxobject.x, float(map_height) - tmxobject.y
        tr = tmxobject.x + tmxobject.width, tl[1]
        bl = tl[0], float(map_height) - (tmxobject.y + tmxobject.height)
        br = tr[0], bl[1]
        verts = [tl, bl, br, tr]
        shape = pymunk.Poly(static_body, verts, offset, radius)
    else:
        x = float(tmxobject.x)
        y = float(float(map_height) - tmxobject.y)
        mass = body_attrs[u"mass"]
        tl = 0.0, 0.0
        tr = float(tmxobject.width), 0.0
        bl = 0, -float(tmxobject.height)
        br = tr[0], bl[1]
        verts = [tl, bl, br, tr]
        moment = pymunk.moment_for_box(
            mass, tmxobject.height, tmxobject.width)
        body = pymunk.Body(mass, moment)
        body.position = (x, y)

        set_attrs(body_attrs, body,
                  skip_keys=[u"position", u"mass", u"static"])

        shape = pymunk.Poly(body, verts, offset, radius)

    set_attrs(shape_attrs, shape, skip_keys=[u"radius"])
    return [shape]


def load_circle(tmxobject, map_height, static_body, defaults):
    """
    Creates a pymunk.Circle parsed from a TiledObject instance.

    :param TiledObject tmxobject: A TiledObject instance that represents a \
    circle.
    :param int map_height: The height of the TiledMap that the TiledObject \
    was loaded from in pixels.

    :rtype: pymunk.Circle
    :return: A pymunk.Circle shape instance.
    """
    if tmxobject.width != tmxobject.height:
        raise ValueError(u"pymunk only supports perfectly round circles. "
                         "No ovals or other non-uniform ellipses.")

    circle_defaults = defaults["pymunktmx_circle"]
    shape_attrs = get_shape_attrs(tmxobject, circle_defaults)
    body_attrs = get_body_attrs(tmxobject, circle_defaults)
    circle_attrs = get_circle_attrs(tmxobject, circle_defaults)
    outer_radius = float(tmxobject.width / 2.0)
    offset = body_attrs["offset"]
    x = float(tmxobject.x) + outer_radius
    y = float(float(map_height) - (tmxobject.y + outer_radius))

    shape = None

    if body_attrs[u"static"]:
        shape = pymunk.Circle(pymunk.Body(), outer_radius, offset)
    else:
        moment = pymunk.moment_for_circle(
            body_attrs[u"mass"],
            circle_attrs[u"inner_radius"],
            outer_radius,
            body_attrs[u"offset"])
        body = pymunk.Body(body_attrs[u"mass"], moment)
        set_attrs(body_attrs, body,
                  skip_keys=[u"position", u"mass", u"static"])

        shape = pymunk.Circle(body, outer_radius, offset)

    shape.body.position = (x, y)
    set_attrs(shape_attrs, shape, skip_keys=[u"radius"])
    return [shape]


def load_poly(tmxobject, map_height, static_body, defaults):
    """
    Creates a pymunk.Poly parsed from a TiledObject instance.

    :param TiledObject tmxobject: A TiledObject instance that represents a \
    convex polygon with multiple vertices.
    :param int map_height: The height of the TiledMap that the TiledObject \
    was loaded from in pixels.

    :rtype: pymunk.Poly
    :return: A pymunk.Poly shape instance.
    """
    if pymunk.util.is_convex(list(tmxobject.points)):
        return load_poly_convex(tmxobject, map_height, static_body, defaults)
    else:
        return load_poly_concave(tmxobject, map_height, static_body, defaults)


def load_poly_convex(tmxobject, map_height, static_body, defaults):
    """
    Creates a pymunk.Poly parsed from a TiledObject instance.

    :param TiledObject tmxobject: A TiledObject instance that represents a \
    convex polygon with multiple vertices.
    :param int map_height: The height of the TiledMap that the TiledObject \
    was loaded from in pixels.

    :rtype: pymunk.Poly
    :return: A pymunk.Poly shape instance.
    """
    poly_defaults = defaults["pymunktmx_poly"]
    shape_attrs = get_shape_attrs(tmxobject, poly_defaults)
    body_attrs = get_body_attrs(tmxobject, poly_defaults)
    offset = body_attrs[u"offset"]
    radius = shape_attrs[u"radius"]

    shape = None
    if body_attrs[u"static"]:
        verts = [(p[0], map_height - p[1]) for p in tmxobject.points]
        shape = pymunk.Poly(static_body, verts, offset, radius)
    else:
        x = float(tmxobject.x)
        y = float(float(map_height) - tmxobject.y)
        mass = body_attrs[u"mass"]
        verts = [(p[0] - x, -(p[1] - y))
                 for p in tmxobject.points]
        moment = pymunk.moment_for_poly(mass, verts, offset)
        body = pymunk.Body(mass, moment)

        set_attrs(body_attrs, body,
                  skip_keys=[u"position", u"mass", u"static"])

        body.position = (x, y)
        shape = pymunk.Poly(body, verts, offset, radius)

    set_attrs(shape_attrs, shape, skip_keys=[u"radius"])
    return [shape]


def load_poly_concave(tmxobject, map_height, static_body, defaults):
    """
    Creates several pymunk.Poly objects parsed from a TiledObject instance.
    They share a common pymunk.Body object.

    :param TiledObject tmxobject: A TiledObject instance that represents a \
    concave polygon with multiple vertices.
    :param int map_height: The height of the TiledMap that the TiledObject \
    was loaded from in pixels.

    """

    poly_defaults = defaults["pymunktmx_poly"]
    shape_attrs = get_shape_attrs(tmxobject, poly_defaults)
    body_attrs = get_body_attrs(tmxobject, poly_defaults)
    offset = body_attrs[u"offset"]
    radius = shape_attrs[u"radius"]

    # break concave shape into triangles
    points = list(tmxobject.points)

    # pymunk.util.triangulate expects the list to be in anti-clockwise order
    if pymunk.util.is_clockwise(points):
        points.reverse()

    # the pymunk.util.convexise doesn't create shapes that match originals
    # so we will just use the triangles
    triangles = pymunk.util.triangulate(points)

    shapes = []
    if body_attrs[u"static"]:
        for vertices in triangles:
            vertices = [(p[0], map_height - p[1]) for p in vertices]
            shape = pymunk.Poly(static_body, vertices, offset, radius)
            shapes.append(shape)

    else:
        x = float(tmxobject.x)
        y = float(float(map_height) - tmxobject.y)
        mass = body_attrs[u"mass"]
        verts = [(p[0] - x, -(p[1] - y)) for p in tmxobject.points]
        moment = pymunk.moment_for_poly(mass, verts, offset)
        body = pymunk.Body(mass, moment)
        body.position = (x, y)

        set_attrs(body_attrs, body,
                  skip_keys=[u"position", u"mass", u"static"])

        for vertices in triangles:
            vertices = [(p[0] - x, -(p[1] - y)) for p in vertices]
            shape = pymunk.Poly(body, vertices, offset, radius)
            shapes.append(shape)

        shapes.append(body)

    for shape in shapes:
        set_attrs(shape_attrs, shape, skip_keys=[u"radius"])

    return shapes


def load_segment(tmxobject, map_height, static_body, defaults):
    """
    Creates a pymunk.Segment parsed from a TiledObject instance.

    :param TiledObject tmxobject: A TiledObject instance that represents a \
    line segment with two points, A to B.
    :param int map_height: The height of the TiledMap that the TiledObject \
    was loaded from in pixels.

    :rtype: pymunk.Segment
    :return: A pymunk.Segment shape instance.
    """
    segment_defaults = defaults["pymunktmx_segment"]
    shape_attrs = get_shape_attrs(tmxobject, segment_defaults)
    body_attrs = get_body_attrs(tmxobject, segment_defaults)
    radius = shape_attrs[u"radius"]

    shape = None
    if body_attrs[u"static"]:
        verts = [(p[0], map_height - p[1]) for p in tmxobject.points]
        shape = pymunk.Segment(static_body, verts[0], verts[1], radius)
    else:
        x = float(tmxobject.x)
        y = float(float(map_height) - tmxobject.y)
        mass = body_attrs[u"mass"]
        verts = [(p[0] - x, map_height - p[1] - y)
                 for p in tmxobject.points]
        moment = pymunk.moment_for_segment(mass, verts[0], verts[1])
        body = pymunk.Body(mass, moment)

        set_attrs(body_attrs, body,
                  skip_keys=[u"position", u"mass", u"static"])

        body.position = (x, y)
        shape = pymunk.Segment(body, verts[0], verts[1], radius)

    set_attrs(shape_attrs, shape, skip_keys=[u"radius"])

    return [shape]


PYMUNK_TYPES = {u"pymunktmx_box": load_box,
                u"pymunktmx_circle": load_circle,
                u"pymunktmx_poly": load_poly,
                u"pymunktmx_segment": load_segment}


def find_shapes(tmxdata):
    """
    This is a generator function that yields all recognized pymunk shapes from
    all object groups of the TiledMap instance.

    :param TiledMap tmxdata: The TiledMap instance to search for pymunk \
    shapes in.

    :rtype: generator
    :return: A generator that yields TiledObject instances.
    """
    for objectgroup in tmxdata.objectgroups:
        for tmxobject in objectgroup:
            if tmxobject.type in PYMUNK_TYPES:
                yield tmxobject, tmxobject.type


def _add_shapes(shapes_dict, shapes, space, name):
    for i, shape in enumerate(shapes):

        # enumerate the names in case we have broken a shape down
        # (such as in the case of hulling concave polygons)
        if len(shapes) > 1:
            shape_name = "%s_%d" % (name, i)
        else:
            shape_name = name

        shapes_dict[shape_name] = shape
        if space is not None:
            if shape.body is not None:
                if not shape.body.is_static and \
                   shape.body not in space.bodies:
                    space.add(shape.body)
            space.add(shape)
    logger.debug("Loaded shape %s" % name)


class MunkModelFactory(object):
    """
    Use the load_shapes arg with factory_mode=True in order to create
    an instance of MunkModelFactory from a TMX tile map. A
    MunkModelFactory can create multiple identical instances of
    complex models of shapes for inclusion in your game objects. The
    intended strategy of use is not to sub-class MunkModel, but to
    pass a MunkModel created with the create_model function to your
    controlling code or perhaps to the __init__ of your game object
    class.
    """

    def __init__(self, shape_factories):
        self.shape_factories = shape_factories

    def create_model(self, space=None, id_fn=uuid4):
        model = MunkModel(id_fn())
        for name, factory_fn in self.shape_factories:
            shapes = factory_fn()
            _add_shapes(model, shapes, space, name)
        return model


class MunkModel(dict):
    """
    MunkModel's sole purpose is to extend the dict class with an
    additional attribute, id, which helps to uniquely identify a
    grouping of pymunk shapes, mostly for debug purposes. Otherwise
    this dict sub-class provides a convenient method for looking up
    particular shapes within a complex model of pymunk shapes.
    """

    def __init__(self, id, *args):
        """
        Instances of MunkModel should not normally need to be created
        directly. instead, create MunkModel instances using a
        MunkModelFactory.

        :param object id: A unique identifier for this model instance.
        :param iterable args: An iterable of tuples of shape names and,
        shape constructor functions.

        """
        super(dict, self).__init__(args)
        self.id = id


def load_shapes(tmxdata, space=None, objects_xml_path=None,
                factory_mode=False):
    """
    load_shapes has two distinct operational modes.

    In the default mode, load_shapes returns a collection of
    pre-configured pymunk shapes parsed from a PyTMX
    TiledMap. Optionally, a Space instance may be provided and all of
    the shapes will be added to it. If a file path to a tiled object
    definition xml file is provided, then default shape properties
    will be loaded from it and applied to the shapes loaded from the
    tmxdata.

    In factory mode (factory_mode=True), A MunkModelFactory instance
    will be returned which may be used to create multiple identical
    instances of the shapes loaded from the tmxdata.

    :param pymunk.Space space: A pymunk Space instance to load all of the \
    found shapes into. This param os optional.
    :param str objects_xml_path: Path to a Tiled objects definition XML file.
    :param TiledMap tmxdata: A TiledMap instance loaded from a tmx file with \
    pytmx.
    :param bool factory_mode: Changes the behavior of the function. See the \
    docstring for more information.

    :rtype: dict
    :return: A dict of shape names and pymunk shapes.

    """

    # try to load defaults from objects.xml file
    defaults = dict(GLOBAL_DEFAULTS)
    if objects_xml_path is not None:
        with open(objects_xml_path, "rb") as fob:
            data = fob.read()
        defaults = load_defaults(data)

    # override global defaults with map local defaults
    tmxdata_defaults = load_tmxdata_defaults(tmxdata)
    for key, d in tmxdata_defaults.items():
        defaults[key].update(d)

    all_shapes = dict()
    all_factories = list()

    objects = ((o, o.type) for g in tmxdata.objectgroups
               for o in g if o.type in PYMUNK_TYPES)

    map_height = tmxdata.height * tmxdata.tileheight

    static_body = None
    if space is not None:
        static_body = space.static_body

    load_fn_map = {"pymunktmx_box": load_box,
                   "pymunktmx_circle": load_circle,
                   "pymunktmx_poly": load_poly,
                   "pymunktmx_segment": load_segment}

    for o, t in objects:
        name = get_shape_name(o)
        o.name = name
        load_fn = load_fn_map.get(t)
        if load_fn is not None:
            if factory_mode:
                factory_fn = partial(load_fn, o, map_height,
                                     static_body, defaults)
                all_factories.append((name, factory_fn))
            else:
                _add_shapes(
                    all_shapes,
                    load_fn(o, map_height, static_body, defaults),
                    space,
                    o.name)

    if factory_mode:
        return MunkModelFactory(all_factories)

    return all_shapes
