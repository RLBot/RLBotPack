from rlbot.agents.base_agent import SimpleControllerState

from maneuvers.maneuver import Maneuver
from utility import predict
from utility.info import Car, Field
from utility.plane import intersects_plane
from utility.predict import DummyObject
from utility.vec import normalize, xy, Vec3, cross, Mat33, norm


class RecoveryManeuver(Maneuver):
    def __init__(self):
        super().__init__()

    def exec(self, bot) -> SimpleControllerState:
        self.done = bot.info.my_car.on_ground
        target_rot = self.find_landing_orientation(bot.info.my_car)
        return bot.fly.align(bot, target_rot)

    @staticmethod
    def find_landing_orientation(car: Car) -> Mat33:

        # FIXME: This uses a cheap approximation of the walls to find landing orientation

        obj = DummyObject(car)
        prev_pos = obj.pos
        for i in range(100):
            predict.fall(obj, 0.1)

            # Checking for intersections
            for plane in Field.SIDE_WALLS_AND_GROUND:
                if intersects_plane(prev_pos, obj.pos, plane):
                    # Bingo!
                    fall_dir = normalize(obj.pos - prev_pos)
                    left = -cross(fall_dir, plane.normal)
                    forward = -cross(plane.normal, left)

                    return Mat33.from_columns(forward, left, plane.normal)

            prev_pos = obj.pos

        # No wall/ground intersections found in fall
        # Default to looking in direction of velocity, but upright

        forward = normalize(xy(car.vel)) if norm(xy(car.vel)) > 20 else car.forward
        up = Vec3(z=1)
        left = cross(up, forward)

        return Mat33.from_columns(forward, left, up)
