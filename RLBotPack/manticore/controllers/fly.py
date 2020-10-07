import math

from rlbot.agents.base_agent import SimpleControllerState

from utility.rlmath import clip
from utility.vec import Mat33, dot


class FlyController:

    def __init__(self):
        self.controls = SimpleControllerState()

    def align(self, bot, target_rot: Mat33) -> SimpleControllerState:

        car = bot.info.my_car

        local_forward = dot(target_rot.col(0), car.rot)
        local_up = dot(target_rot.col(2), car.rot)
        local_ang_vel = dot(car.ang_vel, car.rot)

        pitch_ang = math.atan2(-local_forward.z, local_forward.x)
        pitch_ang_vel = local_ang_vel.y

        yaw_ang = math.atan2(-local_forward.y, local_forward.x)
        yaw_ang_vel = -local_ang_vel.z

        roll_ang = math.atan2(-local_up.y, local_up.z)
        roll_ang_vel = local_ang_vel.x
        forwards_dot = dot(target_rot.col(0), car.forward)
        roll_scale = forwards_dot ** 2 if forwards_dot > 0.85 else 0

        self.controls.pitch = clip(-3.3 * pitch_ang + 0.8 * pitch_ang_vel, -1, 1)
        self.controls.yaw = clip(-3.3 * yaw_ang + 0.9 * yaw_ang_vel, -1, 1)
        self.controls.roll = clip(-3 * roll_ang + 0.5 * roll_ang_vel, -1, 1) * roll_scale
        self.controls.throttle = 1

        return self.controls
