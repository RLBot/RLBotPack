from maneuvers.maneuver import Maneuver
from maneuvers.driving.drive import Drive
from rlutilities.linear_algebra import vec3, norm, normalize
from rlutilities.simulation import Car, Ball
from tools.drawing import DrawingTool
from tools.math import clamp, sign
from tools.vector_math import distance, ground_distance, direction, local, ground, world


class Carry(Maneuver):
    """
    Carry the ball on roof towards a target.
    Finishes if the ball hits the floor.
    """
    def __init__(self, car: Car, ball: Ball, target: vec3):
        super().__init__(car)

        self.ball = ball
        self.target = ground(target)
        self.drive = Drive(car)
        self._shift_direction = vec3(0, 0, 0)

    def step(self, dt):
        ball = Ball(self.ball)
        car = self.car

        # simulate ball until it gets near the floor
        while (ball.position[2] > 120 or ball.velocity[2] > 0) and ball.time < car.time + 10:
            ball.step(1/60)

        ball_local = local(car, ground(ball.position))
        target = local(car, self.target)

        shift = ground(direction(ball_local, target))
        shift[1] *= 1.8
        shift = normalize(shift)
        
        max_turn = clamp(norm(car.velocity) / 800, 0, 1)
        max_shift = normalize(vec3(1 - max_turn, max_turn * sign(shift[1]), 0))

        if abs(shift[1]) > abs(max_shift[1]) or shift[0] < 0:
            shift = max_shift
        shift *= clamp(car.boost, 40, 60)

        shift[1] *= clamp(norm(car.velocity)/1000, 1, 2)

        self._shift_direction = normalize(world(car, shift) - car.position)

        target = world(car, ball_local - shift)
        speed = distance(car.position, target) / max(0.001, ball.time - car.time)

        self.drive.target_speed = speed
        self.drive.target_pos = target

        self.drive.step(dt)
        self.controls = self.drive.controls
        self.finished = self.ball.position[2] < 100 or ground_distance(self.ball, self.car) > 2000

    def render(self, draw: DrawingTool):
        draw.color(draw.pink)
        draw.triangle(self.car.position + self._shift_direction * 50, self._shift_direction)
