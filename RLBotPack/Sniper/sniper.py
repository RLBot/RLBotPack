import math

from RLUtilities.GameInfo import GameInfo
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.game_state_util import *
from rlbot.utils.structures.game_data_struct import GameTickPacket

from RLUtilities.LinearAlgebra import *

NORMAL_SPEED = 2100
SUPER_SPEED = 3500
AIM_DURATION = 2.0
AIM_DURATION_AFTER_KICKOFF = 1.0
GOAL_AIM_BIAS_AMOUNT = 60

class SniperBot(BaseAgent):
    AIMING = 0
    FLYING = 1
    KICKOFF = 2

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.controls = SimpleControllerState()
        self.info = GameInfo(self.index, self.team)
        self.t_index = 0
        self.standby_position = vec3(0, 0, 300)
        self.direction = vec3(0, 0, 1)
        self.state = self.KICKOFF
        self.shoot_time = 0
        self.last_pos = self.standby_position
        self.last_elapsed_seconds = 0
        self.kickoff_timer_edge = False
        self.ball_moved = False
        self.next_is_super = False
        self.doing_super = False
        self.hit_pos = vec3(0, 0, 0)
        self.standby_initiated = False

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        dt = packet.game_info.seconds_elapsed - self.last_elapsed_seconds
        self.last_elapsed_seconds = packet.game_info.seconds_elapsed
        self.info.read_packet(packet)

        ball_pos = self.info.ball.pos

        if not self.standby_initiated:
            self.initiate_standby(packet)

        if ball_pos[0] != 0 or ball_pos[1] != 0:
            self.ball_moved = True

        if ball_pos[0] == 0 and ball_pos[1] == 0 and self.info.my_car.boost == 34 and not self.state == self.KICKOFF and self.ball_moved:
            # Ball is placed at the center - assume kickoff
            self.state = self.KICKOFF
            self.ball_moved = False

        if self.state == self.KICKOFF:
            if packet.game_info.is_kickoff_pause:
                self.kickoff_timer_edge = True
            if ball_pos[0] != 0 or ball_pos[1] != 0 or (self.kickoff_timer_edge and not packet.game_info.is_kickoff_pause):
                self.shoot_time = self.info.time + AIM_DURATION_AFTER_KICKOFF + self.t_index
                self.controls.boost = False
                self.controls.roll = 0
                self.kickoff_timer_edge = False
                self.state = self.AIMING
                self.last_pos = self.standby_position

        elif self.state == self.AIMING:

            self.controls.boost = False
            self.controls.roll = 0
            self.hit_pos = self.predict_hit_pos()
            self.direction = d = normalize(self.hit_pos - self.standby_position)

            rotation = Rotator(math.asin(d[2]), math.atan2(d[1], d[0]), 0)
            car_state = CarState(Physics(location=to_fb(self.standby_position),
                                         velocity=Vector3(0, 0, 0),
                                         rotation=rotation,
                                         angular_velocity=Vector3(0, 0, 0)))
            game_state = GameState(cars={self.index: car_state})
            self.set_game_state(game_state)

            self.render_aiming(self.hit_pos)

            if self.shoot_time < self.info.time:
                self.state = self.FLYING
                if self.next_is_super:
                    self.doing_super = True
                    self.next_is_super = False
                else:
                    self.doing_super = False

        elif self.state == self.FLYING:

            speed = SUPER_SPEED if self.doing_super else NORMAL_SPEED
            vel = self.direction * speed
            n_pos = self.last_pos + vel * dt

            car_state = CarState(Physics(location=to_fb(n_pos), velocity=to_fb(vel)))
            game_state = GameState(cars={self.index: car_state})
            self.set_game_state(game_state)

            self.last_pos = n_pos
            self.controls.boost = self.doing_super
            self.controls.roll = self.doing_super

            if abs(n_pos[0]) > 4080 or abs(n_pos[1]) > 5080 or n_pos[2] < 0 or n_pos[2] > 2020:
                # Crash
                self.state = self.AIMING
                self.shoot_time = self.info.time + AIM_DURATION
                self.last_pos = self.standby_position
                self.next_is_super = self.info.my_car.boost >= 99

        self.render_aiming(self.hit_pos)

        return self.controls

    def predict_hit_pos(self):
        speed = SUPER_SPEED if self.next_is_super else NORMAL_SPEED
        ball_prediction = self.get_ball_prediction_struct()

        if ball_prediction is not None:
            TIME_PER_SLICES = 1/60.0
            SLICES = 360

            # Iterate to find the first location which can be hit
            for i in range(0, 360):
                time = i * TIME_PER_SLICES
                rlpos = ball_prediction.slices[i].physics.location
                pos = vec3(rlpos.x, rlpos.y, rlpos.z)
                dist = norm(self.standby_position - pos)
                travel_time = dist / speed
                if time + TIME_PER_SLICES > travel_time:
                    # Add small bias for aiming
                    tsign = -1 if self.team == 0 else 1
                    enemy_goal = vec3(0, tsign * -5030, 300)
                    bias_direction = normalize(pos - enemy_goal)
                    pos = pos + bias_direction * GOAL_AIM_BIAS_AMOUNT
                    return pos

            # Use last
            rlpos = ball_prediction.slices[SLICES - 1].physics.location
            return vec3(rlpos.x, rlpos.y, rlpos.z)

        return vec3(0, 0, 0)

    def render_aiming(self, pos):
        if self.state == self.AIMING or self.state == self.FLYING:
            self.renderer.begin_rendering()
            t = max(0, self.shoot_time - self.info.time)
            r = 50 + 400 * t
            self.draw_circle(pos, self.direction, r, 20 + int(r / (math.tau * 5)))
            if self.state != self.FLYING:
                l = self.direction * (70 + t * 100)
                self.renderer.draw_line_3d(pos - l, pos + l, self.renderer.team_color())
            else:
                s = 70
                x = vec3(s, 0, 0)
                y = vec3(0, s, 0)
                z = vec3(0, 0, s)
                self.renderer.draw_line_3d(pos - x, pos + x, self.renderer.team_color())
                self.renderer.draw_line_3d(pos - y, pos + y, self.renderer.team_color())
                self.renderer.draw_line_3d(pos - z, pos + z, self.renderer.team_color())
            self.renderer.end_rendering()

    def draw_circle(self, center: vec3, normal: vec3, radius: float, pieces: int):
        # Construct the arm that will be rotated
        arm = normalize(cross(normal, center)) * radius
        angle = 2 * math.pi / pieces
        rotation_mat = axis_rotation(angle * normalize(normal))
        points = [center + arm]

        for i in range(pieces):
            arm = dot(rotation_mat, arm)
            points.append(center + arm)

        self.renderer.draw_polyline_3d(points, self.renderer.team_color())

    def initiate_standby(self, packet):
        self.standby_initiated = True
        snipers_on_team = 0
        for i in range(0, packet.num_cars):
            car = packet.game_cars[i]
            if car.team == self.team:
                if car.name == self.name:
                    self.t_index = snipers_on_team
                if car.name[:6] == "Sniper":
                    snipers_on_team += 1

        tsign = -1 if self.team == 0 else 1

        z = 300
        y = 5030
        spacing = 400

        if snipers_on_team == 1:
            self.standby_position = vec3(0, tsign * y, z)
        elif snipers_on_team == 2:
            self.standby_position = vec3(-400 + self.t_index * 800, tsign * y, z)
        else:
            # There are an even number of snipers on the team
            is_top_row = (self.t_index < snipers_on_team / 2)
            offset = spacing * (snipers_on_team - 2) / 4
            row_index = self.t_index if is_top_row else self.t_index - snipers_on_team / 2
            x = -offset + row_index * spacing
            self.standby_position = vec3(x, tsign * y, z + 150 * is_top_row)



def to_fb(vec: vec3):
    return Vector3(vec[0], vec[1], vec[2])
