from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
import numpy as np
from agent import Agent
from obs.stacking_obs import AdvancedStacker
from rlgym_compat import GameState


class RLGymExampleBot(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.obs_builder = AdvancedStacker()
        self.agent = Agent()
        self.tick_skip = 8

        self.game_state: GameState = None
        self.controls = None
        self.prev_action = None
        self.ticks = 0
        self.prev_time = 0
        print(f"{name} loaded and ready!")

    def initialize_agent(self):
        self.game_state = GameState(self.get_field_info())
        self.ticks = self.tick_skip
        self.prev_time = 0
        self.controls = SimpleControllerState()
        self.prev_action = np.zeros(8)

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        cur_time = packet.game_info.seconds_elapsed
        delta = cur_time - self.prev_time
        self.prev_time = cur_time

        self.ticks += delta // 0.008

        if self.ticks >= self.tick_skip:
            self.ticks = 0

            self.game_state.decode(packet)
            player = self.game_state.players[self.index]
            opponents = [p for p in self.game_state.players if p.team_num != self.team]
            closest_op = min(opponents, key=lambda p: np.linalg.norm(self.game_state.ball.position - p.car_data.position))

            self.game_state.players = [player, closest_op]

            obs = self.obs_builder.build_obs(player, self.game_state, self.prev_action)
            action, discrete = self.agent.act(obs)
            self.update_controls(action, discrete_action=discrete)

        return self.controls

    def update_controls(self, action, discrete_action=None):
        if discrete_action == None:
            self.prev_action[:] = action[:]
        else:
            self.prev_action = discrete_action

        self.controls.throttle = action[0]
        self.controls.steer = action[1]
        self.controls.pitch = action[2]
        self.controls.yaw = action[3]
        self.controls.roll = action[4]
        self.controls.jump = action[5] > 0
        self.controls.boost = action[6] > 0
        self.controls.handbrake = action[7] > 0
