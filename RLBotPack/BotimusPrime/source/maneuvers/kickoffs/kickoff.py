from maneuvers.kit import *

from maneuvers.driving.arrive import Arrive

class Kickoff(Maneuver):
    def __init__(self, car: Car, info: GameInfo):
        super().__init__(car)

        self.info = info

        self.action = Arrive(car, vec3(0,0,0), 0, direction(info.ball, info.their_goal.center))
        self.action.lerp_t = 0.4

        self.dodging = False
        self.dodge = AirDodge(car, 0.05, info.ball.pos)

    def step(self, dt):
        if not self.dodging and distance(self.car, self.info.ball) < 800:

            is_opponent_going_for_kickoff = False
            for opponent in self.info.opponents:
                if distance(self.info.ball, opponent) < 1500:
                    is_opponent_going_for_kickoff = True

            if is_opponent_going_for_kickoff:
                self.action = self.dodge
                self.dodging = True
            else:
                self.action.target = self.info.ball.pos + vec3(115, 0, 0)

        self.action.step(dt)
        self.controls = self.action.controls
        self.finished = self.info.ball.pos[0] != 0

    def render(self, draw: DrawingTool):
        if not self.dodging:
            self.action.render(draw)
