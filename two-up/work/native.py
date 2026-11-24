"""Small stock-feature builder; completed FCStd files need no project code."""
import math
import FreeCAD as App
import Part
import Sketcher


class E(float):
    def __new__(cls, value, expression):
        obj = super().__new__(cls, value)
        obj.expression = expression
        return obj

    def op(self, other, sign, operation):
        return E(operation(float(self), float(other)), '(' + ex(self) + sign + ex(other) + ')')

    def __add__(self, v): return self.op(v, '+', lambda a, b: a + b)
    __radd__ = __add__
    def __sub__(self, v): return self.op(v, '-', lambda a, b: a - b)
    def __rsub__(self, v): return E(float(v) - float(self), '(' + ex(v) + '-' + ex(self) + ')')
    def __mul__(self, v): return self.op(v, '*', lambda a, b: a * b)
    __rmul__ = __mul__
    def __truediv__(self, v): return self.op(v, '/', lambda a, b: a / b)
    def __neg__(self): return E(-float(self), '(-' + ex(self) + ')')


def ex(value):
    return value.expression if isinstance(value, E) else repr(float(value))


def bind(obj, prop, value):
    if isinstance(value, E): obj.setExpression(prop, value.expression)


class Native:
    def __init__(self, document, group):
        self.doc, self.group = document, group

    def obj(self, kind, name, label):
        obj = self.doc.addObject(kind, name)
        obj.Label = label
        self.group.addObject(obj)
        obj.addProperty('App::PropertyString', 'DesignFamily', 'Provenance')
        obj.DesignFamily = 'Minimalist M1'
        return obj

    def sketch(self, name, wires, plane='XY', origin=(0, 0, 0)):
        obj = self.obj('Sketcher::SketchObject', name, name)
        rotations = {
            'XY': App.Rotation(),
            'YZ': App.Rotation(App.Vector(0, 1, 0), App.Vector(0, 0, 1), App.Vector(1, 0, 0), 'ZXY'),
            'XZ': App.Rotation(App.Vector(1, 0, 0), 90),
        }
        obj.Placement = App.Placement(App.Vector(*map(float, origin)), rotations[plane])
        for axis, value in zip('xyz', origin): bind(obj, 'Placement.Base.' + axis, value)
        for points in wires:
            first = obj.GeometryCount
            count = len(points)
            obj.addGeometry([Part.LineSegment(App.Vector(float(points[i][0]), float(points[i][1]), 0),
                                             App.Vector(float(points[(i + 1) % count][0]),
                                                        float(points[(i + 1) % count][1]), 0))
                             for i in range(count)], False)
            for i in range(count):
                obj.addConstraint(Sketcher.Constraint('Coincident', first + i, 2, first + (i + 1) % count, 1))
            for i, point in enumerate(points):
                for axis, value in zip('XY', point):
                    ci = obj.addConstraint(Sketcher.Constraint('Distance' + axis, first + i, 1, float(value)))
                    bind(obj, 'Constraints[' + str(ci) + ']', value)
        obj.Visibility = False
        return obj

    def circle(self, name, circles, plane='XY', origin=(0, 0, 0)):
        obj = self.sketch(name, [], plane, origin)
        for x, y, radius in circles:
            i = obj.addGeometry(Part.Circle(App.Vector(float(x), float(y), 0), App.Vector(0, 0, 1), float(radius)), False)
            for axis, value in zip('XY', (x, y)):
                ci = obj.addConstraint(Sketcher.Constraint('Distance' + axis, i, 3, float(value)))
                bind(obj, 'Constraints[' + str(ci) + ']', value)
            ci = obj.addConstraint(Sketcher.Constraint('Radius', i, float(radius)))
            bind(obj, 'Constraints[' + str(ci) + ']', radius)
        return obj

    def extrusion(self, name, sketch, length):
        obj = self.obj('Part::Extrusion', name, name)
        obj.Base = sketch
        obj.DirMode = 'Normal'
        obj.LengthFwd = float(length)
        bind(obj, 'LengthFwd', length)
        obj.Solid = True
        sketch.Visibility = False
        obj.Visibility = False
        return obj

    def prism(self, name, points, plane, origin, length):
        return self.extrusion(name, self.sketch(name + 'Profile', [points], plane, origin), length)

    def box(self, name, x0, x1, y0, y1, z0, z1):
        return self.prism(name, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 'XY', (0, 0, z0), z1 - z0)

    def fuse(self, name, shapes):
        obj = self.obj('Part::MultiFuse', name, name)
        obj.Shapes = shapes
        obj.Refine = True
        for shape in shapes: shape.Visibility = False
        obj.Visibility = False
        return obj

    def compound(self, name, shapes):
        obj = self.obj('Part::Compound', name, name)
        obj.Links = shapes
        for shape in shapes: shape.Visibility = False
        obj.Visibility = False
        return obj

    def cut(self, name, shape, tool):
        obj = self.obj('Part::Cut', name, name)
        obj.Base, obj.Tool, obj.Refine = shape, tool, True
        shape.Visibility = tool.Visibility = obj.Visibility = False
        return obj

    def move(self, name, shape, origin=(0, 0, 0), rotation=None):
        obj = self.compound(name, [shape])
        obj.Placement = App.Placement(App.Vector(*map(float, origin)), rotation or App.Rotation())
        for axis, value in zip('xyz', origin): bind(obj, 'Placement.Base.' + axis, value)
        return obj

    def mirror(self, name, shape):
        obj = self.obj('Part::Mirroring', name, name)
        obj.Source = shape
        obj.Normal = App.Vector(1, 0, 0)
        obj.Visibility = False
        return obj


def rectangle(x0, x1, y0, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
