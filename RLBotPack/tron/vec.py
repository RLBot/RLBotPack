import math
import random

from rlbot.utils.game_state_util import Vector3


class Vec3:
    def __init__(self, x: float or 'Vec3'=0.0, y: float=0.0, z: float=0.0):
        if hasattr(x, 'x'):
            # We have been given a vector. Copy it
            self.x = float(x.x)
            self.y = float(x.y) if hasattr(x, 'y') else 0
            self.z = float(x.z) if hasattr(x, 'z') else 0
        else:
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)

    def __getitem__(self, item: int):
        return (self.x, self.y, self.z)[item]

    def __add__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __neg__(self) -> 'Vec3':
        return Vec3(-self.x, -self.y, -self.z)

    def __mul__(self, scale: float) -> 'Vec3':
        return Vec3(self.x * scale, self.y * scale, self.z * scale)

    def __rmul__(self, scale: float) -> 'Vec3':
        return self * scale

    def __truediv__(self, scale: float) -> 'Vec3':
        scale = 1 / float(scale)
        return self * scale

    def __str__(self):
        return "Vec3(" + str(self.x) + ", " + str(self.y) + ", " + str(self.z) + ")"

    def dot(self, other: 'Vec3') -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def mag2(self) -> float:
        return self.dot(self)

    def mag(self) -> float:
        return math.sqrt(self.mag2())

    def longer_than(self, magnitude: float) -> bool:
        return magnitude * magnitude < self.mag2()

    def unit(self) -> 'Vec3':
        return self / self.mag()

    def to_desired_vec(self):
        return Vector3(self.x, self.y, self.z)

    @staticmethod
    def random() -> 'Vec3':
        return Vec3(
            1 - 2 * random.random(),
            1 - 2 * random.random(),
            1 - 2 * random.random(),
        )
