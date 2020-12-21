import math

from rlbot.agents.base_agent import SimpleControllerState

from maneuvers.maneuver import Maneuver


from utility.rlmath import sign0, clip
from utility.vec import transpose, dot, rotation_to_axis, Vec3, norm, Mat33


# Credits to chip
class ChipAerialTurnManeuver(Maneuver):
    ALPHA_MAX = 9.0

    def __init__(self, target, epsilon_ang_vel=0.01, epsilon_rotation=0.04):
        super().__init__()

        self.target = target
        self.epsilon_ang_vel = epsilon_ang_vel
        self.epsilon_rotation = epsilon_rotation

    def exec(self, bot) -> SimpleControllerState:

        controls = SimpleControllerState()
        dt = bot.info.dt
        car = bot.info.my_car

        relative_rotation = dot(transpose(car.rot), self.target)
        geodesic_local = rotation_to_axis(relative_rotation)

        # figure out the axis of minimal rotation to target
        geodesic_world = dot(car.rot, geodesic_local)

        # get the angular acceleration
        alpha = Vec3(
            self.controller(geodesic_world.x, car.ang_vel.x, dt),
            self.controller(geodesic_world.y, car.ang_vel.y, dt),
            self.controller(geodesic_world.z, car.ang_vel.z, dt)
        )

        # reduce the corrections for when the solution is nearly converged
        alpha.x = self.q(abs(geodesic_world.x) + abs(car.ang_vel.x)) * alpha.x
        alpha.y = self.q(abs(geodesic_world.y) + abs(car.ang_vel.y)) * alpha.y
        alpha.z = self.q(abs(geodesic_world.z) + abs(car.ang_vel.z)) * alpha.z

        # set the desired next angular velocity
        ang_vel_next = car.ang_vel + alpha * dt

        # determine the controls that produce that angular velocity
        roll_pitch_yaw = ChipAerialTurnManeuver._aerial_rpy(car.ang_vel, ang_vel_next, car.rot, dt)
        controls.roll = roll_pitch_yaw.x
        controls.pitch = roll_pitch_yaw.y
        controls.yaw = roll_pitch_yaw.z

        if ((norm(car.ang_vel) < self.epsilon_ang_vel and
             norm(geodesic_world) < self.epsilon_rotation) or car.on_ground):
            self.done = True

        controls.throttle = 1.0

        return controls

    def periodic(self, x):
        return ((x - math.pi) % (2 * math.pi)) + math.pi

    def q(self, x):
        return 1.0 - (1.0 / (1.0 + 500.0 * x * x))

    def r(self, delta, v):
        return delta - 0.5 * sign0(v) * v * v / self.ALPHA_MAX

    def controller(self, delta, v, dt):
        ri = self.r(delta, v)

        alpha = sign0(ri) * self.ALPHA_MAX

        rf = self.r(delta - v * dt, v + alpha * dt)

        # use a single step of secant method to improve
        # the acceleration when residual changes sign
        if ri * rf < 0.0:
            alpha *= (2.0 * (ri / (ri - rf)) - 1)

        return alpha

    @staticmethod
    def _aerial_rpy(ang_vel_start, ang_vel_next, rot, dt):
        """
        :param ang_vel_start: beginning step angular velocity (world coordinates)
        :param ang_vel_next: next step angular velocity (world coordinates)
        :param rot: orientation matrix
        :param dt: time step
        :return: Vec3 with roll pitch yaw controls
        """
        # car's moment of inertia (spherical symmetry)
        J = 10.5

        # aerial control torque coefficients
        T = Vec3(-400.0, -130.0, 95.0)

        # aerial damping torque coefficients
        H = Vec3(-50.0, -30.0, -20.0)

        # get angular velocities in local coordinates
        w0_local = dot(ang_vel_start, rot)
        w1_local = dot(ang_vel_next, rot)

        # PWL equation coefficients
        a = [T[i] * dt / J for i in range(0, 3)]
        b = [-w0_local[i] * H[i] * dt / J for i in range(0, 3)]
        c = [w1_local[i] - (1 + H[i] * dt / J) * w0_local[i] for i in range(0, 3)]

        # RL treats roll damping differently
        b[0] = 0

        return Vec3(
            solve_PWL(a[0], b[0], c[0]),
            solve_PWL(a[1], b[1], c[1]),
            solve_PWL(a[2], b[2], c[2])
        )


# Solves a piecewise linear (PWL) equation of the form
#
# a x + b | x | + (or - ?) c == 0
#
# for -1 <= x <= 1. If no solution exists, this returns
# the x value that gets closest
def solve_PWL(a, b, c):
    xp = c / (a + b) if abs(a + b) > 10e-6 else -1
    xm = c / (a - b) if abs(a - b) > 10e-6 else 1

    if xm <= 0 <= xp:
        if abs(xp) < abs(xm):
            return clip(xp, 0, 1)
        else:
            return clip(xm, -1, 0)
    else:
        if 0 <= xp:
            return clip(xp, 0, 1)
        if xm <= 0:
            return clip(xm, -1, 0)

    return 0
