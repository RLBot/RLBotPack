from rlbot.agents.base_agent import SimpleControllerState

from maneuvers.maneuver import Maneuver
from utility import draw
from utility.curves import curve_from_arrival_dir
from utility.rlmath import sign
from utility.vec import Vec3, norm, proj_onto_size


def choose_kickoff_maneuver(bot) -> Maneuver:
    # Do we have teammates? If no -> always go for kickoff
    if len(bot.info.teammates) == 0:
        return KickoffManeuver()

    # Kickoff spawn locations (corners may vary from map to map)
    ts = bot.info.team_sign
    right_corner_loc = Vec3(-1970, ts * 2450, 0)  # actually left for orange
    left_corner_loc = Vec3(1970, ts * 2450, 0)  # actually right for orange
    back_right_loc = Vec3(-256, ts * 3840, 0)  # actually left for orange
    back_left_loc = Vec3(256, ts * 3840, 0)  # actually right for orange
    back_center_loc = Vec3(0, ts * 4608, 0)

    boost_x = 3072
    boost_y = ts * 4096
    left_boost_pad_loc = Vec3(boost_x, boost_y, 0)
    right_boost_pad_loc = Vec3(-boost_x, boost_y, 0)

    # Are we in the corner -> go for kickoff (If two bots are in the corners, we assume lowest index goes for kickoff)
    if is_my_kickoff_spawn(bot, right_corner_loc):
        tm_index = index_of_teammate_at_kickoff_spawn(bot, left_corner_loc)
        if 0 <= tm_index < bot.index:
            return SecondManSlowCornerKickoffManeuver(bot)
        else:
            return KickoffManeuver()
    if is_my_kickoff_spawn(bot, left_corner_loc):
        tm_index = index_of_teammate_at_kickoff_spawn(bot, right_corner_loc)
        if 0 <= tm_index < bot.index:
            return SecondManSlowCornerKickoffManeuver(bot)
        else:
            return KickoffManeuver()

    # Is a teammate in the corner -> collect boost
    if 0 <= index_of_teammate_at_kickoff_spawn(bot, right_corner_loc) \
            or 0 <= index_of_teammate_at_kickoff_spawn(bot, left_corner_loc):
        if bot.info.my_car.pos.x > 10:
            # go for left boost
            return CollectSpecificBoostManeuver(left_boost_pad_loc)
        if bot.info.my_car.pos.x < -10:
            # go for right boost
            return CollectSpecificBoostManeuver(right_boost_pad_loc)
        if 0 <= index_of_teammate_at_kickoff_spawn(bot, back_right_loc):
            # go for left boost
            return CollectSpecificBoostManeuver(left_boost_pad_loc)
        else:
            # go for right boost
            return CollectSpecificBoostManeuver(right_boost_pad_loc)

    # No teammate in the corner
    # Are we back right or left -> go for kickoff
    # (If two bots are in the back corners, we assume lowest index goes for kickoff)
    if is_my_kickoff_spawn(bot, back_left_loc):
        tm_index = index_of_teammate_at_kickoff_spawn(bot, back_right_loc)
        if 0 <= tm_index < bot.index:
            # go for left boost
            return CollectSpecificBoostManeuver(left_boost_pad_loc)
        else:
            return KickoffManeuver()
    if is_my_kickoff_spawn(bot, back_right_loc):
        tm_index = index_of_teammate_at_kickoff_spawn(bot, back_left_loc)
        if 0 <= tm_index < bot.index:
            # go for right boost
            return CollectSpecificBoostManeuver(right_boost_pad_loc)
        else:
            return KickoffManeuver()

    # No teammate in the corner
    # Is a teammate back right or left -> collect boost
    if 0 <= index_of_teammate_at_kickoff_spawn(bot, back_right_loc):
        # go for left boost
        return CollectSpecificBoostManeuver(left_boost_pad_loc)
    elif 0 <= index_of_teammate_at_kickoff_spawn(bot, back_left_loc):
        # go for right boost
        return CollectSpecificBoostManeuver(right_boost_pad_loc)

    # We have no teammates
    return KickoffManeuver()


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


class KickoffManeuver(Maneuver):
    def exec(self, bot) -> SimpleControllerState:
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

        # Dodge when close to (0, 0) - but only if the opponent also goes for kickoff.
        # The dodge itself should happen in about 0.3 seconds
        if dist - DODGE_DIST < vel_p * 0.3 and opp_does_kick:
            bot.drive.start_dodge(bot)

        # Make two dodges when spawning far back
        elif dist > 3640 and vel_p > 1200 and not opp_does_kick:
            bot.drive.start_dodge(bot)

        # Pickup boost when spawning back corner by driving a bit towards the middle boost pad first
        elif abs(car.pos.x) > 230 and abs(car.pos.y) > 2880:
            # The pads exact location is (0, 2816), but don't have to be exact
            point.y = bot.info.team_sign * 2790

        self.done = not bot.info.is_kickoff
        draw.line(car.pos, point, bot.renderer.white())

        return bot.drive.towards_point(bot, point, target_vel=speed, slide=False, boost_min=0,
                                       can_dodge=False, can_keep_speed=False)


class SecondManSlowCornerKickoffManeuver(Maneuver):
    def __init__(self, bot):
        super().__init__()

        # These vectors will help us make the curve
        ts = bot.info.team_sign
        self.target_loc = Vec3(0, ts * 400, 0)
        self.target_dir = Vec3(0, -ts, 0)

    def exec(self, bot) -> SimpleControllerState:
        car = bot.info.my_car

        self.done = norm(car.pos) < 1100  # End when getting close to ball (approx at boost pad)

        curve_point = curve_from_arrival_dir(car.pos, self.target_loc, self.target_dir)
        return bot.drive.towards_point(bot, curve_point, target_vel=1200, slide=True, boost_min=20,
                                       can_keep_speed=False)


class CollectSpecificBoostManeuver(Maneuver):
    def __init__(self, pad_pos: Vec3):
        super().__init__()
        self.boost_pad_pos = pad_pos

    def exec(self, bot) -> SimpleControllerState:
        car = bot.info.my_car

        car_to_pad = self.boost_pad_pos - car.pos
        vel = proj_onto_size(car.vel, car_to_pad)
        dist = norm(car_to_pad)
        if dist < vel * 0.3:
            self.done = True

        # Drive towards the pad
        return bot.drive.towards_point(bot, self.boost_pad_pos, target_vel=2300, boost_min=0, can_keep_speed=True)
