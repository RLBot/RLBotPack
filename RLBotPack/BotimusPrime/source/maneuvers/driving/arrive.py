from maneuvers.kit import *

from maneuvers.driving.drive import Drive
from maneuvers.driving.travel import Travel

class Arrive(Maneuver):

    def __init__(self, car: Car, target=vec3(0, 0, 0), time=0, target_direction: vec3 = None):
        super().__init__(car)

        self.target_direction = target_direction
        self.target = target
        self.time = time
        self.drive = Drive(car, target)
        self.travel = Travel(car)
        self.lerp_t = 0.6

    def step(self, dt):
        target = self.target
        car = self.car

        if self.target_direction is not None:
            car_vel = norm(car.vel)
            target_direction = normalize(self.target_direction)
            shift = clamp(distance(car.pos, target) * self.lerp_t, 0, car_vel * 1.5)
            if shift < turn_radius(clamp(car_vel, 1400, 2000) * 1.1):
                shift = 0
            translated_target = target - target_direction * shift

            translated_time = self.time - distance(translated_target, target) / max(1, clamp(car_vel, 500, 2300))
        else:
            translated_target = target
            translated_time = self.time
        
        self.drive.target_pos = translated_target
        dist_to_target = distance(car.pos, translated_target)
        target_speed = clamp(dist_to_target / max(0.001, translated_time - car.time), 0, 2300)

        self.drive.target_speed = target_speed

        if car.boost < 1 and dist_to_target > 3000:
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

        