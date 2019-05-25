import math


class Vector3:

    def __init__(self, x=0.0, y=0.0, z=0.0):
        if isinstance(x, Vector3):
            self = x
        elif isinstance(x, (list, tuple)):
            self.x = x[0]
            self.y = x[1]
            self.z = x[2]
        elif hasattr(x, "x") and hasattr(x, "y"):
            self.x = x.x
            self.y = x.y
            if hasattr(x, "z"):
                self.z = x.z
            else:
                self.z = 0.0
        elif isinstance(x, (int, float)):
            self.x = x
            self.y = y
            self.z = z
        else:
            raise Exception("Invalid vector constructor input")


    @property
    def length(self):
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    @property
    def size(self):
        return self.length

    def normalize(self):
        temp = self.size

        if temp == 0.0:
            self.x = 1.0
            self.y = 1.0
            self.z = 1.0
        else:
            self /= temp

        return self

    @property
    def normalized(self):
        return Vector3(self.x,self.y,self.z).normalize()

    def angle_to(self, other):
        return math.degrees(math.acos((self * other) / (self.size * other.size)))

    @property
    def angle(self):
        return self.angle_to(Vector3(1,0,0))

    def __iter__(self):
        return iter([self.x, self.y, self.z])

    def __mul__(self, other):
        if isinstance(other, float) or isinstance(other, int):
            return Vector3(self.x * other, self.y * other, self.z * other)
        elif isinstance(other, Vector3):
            return self.x * other.x + self.y * other.y + self.z * other.z

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        return Vector3(self.x / other, self.y / other, self.z / other)

    def __add__(self, other):
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __neg__(self):
        return Vector3(-self.x, -self.y, -self.z)

    def __imul__(self, other):
        self = self * other
        return self

    def __mod__(self, other):
        x = self.y * other.z - other.y * self.z
        y = self.z * other.x - other.z * self.x
        z = self.x * other.y - other.x * self.y
        return Vector3(x,y,z)

    def __itruediv__(self, other):
        self = self / other
        return self

    def __iadd__(self, other):
        self = self + other
        return self

    def __isub__(self, other):
        self = self - other
        return self

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __ne__(self, other):
        return not self == other

    def to_rotation(self):
        return Rotator(math.atan2(self.z, math.sqrt((self.x * self.x) + (self.y * self.y))),
                         math.atan2(self.y, self.x),
                         0.0)

    def to_tuple(self):
        return self.x, self.y, self.z

    @property
    def location(self):
        return self


class Rotator:

    def __init__(self, pitch=0.0, yaw=0.0, roll=0.0):
        self.pitch = pitch
        self.yaw = yaw
        self.roll = roll

    def set_from_rotator(self, rotator):
        self.pitch = rotator.pitch
        self.yaw = rotator.yaw
        self.roll = rotator.roll

    @staticmethod
    def normalize_axis(angle):
        angle &= 0xFFFF

        if angle > 32767:
            angle -= 0x10000

        return angle

    def __add__(self, other):
        return Rotator(self.pitch + other.pitch, self.yaw + other.yaw, self.roll + other.roll)

    def __sub__(self, other):
        return Rotator(self.pitch - other.pitch, self.yaw - other.yaw, self.roll - other.roll)

    def normalize(self):
        self.pitch = self.normalize_axis(self.pitch)
        self.yaw = self.normalize_axis(self.yaw)
        self.roll = self.normalize_axis(self.roll)
        return self

    def to_vector3(self):
        cos_pitch = math.cos(self.pitch)
        return Vector3(math.cos(self.yaw) * cos_pitch, math.sin(self.yaw) * cos_pitch, math.sin(self.pitch))