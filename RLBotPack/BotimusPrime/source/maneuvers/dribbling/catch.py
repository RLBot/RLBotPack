from maneuvers.kit import *

from maneuvers.driving.arrive import Arrive


class Catch(Maneuver):

    def __init__(self, car: Car, info: GameInfo, target: vec3):
        super().__init__(car)

        catch = Ball()
        for ball in info.ball_predictions:
            if ball.pos[2] < 120 and ball.vel[2] < 0:
                if estimate_time(car, ball.pos, estimate_max_car_speed(car)) < ball.t - car.time:
                    catch = ball
                    break
    
        self.arrive = Arrive(car, ground(catch), catch.t + 0.05, ground_direction(car, target))
        

    def step(self, dt):
        self.arrive.step(dt)
        self.finished = self.arrive.finished
        self.controls = self.arrive.controls
        if self.arrive.drive.target_speed < 300 and distance(self.car, self.arrive.target) < 200:
            self.controls.throttle = 0

    def render(self, draw: DrawingTool):
        self.arrive.render(draw)

