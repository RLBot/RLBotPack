from maneuvers.kit import *

from maneuvers.driving.drive import Drive

class Carry(Maneuver):

    def __init__(self, car: Car, ball: Ball, target: vec3):
        super().__init__(car)

        self.ball = ball
        self.target = ground(target)
        self.drive = Drive(car)
        self._shift_direction = vec3(0, 0, 0)

    def step(self, dt):
        ball = Ball(self.ball)
        car = self.car

        while (ball.pos[2] > 120 or ball.vel[2] > 0) and ball.t < car.time + 10:
            ball.step(1/60)

        ball_local = local(car, ground(ball.pos))
        target = local(car, self.target)

        shift = ground(direction(ball_local, target))
        shift[1] *= 1.8
        shift = normalize(shift)
        
        max_turn = clamp(norm(car.vel) / 800, 0, 1)
        max_shift = normalize(vec3(1 - max_turn, max_turn * sign(shift[1]), 0))

        if abs(shift[1]) > abs(max_shift[1]) or shift[0] < 0:
            shift = max_shift
        shift *= 45

        shift[1] *= clamp(norm(car.vel)/1000, 1, 2)

        self._shift_direction = normalize(world(car, shift) - car.pos)

        target = world(car, ball_local - shift)
        speed = distance(car.pos, target) / max(0.001, ball.t - car.time)

        self.drive.target_speed = speed
        self.drive.target_pos = target

        self.drive.step(dt)
        self.controls = self.drive.controls
        self.finished = self.ball.pos[2] < 100 or ground_distance(self.ball, self.car) > 1500

    def render(self, draw: DrawingTool):
        draw.color(draw.pink)
        draw.triangle(self.car.pos + self._shift_direction * 50, self._shift_direction)
