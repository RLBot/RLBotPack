from rlbot.agents.base_agent import SimpleControllerState
from rlbot.messages.flat import GameTickPacket, FieldInfo

from strategy.objective import Objective
from util.rlmath import clip
from util.vec import Vec3, Mat33, euler_to_rotation, angle_between, norm


GRAVITY = Vec3(0, 0, -650)


class Field:
    WIDTH = 8192
    WIDTH2 = WIDTH / 2
    LENGTH = 10240
    LENGTH2 = LENGTH / 2
    HEIGHT = 2044


class Ball:
    RADIUS = 92

    def __init__(self, pos=Vec3(), vel=Vec3(), ang_vel=Vec3(), time=0.0):
        self.pos = pos
        self.vel = vel
        self.ang_vel = ang_vel
        self.time = time
        # self.last_touch # TODO
        # self.last_bounce # TODO


class Car:
    def __init__(self, index=-1, name="Unknown", team=0, pos=Vec3(), vel=Vec3(), ang_vel=Vec3(), rot=Mat33(), time=0.0):
        self.id = index
        self.name = name
        self.team = team
        self.team_sign = -1 if team == 0 else 1
        self.pos = pos
        self.vel = vel
        self.rot = rot
        self.ang_vel = ang_vel
        self.time = time

        self.is_demolished = False
        self.jumped = False
        self.double_jumped = False
        self.on_ground = True
        self.supersonic = False

        self.last_expected_time_till_reach_ball = 3

        self.last_input = SimpleControllerState()

        # Analytic info
        self.objective = Objective.UNKNOWN
        self.possession = 0
        self.onsite = False
        self.reach_ball_time = 0

    @property
    def forward(self) -> Vec3:
        return self.rot.col(0)

    @property
    def left(self) -> Vec3:
        return self.rot.col(1)

    @property
    def up(self) -> Vec3:
        return self.rot.col(2)


class BoostPad:
    def __init__(self, index, pos, is_big, is_active, timer):
        self.index = index
        self.pos = pos
        self.is_active = is_active
        self.timer = timer
        self.is_big = is_big


class Goal:
    WIDTH = 1900
    WIDTH2 = 1900 / 2
    HEIGHT = 640
    DEPTH = 880

    def __init__(self, team: int):
        team_sign = -1 if team == 0 else 1
        self.pos = Vec3(0, team_sign * Field.LENGTH2, 0)
        self.right_post = Vec3(-(Goal.WIDTH2 - 30) * team_sign, team_sign * Field.LENGTH2, 0)
        self.left_post = Vec3((Goal.WIDTH2 - 30) * team_sign, team_sign * Field.LENGTH2, 0)
        self.front = self.pos * 0.86  # A spot in front the goal


class GameInfo:
    def __init__(self, index, team):

        self.team = team
        self.index = index
        self.team_sign = -1 if team == 0 else 1

        self.dt = 0.016666
        self.time = 0
        self.is_kickoff = False
        self.last_kickoff_end_time = 0
        self.time_since_last_kickoff = 0

        self.ball = Ball()

        self.boost_pads = []
        self.small_boost_pads = []
        self.big_boost_pads = []
        self.convenient_boost_pad = None
        self.convenient_boost_pad_score = 0

        self.my_car = Car()
        self.cars = []
        self.teammates = []
        self.team_cars = []  # Includes us
        self.opponents = []

        self.goals = [Goal(0), Goal(1)]
        self.own_goal = self.goals[team]
        self.opp_goal = self.goals[not team]

        self.field_info_loaded = False

    def read_field_info(self, field_info: FieldInfo):
        if field_info is None or field_info.num_boosts == 0:
            return

        self.boost_pads = []
        self.small_boost_pads = []
        self.big_boost_pads = []
        for i in range(field_info.num_boosts):
            pad = field_info.boost_pads[i]
            pos = Vec3(pad.location)
            pad = BoostPad(i, pos, pad.is_full_boost, True, 0.0)
            self.boost_pads.append(pad)
            if pad.is_big:
                self.big_boost_pads.append(pad)
            else:
                self.small_boost_pads.append(pad)

        self.convenient_boost_pad = self.boost_pads[0]
        self.convenient_boost_pad_score = 0

        self.field_info_loaded = True

    def read_packet(self, packet: GameTickPacket):

        # Game state
        self.dt = packet.game_info.seconds_elapsed - self.time
        self.time = packet.game_info.seconds_elapsed
        self.is_kickoff = packet.game_info.is_kickoff_pause
        if self.is_kickoff:
            self.last_kickoff_end_time = self.time
        self.time_since_last_kickoff = self.time - self.last_kickoff_end_time

        # Read ball
        ball_phy = packet.game_ball.physics
        self.ball.pos = Vec3(ball_phy.location)
        self.ball.vel = Vec3(ball_phy.velocity)
        self.ball.ang_vel = Vec3(ball_phy.angular_velocity)
        self.ball.t = self.time
        # self.ball.step(dt)

        # Read cars
        for i in range(0, packet.num_cars):

            game_car = packet.game_cars[i]

            car_phy = game_car.physics

            car = self.cars[i] if i < len(self.cars) else Car()

            car.pos = Vec3(car_phy.location)
            car.vel = Vec3(car_phy.velocity)
            car.ang_vel = Vec3(car_phy.angular_velocity)
            car.rot = euler_to_rotation(Vec3(car_phy.rotation.pitch, car_phy.rotation.yaw, car_phy.rotation.roll))

            car.is_demolished = game_car.is_demolished
            car.on_ground = game_car.has_wheel_contact
            car.supersonic = game_car.is_super_sonic
            car.jumped = game_car.jumped
            car.double_jumped = game_car.double_jumped
            car.boost = game_car.boost
            car.time = self.time

            # car.extrapolate(dt)

            if len(self.cars) <= i:

                # First time we see this car
                car.index = i
                car.team = game_car.team
                car.name = game_car.name
                self.cars.append(car)

                if game_car.team == self.team:
                    if i == self.index:
                        self.my_car = car
                    else:
                        self.teammates.append(car)
                    self.team_cars.append(car)
                else:
                    self.opponents.append(car)

        # Read boost pads
        for i in range(0, len(self.boost_pads)):
            boost_pad = packet.game_boosts[i]
            self.boost_pads[i].is_active = boost_pad.is_active
            self.boost_pads[i].timer = boost_pad.timer

        self.convenient_boost_pad_score = 0
        for pad in self.boost_pads:
            pad_state = packet.game_boosts[pad.index]
            pad.is_active = pad_state.is_active
            pad.timer = pad_state.timer

            score = self.get_boost_pad_convenience_score(pad)
            if score > self.convenient_boost_pad_score:
                self.convenient_boost_pad = pad

        # self.time += dt

    def get_boost_pad_convenience_score(self, pad):
        if not pad.is_active:
            return 0

        car_to_pad = pad.pos - self.my_car.pos
        angle = angle_between(self.my_car.forward, car_to_pad)

        # Pads behind the car is bad
        if abs(angle) > 1.3:
            return 0

        dist = norm(car_to_pad)

        dist_score = 1 - clip((abs(dist) / 2500)**2, 0, 1)
        angle_score = 1 - clip((abs(angle) / 3), 0, 1)

        return dist_score * angle_score * (0.8, 1)[pad.is_big]

    def closest_enemy(self, pos: Vec3):
        enemy = None
        dist = -1
        for e in self.opponents:
            d = norm(e.pos - pos)
            if enemy is None or d < dist:
                enemy = e
                dist = d
        return enemy, dist


def is_near_wall(point: Vec3, offset: float=110) -> bool:
    return abs(point.x) > Field.WIDTH - offset or abs(point.y) > Field.LENGTH - offset  # TODO Add diagonal walls
