from maneuvers.driving.travel import Travel
from maneuvers.driving.stop import Stop
from maneuvers.driving.drive import Drive
from maneuvers.maneuver import Maneuver
from rlutilities.linear_algebra import vec3
from rlutilities.simulation import Car
from tools.arena import Arena
from tools.drawing import DrawingTool
from tools.game_info import GameInfo
from tools.vector_math import nearest_point, farthest_point, ground_distance, ground_direction, ground, angle_to,\
    distance, angle_between


class GeneralDefense(Maneuver):
    """
    First, attempt to rotate on the far side, and when far away enough from the target (usually the ball),
    turn around to face it. If already far enough and facing the target, just stop and wait.
    Also try to pickup boost pads along the way.
    This state expires after a short amount of time, so we can look if there's something better to do. If not,
    it can be simply instantiated again.
    """

    DURATION = 0.5

    BOOST_LOOK_RADIUS = 1200
    BOOST_LOOK_ANGLE = 0.5

    def __init__(self, car: Car, info: GameInfo, face_target: vec3, distance_from_target: float):
        super().__init__(car)

        self.info = info
        self.face_target = face_target

        dist = min(distance_from_target, ground_distance(face_target, self.info.my_goal.center) - 50)
        target_pos = ground(face_target) + ground_direction(face_target, self.info.my_goal.center) * dist

        near_goal = ground_distance(car, info.my_goal.center) < 3000
        side_shift = 400 if near_goal else 2500
        points = [target_pos + vec3(side_shift, 0, 0), target_pos - vec3(side_shift, 0, 0)]
        target_pos = nearest_point(face_target, points) if near_goal else farthest_point(face_target, points)
        target_pos = Arena.clamp(target_pos, 500)

        self.travel = Travel(car, target_pos)
        self.travel.finish_distance = 800 if near_goal else 1500
        self.drive = Drive(car)
        self.stop = Stop(car)

        self.start_time = car.time

        self.pad = None

    def interruptible(self) -> bool:
        return self.travel.interruptible()

    def step(self, dt):
        # update finished state even if we are not using the controls
        self.travel.step(dt)

        if self.travel.finished:
            # turn around to face the target direction
            if angle_to(self.car, self.face_target) > 0.3:
                self.drive.target_pos = self.face_target
                self.drive.target_speed = 1000
                self.drive.step(dt)
                self.controls = self.drive.controls
                self.controls.handbrake = False
            else:
                self.stop.step(dt)
                self.controls = self.stop.controls

        else:
            self.pad = None

            # collect boost pads on the way (greedy algorithm, assumes first found is best)
            if self.car.boost < 90 and self.travel.interruptible():
                to_target = ground_direction(self.car, self.travel.target)

                for pad in self.info.large_boost_pads + self.info.small_boost_pads:
                    to_pad = ground_direction(self.car, pad)

                    if (
                        pad.is_active and distance(self.car, pad) < self.BOOST_LOOK_RADIUS
                        and angle_between(to_target, to_pad) < self.BOOST_LOOK_ANGLE
                    ):
                        self.pad = pad
                        self.drive.target_pos = pad.position
                        self.drive.target_speed = 2200
                        self.drive.step(dt)
                        self.controls = self.drive.controls
                        break

            # go to the actual target
            if self.pad is None:
                self.controls = self.travel.controls

        # don't waste boost during downtime
        self.controls.boost = False

        self.finished = self.travel.driving and self.car.time > self.start_time + self.DURATION

    def render(self, draw: DrawingTool):
        self.travel.render(draw)

        # render target pad
        if self.pad:
            draw.color(draw.blue)
            draw.circle(self.pad.position, 50)

