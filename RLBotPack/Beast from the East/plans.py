import time

from RLUtilities.Maneuvers import AerialTurn
from rlbot.agents.base_agent import SimpleControllerState

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
                target_local = dot(car_to_target, car.theta)
                target_local[Z] = 0

                direction = normalize(target_local)

                self.controls.roll = 0
                self.controls.pitch = -direction[X]
                self.controls.yaw = sign(car.theta[2, 2]) * direction[Y]

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
                target_local = dot(car_to_target, car.theta)
                target_local[Z] = 0

                direction = normalize(target_local)

                self.controls.roll = 0
                self.controls.pitch = -direction[X]
                self.controls.yaw = sign(car.theta[2, 2]) * direction[Y]

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

        point = vec3(0, bot.info.team_sign * (dist / 2.6 - MIDDLE_OFFSET), 0)
        speed = 2300
        opp_dist = norm(bot.info.opponents[0].pos)
        opp_does_kick = opp_dist < dist + 600

        # Opponent is not going for kickoff, so we slow down a bit
        if not opp_does_kick:
            speed = 2210
            point = vec3(0, bot.info.team_sign * (dist / 2.05 - MIDDLE_OFFSET), 0)
            point += vec3(35 * sign(car.pos[X]), 0, 0)


        # Dodge when close to (0, 0) - but only if the opponent also goes for kickoff. The dodge itself should happen in about 0.3 seconds
        if dist - DODGE_DIST < vel_p * 0.3 and opp_does_kick:
            bot.drive.start_dodge()

        # Make two dodges when spawning far back
        elif dist > 3640 and vel_p > 1200 and not opp_does_kick:
            bot.drive.start_dodge()

        # Pickup boost when spawning back corner by driving a bit towards the middle boost pad first
        elif abs(car.pos[X]) > 230 and abs(car.pos[Y]) > 2880:
            # The pads exact location is (0, 2816), but don't have to be exact
            point[Y] = bot.info.team_sign * 2790

        bot.controls = bot.drive.go_towards_point(bot, point, target_vel=speed, slide=False, boost=True, can_dodge=False, can_keep_speed=False)
        self.finished = not bot.info.is_kickoff

        if bot.do_rendering:
            bot.renderer.draw_line_3d(car.pos, point, bot.renderer.white())


def choose_kickoff_plan(bot):

    # Do we have teammates? If no -> always go for kickoff
    if len(bot.info.teammates) == 0:
        return KickoffPlan()

    # Kickoff spawn locations (corners may vary from map to map)
    ts = bot.info.team_sign
    right_corner_loc = vec3(-1970, ts * 2450, 0)   # actually left for orange
    left_corner_loc = vec3(1970, ts * 2450, 0)   # actually right for orange
    back_right_loc = vec3(-256, ts * 3840, 0)   # actually left for orange
    back_left_loc = vec3(256, ts * 3840, 0)   # actually right for orange
    back_center_loc = vec3(0, ts * 4608, 0)

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
        if bot.info.my_car.pos[X] > 10:
            # go for left boost
            return CollectSpecificBoostPlan(vec3(boost_x, boost_y, 0))
        if bot.info.my_car.pos[X] < -10:
            # go for right boost
            return CollectSpecificBoostPlan(vec3(-boost_x, boost_y, 0))
        if 0 <= index_of_teammate_at_kickoff_spawn(bot, back_right_loc):
            # go for left boost
            return CollectSpecificBoostPlan(vec3(boost_x, boost_y, 0))
        else:
            # go for right boost
            return CollectSpecificBoostPlan(vec3(-boost_x, boost_y, 0))

    # No teammate in the corner
    # Are we back right or left -> go for kickoff
    if is_my_kickoff_spawn(bot, back_right_loc)\
            or is_my_kickoff_spawn(bot, back_left_loc):
        return KickoffPlan()

    # No teammate in the corner
    # Is a teammate back right or left -> collect boost
    if 0 <= index_of_teammate_at_kickoff_spawn(bot, back_right_loc):
        # go for left boost
        return CollectSpecificBoostPlan(vec3(boost_x, boost_y, 0))
    elif 0 <= index_of_teammate_at_kickoff_spawn(bot, back_left_loc):
        # go for right boost
        return CollectSpecificBoostPlan(vec3(-boost_x, boost_y, 0))

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
    for i, car in enumerate(bot.info.cars):
        if car.team == bot.info.my_car.team:
            dist = norm(car.pos - loc)
            if dist < 150:
                return i
    return -1


class SecondManSlowCornerKickoffPlan:
    def __init__(self, bot):
        self.finished = False

        # These vectors will help us make the curve
        ts = bot.info.team_sign
        self.target_loc = vec3(0, ts * 400, 0)
        self.target_dir = vec3(0, -ts, 0)

    def execute(self, bot):
        car = bot.info.my_car

        curve_point = curve_from_arrival_dir(car.pos, self.target_loc, self.target_dir)
        bot.controls = bot.drive.go_towards_point(bot, curve_point, target_vel=1400, slide=True, boost=True, can_keep_speed=False)

        self.finished = norm(car.pos) < 1000   # End plan when reaching getting close to ball (approx at boost pad)


class CollectSpecificBoostPlan:
    def __init__(self, pad_pos):
        self.finished = False
        self.boost_pad_pos = pad_pos

    def execute(self, bot):
        car = bot.info.my_car

        # Drive towards the pad
        bot.controls = bot.drive.go_towards_point(bot, self.boost_pad_pos, target_vel=2300, boost=True, can_keep_speed=True)

        car_to_pad = self.boost_pad_pos - car.pos
        vel = proj_onto_size(car.vel, car_to_pad)
        dist = norm(car_to_pad)
        if dist < vel * 0.3:
            self.finished = True


class CollectClosestBoostPlan:
    def __init__(self, specific_loc=None):
        self.finished = False
        self.big_pad_locs = [
            vec3(3584, 0, 0),
            vec3(-3584, 0, 0),
            vec3(3072, 4096, 0),
            vec3(3072, -4096, 0),
            vec3(-3072, 4096, 0),
            vec3(-3072, -4096, 0)
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
        bot.controls = bot.drive.go_towards_point(bot, self.closest_pad, target_vel=2300, boost=True, can_keep_speed=True)

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
            self.aerialturn = AerialTurn(bot.info.my_car)

        self.aerialturn.step(0.01666)
        self.aerialturn.controls.throttle = 1
        bot.controls = self.aerialturn.controls
        bot.controls.throttle = True
        self.finished = self.aerialturn.finished
