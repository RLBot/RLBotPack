from typing import List

from maneuvers.strikes.strike import Strike
from rlutilities.linear_algebra import vec3, norm, normalize, look_at, dot, xy
from rlutilities.mechanics import Aerial
from rlutilities.simulation import Car, Ball
from tools.drawing import DrawingTool
from tools.game_info import GameInfo
from tools.intercept import Intercept
from tools.math import range_map
from tools.vector_math import ground_direction, angle_to, distance, ground_distance, direction


class AerialStrike(Strike):
    MAX_DISTANCE_ERROR = 50
    DELAY_TAKEOFF = True
    MINIMAL_HEIGHT = 500
    MAXIMAL_HEIGHT = 800
    MINIMAL_HEIGHT_TIME = 0.8
    MAXIMAL_HEIGHT_TIME = 1.5
    DOUBLE_JUMP = False

    def __init__(self, car: Car, info: GameInfo, target: vec3 = None):
        self.aerial = Aerial(car)
        self.aerial.angle_threshold = 0.8
        self.aerial.double_jump = self.DOUBLE_JUMP
        super().__init__(car, info, target)
        self.arrive.allow_dodges_and_wavedashes = False

        self.aerialing = False
        self.too_early = False
        self._flight_path: List[vec3] = []

    def intercept_predicate(self, car: Car, ball: Ball):
        required_time = range_map(ball.position[2],
                                  self.MINIMAL_HEIGHT,
                                  self.MAXIMAL_HEIGHT,
                                  self.MINIMAL_HEIGHT_TIME,
                                  self.MAXIMAL_HEIGHT_TIME)
        return self.MINIMAL_HEIGHT < ball.position[2] < self.MAXIMAL_HEIGHT and ball.time - car.time > required_time

    def configure(self, intercept: Intercept):
        super().configure(intercept)
        self.aerial.target_position = intercept.position - direction(intercept, self.target) * 100
        self.aerial.up = normalize(ground_direction(intercept, self.car) + vec3(0, 0, 0.5))
        self.aerial.arrival_time = intercept.time

    @staticmethod
    def simulate_flight(car: Car, aerial: Aerial, flight_path: List[vec3] = None) -> Car:
        test_car = Car(car)
        test_aerial = Aerial(test_car)
        test_aerial.target_position = aerial.target_position
        test_aerial.arrival_time = aerial.arrival_time
        test_aerial.angle_threshold = aerial.angle_threshold
        test_aerial.up = aerial.up
        test_aerial.double_jump = aerial.double_jump

        if flight_path: flight_path.clear()

        while not test_aerial.finished:
            test_aerial.step(1 / 120)
            test_car.boost = 100  # TODO: fix boost depletion in RLU car sim
            test_car.step(test_aerial.controls, 1 / 120)

            if flight_path:
                flight_path.append(vec3(test_car.position))

        return test_car

    def interruptible(self) -> bool:
        return self.aerialing or super().interruptible()

    def step(self, dt):
        time_left = self.aerial.arrival_time - self.car.time

        if self.aerialing:
            to_ball = direction(self.car, self.info.ball)

            # freestyling
            if self.car.position[2] > 200:
                # if time_left > 0.7:
                #     rotation = axis_to_rotation(self.car.forward() * 0.5)
                #     self.aerial.up = dot(rotation, self.car.up())
                # else:
                self.aerial.up = vec3(0, 0, -1) + xy(to_ball)

            if time_left > 0.5:
                self.info.predict_ball(3.0)
                same_time_intercept = Intercept(self.car, self.info.ball_predictions, lambda car, ball: ball.time >= self.intercept.time, ignore_time_estimate=True)
                self.intercept.ball.position = same_time_intercept.position  # just for rendering
                self.configure(same_time_intercept)

            self.aerial.target_orientation = look_at(to_ball, vec3(0, 0, -3) + to_ball)
            self.aerial.step(dt)

            self.controls = self.aerial.controls
            self.finished = self.aerial.finished and time_left < -0.3

        else:
            super().step(dt)

            # simulate aerial from current state
            simulated_car = self.simulate_flight(self.car, self.aerial, self._flight_path)

            speed_towards_target = dot(self.car.velocity, ground_direction(self.car, self.aerial.target_position))
            speed_needed = ground_distance(self.car, self.aerial.target_position) / time_left

            # too fast, slow down
            if speed_towards_target > speed_needed and angle_to(self.car, self.aerial.target_position) < 0.1:
                self.controls.throttle = -1

            # if it ended up near the target, we could take off
            elif distance(simulated_car, self.aerial.target_position) < self.MAX_DISTANCE_ERROR:
                if angle_to(self.car, self.aerial.target_position) < 0.1 or norm(self.car.velocity) < 1000:

                    if self.DELAY_TAKEOFF and ground_distance(self.car, self.aerial.target_position) > 1000:
                        # extrapolate current state a small amount of time
                        future_car = Car(self.car)
                        time = 0.5
                        future_car.time += time
                        displacement = future_car.velocity * time if norm(future_car.velocity) > 500\
                            else normalize(future_car.velocity) * 500 * time
                        future_car.position += displacement

                        # simulate aerial fot the extrapolated car again
                        future_simulated_car = self.simulate_flight(future_car, self.aerial)

                        # if the aerial is also successful, that means we should continue driving instead of taking off
                        # this makes sure that we go for the most late possible aerials, which are the most effective
                        if distance(future_simulated_car, self.aerial.target_position) > self.MAX_DISTANCE_ERROR:
                            self.aerialing = True
                        else:
                            self.too_early = True
                    else:
                        self.aerialing = True

            else:
                # self.controls.boost = True
                self.controls.throttle = 1

    def render(self, draw: DrawingTool):
        super().render(draw)
        draw.color(draw.lime if self.aerialing else (draw.orange if self.too_early else draw.red))
        draw.polyline(self._flight_path)


class FastAerialStrike(AerialStrike):
    DELAY_TAKEOFF = False
    MINIMAL_HEIGHT = 800
    MAXIMAL_HEIGHT = 1800
    MINIMAL_HEIGHT_TIME = 1.3
    MAXIMAL_HEIGHT_TIME = 2.5
    DOUBLE_JUMP = True
