from maneuvers.kit import *

from maneuvers.driving.drive import Drive
from RLUtilities.Maneuvers import HalfFlip
from RLUtilities.Maneuvers import Wavedash

class Travel(Maneuver):

    def __init__(self, car: Car, target: vec3 = vec3(0, 0, 0), waste_boost=False):
        super().__init__(car)

        self.target = Arena.clamp(ground(target), 100)
        self.waste_boost = waste_boost
        self.finish_distance = 500

        self._time_on_ground = 0
        self._driving = True

        self.dodge_duration = 1.6
        self.halflip_duration = 2
        self.wavedash_duration = 1.3

        # decide whether to start driving backwards and halfflip later
        forward_est = estimate_time(car, target, estimate_max_car_speed(car))
        backwards_est = estimate_time(car, target, 1400, -1) + 0.5
        backwards = backwards_est < forward_est \
                    and (distance(car, target) > 3000 or distance(car, target) < 300) \
                    and car.pos[2] < 200

        self.drive = Drive(car, self.target, 2300, backwards)
        self.action = self.drive

    def step(self, dt):
        car = self.car
        target = ground(self.target)

        car_vel = norm(car.vel)
        time_left = distance(car, target) / max(car_vel + 500, 1400)
        vf = dot(car.forward(), car.vel)

        if self._driving and car.on_ground:
            self.action.target_pos = target
            self._time_on_ground += dt
            
            if self._time_on_ground > 0.2 and car.pos[2] < 200 and angle_to(car, target, vf < 0) < 0.1:

                if vf > 0:
                    if car_vel > 1000 and (not self.waste_boost or car.boost < 10):
                        if time_left > self.dodge_duration:
                            self.action = AirDodge(car, 0.05, target)
                            self._driving = False

                        elif time_left > self.wavedash_duration:
                            self.action = Wavedash(car, target)
                            self._driving = False

                elif time_left > self.halflip_duration and car_vel > 800:
                    self.action = HalfFlip(car, self.waste_boost and time_left > 3)
                    self._driving = False
                    

        self.action.step(dt)
        self.controls = self.action.controls

        if self._driving and not car.on_ground:
            self.controls.boost = False

        if self.action.finished and not self._driving:
            self._driving = True
            self._time_on_ground = 0
            self.action = self.drive
            self.drive.backwards = False

        if distance(car, target) < self.finish_distance:
            self.finished = True

        if not self.waste_boost:
            self.controls.boost = 0

    def render(self, draw: DrawingTool):
        if self._driving:
            self.action.render(draw)
        draw.color(draw.orange)
        draw.square(self.target, clamp(distance(self.car, self.target) / 10, 100, 1000))