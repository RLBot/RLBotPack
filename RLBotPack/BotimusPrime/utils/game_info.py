from typing import List

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

    def __init__(self, index, team):
        super().__init__(index, team)
        self.my_goal = Goal(team)
        self.their_goal = Goal(1 - team)

        self.about_to_score = False
        self.about_to_be_scored_on = False
        self.time_of_goal = -1

        self.ball_predictions: List[Ball] = list()

        self.teammates: List[Car] = []
        self.opponents: List[Car] = []
        self.large_boost_pads: List[Pad] = []

    def read_packet(self, packet, field_info):
        self.read_game_information(packet, field_info)
        self.teammates = self.get_teammates()
        self.opponents = self.get_opponents()
        self.large_boost_pads = self.get_large_boost_pads()
        
    def get_large_boost_pads(self) -> List[Pad]:
        return [self.pads[3], 
                self.pads[4], 
                self.pads[15],
                self.pads[18],
                self.pads[29],
                self.pads[30]]

    def get_teammates(self) -> List[Car]:
        cars: List[Car] = []
        for i in range(self.num_cars):
            if self.cars[i].team == self.team and self.cars[i].id != self.id:
                cars.append(self.cars[i])
        return cars

    def get_opponents(self) -> List[Car]:
        cars: List[Car] = []
        for i in range(self.num_cars):
            if self.cars[i].team != self.team:
                cars.append(self.cars[i])
        return cars

    def predict_ball(self, num_steps, dt):

        self.about_to_score = False
        self.about_to_be_scored_on = False
        self.time_of_goal = -1

        self.ball_predictions = []
        prediction = Ball(self.ball)

        for _ in range(0, num_steps):
            prediction.step(dt)
            self.ball_predictions.append(Ball(prediction))

            if self.time_of_goal == -1:
                if self.my_goal.inside(prediction.position):
                    self.about_to_be_scored_on = True
                    self.time_of_goal = prediction.time
                if self.their_goal.inside(prediction.position):
                    self.about_to_score = True
                    self.time_of_goal = prediction.time
