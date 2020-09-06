import math
from physics.math.vector3 import Vec3


class Orientation3:
    """The Orientation3's sole purpose is to convert roll, pitch, and yaw data from the gametickpaket into an orientation matrix
        An orientation matrix contains 3 Vector3s
        - Matrix3[0] is the "forward" direction of a given car
        - Matrix3[1] is the "left" direction of a given car
        - Matrix3[2] is the "up" direction of a given car
    If you have a distance between the car and some object, ie ball.location - car.location,
    you can convert that to local coordinates by dotting it with this matrix
    ie: local_ball_location = Orientation3 * (ball.location - car.location)

    :param : Rotation around the Y axis (left / transverse)
    :type pitch: float
    :param yaw: Rotation around the Z axis (upward / vertical)
    :type yaw: float
    :param roll: Rotation around the X axis (forward / longitudinal)
    :type roll: float
    """

    def __init__(self, pitch: float, yaw: float, roll: float):
        cp = math.cos(pitch)
        sp = math.sin(pitch)
        cy = math.cos(yaw)
        sy = math.sin(yaw)
        cr = math.cos(roll)
        sr = math.sin(roll)

        # List of 3 vectors, each descriping the direction of an axis: Forward, Left, and Up
        self.data = [
            Vec3(cp * cy, cp * sy, sp),
            Vec3(cy * sp * sr - cr * sy, sy * sp * sr + cr * cy, -cp * sr),
            Vec3(-cr * cy * sp - sr * sy, -cr * sy * sp + sr * cy, cp * cr)]
        self.forward, self.left, self.up = self.data

    def __getitem__(self, key: int) -> Vec3:
        """Retrieves either the forward / left / up vector of this orientation matrix."""
        return self.data[key]

    def __mul__(self, other: Vec3) -> Vec3:
        """Performs default matrix multiplications."""
        if isinstance(other, Vec3):
            return Vec3(self.forward * other, self.left * other, self.up * other)

    def __str__(self) -> str:
        """Returns a 4 decimal accurate string representation of this orientation matrix."""
        dec = 4
        return f"{str(round(self.data[0][0], dec)).rjust(dec + 3)}, {str(round(self.data[0][1], dec)).rjust(dec + 3)}," \
               f" {str(round(self.data[0][2], dec)).rjust(dec + 3)}\n{str(round(self.data[1][0], dec)).rjust(dec + 3)}, " \
               f"{str(round(self.data[1][1], dec)).rjust(dec + 3)}, {str(round(self.data[1][2], dec)).rjust(dec + 3)}\n" \
               f"{str(round(self.data[2][0], dec)).rjust(dec + 3)}, {str(round(self.data[2][1], dec)).rjust(dec + 3)}, " \
               f"{str(round(self.data[2][2], dec)).rjust(dec + 3)}\n"
