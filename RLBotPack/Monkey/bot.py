from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

import numpy as np
from agent import Agent
from obs.advanced_obs import AdvancedObs
from rlgym_compat import GameState

from vec import Vec3

KICKOFF_CONTROLS_BASIC = (
        1 * 4 * [SimpleControllerState(throttle=1, boost=True)]
)

KICKOFF_NUMPY1 = np.array([
    [scs.throttle, scs.steer, scs.pitch, scs.yaw, scs.roll, scs.jump, scs.boost, scs.handbrake]
    for scs in KICKOFF_CONTROLS_BASIC
])

KICKOFF_CONTROLS_BACK_RIGHT = (
    1 * 4 * [SimpleControllerState(throttle=1, boost=True, steer=-0.08)]
)

KICKOFF_NUMPY2 = np.array([
    [scs.throttle, scs.steer, scs.pitch, scs.yaw, scs.roll, scs.jump, scs.boost, scs.handbrake]
    for scs in KICKOFF_CONTROLS_BACK_RIGHT
])

KICKOFF_CONTROLS_BACK_LEFT = (
    1 * 4 * [SimpleControllerState(throttle=1, boost=True, steer=0.08)]
)

KICKOFF_NUMPY3 = np.array([
    [scs.throttle, scs.steer, scs.pitch, scs.yaw, scs.roll, scs.jump, scs.boost, scs.handbrake]
    for scs in KICKOFF_CONTROLS_BACK_LEFT
])

FRONT_FLIP_CONTROLS = (
    3 * 1 * [SimpleControllerState(throttle=1, jump=True,  boost=True, pitch=-1, yaw=0, roll=0)]
    + 5 * 25 * [SimpleControllerState(throttle=1, steer=0, pitch=-1, yaw=0, jump=True, boost=False, roll=0)]
)

FRONT_FLIP = np.array([
    [scs.throttle, scs.steer, scs.pitch, scs.yaw, scs.roll, scs.jump, scs.boost, scs.handbrake]
    for scs in FRONT_FLIP_CONTROLS
])

class RLGymExampleBot(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)

        # FIXME Hey, botmaker. Start here:
        # Swap the obs builder if you are using a different one, RLGym's AdvancedObs is also available
        self.obs_builder = AdvancedObs()
        # Your neural network logic goes inside the Agent class, go take a look inside src/agent.py
        self.agent = Agent()
        # Adjust the tickskip if your agent was trained with a different value
        self.tick_skip = 8

        self.game_state: GameState = None
        self.controls = None
        self.action = None
        self.update_action = True
        self.ticks = 0
        self.prev_time = 0
        self.expected_teammates = 0
        self.expected_opponents = 1
        print(f'{self.name} Ready - Index:', index)


    def initialize_agent(self):
        # Initialize the rlgym GameState object now that the game is active and the info is available
        self.game_state = GameState(self.get_field_info())
        self.ticks = self.tick_skip  # So we take an action the first tick
        self.prev_time = 0
        self.controls = SimpleControllerState()
        self.action = np.zeros(8)
        self.update_action = True

    def reshape_state(self, gamestate, player, opponents, allies):
        """ TODO - replace me with code that handles different sized teams
        - converting to 1v1 currently """
        closest_op = min(opponents, key=lambda p: np.linalg.norm(self.game_state.ball.position - p.car_data.position))
        self.game_state.players = [player, closest_op]

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        cur_time = packet.game_info.seconds_elapsed
        delta = cur_time - self.prev_time
        self.prev_time = cur_time

        ticks_elapsed = delta * 120
        self.ticks += ticks_elapsed
        self.game_state.decode(packet, ticks_elapsed)

        if self.update_action:
            self.update_action = False
            player = self.game_state.players[self.index]
            opponents = [p for p in self.game_state.players if p.team_num != self.team]
            allies = [p for p in self.game_state.players if p.team_num == self.team and p.car_id != self.index]

            if len(opponents) != self.expected_opponents or len(allies) != self.expected_teammates:
                self.reshape_state(self.game_state, player, opponents, allies)

            obs = self.obs_builder.build_obs(player, self.game_state, self.action)
            self.action = self.agent.act(obs)

        if self.ticks >= self.tick_skip:
            self.ticks = 0
            self.update_controls(self.action)
            self.update_action = True

        self.maybe_do_kickoff(packet, ticks_elapsed)
        return self.controls

    def maybe_do_kickoff(self, packet, ticks_elapsed):
        y = packet.game_ball.physics.location.y
        x = packet.game_ball.physics.location.x
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        ball_location = Vec3(packet.game_ball.physics.location)

        y_car = packet.game_cars[0].physics.location.y
        x_car = packet.game_cars[0].physics.location.x

        if packet.game_info.is_kickoff_pause:
            if x == 0 and y == 0 and car_location.dist(ball_location) > 2000:
                if car_location.dist(ball_location) > 3350:
                    if x_car > 0:
                        self.kickoff_index = 3
                    elif x_car < 0:
                        self.kickoff_index = 2
                    elif x_car == 0:
                        self.kickoff_index = -1
                else:
                    self.kickoff_index = 1
            else:
                if car_location.dist(ball_location) < 600:
                    self.kickoff_index = 4
                else:
                    self.kickoff_index = -1
               
            if 1 == self.kickoff_index and packet.game_ball.physics.location.y == 0:
                action = KICKOFF_NUMPY1[self.kickoff_index]
                self.action = action
                self.update_controls(self.action)
            elif 2 == self.kickoff_index and packet.game_ball.physics.location.y == 0:
                action = KICKOFF_NUMPY2[self.kickoff_index]
                self.action = action
                self.update_controls(self.action)
            elif 3 == self.kickoff_index and packet.game_ball.physics.location.y == 0:
                action = KICKOFF_NUMPY3[self.kickoff_index]
                self.action = action
                self.update_controls(self.action)
            elif 4 == self.kickoff_index and packet.game_ball.physics.location.y == 0:
                action = FRONT_FLIP[self.kickoff_index]
                self.action = action
                self.update_controls(self.action)
        else:
            self.kickoff_index = -1

    def update_controls(self, action):
        self.controls.throttle = action[0]
        self.controls.steer = action[1]
        self.controls.pitch = action[2]
        self.controls.yaw = action[3]
        self.controls.roll = action[4]
        self.controls.jump = action[5] > 0
        self.controls.boost = action[6] > 0
        self.controls.handbrake = action[7] > 0