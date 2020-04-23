from maneuvers.dribbling.carry import Carry
from maneuvers.jumps.air_dodge import AirDodge
from maneuvers.maneuver import Maneuver
from rlutilities.linear_algebra import vec3, dot, norm
from rlutilities.simulation import Car
from utils.drawing import DrawingTool
from utils.game_info import GameInfo
from utils.vector_math import ground_direction, distance, ground_distance, direction


class Dribble(Maneuver):
    """
    Carry the ball on roof, and flick it if an opponent is close or
    if fast enough and facing the target.
    """
    def __init__(self, car: Car, info: GameInfo, target: vec3):
        super().__init__(car)

        self.target = target
        self.info = info

        self.carry = Carry(car, info.ball, target)
        self.flick = AirDodge(car, 0.15, info.ball.position)
        self.flicking = False

    def interruptible(self) -> bool:
        return not self.flicking

    def step(self, dt):
        if not self.flicking:
            self.carry.step(dt)
            self.controls = self.carry.controls
            self.finished = self.carry.finished
            car = self.car
            ball = self.info.ball
            
            # check if it's a good idea to flick
            dir_to_target = ground_direction(car, self.target)
            if (
                distance(car, ball) < 150
                and ground_distance(car, ball) < 80
                and dot(car.forward(), dir_to_target) > 0.7
                and norm(car.velocity) > distance(car, self.target) / 3
                and norm(car.velocity) > 1300
                and dot(dir_to_target, ground_direction(car, ball)) > 0.9
            ):
                self.flicking = True
            
            # flick if opponent is close
            for opponent in self.info.get_opponents(car):
                if (
                    distance(opponent.position + opponent.velocity, car) < max(300.0, norm(opponent.velocity))
                    and dot(opponent.velocity, direction(opponent, self.info.ball)) > 0.5
                ):
                    if distance(car.position, self.info.ball.position) < 200:
                        self.flicking = True
                    else:
                        self.finished = True
        else:
            self.flick.step(dt)
            self.controls = self.flick.controls
            self.finished = self.flick.finished

    def render(self, draw: DrawingTool):
        if not self.flicking:
            self.carry.render(draw)
