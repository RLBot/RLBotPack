import math

from RLUtilities.GameInfo import GameInfo
from RLUtilities.LinearAlgebra import vec3, normalize, vec2, dot, norm
from RLUtilities.Maneuvers import Drive, AerialTurn, AirDodge
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.game_state_util import Vector3, GameState, BallState, Physics, CarState, Rotator
from rlbot.utils.structures.game_data_struct import GameTickPacket

from catching import Catching
from defending import defending
from dribble import Dribbling
from kickOff import initKickOff, kickOff
from shooting import shooting
from util import distance_2d, get_bounce, line_backline_intersect, sign


class hypebot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.name = name
        self.team = team
        self.index = index
        self.defending = False
        self.info = None
        self.bounces = []
        self.drive = None
        self.catching = None
        self.dodge = None
        self.recovery = None
        self.dribble = None
        self.controls = SimpleControllerState()
        self.kickoff = False
        self.inFrontOfBall = False
        self.kickoffStart = None
        self.step = "Catching"
        self.time = 0
        self.FPS = 1 / 120
        self.p_s = 0.
        self.kickoffTime = 0

    def initialize_agent(self):
        self.info = GameInfo(self.index, self.team, self.get_field_info())

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        if packet.game_info.seconds_elapsed - self.time > 0:
            self.FPS = packet.game_info.seconds_elapsed - self.time
        self.time = packet.game_info.seconds_elapsed
        self.info.read_packet(packet)
        self.predict()
        self.set_mechanics()
        prev_kickoff = self.kickoff
        self.kickoff = packet.game_info.is_kickoff_pause
        self.defending = self.should_defending()
        if self.kickoff and not prev_kickoff:
            initKickOff(self)
        if self.kickoff or self.step == "Dodge2":
            kickOff(self)
        else:
            self.get_controls()
        self.render_string(str(self.step))
        if not packet.game_info.is_round_active:
            self.controls.steer = 0
        return self.controls

    def predict(self):
        self.bounces = []
        ball_prediction = self.get_ball_prediction_struct()
        for i in range(ball_prediction.num_slices):
            location = vec3(ball_prediction.slices[i].physics.location.x,
                            ball_prediction.slices[i].physics.location.y,
                            ball_prediction.slices[i].physics.location.z)
            prev_ang_vel = ball_prediction.slices[i - 1].physics.angular_velocity
            prev_normalized_ang_vel = normalize(vec3(prev_ang_vel.x, prev_ang_vel.y, prev_ang_vel.z))
            current_ang_vel = ball_prediction.slices[i].physics.angular_velocity
            current_normalized_ang_vel = normalize(vec3(current_ang_vel.x, current_ang_vel.y, current_ang_vel.z))
            if prev_normalized_ang_vel != current_normalized_ang_vel and location[2] < 125:
                self.bounces.append((location, i * 1 / 60))

    def set_mechanics(self):
        if self.drive is None:
            self.drive = Drive(self.info.my_car, self.info.ball.pos, 1399)
        if self.catching is None:
            self.catching = Catching(self.info.my_car, self.info.ball.pos, 1399)
        if self.recovery is None:
            self.recovery = AerialTurn(self.info.my_car)
        if self.dodge is None:
            self.dodge = AirDodge(self.info.my_car, 0.25, self.info.ball.pos)
        if self.dribble is None:
            self.dribble = Dribbling(self.info.my_car, self.info.ball, self.info.their_goal)

    def get_controls(self):
        if self.step == "Steer" or self.step == "Dodge2":
            self.step = "Catching"
        if self.step == "Catching":
            target = get_bounce(self)
            if target is None:
                self.step = "Defending"
            else:
                self.catching.target_pos = target[0]
                self.catching.target_speed = (distance_2d(self.info.my_car.pos, target[0]) + 50) / target[1]
                self.catching.step(self.FPS)
                self.controls = self.catching.controls
                ball = self.info.ball
                car = self.info.my_car
                if distance_2d(ball.pos, car.pos) < 150 and 65 < abs(ball.pos[2] - car.pos[2]) < 127:
                    self.step = "Dribbling"
                    self.dribble = Dribbling(self.info.my_car, self.info.ball, self.info.their_goal)
                if self.defending:
                    self.step = "Defending"
                if not self.info.my_car.on_ground:
                    self.step = "Recovery"
                ball = self.info.ball
                if abs(ball.vel[2]) < 100 and sign(self.team) * ball.vel[1] < 0 and sign(self.team) * ball.pos[1] < 0:
                    self.step = "Shooting"
        elif self.step == "Dribbling":
            self.dribble.step(self.FPS)
            self.controls = self.dribble.controls
            ball = self.info.ball
            car = self.info.my_car
            bot_to_opponent = self.info.opponents[0].pos - self.info.my_car.pos
            local_bot_to_target = dot(bot_to_opponent, self.info.my_car.theta)
            angle_front_to_target = math.atan2(local_bot_to_target[1], local_bot_to_target[0])
            opponent_is_near = norm(vec2(bot_to_opponent)) < 2000
            opponent_is_in_the_way = math.radians(-10) < angle_front_to_target < math.radians(10)
            if not (distance_2d(ball.pos, car.pos) < 150 and 65 < abs(ball.pos[2] - car.pos[2]) < 127):
                self.step = "Catching"
            if self.defending:
                self.step = "Defending"
            if opponent_is_near and opponent_is_in_the_way:
                self.step = "Dodge"
                self.dodge = AirDodge(self.info.my_car, 0.25, self.info.their_goal.center)
            if not self.info.my_car.on_ground:
                self.step = "Recovery"
        elif self.step == "Defending":
            defending(self)
        elif self.step == "Dodge":
            self.dodge.step(self.FPS)
            self.controls = self.dodge.controls
            self.controls.boost = 0
            if self.dodge.finished and self.info.my_car.on_ground:
                self.step = "Catching"
        elif self.step == "Recovery":
            self.recovery.step(self.FPS)
            self.controls = self.recovery.controls
            if self.info.my_car.on_ground:
                self.step = "Catching"
        elif self.step == "Shooting":
            shooting(self)

    def render_string(self, string):
        self.renderer.begin_rendering('The State')
        if self.step == "Dodge1":
            self.renderer.draw_line_3d(self.info.my_car.pos, self.dodge.target, self.renderer.black())
        self.renderer.draw_line_3d(self.info.my_car.pos, self.bounces[0][0], self.renderer.blue())
        self.renderer.draw_string_2d(20, 20, 3, 3, string + " " + str(abs(self.info.ball.vel[2])) + " " + str(
            sign(self.team) * self.info.ball.vel[1]), self.renderer.red())
        self.renderer.end_rendering()

    def should_defending(self):
        ball = self.info.ball
        car = self.info.my_car
        our_goal = self.info.my_goal.center
        car_to_ball = ball.pos - car.pos
        in_front_of_ball = distance_2d(ball.pos, our_goal) < distance_2d(car.pos, our_goal)
        backline_intersect = line_backline_intersect(self.info.my_goal.center[1], vec2(car.pos), vec2(car_to_ball))
        return in_front_of_ball and abs(backline_intersect) < 2000
