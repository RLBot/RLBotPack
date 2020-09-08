from __future__ import annotations
import math
from gosling.objects import Vector3 as GoslingsVector3
from rlbot.utils.game_state_util import Vector3
from typing import Union, Tuple, List

TUPLE_VEC = Tuple[Union[float, int], Union[float, int], Union[float, int]]
LIST_VEC = List[Union[float, int]]


class Vec3(Vector3):

    @staticmethod
    def from_other_vec(
            other: Union[Vec3, Vector3, TUPLE_VEC, LIST_VEC]):
        """"Creates a Vec3 from a different Vector container for compatibility reasons."""
        if isinstance(other, list) or isinstance(other, tuple) or isinstance(other, Vec3):
            return Vec3(other[0], other[1], other[2])
        else:
            return Vec3(other.x, other.y, other.z)

    def magnitude(self) -> float:
        """Magnitude() returns the length of the vector.

        :return: The magnitude of this vector.
        :rtype: float"""
        return math.sqrt((self.x * self.x) + (self.y * self.y) + (self.z * self.z))

    def normalize(self, return_magnitude: bool = False) -> Union[Vec3, Tuple[Vec3, float]]:
        """Normalize() returns a Vector3 that shares the same direction but has a length of 1.0
        Normalize(True) can also be used if you'd like the length of this Vector3 (used for optimization).

        :param return_magnitude: Whether you want to return the magnitude as well.
        :type return_magnitude: bool
        :return: Either a normalized vector or a tuple with a normalized vector and its original magnitude.
        :rtype: Vec3
        """
        magnitude = self.magnitude()
        if magnitude != 0:
            if return_magnitude:
                return Vec3(self.x / magnitude, self.y / magnitude, self.z / magnitude), magnitude
            return Vec3(self.x / magnitude, self.y / magnitude, self.z / magnitude)
        if return_magnitude:
            return Vec3(0, 0, 0), 0
        return Vec3(0, 0, 0)

    def cross(self, vector: Union[Vec3, Vector3, TUPLE_VEC, LIST_VEC]) -> Vec3:
        """Cross product between this vector and a given vector.

        :param vector: The other vector
        :type vector: Vec3
        :return: A vector perpendicular to this vector and the given vector.
        :rtype: Vec3
        """
        if isinstance(vector, Vector3):
            return Vec3((self.y * vector.z) - (self.z * vector.y), (self.z * vector.x) - (self.x * vector.z),
                        (self.x * vector.y) - (self.y * vector.x))
        else:
            return Vec3((self.y * vector[2]) - (self.z * vector[1]), (self.z * vector[0]) - (self.x * vector[2]),
                        (self.x * vector[1]) - (self.y * vector[0]))

    def flatten(self) -> Vec3:
        """Sets Z (Vector3[2]) to 0.

        :return: A vector with Z=0.
        :rtype: Vec3"""
        return Vec3(self.x, self.y, 0)

    def angle_2d(self, vector: Union[Vec3, Vector3, TUPLE_VEC, LIST_VEC]) -> float:
        """Returns the angle between this Vector3 and another Vector in 2D.

        :param vector: Vec3
        :type vector: Vec3
        :return: Angle between this vector and the given vector in 2D.
        :rtype: float"""
        if not isinstance(vector, Vec3):
            vector = Vec3.from_other_vec(vector)

        return math.acos(
            (self.flatten() * vector.flatten()) / (self.flatten().magnitude() * vector.flatten().magnitude()))

    def clamp(self, start: Union[Vec3, Vector3, TUPLE_VEC, LIST_VEC],
              end: Union[Vec3, Vector3, TUPLE_VEC, LIST_VEC]) -> Vec3:
        """Similar to integer clamping, Vector3's clamp() forces the Vector3's direction between a start and end Vector3
        Such that Start < Vector3 < End in terms of clockwise rotation. Note that this is only 2D, in the x and y axis.

        :param start: The minimal rotation in terms of clockwise rotation from start to end in 2d
        :type start: Vec3
        :param end: The maximal rotation in terms of clockwise rotation from start to end in 2d
        :type end: Vec3
        :return: The resulting vector clamped between the given angles.
        :rtype: Vec3
        """
        if not isinstance(start, Vec3):
            start = Vec3.from_other_vec(start)

        if not isinstance(end, Vec3):
            end = Vec3.from_other_vec(end)

        s = self.normalize()
        right = s * (end.cross(Vec3(0, 0, -1))) < 0
        left = s * (start.cross(Vec3(0, 0, -1))) > 0
        if (right and left) if end * (start.cross(Vec3(0, 0, -1))) > 0 else (right or left):
            return self
        if start * s < end * s:
            return end
        return start

    # def angle_3d(self, vector) -> float:
    #     """ Returns the angle between this Vector3 and another Vector3 """
    #     return math.acos((self * vector) / (self.magnitude() * vector.magnitude()))

    # def render(self):
    #     """ Returns a list with the x and y values, to be used with pygame """
    #     return [self.x, self.y]

    # def copy(self):
    #     """ Returns a copy of this Vector3 """
    #     return Vec3(self.data[:])

    # def rotate_2d(self, angle):
    #     """Rotates this Vector3 by the given angle in radians
    #     Note that this is only 2D, in the x and y axis"""
    #     return Vec3((math.cos(angle) * self.x) - (math.sin(angle) * self.y),
    #                 (math.sin(angle) * self.x) + (math.cos(angle) * self.y), self.z)

    # def element_wise_division(self, vector):
    #     if isinstance(vector, Vec3) or len(vector) > 0:
    #         return Vec3(self[0] / vector[0], self[1] / vector[1], self[2] / vector[2])
    #     raise TypeError("This cannot be done on a vector!")
    #
    # def element_wise_multiplication(self, vector):
    #     if isinstance(vector, Vec3) or len(vector) > 0:
    #         return Vec3(self[0] * vector[0], self[1] * vector[1], self[2] * vector[2])
    #     raise TypeError("This cannot be done on a vector!")

    def __getitem__(self, item: int) -> float:
        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        else:
            return self.z

    def __setitem__(self, key: int, value: float):
        if key == 0:
            self.x = value
        elif key == 1:
            self.y = value
        else:
            self.z = value

    def __str__(self) -> str:
        return f"X: {self.x}, Y: {self.y}, Z:{self.z}"

    def __repr__(self) -> str:
        return f"X: {self.x}, Y: {self.y}, Z:{self.z}"

    def __eq__(self, other: Union[Vec3, Vector3, TUPLE_VEC, LIST_VEC]) -> bool:
        if isinstance(other, Vector3):
            return (self.x == other.x) * (self.y == other.y) * (self.z == other.z)
        else:
            return (self.x == other[0]) * (self.y == other[1]) * (self.z == other[2])

    def __add__(self, other: Union[float, int, Vec3, Vector3, TUPLE_VEC, LIST_VEC]) -> Vec3:
        if isinstance(other, int) or isinstance(other, float):
            return Vec3(self.x + other, self.y + other, self.z + other)
        elif isinstance(other, Vector3):
            return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)
        else:
            return Vec3(self.x + other[0], self.y + other[1], self.z + other[2])

    __radd__ = __add__

    def __sub__(self, value: Union[float, int, Vec3, Vector3, TUPLE_VEC, LIST_VEC]) -> Vec3:
        if isinstance(value, int) or isinstance(value, float):
            return Vec3(self[0] - value, self[1] - value, self[2] - value)
        if isinstance(value, Vec3):
            return Vec3(self[0] - value[0], self[1] - value[1], self[2] - value[2])
        if isinstance(value, Vector3):
            return Vec3(self[0] - value.x, self[1] - value.y, self[2] - value.z)

    __rsub__ = __sub__

    def __neg__(self) -> Vec3:
        return Vec3(-self[0], -self[1], -self[2])

    def __mul__(self, value: Union[float, Vec3, Vector3]) -> Union[float, Vec3]:
        if isinstance(value, int) or isinstance(value, float):
            return Vec3(self[0] * value, self[1] * value, self[2] * value)
        if isinstance(value, Vec3):
            return self[0] * value[0] + self[1] * value[1] + self[2] * value[2]
        if isinstance(value, Vector3):
            return self[0] * value.x + self[1] * value.y + self[2] * value.z

    __rmul__ = __mul__

    def __truediv__(self, value: float) -> Vec3:
        if isinstance(value, int) or isinstance(value, float):
            return Vec3(self[0] / value, self[1] / value, self[2] / value)
        raise TypeError("This cannot be done on a vector!")

    def __rtruediv__(self, value):
        raise TypeError("This cannot be done on a vector!")

    def __len__(self) -> int:
        return 3
