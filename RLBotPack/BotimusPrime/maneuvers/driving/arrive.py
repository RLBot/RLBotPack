from maneuvers.kit import *

from maneuvers.driving.drive import Drive
from maneuvers.driving.travel import Travel

class Arrive(Maneuver):
    '''
    Arrive at a target position at a certain time (game seconds).
    You can also specify `target_direction`, and it will try to arrive
    at an angle. However this does work well only if the car is already
    roughly facing the specified direction, and only if it's far enough.
    '''
    def __init__(self, car: Car):
        super().__init__(car)

        self.target_direction: vec3 = None
        self.target: vec3 = None
        self.time: float = 0
        self.drive = Drive(car)
        self.travel = Travel(car)
        self.lerp_t = 0.6
        self.allow_dodges_and_wavedashes: bool = True
        self.additional_shift = 0

    def step(self, dt):
        target = self.target
        car = self.car

        if self.target_direction is not None:
            car_vel = norm(car.velocity)
            target_direction = normalize(self.target_direction)
            shift = clamp(distance(car.position, target) * self.lerp_t, 0, car_vel * 1.5)
            if shift - self.additional_shift < turn_radius(clamp(car_vel, 1400, 2000) * 1.1):
                shift = 0
            else:
                shift += self.additional_shift
            translated_target = target - target_direction * shift

            translated_time = self.time - distance(translated_target, target) * 0.7 / max(1, clamp(car_vel, 500, 2300))
        else:
            translated_target = target
            translated_time = self.time
        
        self.drive.target_pos = translated_target
        dist_to_target = distance(car.position, translated_target)
        target_speed = clamp(dist_to_target / max(0.001, translated_time - car.time), 0, 2300)

        self.drive.target_speed = target_speed

        if (
            self.allow_dodges_and_wavedashes
            and car.boost < 5
            and dist_to_target > clamp(norm(car.velocity) + 600, 1400, 2300)
            and norm(car.velocity) < target_speed - 600
            or not self.travel.driving
        ):
            self.travel.target = target
            self.travel.step(dt)
            self.controls = self.travel.controls
        else:
            self.drive.step(dt)
            self.controls = self.drive.controls


        self.finished = self.car.time >= self.time
        return self.finished

    def render(self, draw: DrawingTool):
        self.drive.render(draw)

        if self.target_direction is not None:
            draw.color(draw.lime)
            draw.triangle(self.target - self.target_direction * 250, self.target_direction)

        