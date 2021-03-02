from enums import *
import json
import numpy as np
import math

def side(x):
    # returns -1 for blue team and 1 for orange team
    return (-1, 1)[x]

def almost_equals(x, y, threshold):
    return x - threshold < y and y < x + threshold


def point_inside_quadrilateral_2d(point, quadrilateral):
    # Point is a 2d vector
    # Quadrilateral is a tuple of 4 2d vectors, in either a clockwise or counter-clockwise order
    # See https://stackoverflow.com/a/16260220/10930209 for an explanation

    def area_of_triangle(triangle):
        return abs(sum((triangle[0].x * (triangle[1].y - triangle[2].y), triangle[1].x * (triangle[2].y - triangle[0].y), triangle[2].x * (triangle[0].y - triangle[1].y))) / 2)

    actual_area = area_of_triangle((quadrilateral[0], quadrilateral[1], point)) + area_of_triangle((quadrilateral[2], quadrilateral[1], point)) + area_of_triangle((quadrilateral[2], quadrilateral[3], point)) + area_of_triangle((quadrilateral[0], quadrilateral[3], point))
    quadrilateral_area = area_of_triangle((quadrilateral[0], quadrilateral[2], quadrilateral[1])) + area_of_triangle((quadrilateral[0], quadrilateral[2], quadrilateral[3]))

    # This is to account for any floating point errors
    return almost_equals(actual_area, quadrilateral_area, 0.001)

def getPosOnField(self):
    quadrilateralJson = '''
        {
        "GOALIE": [
            [2393, 6000],
            [-2393, 6000],
            [-2393, 3000],
            [2393, 3000]
        ],
        "RETREAT_ADVANCE_LEFT": [
            [-2393, 5120],
            [-4096, 5120],
            [-4096, -2000],
            [-2393, -2000]
        ],
        "RETREAT_ADVANCE_RIGHT": [
            [2393, -2000],
            [4096, -2000],
            [4096, 5120],
            [2393, 5120]
        ],
        "RETREAT_ADVANCE_CENTER": [
            [2393, 3000],
            [-2393, 3000],
            [-2393, -2000],
            [2393, -2000]
        ],
        "ATTACKING_CENTER":[
            [2393, -2000],
            [-2393, -2000],
            [-2393, -6000],
            [2393, -6000]
        ],
        "ATTACKING_LEFT_CORNER":[
            [-2393, -2000],
            [-4096, -2000],
            [-4096, -5120],
            [-2393, -5120]
        ],
        "ATTACKING_RIGHT_CORNER":[
            [2393, -2000],
            [4096, -2000],
            [4096, -5120],
            [2393, -5120]
        ]
    }'''

    if self.demolished:
        self.posOnField = posOnField.DEMOLISHED
    else:
        location = self.location * side(self.team)
        possible_quadrilateral = {}
        quadrilaterals = json.loads(quadrilateralJson)
        for quadName, quadrilateral in quadrilaterals.items():
            quadrilateral = [Vector(*point) for point in quadrilateral]
            if point_inside_quadrilateral_2d(location, quadrilateral):
                possible_quadrilateral['name'] = quadName
                possible_quadrilateral['quadrilateral'] = quadrilateral
                break

        if not ('name' in possible_quadrilateral):
            print(f'{self.name} is unknown! Dict: {possible_quadrilateral}')
        
        if possible_quadrilateral['name'] in ["RETREAT_ADVANCE_LEFT", "RETREAT_ADVANCE_RIGHT","RETREAT_ADVANCE_CENTER"]:
            # We need to figure out if we are retreating or advancing
            velocity = self.velocity * side(self.team)
            advancing = velocity.y < 0
            direction = "_CENTER"
            if possible_quadrilateral['name'].endswith('LEFT'):
                direction = "_LEFT"
            elif possible_quadrilateral['name'].endswith('RIGHT'):
                direction = "_RIGHT"
            posString = ("ADVANCING" if advancing else "RETREATING") + direction
            self.posOnField = posOnField[posString]
        else:
            self.posOnField = posOnField[possible_quadrilateral['name']]
    return self.posOnField

def getPosRelativeToBall(self):
    if self.demolished:
        self.posRelativeToBall = posRelativeToBall.DEMOLISHED
    return self.posRelativeToBall

# Vector supports 1D, 2D and 3D Vectors, as well as calculations between them
# Arithmetic with 1D and 2D lists/tuples aren't supported - just set the remaining values to 0 manually
# With this new setup, Vector is much faster because it's just a wrapper for numpy
class Vector:
    def __init__(self, x: float = 0, y: float = 0, z: float = 0):
        # this is a private property - this is so all other things treat this class like a list, and so should you!
        self._np = np.array([x, y, z])

    def __getitem__(self, index):
        return self._np[index].item()

    def __setitem__(self, index, value):
        self._np[index] = value

    @property
    def x(self):
        return self._np[0].item()

    @x.setter
    def x(self, value):
        self._np[0] = value

    @property
    def y(self):
        return self._np[1].item()

    @y.setter
    def y(self, value):
        self._np[1] = value

    @property
    def z(self):
        return self._np[2].item()

    @z.setter
    def z(self, value):
        self._np[2] = value

    # self == value
    def __eq__(self, value):
        if isinstance(value, float) or isinstance(value, int):
            return self.magnitude() == value

        if hasattr(value, "_np"):
            value = value._np
        return (self._np == value).all()

    # len(self)
    def __len__(self):
        return 3  # this is a 3 dimensional vector, so we return 3

    # str(self)
    def __str__(self):
        # Vector's can be printed to console
        return f"[{self.x} {self.y} {self.z}]"

    # repr(self)
    def __repr__(self):
        return f"Vector(x={self.x}, y={self.y}, z={self.z})"

    # -self
    def __neg__(self):
        return Vector(*(self._np * -1))

    # self + value
    def __add__(self, value):
        if hasattr(value, "_np"):
            value = value._np
        return Vector(*(self._np+value))
    __radd__ = __add__

    # self - value
    def __sub__(self, value):
        if hasattr(value, "_np"):
            value = value._np
        return Vector(*(self._np-value))

    def __rsub__(self, value):
        return -self + value

    # self * value
    def __mul__(self, value):
        if hasattr(value, "_np"):
            value = value._np
        return Vector(*(self._np*value))
    __rmul__ = __mul__

    # self / value
    def __truediv__(self, value):
        if hasattr(value, "_np"):
            value = value._np
        return Vector(*(self._np/value))

    def __rtruediv__(self, value):
        return self * (1 / value)

    # round(self)
    def __round__(self, decimals=0):
        # Rounds all of the values
        return Vector(*np.around(self._np, decimals=decimals))

    @staticmethod
    def from_vector(vec):
        return Vector(vec.x, vec.y, vec.z)

    def magnitude(self) -> float:
        # Returns the length of the vector
        return np.linalg.norm(self._np).item()

    def dot(self, value) -> float:
        # Returns the dot product of two vectors
        if hasattr(value, "_np"):
            value = value._np
        return np.dot(self._np, value).item()

    def cross(self, value):
        # Returns the cross product of two vectors
        if hasattr(value, "_np"):
            value = value._np
        return Vector(*np.cross(self._np, value))

    def copy(self):
        # Returns a copy of the vector
        return Vector(*self._np)

    def normalize(self, return_magnitude=False):
        # normalize() returns a Vector that shares the same direction but has a length of 1
        # normalize(True) can also be used if you'd like the length of this Vector (used for optimization)
        magnitude = self.magnitude()
        if magnitude != 0:
            norm_vec = Vector(*(self._np / magnitude))
            if return_magnitude:
                return norm_vec, magnitude
            return norm_vec
        if return_magnitude:
            return Vector(), 0
        return Vector()

    def flatten(self):
        # Sets Z (Vector[2]) to 0, making the Vector 2D
        return Vector(self._np[0], self._np[1])

    def angle2D(self, value) -> float:
        # Returns the 2D angle between this Vector and another Vector in radians
        return self.flatten().angle(value.flatten())

    def angle(self, value) -> float:
        # Returns the angle between this Vector and another Vector in radians
        return math.acos(max(min(np.dot(self.normalize()._np, value.normalize()._np).item(), 1), -1))

    def rotate(self, angle: float):
        # Rotates this Vector by the given angle in radians
        # Note that this is only 2D, in the x and y axis
        return Vector((math.cos(angle)*self.x) - (math.sin(angle)*self.y), (math.sin(angle)*self.x) + (math.cos(angle)*self.y), self.z)

    def clamp2D(self, start, end):
        # Similar to integer clamping, Vector's clamp2D() forces the Vector's direction between a start and end Vector
        # Such that Start < Vector < End in terms of clockwise rotation
        # Note that this is only 2D, in the x and y axis
        s = self.normalize()._np
        right = np.dot(s, np.cross(end._np, (0, 0, -1))) < 0
        left = np.dot(s, np.cross(start._np, (0, 0, -1))) > 0
        if (right and left) if np.dot(end._np, np.cross(start._np, (0, 0, -1))) > 0 else (right or left):
            return self
        if np.dot(start._np, s) < np.dot(end._np, s):
            return end
        return start

    def clamp(self, start, end):
        # This extends clamp2D so it also clamps the vector's z
        s = self.clamp2D(start, end)
        start_z = min(start.z, end.z)
        end_z = max(start.z, end.z)

        if s.z < start_z:
            s.z = start_z
        elif s.z > end_z:
            s.z = end_z

        return s

    def dist(self, value) -> float:
        # Distance between 2 vectors
        if hasattr(value, "_np"):
            value = value._np
        return np.linalg.norm(self._np - value).item()

    def flat_dist(self, value) -> float:
        # Distance between 2 vectors on a 2D plane
        return value.flatten().dist(self.flatten())

    def cap(self, low: float, high: float):
        # Caps all values in a Vector between 'low' and 'high'
        return Vector(*(max(min(item, high), low) for item in self._np))

    def midpoint(self, value):
        # Midpoint of the 2 vectors
        if hasattr(value, "_np"):
            value = value._np
        return Vector(*((self._np + value) / 2))

    def scale(self, value: float):
        # Returns a vector that has the same direction but with a value as the magnitude
        return self.normalize() * value
