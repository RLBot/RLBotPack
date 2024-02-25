import math

from rlbot.agents.base_agent import SimpleControllerState

from maneuvers.maneuver import Maneuver


# Credits to chip
from utility.rlmath import sign0, clip, clip01
from utility.vec import transpose, dot, rotation_to_axis, Vec3, norm, normalize, cross, Mat33


class AerialTurnManeuver(Maneuver):

    def __init__(self, target):
        super().__init__()
        self.target = target

    def exec(self, bot):

        car = bot.info.my_car

        # For testing
        # f = normalize(bot.info.ball.pos - car.pos)
        # l = cross(f, Vec3(z=1))
        # u = cross(l, f)
        # self.target = Mat33.from_columns(f, l, u)

        bot.renderer.draw_line_3d(car.pos, car.pos + 200 * self.target.col(0), bot.renderer.red())
        bot.renderer.draw_line_3d(car.pos, car.pos + 200 * self.target.col(1), bot.renderer.green())
        bot.renderer.draw_line_3d(car.pos, car.pos + 200 * self.target.col(2), bot.renderer.blue())

        self.done |= car.on_ground

        local_forward = dot(self.target.col(0), car.rot)
        local_up = dot(self.target.col(2), car.rot)
        local_ang_vel = dot(car.ang_vel, car.rot)

        pitch_ang = math.atan2(local_forward.z, local_forward.x)
        pitch_ang_vel = local_ang_vel.y

        yaw_ang = math.atan2(-local_forward.y, local_forward.x)
        yaw_ang_vel = -local_ang_vel.z

        roll_ang = math.atan2(-local_up.y, local_up.z)
        roll_ang_vel = local_ang_vel.x

        P_pitch = 3.8
        D_pitch = 0.8

        P_yaw = -3.8
        D_yaw = 0.9

        P_roll = -3.3
        D_roll = 0.5

        uprightness = dot(car.up, self.target.col(2))
        yaw_scale = 0.0 if uprightness < 0.6 else uprightness ** 2

        return SimpleControllerState(
            pitch=clip(P_pitch * pitch_ang + D_pitch * pitch_ang_vel, -1, 1),
            yaw=clip((P_yaw * yaw_ang + D_yaw * yaw_ang_vel) * yaw_scale, -1, 1),
            roll=clip(P_roll * roll_ang + D_roll * roll_ang_vel, -1, 1),
            throttle=1.0,
        )
