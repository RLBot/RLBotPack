from typing import List

from maneuvers.strikes.strike import Strike
from rlutilities.linear_algebra import vec3, norm, normalize, look_at
from rlutilities.mechanics import Aerial
from rlutilities.simulation import Car, Ball
from utils.drawing import DrawingTool
from utils.game_info import GameInfo
from utils.intercept import Intercept
from utils.math import range_map
from utils.vector_math import ground_direction, angle_to, distance, ground_distance, direction


class AerialStrike(Strike):
    MAX_DISTANCE_ERROR = 50
    DELAY_TAKEOFF = True
    MINIMAL_HEIGHT = 400
    MAXIMAL_HEIGHT = 800
    MINIMAL_HEIGHT_TIME = 1.0
    MAXIMAL_HEIGHT_TIME = 2.5
    DOUBLE_JUMP = False

    def __init__(self, car: Car, info: GameInfo, target: vec3 = None):
        self.aerial = Aerial(car)
        self.aerial.angle_threshold = 0.8
        self.aerial.single_jump = not self.DOUBLE_JUMP
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
        self.aerial.target = intercept.position - direction(intercept, self.target) * 80
        self.aerial.up = normalize(ground_direction(intercept, self.car) + vec3(0, 0, 0.5))
        self.aerial.arrival_time = intercept.time

    def simulate_flight(self, car: Car, write_to_flight_path=True) -> Car:
        test_car = Car(car)
        test_aerial = Aerial(test_car)
        test_aerial.target = self.aerial.target
        test_aerial.arrival_time = self.aerial.arrival_time
        test_aerial.angle_threshold = self.aerial.angle_threshold
        test_aerial.up = self.aerial.up
        test_aerial.single_jump = self.aerial.single_jump

        if write_to_flight_path:
            self._flight_path.clear()

        while not test_aerial.finished:
            test_aerial.step(1 / 120)
            test_car.boost = 100  # TODO: fix boost depletion in RLU car sim
            test_car.step(test_aerial.controls, 1 / 120)

            if write_to_flight_path:
                self._flight_path.append(vec3(test_car.position))

        return test_car

    def interruptible(self) -> bool:
        return self.aerialing or super().interruptible()

    def step(self, dt):
        if self.aerialing:
            self.aerial.target_orientation = look_at(direction(self.car, self.target), vec3(0, 0, -1))
            self.aerial.step(dt)
            self.controls = self.aerial.controls
            self.finished = self.aerial.finished

        else:
            super().step(dt)

            # simulate aerial from current state
            simulated_car = self.simulate_flight(self.car)

            # if the car ended up too far, we're too fast and we need to slow down
            if ground_distance(self.car, self.aerial.target) + 100 < ground_distance(self.car, simulated_car):
                # self.controls.throttle = -1
                pass

            # if it ended up near the target, we could take off
            elif distance(simulated_car, self.aerial.target) < self.MAX_DISTANCE_ERROR:
                if angle_to(self.car, self.aerial.target) < 0.1 or norm(self.car.velocity) < 1000:

                    if self.DELAY_TAKEOFF:
                        # extrapolate current state a small amount of time
                        future_car = Car(self.car)
                        time = 0.2
                        future_car.time += time
                        displacement = future_car.velocity * time if norm(future_car.velocity) > 500\
                            else normalize(future_car.velocity) * 500 * time
                        future_car.position += displacement

                        # simulate aerial fot the extrapolated car again
                        future_simulated_car = self.simulate_flight(future_car, write_to_flight_path=False)

                        # if the aerial is also successful, that means we should continue driving instead of taking off
                        # this makes sure that we go for the most late possible aerials, which are the most effective
                        if distance(future_simulated_car, self.aerial.target) > self.MAX_DISTANCE_ERROR:
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
    MINIMAL_HEIGHT_TIME = 1.5
    MAXIMAL_HEIGHT_TIME = 3.0
    DOUBLE_JUMP = True
