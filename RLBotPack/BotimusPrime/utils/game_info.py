from typing import List

from rlbot.utils.structures.game_data_struct import GameTickPacket, FieldInfoPacket

from rlutilities.simulation import Game, Car, Ball, Pad
from rlutilities.linear_algebra import vec3


class Goal:

    WIDTH = 1784.0
    HEIGHT = 640.0
    DISTANCE = 5120.0

    def __init__(self, team):
        sign = -1 if team == 0 else 1
        self.center = vec3(0, sign * Goal.DISTANCE, Goal.HEIGHT / 2.0)
        self.team = team

    def inside(self, pos) -> bool:
        return pos[1] < -Goal.DISTANCE if self.team == 0 else pos[1] > Goal.DISTANCE


class GameInfo(Game):

    def __init__(self, team):
        super().__init__(team)
        self.my_goal = Goal(team)
        self.their_goal = Goal(1 - team)

        self.ball_predictions: List[Ball] = []
        self.about_to_score = False
        self.about_to_be_scored_on = False
        self.time_of_goal = -1

        self.large_boost_pads: List[Pad] = []

    def read_packet(self, packet: GameTickPacket, field_info: FieldInfoPacket):
        self.read_game_information(packet, field_info)
        self.large_boost_pads = self._get_large_boost_pads(field_info)

        # invert large boost pad timers
        for pad in self.large_boost_pads:
            pad.timer = 10.0 - pad.timer
        
    def _get_large_boost_pads(self, field_info: FieldInfoPacket) -> List[Pad]:
        return [self.pads[i] for i in range(field_info.num_boosts) if field_info.boost_pads[i].is_full_boost]

    def get_teammates(self, car: Car) -> List[Car]:
        return [self.cars[i] for i in range(self.num_cars)
                if self.cars[i].team == self.team and self.cars[i].id != car.id]

    def get_opponents(self, car: Car) -> List[Car]:
        return [self.cars[i] for i in range(self.num_cars) if self.cars[i].team != car.team]

    def predict_ball(self, time_limit=6.0, dt=1/120):
        self.about_to_score = False
        self.about_to_be_scored_on = False
        self.time_of_goal = -1

        self.ball_predictions = []
        prediction = Ball(self.ball)

        while prediction.time < self.ball.time + time_limit:
            prediction.step(dt)
            self.ball_predictions.append(Ball(prediction))

            if self.time_of_goal == -1:
                if self.my_goal.inside(prediction.position):
                    self.about_to_be_scored_on = True
                    self.time_of_goal = prediction.time
                if self.their_goal.inside(prediction.position):
                    self.about_to_score = True
                    self.time_of_goal = prediction.time
