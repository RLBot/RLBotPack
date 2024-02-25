import math

from rlbot.utils.structures.game_data_struct import PlayerInfo

from util.orientation import Orientation, relative_location
from util.vec import Vec3

def safe_div(x):
    if x != 0:
        return 1 / x
    else:
        return math.inf

def limit_to_safe_range(value: float) -> float:
    """
    Controls like throttle, steer, pitch, yaw, and roll need to be in the range of -1 to 1.
    This will ensure your number is in that range. Something like 0.45 will stay as it is,
    but a value of -5.6 would be changed to -1.
    """
    if value < -1:
        return -1
    if value > 1:
        return 1
    return value

def forward(car: PlayerInfo):
    d1 = Vec3(car.physics.velocity) * safe_div(Vec3(car.physics.velocity).length())
    r = car.physics.rotation
    d2 = Vec3(math.cos(r.yaw) * math.cos(r.pitch), math.sin(r.yaw) * math.cos(r.pitch), math.sin(r.pitch)) * safe_div(Vec3(math.cos(r.yaw) * math.cos(r.pitch), math.sin(r.yaw) * math.cos(r.pitch), math.sin(r.pitch)).length())
    return (d1 - d2).length() <= math.sqrt(2)
    
def steer_toward_target(car: PlayerInfo, target: Vec3) -> float:
    relative = relative_location(Vec3(car.physics.location), Orientation(car.physics.rotation), target)
    angle = math.atan2(relative.y, relative.x)
    if forward(car) == False:
        angle = angle / abs(angle) * (math.pi - abs(angle))
    return limit_to_safe_range(angle * 5)
