import math
from rlutilities.linear_algebra import vec3


# This is a helper class for vector math. You can extend it or delete if you want.
class Vec3:
    """
    This class should provide you with all the basic vector operations that you need, but feel free to extend its
    functionality when needed.
    The vectors found in the GameTickPacket will be flatbuffer vectors. Cast them to Vec3 like this:
    `car_location = Vec3(car.physics.location)`.

    Remember that the in-game axis are left-handed.

    When in doubt visit the wiki: https://github.com/RLBot/RLBot/wiki/Useful-Game-Values
    """

    def __init__(self, x: float or 'Vec3'=0, y: float=0, z: float=0):
        """
        Create a new Vec3. The x component can alternatively be another vector with an x, y, and z component, in which
        case the created vector is a copy of the given vector and the y and z parameter is ignored. Examples:

        a = Vec3(1, 2, 3)

        b = Vec3(a)

        """

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

    def __neg__(self):
        return Vec3(-self.x, -self.y, -self.z)

    def __mul__(self, scale: float) -> 'Vec3':
        return Vec3(self.x * scale, self.y * scale, self.z * scale)

    def __rmul__(self, scale):
        return self * scale

    def __truediv__(self, scale: float) -> 'Vec3':
        scale = 1 / float(scale)
        return self * scale

    def __str__(self):
        return "Vec3(" + str(self.x) + ", " + str(self.y) + ", " + str(self.z) + ")"

    def flat(self):
        """Projects the current vector on the ground plane."""
        return Vec3(self.x, self.y, 0)

    def length(self):
        """Returns the length of the vector. Also called magnitude and norm."""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def dist(self, other: 'Vec3') -> float:
        """Returns the distance between this vector and another vector using pythagoras."""
        return (self - other).length()

    def normalized(self):
        """Returns a vector with the same direction but a length of one."""
        return self / self.length()

    def rescale(self, new_len: float) -> 'Vec3':
        """Returns a vector with the same direction but a different length."""
        return new_len * self.normalized()

    def dot(self, other: 'Vec3') -> float:
        """Returns the dot product."""
        return self.x*other.x + self.y*other.y + self.z*other.z

    def cross(self, other: 'Vec3') -> 'Vec3':
        """Returns the cross product."""
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def ang_to(self, ideal: 'Vec3') -> float:
        """Returns the angle to the ideal vector. Angle will be between 0 and pi."""
        cos_ang = self.dot(ideal) / (self.length() * ideal.length())
        return math.acos(cos_ang)

    # STUFF ADDED BY ME (L0laapk3)

    def project(self, other: 'Vec3') -> 'Vec3':
        return other.rescale(other.normalized().dot(self))
        
    def orthogonalize(self, other: 'Vec3') -> 'Vec3':
        return self - self.project(other)

    def rotate_2D(self, angle: float) -> 'Vec3':
        """rotates the vector on a flat surface by angle"""
        return Vec3(
            self.x * math.cos(angle) - self.y * math.sin(angle),
            self.x * math.sin(angle) + self.y * math.cos(angle),
            self.z
        )
    
    def atan2(self) -> 'float':
        return math.atan2(self.y, self.x)


    def toRLU(self) -> vec3:
        return vec3(self.x, self.y, self.z)
