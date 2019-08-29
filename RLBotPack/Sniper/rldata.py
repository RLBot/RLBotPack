from rlbot.agents.base_agent import SimpleControllerState
from rlbot.messages.flat import GameTickPacket

from rlmath import euler_to_rotation
from vec import Vec3, norm, dot, Mat33

GRAVITY = Vec3(0, 0, -650)


class Field:
    WIDTH = 8192
    LENGTH = 10240
    HEIGHT = 2044
    GOAL_WIDTH = 1900
    GOAL_HEIGHT = 640


class Ball:
    RADIUS = 92

    def __init__(self, pos=Vec3(), vel=Vec3(), ang_vel=Vec3(), time=0.0):
        self.pos = pos
        self.vel = vel
        self.ang_vel = ang_vel
        self.time = time


class Car:
    def __init__(self, index=-1, name="Unknown", team=0, pos=Vec3(), vel=Vec3(), ang_vel=Vec3(), rot=Mat33(), time=0.0):
        self.index = index
        self.name = name
        self.team = team
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

        self.last_input = SimpleControllerState()

        self.is_sniper = False
        self.sniper_index = -1  # Index in GameInfo::sniper_teammates
        self.aim_pos = Vec3()

        # Spike Rush stuff
        self._ball_last_rel_poss = [Vec3(), Vec3(), Vec3()]
        self._next_rel_pos_to_replace = 0
        self.has_ball_spiked = False

    def eval_spike_rush(self, ball_pos):
        dist = norm(ball_pos - self.pos)
        if dist > 160:
            self.has_ball_spiked = False

        rel_pos = dot(ball_pos - self.pos, self.rot)
        self._ball_last_rel_poss[self._next_rel_pos_to_replace] = rel_pos
        self._next_rel_pos_to_replace = (self._next_rel_pos_to_replace + 1) % 3

        change = norm(self._ball_last_rel_poss[0] - self._ball_last_rel_poss[1]) + \
                 norm(self._ball_last_rel_poss[1] - self._ball_last_rel_poss[2])

        self.has_ball_spiked = change < 1 and dist < 200

    @property
    def forward(self) -> Vec3:
        return self.rot.col(0)

    @property
    def left(self) -> Vec3:
        return self.rot.col(1)

    @property
    def up(self) -> Vec3:
        return self.rot.col(2)


class GameInfo:
    def __init__(self, index, team):

        self.team = team
        self.index = index
        self.team_sign = -1 if team == 0 else 1
        self.snipers_on_team = 0
        self.aim_poss_determined = False

        self.dt = 0.016666
        self.time = 0
        self.clock_dt = 0
        self.clock = -1
        self.is_kickoff = False

        self.ball = Ball()

        self.my_car = Car()
        self.cars = []
        self.teammates = []
        self.allied_snipers = []
        self.opponents = []

        self.own_goal = Vec3(0, self.team_sign * Field.LENGTH / 2, 0)
        self.enemy_goal = Vec3(0, -self.team_sign * Field.LENGTH / 2, 0)

        # Spike Rush stuff
        self.car_spiking_ball = None
        self.prev_car_spiking_ball = None
        self.car_spiking_changed = False

    def read_packet(self, packet: GameTickPacket):

        # Game state
        self.dt = packet.game_info.seconds_elapsed - self.time
        self.time = packet.game_info.seconds_elapsed
        self.clock_dt = packet.game_info.game_time_remaining - self.clock if self.clock != -1 else 0
        self.clock = packet.game_info.game_time_remaining
        self.is_kickoff = packet.game_info.is_kickoff_pause

        # Read ball
        ball_phy = packet.game_ball.physics
        self.ball.pos = Vec3(ball_phy.location)
        self.ball.vel = Vec3(ball_phy.velocity)
        self.ball.ang_vel = Vec3(ball_phy.angular_velocity)
        self.ball.t = self.time

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
                else:
                    self.opponents.append(car)

                if car.name[:6] == "Sniper":
                    car.is_sniper = True
                    if game_car.team == self.team:
                        car.sniper_index = len(self.allied_snipers)  # Self included
                        self.allied_snipers.append(car)

                self.determine_aim_poss()  # Update all aim poss

        # Spike Rush stuff
        self.prev_car_spiking_ball = self.car_spiking_ball
        self.car_spiking_ball = None
        for car in self.cars:
            car.eval_spike_rush(self.ball.pos)
            if car.has_ball_spiked:
                self.car_spiking_ball = car
        self.car_spiking_changed = self.prev_car_spiking_ball != self.car_spiking_ball

    def determine_aim_poss(self):
        self.aim_poss_determined = True
        snipers_on_team = len(self.allied_snipers)  # Self included

        z = 300
        y = 5030
        spacing = 400

        for car in self.allied_snipers:
            if snipers_on_team == 1:
                car.aim_pos = Vec3(0, self.team_sign * y, z)
            elif snipers_on_team == 2:
                car.aim_pos = Vec3(-400 + car.sniper_index * 800, self.team_sign * y, z)
            else:
                is_top_row = (car.sniper_index < snipers_on_team / 2)
                offset = spacing * (snipers_on_team - 2) / 4
                row_index = car.sniper_index if is_top_row else car.sniper_index - snipers_on_team / 2
                x = -offset + row_index * spacing
                car.aim_pos = Vec3(x, self.team_sign * y, z + 150 * is_top_row)


def is_near_wall(point: Vec3, offset: float = 110) -> bool:
    return abs(point.x) > Field.WIDTH - offset or abs(point.y) > Field.LENGTH - offset  # TODO Add diagonal walls
