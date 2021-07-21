import math
import rlbot.utils.structures.game_data_struct as game_data_struct


class Vector3:
    # A Vector3 can be created with:
    # - Anything that has a __getitem__ (lists, tuples, Vector3's, etc)
    # - 3 numbers
    # - A vector or rotator from the GameTickPacket
    def __init__(self, *args):
        if hasattr(args[0], "__getitem__"):
            self.data = list(args[0])
        elif isinstance(args[0], game_data_struct.Vector3):
            self.data = [args[0].x, args[0].y, args[0].z]
        elif isinstance(args[0], game_data_struct.Rotator):
            self.data = [args[0].pitch, args[0].yaw, args[0].roll]
        elif len(args) == 3:
            self.data = list(args)
        else:
            raise TypeError("Vector3 unable to accept %s" % args)

    # Property functions allow you to use `Vector3.x` vs `Vector3[0]`
    @property
    def x(self):
        return self.data[0]

    @x.setter
    def x(self, value):
        self.data[0] = value

    @property
    def y(self):
        return self.data[1]

    @y.setter
    def y(self, value):
        self.data[1] = value

    @property
    def z(self):
        return self.data[2]

    @z.setter
    def z(self, value):
        self.data[2] = value

    def __getitem__(self, key):
        # To access a single value in a Vector3, treat it like a list
        # ie: to get the first (x) value use: Vector3[0]
        # The same works for setting values
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __str__(self):
        # Vector3's can be printed to console
        return str(self.data)

    __repr__ = __str__

    def __eq__(self, value):
        # Vector3's can be compared with:
        # - Another Vector3, in which case True will be returned if they have the same values
        # - A single value, in which case True will be returned if the Vector's length matches the value
        if hasattr(value, "__getitem__"):
            return self.data == value.data
        else:
            return self.magnitude() == value

    # Vector3's support most operators (+-*/)
    # If using an operator with another Vector3, each dimension will be independent
    # ie x+x, y+y, z+z
    # If using an operator with only a value, each dimension will be affected by that value
    # ie x+v, y+v, z+v
    def __add__(self, value):
        if hasattr(value, "__getitem__"):
            return Vector3(self[0] + value[0], self[1] + value[1], self[2] + value[2])
        return Vector3(self[0] + value, self[1] + value, self[2] + value)

    __radd__ = __add__

    def __sub__(self, value):
        if hasattr(value, "__getitem__"):
            return Vector3(self[0] - value[0], self[1] - value[1], self[2] - value[2])
        return Vector3(self[0] - value, self[1] - value, self[2] - value)

    __rsub__ = __sub__

    def __neg__(self):
        return Vector3(-self[0], -self[1], -self[2])

    def __mul__(self, value):
        if hasattr(value, "__getitem__"):
            return Vector3(self[0] * value[0], self[1] * value[1], self[2] * value[2])
        return Vector3(self[0] * value, self[1] * value, self[2] * value)

    __rmul__ = __mul__

    def __truediv__(self, value):
        if hasattr(value, "__getitem__"):
            return Vector3(self[0] / value[0], self[1] / value[1], self[2] / value[2])
        return Vector3(self[0] / value, self[1] / value, self[2] / value)

    def __rtruediv__(self, value):
        if hasattr(value, "__getitem__"):
            return Vector3(value[0] / self[0], value[1] / self[1], value[2] / self[2])
        raise TypeError("unsupported rtruediv operands")

    def __abs__(self):
        return Vector3(abs(self[0]), abs(self[1]), abs(self[2]))

    def magnitude(self):
        # Magnitude() returns the length of the vector
        return math.sqrt((self[0] * self[0]) + (self[1] * self[1]) + (self[2] * self[2]))

    def normalize(self, return_magnitude=False):
        # Normalize() returns a Vector3 that shares the same direction but has a length of 1.0
        # Normalize(True) can also be used if you'd also like the length of this Vector3 returned
        magnitude = self.magnitude()
        if magnitude != 0:
            if return_magnitude:
                return Vector3(self[0] / magnitude, self[1] / magnitude, self[2] / magnitude), magnitude
            return Vector3(self[0] / magnitude, self[1] / magnitude, self[2] / magnitude)
        if return_magnitude:
            return Vector3(0, 0, 0), 0
        return Vector3(0, 0, 0)

    # Linear algebra functions
    def dot(self, value):
        return self[0] * value[0] + self[1] * value[1] + self[2] * value[2]

    def cross(self, value):
        return Vector3((self[1] * value[2]) - (self[2] * value[1]),
                       (self[2] * value[0]) - (self[0] * value[2]),
                       (self[0] * value[1]) - (self[1] * value[0]))

    def flatten(self, axis=None):
        # Sets Z (Vector3[2]) to 0, or flattens point to some plane orthogonal to the provided axis
        if axis is None:
            return Vector3(self[0], self[1], 0)
        else:
            return self - (axis * self.dot(axis))

    def render(self):
        # Returns a list with the x and y values, to be used with pygame
        return [self[0], self[1]]

    def copy(self):
        # Returns a copy of this Vector3
        return Vector3(self.data[:])

    def angle(self, value):
        # Returns the angle between this Vector3 and another Vector3
        return math.acos(round(self.flatten().normalize().dot(value.flatten().normalize()), 4))

    def rotate(self, angle):
        # Rotates this Vector3 by the given angle in radians
        # Note that this is only 2D, in the x and y axis
        return Vector3((math.cos(angle) * self[0]) - (math.sin(angle) * self[1]),
                       (math.sin(angle) * self[0]) + (math.cos(angle) * self[1]), self[2])

    def clamp(self, start, end):
        # Similar to integer clamping, Vector3's clamp() forces the Vector3's direction between a start and end Vector3
        # Such that Start < Vector3 < End in terms of clockwise rotation
        # Note that this is only 2D, in the x and y axis
        s = self.normalize()
        right = s.dot(end.cross((0, 0, -1))) < 0
        left = s.dot(start.cross((0, 0, -1))) > 0
        if (right and left) if end.dot(start.cross((0, 0, -1))) > 0 else (right or left):
            return self
        if start.dot(s) < end.dot(s):
            return end
        return start


class Matrix3:

    def __init__(self, *args):
        if len(args) > 0:
            self.data = (args[0], args[1], args[2])
        else:
            self.data = (Vector3(0, 0, 0), Vector3(0, 0, 0), Vector3(0, 0, 0))
        self.forward, self.left, self.up = self.data

    def convert_euler(self, pitch, yaw, roll):
        cp = math.cos(pitch)
        sp = math.sin(pitch)
        cy = math.cos(yaw)
        sy = math.sin(yaw)
        cr = math.cos(roll)
        sr = math.sin(roll)
        self.data = (
            Vector3(cp * cy, cp * sy, sp),
            # Have to invert because rocket league is backwards. Two negatives make a left, apparently
            -Vector3(cy * sp * sr - cr * sy, sy * sp * sr + cr * cy, -cp * sr),
            Vector3(-cr * cy * sp - sr * sy, -cr * sy * sp + sr * cy, cp * cr))
        self.forward, self.left, self.up = self.data

    def local(self, vector):
        # transforms a relative distance from world coordinates into local coordinates
        # relative_distance = ball.location - car.location
        # local_coordinate = car.local(relative_distance)
        return Vector3(self.forward.dot(vector),
                       self.left.dot(vector),
                       self.up.dot(vector))

    def transpose(self):
        return Matrix3(
            Vector3(self[0][0], self[1][0], self[2][0]),
            Vector3(self[0][1], self[1][1], self[2][1]),
            Vector3(self[0][2], self[1][2], self[2][2]))

    def axis_angle(self):
        theta = math.acos((self[0][0] + self[1][1] + self[2][2] - 1.0) / 2)
        x = (self[2][1] - self[1][2]) / (2 * math.sin(theta))
        y = (self[0][2] - self[2][0]) / (2 * math.sin(theta))
        z = (self[1][0] - self[0][1]) / (2 * math.sin(theta))
        return Vector3(x, y, z)

    def __getitem__(self, value):
        return self.data[value]

    def __mul__(self, mat):
        return Matrix3(
            Vector3(self[0][0] * mat[0][0] + self[1][0] * mat[0][1] + self[2][0] * mat[0][2],
                    self[0][1] * mat[0][0] + self[1][1] * mat[0][1] + self[2][1] * mat[0][2],
                    self[0][2] * mat[0][0] + self[1][2] * mat[0][1] + self[2][2] * mat[0][2]),
            Vector3(self[0][0] * mat[1][0] + self[1][0] * mat[1][1] + self[2][0] * mat[1][2],
                    self[0][1] * mat[1][0] + self[1][1] * mat[1][1] + self[2][1] * mat[1][2],
                    self[0][2] * mat[1][0] + self[1][2] * mat[1][1] + self[2][2] * mat[1][2]),
            Vector3(self[0][0] * mat[2][0] + self[1][0] * mat[2][1] + self[2][0] * mat[2][2],
                    self[0][1] * mat[2][0] + self[1][1] * mat[2][1] + self[2][1] * mat[2][2],
                    self[0][2] * mat[2][0] + self[1][2] * mat[2][1] + self[2][2] * mat[2][2]),
        )


'''
Sanity Test
a = Vector3(1, 4, 7)
b = Vector3(2, 5, 8)
c = Vector3(3, 6, 9)
d = Vector3(10, 13, 16)
e = Vector3(11, 14, 17)
f = Vector3(12, 15, 18)
A = Matrix3(a, b, c)
B = Matrix3(d, e, f)
C = A * B

[[84, 201, 318], [90, 216, 342], etc]
'''
