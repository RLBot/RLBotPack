import numpy as np
import torch
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlgym_compat import GameState
from obs.advanced_obs import ExpandAdvancedObs
from action.actionparser import ImmortalAction

from agent import Agent


class RLGymExampleBot(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)

        # Swap the obs builder if you are using a different one, RLGym's AdvancedObs is also available
        self.obs_builder = ExpandAdvancedObs()
        # Swap the action parser if you are using a different one, RLGym's Discrete and Continuous are also available
        self.act_parser = ImmortalAction()
        # Your neural network logic goes inside the Agent class, go take a look inside src/agent.py
        self.agent = Agent()
        # Adjust the tickskip if your agent was trained with a different value
        self.tick_skip = 6

        self.game_state: GameState = None
        self.controls = None
        self.action = None
        self.update_action = True
        self.ticks = 0
        self.prev_time = 0
        print('Immortal - Index:', index)

    def initialize_agent(self):
        # Initialize the rlgym GameState object now that the game is active and the info is available
        self.game_state = GameState(self.get_field_info())
        self.ticks = self.tick_skip  # So we take an action the first tick
        self.prev_time = 0
        self.controls = SimpleControllerState()
        self.action = np.zeros(8)
        self.update_action = True

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        cur_time = packet.game_info.seconds_elapsed
        delta = cur_time - self.prev_time
        self.prev_time = cur_time

        ticks_elapsed = round(delta * 120)
        self.ticks += ticks_elapsed
        self.game_state.decode(packet, ticks_elapsed)

        if self.update_action:
            self.update_action = False

            # By default we treat every match as a 1v1 against a fixed opponent,
            # by doing this your bot can participate in 2v2 or 3v3 matches. Feel free to change this
            player = self.game_state.players[self.index]
            teammates = [p for p in self.game_state.players if p.team_num == self.team]
            opponents = [p for p in self.game_state.players if p.team_num != self.team]

            if len(opponents) == 0:
                # There's no opponent, we assume this model is 1v0
                self.game_state.players = [player]
            else:
                # Sort by distance to ball
                teammates.sort(key=lambda p: np.linalg.norm(self.game_state.ball.position - p.car_data.position))
                opponents.sort(key=lambda p: np.linalg.norm(self.game_state.ball.position - p.car_data.position))

                # Grab opponent in same "position" relative to it's teammates
                opponent = opponents[min(teammates.index(player), len(opponents) - 1)]

                self.game_state.players = [player, opponent]

            obs = self.obs_builder.build_obs(player, self.game_state, self.action)
            self.action = self.act_parser.parse_actions(self.agent.act(obs))  # Dim is (N, 8)

        if self.ticks >= self.tick_skip - 1:
            self.update_controls(self.action)

        if self.ticks >= self.tick_skip:
            self.ticks = 0
            self.update_action = True

        return self.controls

    def update_controls(self, action):
        self.controls.throttle = action[0]
        self.controls.steer = action[1]
        self.controls.pitch = action[2]
        self.controls.yaw = 0 if action[5] > 0 else action[3]
        self.controls.roll = action[4]
        self.controls.jump = action[5] > 0
        self.controls.boost = action[6] > 0
        self.controls.handbrake = action[7] > 0