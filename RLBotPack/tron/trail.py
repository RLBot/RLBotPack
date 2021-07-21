from dataclasses import dataclass

from rlbot.utils.game_state_util import GameState, BallState, Physics, CarState

from orientation import Orientation
from settings import IGNORE_BOT_COLLISION, IGNORE_HUMAN_COLLISION, IGNORE_BALL_COLLISION, MAX_TRAIL_LENGTH
from vec import Vec3


class Trail:
    def __init__(self, index, team):
        self.index = index
        self.team = team
        self.points = []

        self.duration = 13

        self.segment_size = 115

    def clear(self, renderer):
        self.points = []
        renderer.begin_rendering(f"trail-{self.index}-top")
        renderer.end_rendering()
        renderer.begin_rendering(f"trail-{self.index}-mid")
        renderer.end_rendering()
        renderer.begin_rendering(f"trail-{self.index}-bottom")
        renderer.end_rendering()

    def update(self, car, time):
        ori = Orientation(car.physics.rotation)
        pos = Vec3(car.physics.location) + Vec3(z=12) - 30 * ori.forward
        if len(self.points) == 0:
            # Initial point
            point = TrailPoint(pos, time)
            self.points.append(point)
        else:
            # Add points
            prev = self.points[-1]
            diff = pos - prev.pos
            if diff.longer_than(self.segment_size):
                point = TrailPoint(pos, time)
                self.points.append(point)

        # Remove points
        earliest = self.points[0]
        if earliest.time + self.duration < time:
            self.points = self.points[1:]
        self.points = self.points[-MAX_TRAIL_LENGTH:]

    def do_collisions(self, script, packet):
        ball_pos = Vec3(packet.game_ball.physics.location)
        for i in range(len(self.points) - 2):
            seg_start = self.points[i].pos
            seg_end = self.points[i + 1].pos
            seg = seg_end - seg_start

            # Ball
            if not IGNORE_BALL_COLLISION:
                ball_pos_from_seg_pov = ball_pos - seg_start
                t = (ball_pos_from_seg_pov.dot(seg) / seg.dot(seg))
                ball_proj_seg = seg * t
                seg_ball = (ball_pos_from_seg_pov - ball_proj_seg)
                if 0 <= t <= 1 and not seg_ball.longer_than(100):
                    # Collision
                    seg_ball_u = seg_ball.unit()
                    vel = Vec3(packet.game_ball.physics.velocity)
                    refl_vel = vel - 1.9 * vel.dot(seg_ball_u) * seg_ball_u
                    ball_pos_moved = seg_start + ball_proj_seg + seg_ball_u * 101
                    script.set_game_state(GameState(ball=BallState(physics=Physics(
                        location=ball_pos_moved.to_desired_vec(),
                        velocity=refl_vel.to_desired_vec())
                    )))
                    script.particle_burst(
                        packet.game_info.seconds_elapsed,
                        seg_start + ball_proj_seg + seg_ball_u * 10,
                        seg_ball_u,
                        int(1 + abs(vel.dot(seg_ball_u) / 300) ** 3),
                        self.team
                    )
                    hit_strength = abs(seg_ball_u.dot(vel))
                    script.sounds.ball_hit(hit_strength)

            # Cars
            for car_index in range(packet.num_cars):
                car = packet.game_cars[car_index]
                if car.is_demolished \
                        or (car.is_bot and IGNORE_BOT_COLLISION) \
                        or (not car.is_bot and IGNORE_HUMAN_COLLISION):
                    continue
                car_ori = Orientation(car.physics.rotation)
                car_pos = Vec3(car.physics.location)
                car_pos_from_seg_pov = car_pos - seg_start
                t = (car_pos_from_seg_pov.dot(seg) / seg.dot(seg))
                car_proj_seg = seg * t
                seg_car = (car_pos_from_seg_pov - car_proj_seg)
                # seg_car_local = relative_location(Vec3(), car_ori, seg_car)
                if 0 <= t <= 1 and not seg_car.longer_than(85):
                    # Collision
                    seg_car_u = seg_car.unit()
                    vel = Vec3(car.physics.velocity)
                    refl_vel = vel - 1.5 * vel.dot(seg_car_u) * seg_car_u
                    car_pos_moved = seg_start + car_proj_seg + seg_car_u * 86
                    script.set_game_state(GameState(cars={car_index: CarState(physics=Physics(
                        location=car_pos_moved.to_desired_vec(),
                        velocity=refl_vel.to_desired_vec())
                    )}))
                    script.particle_burst(
                        packet.game_info.seconds_elapsed,
                        seg_start + car_proj_seg + seg_car_u * 13,
                        seg_car_u,
                        int(1 + abs(vel.dot(seg_car_u) / 300) ** 3),
                        self.team
                    )
                    hit_strength = abs(seg_car_u.dot(vel))
                    script.sounds.car_hit(hit_strength)

    def render(self, renderer):
        if len(self.points) > 1:
            renderer.begin_rendering(f"trail-{self.index}-mid")
            points = list(map(lambda p: p.pos, self.points))
            renderer.draw_polyline_3d(points, renderer.white())
            renderer.end_rendering()

            renderer.begin_rendering(f"trail-{self.index}-top")
            blue = renderer.create_color(255, 0, 150, 255)
            orange = renderer.orange()
            points = list(map(lambda p: p.pos + Vec3(z=10), self.points))
            color = blue if self.team == 0 else orange
            renderer.draw_polyline_3d(points, color)
            renderer.end_rendering()

            renderer.begin_rendering(f"trail-{self.index}-bottom")
            blue = renderer.create_color(255, 0, 150, 255)
            orange = renderer.orange()
            points = list(map(lambda p: p.pos + Vec3(z=-10), self.points))
            color = blue if self.team == 0 else orange
            renderer.draw_polyline_3d(points, color)
            renderer.end_rendering()


@dataclass
class TrailPoint:
    pos: Vec3
    time: float