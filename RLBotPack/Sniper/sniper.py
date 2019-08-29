import math

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.game_state_util import *
from rlbot.utils.structures.game_data_struct import GameTickPacket

import rendering
from rldata import GameInfo
from vec import Vec3, norm, normalize

NORMAL_SPEED = 2100
SUPER_SPEED = 3500
AIM_DURATION = 2.0
AIM_DURATION_AFTER_KICKOFF = 1.0
AIM_DURATION_AFTER_KICKOFF_INDEX_EXTRA = 1.0
GOAL_AIM_BIAS_AMOUNT = 50


class SniperBot(BaseAgent):
    AIMING = 0
    FLYING = 1
    KICKOFF = 2

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.info = GameInfo(index, team)
        self.controls = SimpleControllerState()
        self.direction = Vec3(0, 0, 1)
        self.state = self.KICKOFF
        self.next_flight_start_time = 0
        self.last_pos = Vec3(0, 0, 1)
        self.last_elapsed_seconds = 0
        self.last_clock = 0
        self.kickoff_timer_edge = False  # Set to True first time is_kickoff_pause is True and self.state == KICKOFF
        self.ball_moved = False  # True if moved since last kickoff start was detected
        self.next_is_super = False
        self.doing_super = False
        self.expected_hit_pos = Vec3(0, 1, 0)
        self.expected_hit_time = 0
        self.standby_initiated = False

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        self.info.read_packet(packet)
        if not packet.game_info.is_round_active:
            return SimpleControllerState()

        # Reset buttons
        self.controls.boost = False
        self.controls.roll = 0

        self.renderer.begin_rendering()

        if not self.info.aim_poss_determined:
            self.info.determine_aim_poss()

        ball_pos = self.info.ball.pos

        if ball_pos.x != 0 or ball_pos.y != 0:
            self.ball_moved = True

        if ball_pos.x == 0 and ball_pos.y == 0 and self.info.my_car.boost == 34 and not self.state == self.KICKOFF and self.ball_moved:
            # Ball is placed at the center - assume kickoff
            self.state = self.KICKOFF
            self.ball_moved = False

        if self.state == self.KICKOFF:
            self.do_kickoff_state()

        elif self.state == self.AIMING:
            self.do_aiming_state()

        elif self.state == self.FLYING:
            self.do_fly_state()

        # Extra rendering
        self.render_stuff()
        self.renderer.end_rendering()

        return self.controls

    def predict_hit_pos(self, from_pos):
        speed = SUPER_SPEED if self.next_is_super else NORMAL_SPEED
        ball_prediction = self.get_ball_prediction_struct()

        if ball_prediction is not None:
            TIME_PER_SLICES = 1/60.0
            SLICES = 360

            # Iterate to find the first location which can be hit
            for i in range(0, 360):
                time = i * TIME_PER_SLICES
                rlpos = ball_prediction.slices[i].physics.location
                pos = Vec3(rlpos.x, rlpos.y, rlpos.z)
                dist = norm(from_pos - pos)
                travel_time = dist / speed
                if time >= travel_time:
                    # Add small bias for aiming
                    tsign = -1 if self.team == 0 else 1
                    enemy_goal = Vec3(0, tsign * -5030, 300)
                    bias_direction = normalize(pos - enemy_goal)
                    pos = pos + bias_direction * GOAL_AIM_BIAS_AMOUNT
                    return pos, travel_time

            # Use last
            rlpos = ball_prediction.slices[SLICES - 1].physics.location
            return Vec3(rlpos.x, rlpos.y, rlpos.z), 6

        return Vec3(0, 0, 0), 5

    def render_stuff(self):
        if self.state == self.AIMING or self.state == self.FLYING:
            time_till_flight = max(0, self.next_flight_start_time - self.info.time)
            radius = 50 + 400 * time_till_flight
            rendering.draw_circle(self, self.expected_hit_pos, self.direction, radius, 20 + int(radius / (math.tau * 5)), self.renderer.team_color)
            pos = self.expected_hit_pos
            if self.state == self.FLYING:
                s = 70
                x = Vec3(s, 0, 0)
                y = Vec3(0, s, 0)
                z = Vec3(0, 0, s)
                self.renderer.draw_line_3d(pos - x, pos + x, self.renderer.team_color())
                self.renderer.draw_line_3d(pos - y, pos + y, self.renderer.team_color())
                self.renderer.draw_line_3d(pos - z, pos + z, self.renderer.team_color())
            else:
                length = self.direction * (70 + time_till_flight * 100)
                self.renderer.draw_line_3d(pos - length, pos + length, self.renderer.team_color())

    def do_kickoff_state(self):
        if self.info.is_kickoff:
            self.kickoff_timer_edge = True

        ball_pos = self.info.ball.pos

        if ball_pos.x != 0 or ball_pos.y != 0\
                or self.info.clock_dt != 0\
                or (self.kickoff_timer_edge and not self.info.is_kickoff
        ):
            self.next_flight_start_time = self.info.time + AIM_DURATION_AFTER_KICKOFF + self.info.my_car.sniper_index * AIM_DURATION_AFTER_KICKOFF_INDEX_EXTRA
            self.kickoff_timer_edge = False
            self.state = self.AIMING
            self.last_pos = self.info.my_car.aim_pos

    def do_aiming_state(self):
        self.expected_hit_pos, travel_time = self.predict_hit_pos(self.info.my_car.aim_pos)
        self.expected_hit_time = self.info.time + travel_time
        self.direction = d = normalize(self.expected_hit_pos - self.info.my_car.aim_pos)

        rotation = Rotator(math.asin(d.z), math.atan2(d.y, d.x), 0)
        car_state = CarState(Physics(location=to_fb(self.info.my_car.aim_pos),
                                     velocity=Vector3(0, 0, 0),
                                     rotation=rotation,
                                     angular_velocity=Vector3(0, 0, 0)))
        game_state = GameState(cars={self.index: car_state})
        self.set_game_state(game_state)

        if self.next_flight_start_time < self.info.time:
            self.state = self.FLYING
            if self.next_is_super:
                self.doing_super = True
                self.next_is_super = False
            else:
                self.doing_super = False

    def do_fly_state(self):
        speed = SUPER_SPEED if self.doing_super else NORMAL_SPEED
        vel = self.direction * speed
        new_pos = self.last_pos + vel * self.info.dt

        car_state = CarState(Physics(location=to_fb(new_pos), velocity=to_fb(vel)))
        game_state = GameState(cars={self.index: car_state})
        self.set_game_state(game_state)

        self.last_pos = new_pos
        self.controls.boost = self.doing_super
        self.controls.roll = self.doing_super

        # Crash?
        if abs(new_pos.x) > 4080 or abs(new_pos.y) > 5080 or new_pos.z < 0 or new_pos.z > 2020:
            self.state = self.AIMING
            self.next_flight_start_time = self.info.time + AIM_DURATION
            self.last_pos = self.info.my_car.aim_pos
            self.next_is_super = self.info.my_car.boost >= 100


def to_fb(vec):
    return Vector3(vec[0], vec[1], vec[2])
