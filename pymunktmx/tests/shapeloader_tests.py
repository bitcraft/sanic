# -*- coding: utf-8; -*-

from os.path import join
from os.path import realpath
from os.path import split
from unittest import TestCase

from pytmx.tmxloader import load_tmx
from pymunktmx.shapeloader import *


OBJECTSXML = u"""<?xml version="1.0" encoding="UTF-8"?>
<objecttypes>
 <objecttype name="pymunktmx_box" color="#a40002"/>
 <objecttype name="pymunktmx_poly" color="#a400a4"/>
 <objecttype name="pymunktmx_circle" color="#00fbff"/>
 <objecttype name="pymunktmx_segment" color="#00ff08"/>

 <pymunktmx_defaults>
   <pymunktmx_box>
     <default key="body.static" value="True" />
     <default key="shape.friction" value="0.9" />
   </pymunktmx_box>

   <pymunktmx_poly>
     <default key="body.static" value="True" />
     <default key="shape.friction" value="0.9" />
   </pymunktmx_poly>

   <pymunktmx_circle>
     <default key="circle.inner_radius" value="1.23" />
   </pymunktmx_circle>
 </pymunktmx_defaults>
</objecttypes>
"""


class ShapeLoaderTests(TestCase):

    def setUp(self):
        self.path = split(realpath(__file__))[0]
        self.tmxdata = load_tmx(join(self.path, "shapes.tmx"))
        self.objects_xml_path = join(self.path, "objects.xml")
        self.maxDiffDefault = self.maxDiff
        self.maxDiff = 1000

    def tearDown(self):
        self.maxDiff = self.maxDiffDefault

    def get_shape_by_name(self, name):
        for shape, _ in find_shapes(self.tmxdata):
            if shape.name == name:
                return shape

    def get_shape_by_name_test(self):
        poly = self.get_shape_by_name("static_poly")
        self.assertIsNotNone(poly)

    def COORDS_RE_test(self):
        data = "(1, 1)|1, 1|1,1|(1.5, 1.5)|1.5,1.5|1.5, 1.5|-1.5, -1.5|-1.5, 1"
        patterns = data.split("|")
        valid_nums = set(["1", "-1", "1.5", "-1.5"])
        for pattern in patterns:
            m = COORDS_RE.match(pattern)
            self.assertIsNotNone(m)
            x = m.group(1)
            y = m.group(2)
            self.assertTrue(x in valid_nums)
            self.assertTrue(y in valid_nums)

    def parse_coords_test(self):
        coords = parse_coordinates("(17, 1.567)")
        self.assertEqual(coords, (17.0, 1.567))
        self.assertIsNone(parse_coordinates(None))

    def parse_coords_bad_Test(self):
        self.assertRaises(ValueError, parse_coordinates, "asdfasdf")

    def find_shapes_test(self):
        all_shapes = find_shapes(self.tmxdata)
        self.assertEquals(len(list(all_shapes)), 10)

    def set_attrs_test(self):

        class TestObj(object):

            def __init__(self):
                self.foo = "bar"
                self.bar = "foo"

            def __setattr__(self, key, value):
                if key == "blah":
                    raise AttributeError("Na na na na, can't touch this")
                else:
                    self.__dict__[key] = value


        obj = TestObj()
        set_attrs({"foo": 123, "bar": 321}, obj, skip_keys=["bar"])
        self.assertEqual(123, obj.foo)
        self.assertEqual("foo", obj.bar)
        self.assertRaises(AttributeError, set_attrs, {"blah": None}, obj)

    def get_attrs_test(self):
        shape = self.get_shape_by_name(u"circle")
        self.assertRaises(ValueError, get_attrs, "non-existant", dict(), None)

        type_and_counts = ((u"shape", 5), (u"body", 8), (u"circle", 1),
                           (u"segment", 0))
        for t, c in type_and_counts:
            self.assertEqual(c, len(get_attrs(t, shape, dict())))

    def get_body_attrs_test(self):
        shape = self.get_shape_by_name(u"circle")
        body_attrs = {
            u"angle": 1.0,
            u"angular_velocity_limit": 5.0,
            u"mass": 17.321,
            u"position": (15.0, 15.0),
            u"offset": (-5.1, 16.2),
            u"velocity_limit": 1.123,
            u"sensor": True,
            u"static": False
        }
        self.assertEqual(get_body_attrs(shape, dict()), body_attrs)

    def get_shape_attrs_test(self):
        shape = self.get_shape_by_name(u"circle")
        shape_attrs = {
            u"collision_type": 8,
            u"elasticity": 0.55,
            u"friction": 1.125,
            u"layers": 8,
            u"radius": 0.0,
            u"sensor": True
        }
        self.assertEqual(get_shape_attrs(shape, dict()), shape_attrs)

    def get_circle_attrs_test(self):
        shape = self.get_shape_by_name(u"circle")
        circle_attrs = {
            u"inner_radius": 10.0
        }
        self.assertEqual(get_circle_attrs(shape, dict()), circle_attrs)

    def get_segment_attrs_test(self):
        shape = self.get_shape_by_name(u"segment")
        segment_attrs = {
            u"radius": 2.447
        }
        self.assertEqual(get_segment_attrs(shape, dict()), segment_attrs)

    def get_shape_name_test(self):
        shape = self.get_shape_by_name(u"circle")
        self.assertEqual(u"circle", get_shape_name(shape))
        shape.name = None

        def suffix_fn():
            return "suffix"

        self.assertEqual(u"pymunktmx_circle_suffix",
                         get_shape_name(shape, suffix_fn))

    def load_box_test(self):
        tmxobj = self.get_shape_by_name(u"rigid_body_box")
        space = pymunk.Space()
        box = load_box(tmxobj, 768, space.static_body, GLOBAL_DEFAULTS)[0]
        posx, posy = box.body.position
        verts = [(v[0], v[1]) for v in reversed(box.get_vertices())]
        self.assertEqual([(posx, posy),
                          (posx, posy - 96.0),
                          (posx + 96.0, posy - 96.0),
                          (posx + 96.0, posy)],
                         verts)
        self.assertEqual(box.body.position, (128.0, 768.0))

        box_with_angle = load_box(
            self.get_shape_by_name(u"box_with_angle"),
            768, space.static_body, GLOBAL_DEFAULTS)[0]
        self.assertEqual(box_with_angle.body.angle, 1.232)

        tmxobj = self.get_shape_by_name(u"static_box")
        box = load_box(tmxobj, 768, space.static_body, GLOBAL_DEFAULTS)[0]
        verts = [(v[0], v[1]) for v in reversed(box.get_vertices())]
        self.assertEqual([(128, 512.0),
                          (128, 416.0),
                          (224, 416.0),
                          (224, 512.0)],
                         verts)

    def load_circle_test(self):
        space = pymunk.Space()
        tmxobj = self.get_shape_by_name(u"circle")
        self.assertIsNotNone(tmxobj)
        circle = load_circle(tmxobj, 768, space.static_body, GLOBAL_DEFAULTS)[0]
        self.assertEqual(circle.body.position, (304.0, 720.0))
        self.assertEqual(circle.radius, 48.0)

        setattr(tmxobj, "body.static", "True")
        circle = load_circle(tmxobj, 768, space.static_body, GLOBAL_DEFAULTS)
        self.assertIsNotNone(circle)

        ovalobj = self.get_shape_by_name(u"oval")
        self.assertRaises(ValueError, load_circle, ovalobj, 768,
                          space.static_body, dict())

    def load_poly_test(self):
        tmxobj = self.get_shape_by_name("static_poly")
        space = pymunk.Space()
        poly = load_poly(tmxobj, 768, space.static_body, GLOBAL_DEFAULTS)[0]
        verts = [(v[0], v[1]) for v in reversed(poly.get_vertices())]
        self.assertEqual([(32.0, 768.0),
                          (0.0, 736.0),
                          (0.0, 704.0),
                          (32.0, 672.0),
                          (64.0, 672.0),
                          (96.0, 704.0),
                          (96.0, 736.0),
                          (64.0, 768.0)],
                         verts)

        tmxobj = self.get_shape_by_name("rigid_body_poly")
        poly = load_poly(tmxobj, 768, space.static_body, GLOBAL_DEFAULTS)[0]
        self.assertEqual(poly.body.position, (32.0, 640.0))
        verts = [(v[0], v[1]) for v in reversed(poly.get_vertices())]
        self.assertEqual([(32.0, 1152.0),
                          (0.0, 1120.0),
                          (0.0, 1088.0),
                          (32.0, 1056.0),
                          (64.0, 1056.0),
                          (96.0, 1088.0),
                          (96.0, 1120.0),
                          (64.0, 1152.0)],
                         verts)

    def load_segment_test(self):
        space = pymunk.Space()
        tmxobj = self.get_shape_by_name("segment")
        segment = load_segment(tmxobj, 768, space.static_body, GLOBAL_DEFAULTS)[0]
        self.assertEqual(segment.a, (384.0, 768.0))
        self.assertEqual(segment.b, (480.0, 672.0))

    def load_shapes_test(self):
        space = pymunk.Space()
        all_good_tmxdata = load_tmx(join(self.path, "shapes_all_good.tmx"))
        shapes = load_shapes(all_good_tmxdata, space)
        self.assertEqual(12, len(shapes))
        self.assertEqual(13, len(space._shapes))

    def load_shapes_with_global_defaults_test(self):
        space = pymunk.Space()
        all_good_tmxdata = load_tmx(join(self.path, "shapes_all_good.tmx"))
        shapes = load_shapes(all_good_tmxdata, space, self.objects_xml_path)
        self.assertEqual(12, len(shapes))
        self.assertEqual(13, len(space._shapes))

    def non_rigid_shapes_use_static_body_test(self):
        """
        static shapes, like level geometry, should all use a common body,
        for performance reasons. the load_shape functions cannot
        handle shapes in this way since they do not have a reference
        to the space. a reference should be added, along with check to
        make sure the space is not none. - bitcraft
        """
        space = pymunk.Space()
        all_good_tmxdata = load_tmx(join(self.path, "shapes_all_good.tmx"))
        shapes = load_shapes(all_good_tmxdata, space)
        self.assertTrue(len(shapes) > 0)
        for name, shape in shapes.items():
            if name == "box2":
                self.assertIs(shape.body, space.static_body)

    def load_poly_concave_rigid_test(self):
        tmxobj = self.get_shape_by_name("concave_poly_rigid")
        space = pymunk.Space()

        # Tiled will always return the points in counter-clockwise
        # order so we need to reverse them in order to test the
        # is_clockwise usage in load_poly_concave.
        tmxobj.points = tuple([t for t in reversed(tmxobj.points)])

        objects = load_poly(tmxobj, 768, space.static_body, GLOBAL_DEFAULTS)

        # let's just make sure there is only 1 body in the returned list
        # testing the vertex math would only prove that pymunk isn't broken
        # which is an assumption we have to make here
        bodies = [b for b in objects if isinstance(b, pymunk.Body)]

        # make sure there is only 1 body
        self.assertEqual(1, len(bodies))

        # make sure everything else is a shape that has the same body
        # instance
        body = bodies[0]
        for o in objects:
            if o is not body:
                self.assertIs(o.body, body)

    def load_poly_concave_static_test(self):
        tmxobj = self.get_shape_by_name("concave_poly_static")
        space = pymunk.Space()
        tmxobj.points = tuple([t for t in reversed(tmxobj.points)])
        objects = load_poly(tmxobj, 768, space.static_body, GLOBAL_DEFAULTS)
        for o in objects:
            self.assertIs(o.body, space.static_body)

    def load_defaults_test(self):
        defaults = load_defaults(OBJECTSXML)
        expected = {
            "pymunktmx_box": {"body.static": "True",
                              "shape.friction": "0.9"},

            "pymunktmx_poly": {"body.static": "True",
                               "shape.friction": "0.9"},

            "pymunktmx_circle": {"circle.inner_radius": "1.23"},

            "pymunktmx_segment": dict()
        }
        self.assertEqual(defaults, expected)

    def munk_model_factory_test(self):
        factory = MunkModelFactory(123)
        self.assertEquals(factory.shape_factories, 123)

    def munk_model_factory_create_model_test(self):
        factory = MunkModelFactory([("foo", lambda: ["bar"])])
        model = factory.create_model(id_fn=lambda: "id")
        self.assertIsNotNone(model)
        self.assertIn("foo", model)
        self.assertEquals("id", model.id)

    def munk_load_shapes_factory_mode_test(self):
        space = pymunk.Space()
        all_good_tmxdata = load_tmx(join(self.path, "shapes_all_good.tmx"))
        factory = load_shapes(all_good_tmxdata, space, factory_mode=True)
        self.assertIsInstance(factory, MunkModelFactory)
