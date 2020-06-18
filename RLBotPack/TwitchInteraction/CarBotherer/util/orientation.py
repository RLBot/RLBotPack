import math
from rlbot.utils.game_state_util import Rotator

from util.vec import Vec3


# This is a helper class for calculating directions relative to your car. You can extend it or delete if you want.
class Orientation:
    """
    This class describes the orientation of an object from the rotation of the object.
    Use this to find the direction of cars: forward, right, up.
    It can also be used to find relative locations.
    """

    def __init__(self, rotation):
        self.yaw = float(rotation.yaw)
        self.roll = float(rotation.roll)
        self.pitch = float(rotation.pitch)

        cr = math.cos(self.roll)
        sr = math.sin(self.roll)
        cp = math.cos(self.pitch)
        sp = math.sin(self.pitch)
        cy = math.cos(self.yaw)
        sy = math.sin(self.yaw)

        self.forward = Vec3(cp * cy, cp * sy, sp)
        self.right = Vec3(cy*sp*sr-cr*sy, sy*sp*sr+cr*cy, -cp*sr)
        self.up = Vec3(-cr*cy*sp-sr*sy, -cr*sy*sp+sr*cy, cp*cr)

    def to_rotator(self) -> Rotator:
        return Rotator(self.pitch, self.yaw, self.roll)


def look_at_orientation(look_at: Vec3, up_direction: Vec3) -> Orientation:
    forward = look_at.normalized()
    up = up_direction.normalized()
    left = Vec3(up.cross(forward))
    if left.is_zero():
        left = Vec3(1, 0, 0)
    left = left.normalized()

    pitch = math.atan2(forward.z, Vec3(forward.x, forward.y, 0).length())
    yaw = math.atan2(forward.y, forward.x)
    roll = math.atan2(-left.z, up.z)

    # order is yaw-pitch-roll
    orientation = Orientation(Rotator(pitch, yaw, roll))
    return orientation

# Sometimes things are easier, when everything is seen from your point of view.
# This function lets you make any location the center of the world.
# For example, set center to your car's location and ori to your car's orientation, then the target will be
# relative to your car!
def relative_location(center: Vec3, ori: Orientation, target: Vec3) -> Vec3:
    """
    Returns target as a relative location from center's point of view, using the given orientation. The components of
    the returned vector describes:
    * x: how far in front
    * y: how far right
    * z: how far above
    """
    x = (target - center).dot(ori.forward)
    y = (target - center).dot(ori.right)
    z = (target - center).dot(ori.up)
    return Vec3(x, y, z)
