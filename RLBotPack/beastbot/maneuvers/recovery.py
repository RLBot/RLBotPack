from maneuvers.aerialturn import AerialTurnManeuver
from maneuvers.maneuver import Maneuver
from utility.field_sdf import sdf_contains, sdf_normal
from utility.info import Car
from utility.predict import DummyObject, fall
from utility.vec import normalize, xy, Vec3, cross, Mat33, norm


class RecoveryManeuver(Maneuver):
    def __init__(self, bot):
        super().__init__()

    def exec(self, bot):
        self.done = bot.info.my_car.on_ground
        target_rot = self.find_landing_orientation(bot.info.my_car, 120)
        return bot.fly.align(bot, target_rot)

    @staticmethod
    def find_landing_orientation(car: Car, num_points: int) -> Mat33:
        dummy = DummyObject(car)

        for i in range(num_points):
            fall(dummy, 0.0333)  # Apply physics and let car fall through the air

            if i > 5 and sdf_contains(dummy.pos):
                up = normalize(sdf_normal(dummy.pos))
                left = cross(normalize(dummy.vel), up)
                forward = cross(up, left)

                return Mat33.from_columns(forward, left, up)

        # No wall/ground intersections found in fall
        # Default to looking in direction of velocity, but upright

        forward = normalize(xy(car.vel)) if norm(xy(car.vel)) > 20 else car.forward
        up = Vec3(z=1)
        left = cross(up, forward)

        return Mat33.from_columns(forward, left, up)
