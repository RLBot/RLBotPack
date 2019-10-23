from maneuvers.kit import *

from maneuvers.driving.travel import Travel
from maneuvers.driving.stop import Stop
from maneuvers.driving.drive import Drive

class ShadowDefense(Maneuver):

    def __init__(self, car: Car, info: GameInfo, face_target: vec3, distance_from_target: float):
        super().__init__(car)

        self.info = info
        self.face_target = face_target

        dist = min(distance_from_target, ground_distance(face_target, self.info.my_goal.center) - 50)
        target_pos = ground(face_target) + ground_direction(face_target, self.info.my_goal.center) * dist

        near_goal = ground_distance(car, info.my_goal.center) < 3000
        side_shift = 400 if near_goal else 2000
        points = [target_pos + vec3(side_shift, 0, 0), target_pos - vec3(side_shift, 0, 0)]
        target_pos = nearest_point(face_target, points) if near_goal else furthest_point(face_target, points)

        self.target = Arena.clamp(target_pos, 500)

        self.travel = Travel(car, self.target)
        self.travel.finish_distance = 800 if near_goal else 1500
        self.drive = Drive(car)

        self.start_time = car.time
        self.wait = Stop(car)

    def step(self, dt):
        ball = self.info.ball

        # if (
        #     distance(self.car, ball) < 1000
        #     and align(self.car.position, ball, self.info.my_goal.center) > 0.2
        # ):
        #     shift = normalize(cross(direction(ball, self.car), vec3(0, 0, 1))) * 1000
        #     self.travel.target = nearest_point(self.car.position, [ball.position + shift, ball.position - shift])
        # else:
        #     self.travel.target = self.target

        self.travel.step(dt)
        self.controls = self.travel.controls

        if ground_distance(self.car, self.travel.target) < 3000:
            self.controls.boost = False

        if self.travel.finished:
            if angle_to(self.car, self.face_target) > 0.3:
                self.drive.target_pos = self.face_target
                self.drive.step(dt)
                self.drive.target_speed = 700
                self.drive.controls.handbrake = False
                self.controls = self.drive.controls
            else:
                self.wait.step(dt)
                self.controls = self.wait.controls
        self.finished = self.travel.driving and self.car.time > self.start_time + 0.5

    def render(self, draw: DrawingTool):
        self.travel.render(draw)