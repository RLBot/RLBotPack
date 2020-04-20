from maneuvers.aerialturn import AerialTurnManeuver
from util.info import Car
from util.vec import normalize, xy, Vec3, cross, Mat33, norm


class RecoveryManeuver(AerialTurnManeuver):
    def __init__(self, bot):
        super().__init__(RecoveryManeuver.find_landing_orientation(bot.info.my_car))

    @staticmethod
    def find_landing_orientation(car: Car) -> Mat33:

        # FIXME: If we knew the arena's mesh we could test if we are landing or a wall or something

        forward = normalize(xy(car.vel)) if norm(xy(car.vel)) > 20 else car.forward
        up = Vec3(z=1)
        left = cross(up, forward)

        return Mat33.from_columns(forward, left, up)
