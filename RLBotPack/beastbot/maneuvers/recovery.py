from maneuvers.aerialturn import AerialTurnManeuver
from utility.info import Car
from utility.vec import normalize, xy, Vec3, cross, Mat33, norm


class RecoveryManeuver(AerialTurnManeuver):
    def __init__(self, bot):
        super().__init__(RecoveryManeuver.find_landing_orientation(bot.info.my_car, 200))

    @staticmethod
    def find_landing_orientation(car: Car, num_points: int) -> Mat33:
        """
        dummy = DummyObject(car)
        trajectory = [Vec3(dummy.pos)]

        for i in range(0, num_points):
            fall(dummy, 0.0333)  # Apply physics and let car fall through the air
            trajectory.append(Vec3(dummy.pos))
            up = dummy.pitch_surface_normal()
            if norm(up) > 0.0 and i > 10:
                up = normalize(up)
                forward = normalize(dummy.vel - dot(dummy.vel, up) * up)
                left = cross(up, forward)

                return Mat33.from_columns(forward, left, up)

        return Mat33(car.rot)
        """

        forward = normalize(xy(car.vel)) if norm(xy(car.vel)) > 20 else car.forward
        up = Vec3(z=1)
        left = cross(up, forward)

        return Mat33.from_columns(forward, left, up)
