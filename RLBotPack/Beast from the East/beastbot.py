from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

import moves
from behaviour import *
from info import EGameInfo
from moves import DriveController, AimCone, ShotController
from plans import choose_kickoff_plan
from render import FakeRenderer, draw_ball_path
from rlmath import *
from utsystem import UtilitySystem

RENDER = False


class Beast(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.do_rendering = RENDER
        self.controls = SimpleControllerState()
        self.info = None
        self.choice = None
        self.plan = None
        self.doing_kickoff = False

        self.ut = None
        self.drive = DriveController()
        self.shoot = ShotController()

    def initialize_agent(self):
        self.info = EGameInfo(self.index, self.team, )
        self.ut = UtilitySystem([DefaultBehaviour(), ShootAtGoal(), ClearBall(self), SaveGoal(self), Carry()])

        if not RENDER:
            self.renderer = FakeRenderer()

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:

        # Read packet
        if not self.info.field_info_loaded:
            self.info.read_field_info(self.get_field_info())
            if not self.info.field_info_loaded:
                return SimpleControllerState()
        self.info.read_packet(packet)

        self.renderer.begin_rendering()

        # Check if match is over
        if packet.game_info.is_match_ended:
            return moves.celebrate(self)  # Assuming we win!

        # Check kickoff
        if self.info.is_kickoff and not self.doing_kickoff:
            self.plan = choose_kickoff_plan(self)
            self.doing_kickoff = True
            self.print("Hello world!")

        # Execute logic
        if self.plan is None or self.plan.finished:
            # There is no plan, use utility system to find a choice
            self.plan = None
            self.doing_kickoff = False
            self.choice = self.ut.evaluate(self)
            self.choice.execute(self)
            # The choice has started a plan, reset utility system and execute plan instead
            if self.plan is not None:
                self.ut.reset()
                self.choice = None
                self.plan.execute(self)
        else:
            # We have a plan
            self.plan.execute(self)

        # Rendering
        if self.do_rendering:
            draw_ball_path(self, 4, 5)
            doing = self.plan or self.choice
            if doing is not None:
                self.renderer.draw_string_3d(self.info.my_car.pos, 1, 1, doing.__class__.__name__, self.random_color(doing.__class__))

        # Save for next frame
        self.info.my_car.last_input.roll = self.controls.roll
        self.info.my_car.last_input.pitch = self.controls.pitch
        self.info.my_car.last_input.yaw = self.controls.yaw
        self.info.my_car.last_input.boost = self.controls.boost

        self.renderer.end_rendering()
        return fix_controls(self.controls)

    def print(self, s):
        team_name = "[BLUE]" if self.team == 0 else "[ORANGE]"
        print("Beast", self.index, team_name, ":", s)

    def random_color(self, anything):
        color_functions = {
            0: self.renderer.red,
            1: self.renderer.green,
            2: self.renderer.blue,
            3: self.renderer.lime,
            4: self.renderer.yellow,
            5: self.renderer.orange,
            6: self.renderer.cyan,
            7: self.renderer.pink,
            8: self.renderer.purple,
            9: self.renderer.teal,
        }
        return color_functions.get(hash(anything) % 10)()


def fix_controls(controls):
    return SimpleControllerState(
        steer=controls.steer,
        throttle=controls.throttle,
        pitch=controls.pitch,
        yaw=controls.yaw,
        roll=controls.roll,
        jump=controls.jump,
        boost=controls.boost,
        handbrake=controls.handbrake,
        use_item=False
    )


class DefaultBehaviour:
    def __init__(self):
        pass

    def utility(self, bot):
        return 0.1

    def execute(self, bot):

        car = bot.info.my_car
        ball = bot.info.ball

        car_to_ball = ball.pos - car.pos
        ball_to_enemy_goal = bot.info.enemy_goal - ball.pos
        own_goal_to_ball = ball.pos - bot.info.own_goal
        dist = norm(car_to_ball)

        offence = ball.pos[Y] * bot.info.team_sign < 0
        dot_enemy = dot(car_to_ball, ball_to_enemy_goal)
        dot_own = dot(car_to_ball, own_goal_to_ball)
        right_side_of_ball = dot_enemy > 0 if offence else dot_own > 0

        if right_side_of_ball:
            # Aim cone
            dir_to_post_1 = (bot.info.enemy_goal + vec3(3800, 0, 0)) - bot.info.ball.pos
            dir_to_post_2 = (bot.info.enemy_goal + vec3(-3800, 0, 0)) - bot.info.ball.pos
            cone = AimCone(dir_to_post_1, dir_to_post_2)
            cone.get_goto_point(bot, car.pos, bot.info.ball.pos)
            if bot.do_rendering:
                cone.draw(bot, bot.info.ball.pos)

            # Chase ball
            bot.controls = bot.drive.go_towards_point(bot, xy(ball.pos), 2000, True, True, can_dodge=dist > 2200)
        else:
            # Go home
            bot.controls = bot.drive.go_towards_point(bot, bot.info.own_goal_field, 2000, True, True)
