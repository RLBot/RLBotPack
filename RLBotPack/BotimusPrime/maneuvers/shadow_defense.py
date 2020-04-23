from maneuvers.driving.travel import Travel
from maneuvers.driving.stop import Stop
from maneuvers.driving.drive import Drive
from maneuvers.maneuver import Maneuver
from rlutilities.linear_algebra import vec3
from rlutilities.simulation import Car
from utils.arena import Arena
from utils.drawing import DrawingTool
from utils.game_info import GameInfo
from utils.vector_math import nearest_point, farthest_point, ground_distance, ground_direction, ground, angle_to


class ShadowDefense(Maneuver):

    DURATION = 0.5

    def __init__(self, car: Car, info: GameInfo, face_target: vec3, distance_from_target: float):
        super().__init__(car)

        self.info = info
        self.face_target = face_target

        dist = min(distance_from_target, ground_distance(face_target, self.info.my_goal.center) - 50)
        target_pos = ground(face_target) + ground_direction(face_target, self.info.my_goal.center) * dist

        near_goal = ground_distance(car, info.my_goal.center) < 3000
        side_shift = 400 if near_goal else 2000
        points = [target_pos + vec3(side_shift, 0, 0), target_pos - vec3(side_shift, 0, 0)]
        target_pos = nearest_point(face_target, points) if near_goal else farthest_point(face_target, points)
        target_pos = Arena.clamp(target_pos, 500)

        self.travel = Travel(car, target_pos)
        self.travel.finish_distance = 800 if near_goal else 1500
        self.drive = Drive(car)
        self.drive.target_speed = 1000
        self.stop = Stop(car)

        self.start_time = car.time

    def interruptible(self) -> bool:
        return self.travel.interruptible()

    def step(self, dt):
        self.travel.step(dt)
        self.controls = self.travel.controls

        if ground_distance(self.car, self.travel.target) < 3000:
            self.controls.boost = False

        if self.travel.finished:
            if angle_to(self.car, self.face_target) > 0.3:
                self.drive.target_pos = self.face_target
                self.drive.step(dt)
                self.controls = self.drive.controls
                self.controls.handbrake = False
            else:
                self.stop.step(dt)
                self.controls = self.stop.controls

        self.controls.boost = False

        self.finished = self.travel.driving and self.car.time > self.start_time + self.DURATION

    def render(self, draw: DrawingTool):
        self.travel.render(draw)
