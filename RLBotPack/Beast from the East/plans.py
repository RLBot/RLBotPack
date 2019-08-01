import time

from rlbot.agents.base_agent import SimpleControllerState

from info import Car
from rlmath import *


class DodgePlan:
    def __init__(self, target=None, boost=False):
        self.target = target
        self.boost = boost
        self.controls = SimpleControllerState()
        self.start_time = time.time()
        self.finished = False
        self.almost_finished = False

        self._t_first_unjump = 0.10
        self._t_aim = 0.13
        self._t_second_jump = 0.18
        self._t_second_unjump = 0.46
        self._t_finishing = 1.0  # After this, fix orientation until lands on ground

        self._t_steady_again = 0.25  # Time on ground before steady and ready again
        self._max_speed = 2000  # Don't boost if above this speed
        self._boost_ang_req = 0.25

    def execute(self, bot):
        ct = time.time() - self.start_time

        # Target is allowed to be a function that takes bot as a parameter. Check what it is
        if callable(self.target):
            target = self.target(bot)
        else:
            target = self.target

        # Get car and reset controls
        car = bot.info.my_car
        self.controls.throttle = 1
        self.controls.yaw = 0
        self.controls.pitch = 0
        self.controls.jump = False

        # To boost or not to boost, that is the question
        car_to_target = target - car.pos
        vel_p = proj_onto_size(car.vel, car_to_target)
        angle = angle_between(car_to_target, car.forward())
        self.controls.boost = self.boost and angle < self._boost_ang_req and vel_p < self._max_speed

        # States of dodge (note reversed order)
        # Land on ground
        if ct >= self._t_finishing:
            self.almost_finished = True
            if car.on_ground:
                self.finished = True
            else:
                bot.plan = RecoverPlan()
                self.finished = True
            return self.controls
        elif ct >= self._t_second_unjump:
            # Stop pressing jump and rotate and wait for flip is done
            pass
        elif ct >= self._t_aim:
            if ct >= self._t_second_jump:
                self.controls.jump = 1

            # Direction, yaw, pitch, roll
            if self.target is None:
                self.controls.roll = 0
                self.controls.pitch = -1
                self.controls.yaw = 0
            else:
                target_local = dot(car_to_target, car.rot)
                target_local.z = 0

                direction = normalize(target_local)

                self.controls.roll = 0
                self.controls.pitch = -direction.x
                self.controls.yaw = sign(car.rot.get(2, 2)) * direction.y

        # Stop pressing jump
        elif ct >= self._t_first_unjump:
            pass

        # First jump
        else:
            self.controls.jump = 1

        bot.controls = self.controls


class SmallJumpPlan:
    def __init__(self, target=None, boost=False):
        self.target = target
        self.boost = boost
        self.controls = SimpleControllerState()
        self.start_time = time.time()
        self.finished = False
        self.almost_finished = False

        self._t_first_unjump = 0.20
        self._t_aim_prepare = 0.35
        self._t_aim = 0.6
        self._t_second_jump = 0.65
        self._t_second_unjump = 0.95
        self._t_finishing = 1.45  # After this, fix orientation until lands on ground

        self._max_speed = 2000  # Don't boost if above this speed
        self._boost_ang_req = 0.25

    def execute(self, bot):
        ct = time.time() - self.start_time

        # Target is allowed to be a function that takes bot as a parameter. Check what it is
        if callable(self.target):
            target = self.target(bot)
        else:
            target = self.target

        # Get car and reset controls
        car = bot.info.my_car
        self.controls.throttle = 1
        self.controls.yaw = 0
        self.controls.pitch = 0
        self.controls.jump = False

        # To boost or not to boost, that is the question
        car_to_target = target - car.pos
        vel_p = proj_onto_size(car.vel, car_to_target)
        angle = angle_between(car_to_target, car.forward())
        self.controls.boost = self.boost and angle < self._boost_ang_req and vel_p < self._max_speed

        # States of dodge (note reversed order)
        # Land on ground
        if ct >= self._t_finishing:
            self.almost_finished = True
            if car.on_ground:
                self.finished = True
            else:
                bot.plan = RecoverPlan()
                self.finished = True
            return self.controls
        elif ct >= self._t_second_unjump:
            # Stop pressing jump and rotate and wait for flip is done
            pass

        elif ct >= self._t_aim:
            if ct >= self._t_second_jump:
                self.controls.jump = 1

            # Direction, yaw, pitch, roll
            if self.target is None:
                self.controls.roll = 0
                self.controls.pitch = -1
                self.controls.yaw = 0
            else:
                target_local = dot(car_to_target, car.rot)
                target_local.z = 0

                direction = normalize(target_local)

                self.controls.roll = 0
                self.controls.pitch = -direction.x
                self.controls.yaw = sign(car.rot.get(2, 2)) * direction.y

        # Pitch slightly upwards before starting the dodge
        elif ct >= self._t_aim_prepare:
            self.controls.pitch = 1

        # Stop pressing jump
        elif ct >= self._t_first_unjump:
            pass

        # First jump
        else:
            self.controls.jump = 1

        bot.controls = self.controls


# Credits to chip
class AerialTurn:
    ALPHA_MAX = 9.0

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

    def __init__(self, car, target, timeout=5.0):

        self.found = False
        self.car = car
        self.trajectory = []
        self.target = target

        self.timeout = timeout

        self.epsilon_ang_vel = 0.01
        self.epsilon_rotation = 0.04

        self.controls = SimpleControllerState()

        self.timer = 0.0
        self.finished = False
        self.relative_rotation = Vec3()
        self.geodesic_local = Vec3()

    def step(self, dt):

        relative_rotation = dot(transpose(self.car.rot), self.target)
        geodesic_local = rotation_to_axis(relative_rotation)

        # figure out the axis of minimal rotation to target
        geodesic_world = dot(self.car.rot, geodesic_local)

        # get the angular acceleration
        alpha = Vec3(
            self.controller(geodesic_world.x, self.car.ang_vel.x, dt),
            self.controller(geodesic_world.y, self.car.ang_vel.y, dt),
            self.controller(geodesic_world.z, self.car.ang_vel.z, dt)
        )

        # reduce the corrections for when the solution is nearly converged
        alpha.x = self.q(abs(geodesic_world.x) + abs(self.car.ang_vel.x)) * alpha.x
        alpha.y = self.q(abs(geodesic_world.y) + abs(self.car.ang_vel.y)) * alpha.y
        alpha.z = self.q(abs(geodesic_world.z) + abs(self.car.ang_vel.z)) * alpha.z

        # set the desired next angular velocity
        ang_vel_next = self.car.ang_vel + alpha * dt

        # determine the controls that produce that angular velocity
        roll_pitch_yaw = AerialTurn.aerial_rpy(self.car.ang_vel, ang_vel_next, self.car.rot, dt)

        self.controls.roll = roll_pitch_yaw.x
        self.controls.pitch = roll_pitch_yaw.y
        self.controls.yaw = roll_pitch_yaw.z

        self.timer += dt

        if ((norm(self.car.ang_vel) < self.epsilon_ang_vel and
             norm(geodesic_world) < self.epsilon_rotation) or
                self.timer >= self.timeout or self.car.on_ground):
            self.finished = True

        return self.finished

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

        forward = normalize(xy(car.rot.col(0)))
        up = Vec3(z=1)
        left = cross(up, forward)

        return Mat33.from_columns(forward, left, up)

    @staticmethod
    # w0: beginning step angular velocity (world coordinates)
    # w1: beginning step angular velocity (world coordinates)
    # rot: orientation matrix
    # dt: time step
    def aerial_rpy(ang_vel0, ang_vel1, rot, dt):
        # car's moment of inertia (spherical symmetry)
        J = 10.5

        # aerial control torque coefficients
        T = Vec3(-400.0, -130.0, 95.0)

        # aerial damping torque coefficients
        H = Vec3(-50.0, -30.0, -20.0)

        # get angular velocities in local coordinates
        w0_local = dot(ang_vel0, rot)
        w1_local = dot(ang_vel1, rot)

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


class KickoffPlan:
    def __init__(self):
        self.finished = False

    def execute(self, bot):
        DODGE_DIST = 250
        MIDDLE_OFFSET = 430

        # Since ball is at (0,0) we don't we a car_to_ball variable like we do so many other places
        car = bot.info.my_car
        dist = norm(car.pos)
        vel_p = -proj_onto_size(car.vel, car.pos)

        point = Vec3(0, bot.info.team_sign * (dist / 2.6 - MIDDLE_OFFSET), 0)
        speed = 2300
        opp_dist = norm(bot.info.opponents[0].pos)
        opp_does_kick = opp_dist < dist + 600

        # Opponent is not going for kickoff, so we slow down a bit
        if not opp_does_kick:
            speed = 2210
            point = Vec3(0, bot.info.team_sign * (dist / 2.05 - MIDDLE_OFFSET), 0)
            point += Vec3(35 * sign(car.pos.x), 0, 0)

        # Dodge when close to (0, 0) - but only if the opponent also goes for kickoff. The dodge itself should happen in about 0.3 seconds
        if dist - DODGE_DIST < vel_p * 0.3 and opp_does_kick:
            bot.drive.start_dodge()

        # Make two dodges when spawning far back
        elif dist > 3640 and vel_p > 1200 and not opp_does_kick:
            bot.drive.start_dodge()

        # Pickup boost when spawning back corner by driving a bit towards the middle boost pad first
        elif abs(car.pos.x) > 230 and abs(car.pos.y) > 2880:
            # The pads exact location is (0, 2816), but don't have to be exact
            point.y = bot.info.team_sign * 2790

        bot.controls = bot.drive.go_towards_point(bot, point, target_vel=speed, slide=False, boost=True,
                                                  can_dodge=False, can_keep_speed=False)
        self.finished = not bot.info.is_kickoff

        if bot.do_rendering:
            bot.renderer.draw_line_3d(car.pos, point, bot.renderer.white())


def choose_kickoff_plan(bot):
    # Do we have teammates? If no -> always go for kickoff
    if len(bot.info.teammates) == 0:
        return KickoffPlan()

    # Kickoff spawn locations (corners may vary from map to map)
    ts = bot.info.team_sign
    right_corner_loc = Vec3(-1970, ts * 2450, 0)  # actually left for orange
    left_corner_loc = Vec3(1970, ts * 2450, 0)  # actually right for orange
    back_right_loc = Vec3(-256, ts * 3840, 0)  # actually left for orange
    back_left_loc = Vec3(256, ts * 3840, 0)  # actually right for orange
    back_center_loc = Vec3(0, ts * 4608, 0)

    boost_x = 3072
    boost_y = ts * 4096

    # Are we in the corner -> go for kickoff (If two bot's are in the corners, we assume lowest index goes for kickoff)
    if is_my_kickoff_spawn(bot, right_corner_loc):
        tm_index = index_of_teammate_at_kickoff_spawn(bot, left_corner_loc)
        if 0 <= tm_index < bot.index:
            return SecondManSlowCornerKickoffPlan(bot)
        else:
            return KickoffPlan()
    if is_my_kickoff_spawn(bot, left_corner_loc):
        tm_index = index_of_teammate_at_kickoff_spawn(bot, right_corner_loc)
        if 0 <= tm_index < bot.index:
            return SecondManSlowCornerKickoffPlan(bot)
        else:
            return KickoffPlan()

    # Is a teammate in the corner -> collect boost
    if 0 <= index_of_teammate_at_kickoff_spawn(bot, right_corner_loc) \
            or 0 <= index_of_teammate_at_kickoff_spawn(bot, left_corner_loc):
        if bot.info.my_car.pos.x > 10:
            # go for left boost
            return CollectSpecificBoostPlan(Vec3(boost_x, boost_y, 0))
        if bot.info.my_car.pos.x < -10:
            # go for right boost
            return CollectSpecificBoostPlan(Vec3(-boost_x, boost_y, 0))
        if 0 <= index_of_teammate_at_kickoff_spawn(bot, back_right_loc):
            # go for left boost
            return CollectSpecificBoostPlan(Vec3(boost_x, boost_y, 0))
        else:
            # go for right boost
            return CollectSpecificBoostPlan(Vec3(-boost_x, boost_y, 0))

    # No teammate in the corner
    # Are we back right or left -> go for kickoff
    if is_my_kickoff_spawn(bot, back_right_loc) \
            or is_my_kickoff_spawn(bot, back_left_loc):
        return KickoffPlan()

    # No teammate in the corner
    # Is a teammate back right or left -> collect boost
    if 0 <= index_of_teammate_at_kickoff_spawn(bot, back_right_loc):
        # go for left boost
        return CollectSpecificBoostPlan(Vec3(boost_x, boost_y, 0))
    elif 0 <= index_of_teammate_at_kickoff_spawn(bot, back_left_loc):
        # go for right boost
        return CollectSpecificBoostPlan(Vec3(-boost_x, boost_y, 0))

    # We have no teammates
    return KickoffPlan()


def is_my_kickoff_spawn(bot, loc):
    dist = norm(bot.info.my_car.pos - loc)
    return dist < 150


def index_of_teammate_at_kickoff_spawn(bot, loc):
    """
    Returns index of teammate at loc, or -1 if there is no teammate
    """
    # RLU Cars does not contain index, so we have to find that ourselves :(
    for car in bot.info.teammates:
        dist = norm(car.pos - loc)
        if dist < 150:
            return car.index
    return -1


class SecondManSlowCornerKickoffPlan:
    def __init__(self, bot):
        self.finished = False

        # These vectors will help us make the curve
        ts = bot.info.team_sign
        self.target_loc = Vec3(0, ts * 400, 0)
        self.target_dir = Vec3(0, -ts, 0)

    def execute(self, bot):
        car = bot.info.my_car

        curve_point = curve_from_arrival_dir(car.pos, self.target_loc, self.target_dir)
        bot.controls = bot.drive.go_towards_point(bot, curve_point, target_vel=1400, slide=True, boost=True,
                                                  can_keep_speed=False)

        self.finished = norm(car.pos) < 1000  # End plan when reaching getting close to ball (approx at boost pad)


class CollectSpecificBoostPlan:
    def __init__(self, pad_pos):
        self.finished = False
        self.boost_pad_pos = pad_pos

    def execute(self, bot):
        car = bot.info.my_car

        # Drive towards the pad
        bot.controls = bot.drive.go_towards_point(bot, self.boost_pad_pos, target_vel=2300, boost=True,
                                                  can_keep_speed=True)

        car_to_pad = self.boost_pad_pos - car.pos
        vel = proj_onto_size(car.vel, car_to_pad)
        dist = norm(car_to_pad)
        if dist < vel * 0.3:
            self.finished = True


class CollectClosestBoostPlan:
    def __init__(self, specific_loc=None):
        self.finished = False
        self.big_pad_locs = [
            Vec3(3584, 0, 0),
            Vec3(-3584, 0, 0),
            Vec3(3072, 4096, 0),
            Vec3(3072, -4096, 0),
            Vec3(-3072, 4096, 0),
            Vec3(-3072, -4096, 0)
        ]
        self.closest_pad = None

        if specific_loc is not None:
            self.closest_pad = specific_loc

    def execute(self, bot):
        car = bot.info.my_car

        # Choose the closest big boost pad
        if self.closest_pad is None:
            closest_dist = 99999
            for pad in self.big_pad_locs:
                dist = norm(car.pos - pad)
                if dist < closest_dist:
                    closest_dist = dist
                    self.closest_pad = pad

        # Drive towards the pad
        bot.controls = bot.drive.go_towards_point(bot, self.closest_pad, target_vel=2300, boost=True,
                                                  can_keep_speed=True)

        car_to_pad = self.closest_pad - car.pos
        vel = proj_onto_size(car.vel, car_to_pad)
        dist = norm(car_to_pad)
        if dist < vel * 0.3:
            self.finished = True


class RecoverPlan:
    def __init__(self):
        self.finished = False
        self.aerialturn = None

    def execute(self, bot):
        if self.aerialturn is None:
            self.aerialturn = AerialTurn(bot.info.my_car, AerialTurn.find_landing_orientation(bot.info.my_car, 200))

        self.aerialturn.step(0.01666)
        self.aerialturn.controls.throttle = 1
        bot.controls = self.aerialturn.controls
        bot.controls.throttle = True
        self.finished = self.aerialturn.finished
