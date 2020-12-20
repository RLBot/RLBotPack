from rlbot.agents.base_agent import SimpleControllerState

from maneuvers.maneuver import Maneuver
from utility.info import Car
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

        # FIXME: If we knew the arena's mesh we could test if we are landing on a wall or something

        forward = normalize(xy(car.vel)) if norm(xy(car.vel)) > 20 else car.forward
        up = Vec3(z=1)
        left = cross(up, forward)

        return Mat33.from_columns(forward, left, up)
