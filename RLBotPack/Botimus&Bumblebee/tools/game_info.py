from typing import List, Tuple

from rlbot.utils.structures.game_data_struct import GameTickPacket, FieldInfoPacket

from rlutilities.linear_algebra import vec3, vec2, norm, normalize, cross, rotation, dot, xy
from rlutilities.simulation import Game, Car, Ball, BoostPad, BoostPadType
from tools.vector_math import distance


class Goal:

    WIDTH = 1784.0
    HEIGHT = 640.0
    DISTANCE = 5120.0

    def __init__(self, team):
        self.sign = 1 - 2 * team
        self.l_post = vec3(self.sign * Goal.WIDTH / 2, -self.sign * Goal.DISTANCE, 0)
        self.r_post = vec3(-self.sign * Goal.WIDTH / 2, -self.sign * Goal.DISTANCE, 0)
        self.team = team

    def inside(self, pos) -> bool:
        return pos[1] < -Goal.DISTANCE if self.team == 0 else pos[1] > Goal.DISTANCE

    @property
    def center(self):
        return vec3(0, -self.sign * Goal.DISTANCE, Goal.HEIGHT / 2.0)


class GameInfo(Game):

    def __init__(self, team):
        super().__init__()
        self.team = team
        self.my_goal = Goal(team)
        self.their_goal = Goal(1 - team)

        self.ball_predictions: List[Ball] = []
        self.about_to_score = False
        self.about_to_be_scored_on = False
        self.time_of_goal = -1

        self.large_boost_pads: List[BoostPad] = []
        self.small_boost_pads: List[BoostPad] = []

    def read_field_info(self, field_info: FieldInfoPacket):
        super().read_field_info(field_info)
        self.large_boost_pads = [pad for pad in self.pads if pad.type == BoostPadType.Full]
        self.small_boost_pads = [pad for pad in self.pads if pad.type == BoostPadType.Partial]

    def read_packet(self, packet: GameTickPacket):
        super().read_packet(packet)

        # invert large boost pad timers
        for pad in self.large_boost_pads:
            pad.timer = 10.0 - pad.timer
        for pad in self.small_boost_pads:
            pad.timer = 4.0 - pad.timer

    def get_teammates(self, my_car: Car) -> List[Car]:
        return [car for car in self.cars if car.team == self.team and car.id != my_car.id]

    def get_opponents(self) -> List[Car]:
        return [car for car in self.cars if car.team != self.team]

    def predict_ball(self, duration=5.0, dt=1 / 120):
        self.about_to_score = False
        self.about_to_be_scored_on = False
        self.time_of_goal = -1

        self.ball_predictions = []
        prediction = Ball(self.ball)

        while prediction.time < self.time + duration:
            prediction.step(dt)
            self.ball_predictions.append(Ball(prediction))

            if self.time_of_goal == -1:
                if self.my_goal.inside(prediction.position):
                    self.about_to_be_scored_on = True
                    self.time_of_goal = prediction.time
                if self.their_goal.inside(prediction.position):
                    self.about_to_score = True
                    self.time_of_goal = prediction.time

    @staticmethod
    def predict_car_drive(car: Car, time_limit=2.0, dt=1 / 60) -> List[vec3]:
        """Simple prediction of a driving car assuming no acceleration."""
        time_steps = int(time_limit / dt)
        speed = norm(car.velocity)
        ang_vel_z = car.angular_velocity[2]

        # predict circular path
        if ang_vel_z != 0 and car.on_ground:
            radius = speed / ang_vel_z
            centre = car.position - cross(normalize(xy(car.velocity)), vec3(0, 0, 1)) * radius
            centre_to_car = vec2(car.position - centre)
            return [
                vec3(dot(rotation(ang_vel_z * dt * i), centre_to_car)) + centre
                    for i in range(time_steps)]

        # predict straight path
        return [car.position + car.velocity * dt * i for i in range(time_steps)]

    COLLISION_THRESHOLD = 150

    def detect_collisions(self, time_limit=0.5, dt=1/60) -> List[Tuple[int, int, float]]:
        """Returns a list of tuples, where the first two elements are
        indices of cars and the last is time from now until the collision.
        """
        time_steps = int(time_limit / dt)
        predictions = [self.predict_car_drive(car, time_limit=time_limit, dt=dt) for car in self.cars]
        collisions = []
        for i in range(len(self.cars)):
            for j in range(len(self.cars)):
                if i >= j: 
                    continue

                for step in range(time_steps):
                    pos1 = predictions[i][step]
                    pos2 = predictions[j][step]
                    if distance(pos1, pos2) < self.COLLISION_THRESHOLD:
                        collisions.append((i, j, step * dt))
                        break
        
        return collisions
