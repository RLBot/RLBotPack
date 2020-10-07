from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from behaviour.carry import Carry
from behaviour.clear_ball import ClearBall
from behaviour.defend_goal import DefendGoal
from behaviour.follow_up import PrepareFollowUp
from behaviour.save_goal import SaveGoal
from behaviour.shoot_at_goal import ShootAtGoal
from controllers.drive import DriveController
from controllers.fly import FlyController
from controllers.other import celebrate
from controllers.shots import ShotController
from maneuvers.kickoff import choose_kickoff_maneuver
from strategy.analyzer import GameAnalyzer
from strategy.objective import Objective
from strategy.utility_system import UtilitySystem
from utility.info import GameInfo
from utility.vec import Vec3

RENDER = True


class Manticore(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.do_rendering = RENDER
        self.info = None
        self.ut = None
        self.analyzer = GameAnalyzer()
        self.choice = None
        self.maneuver = None
        self.doing_kickoff = False

        self.drive = DriveController()
        self.shoot = ShotController()
        self.fly = FlyController()

    def initialize_agent(self):
        self.info = GameInfo(self.index, self.team)
        self.ut = UtilitySystem([
            ShootAtGoal(),
            SaveGoal(self),
            ClearBall(self),
            Carry(),
            DefendGoal(),
            PrepareFollowUp()
        ])

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        # Read packet
        if not self.info.field_info_loaded:
            self.info.read_field_info(self.get_field_info())
            if not self.info.field_info_loaded:
                return SimpleControllerState()

        self.renderer.begin_rendering()

        self.info.read_packet(packet)
        self.analyzer.update(self)

        # Check if match is over
        if packet.game_info.is_match_ended:
            return celebrate(self)  # Assume we won!

        controller = self.use_brain()

        # Additional rendering
        if self.do_rendering:
            doing = self.maneuver or self.choice
            state_color = {
                Objective.GO_FOR_IT: self.renderer.lime(),
                Objective.FOLLOW_UP: self.renderer.yellow(),
                Objective.ROTATING: self.renderer.red(),
                Objective.UNKNOWN: self.renderer.team_color(alt_color=True)
            }[self.info.my_car.objective]
            if doing is not None:
                self.renderer.draw_string_2d(330, 700 + self.index * 20, 1, 1, f"{self.name}:", self.renderer.team_color(alt_color=True))
                self.renderer.draw_string_2d(500, 700 + self.index * 20, 1, 1, doing.__class__.__name__, state_color)
                self.renderer.draw_rect_3d(self.info.my_car.pos + Vec3(z=60), 16, 16, True, state_color)

        self.renderer.end_rendering()

        # Save some stuff for next tick
        self.feedback(controller)

        return controller

    def print(self, s):
        team_name = "[BLUE]" if self.team == 0 else "[ORANGE]"
        print("Manticore", self.index, team_name, ":", s)

    def feedback(self, controller):
        if controller is None:
            self.print(f"None controller from state: {self.info.my_car.objective} & {self.maneuver.__class__}")
        else:
            self.info.my_car.last_input.roll = controller.roll
            self.info.my_car.last_input.pitch = controller.pitch
            self.info.my_car.last_input.yaw = controller.yaw
            self.info.my_car.last_input.boost = controller.boost

    def use_brain(self) -> SimpleControllerState:
        # Check kickoff
        if self.info.is_kickoff and not self.doing_kickoff:
            self.maneuver = choose_kickoff_maneuver(self)
            self.doing_kickoff = True
            self.print("Kickoff - Hello world!")

        # Execute logic
        if self.maneuver is None or self.maneuver.done:
            # There is no maneuver (anymore)
            self.maneuver = None
            self.doing_kickoff = False

            self.choice = self.ut.get_best_state(self)
            ctrl = self.choice.run(self)

            # The state has started a maneuver. Execute maneuver instead
            if self.maneuver is not None:
                return self.maneuver.exec(self)

            return ctrl

        return self.maneuver.exec(self)
