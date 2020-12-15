from typing import List, Tuple

from rlbot.utils.structures.game_data_struct import GameTickPacket, FieldInfoPacket

from rlutilities.simulation import Game, Car, Ball, Pad, Input
from rlutilities.linear_algebra import vec3, vec2, norm, normalize, cross, rotation, dot, xy

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

        self.large_boost_pads: List[Pad] = []
        self.small_boost_pads: List[Pad] = []

    def read_packet(self, packet: GameTickPacket, field_info: FieldInfoPacket):
        self.read_game_information(packet, field_info)
        self.large_boost_pads = self._get_large_boost_pads(field_info)
        self.small_boost_pads = self._get_small_boost_pads(field_info)

        # invert large boost pad timers
        for pad in self.large_boost_pads:
            pad.timer = 10.0 - pad.timer
        for pad in self.small_boost_pads:
            pad.timer = 4.0 - pad.timer
        
    def _get_large_boost_pads(self, field_info: FieldInfoPacket) -> List[Pad]:
        return [self.pads[i] for i in range(field_info.num_boosts) if field_info.boost_pads[i].is_full_boost]

    def _get_small_boost_pads(self, field_info: FieldInfoPacket) -> List[Pad]:
        return [self.pads[i] for i in range(field_info.num_boosts) if not field_info.boost_pads[i].is_full_boost]

    def get_teammates(self, car: Car) -> List[Car]:
        return [self.cars[i] for i in range(self.num_cars)
                if self.cars[i].team == self.team and self.cars[i].id != car.id]

    def get_opponents(self) -> List[Car]:
        return [self.cars[i] for i in range(self.num_cars) if self.cars[i].team != self.team]

    def predict_ball(self, duration=5.0, dt=1 / 120):
        self.about_to_score = False
        self.about_to_be_scored_on = False
        self.time_of_goal = -1

        self.ball_predictions = []
        prediction = Ball(self.ball)

        # nearest_opponent = Car(min(self.get_opponents(), key=lambda opponent: distance(opponent, prediction)))

        while prediction.time < self.time + duration:
            # if prediction.time < self.time + 1.0:
            #     nearest_opponent.step(Input(), dt)
            #     nearest_opponent.velocity[2] = 0
            #     prediction.step(dt, nearest_opponent)
            # else:
            prediction.step(dt)
            self.ball_predictions.append(Ball(prediction))

            if self.time_of_goal == -1:
                if self.my_goal.inside(prediction.position):
                    self.about_to_be_scored_on = True
                    self.time_of_goal = prediction.time
                if self.their_goal.inside(prediction.position):
                    self.about_to_score = True
                    self.time_of_goal = prediction.time

    def predict_car_drive(self, index, time_limit=2.0, dt=1/60) -> List[vec3]:
        """Simple prediction of a driving car assuming no acceleration."""
        car = self.cars[index]
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
        predictions = [self.predict_car_drive(i, time_limit=time_limit, dt=dt) for i in range(self.num_cars)]
        collisions = []
        for i in range(self.num_cars):
            for j in range(self.num_cars):
                if i >= j: 
                    continue

                for step in range(time_steps):
                    pos1 = predictions[i][step]
                    pos2 = predictions[j][step]
                    if distance(pos1, pos2) < self.COLLISION_THRESHOLD:
                        collisions.append((i, j, step * dt))
                        break
        
        return collisions
