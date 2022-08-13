import numpy as np
import torch
from numpy import ndarray
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from helper import invert_player_data, invert_ball_data, invert_boost_data, Seer_Network, flip_timeout, get_action_encoding, impute_features


def encode_player(packet: GameTickPacket, index: int, has_flip: bool, demo_timer: float, inverted: bool) -> ndarray:
    array = np.array([
        packet.game_cars[index].physics.location.x,
        packet.game_cars[index].physics.location.y,
        packet.game_cars[index].physics.location.z,
        packet.game_cars[index].physics.rotation.pitch,
        packet.game_cars[index].physics.rotation.yaw,
        packet.game_cars[index].physics.rotation.roll,
        packet.game_cars[index].physics.velocity.x,
        packet.game_cars[index].physics.velocity.y,
        packet.game_cars[index].physics.velocity.z,
        packet.game_cars[index].physics.angular_velocity.x,
        packet.game_cars[index].physics.angular_velocity.y,
        packet.game_cars[index].physics.angular_velocity.z,
        demo_timer,
        packet.game_cars[index].boost,
        packet.game_cars[index].has_wheel_contact,
        has_flip,
    ], dtype=np.float32)

    if inverted:
        array = invert_player_data(array)

    return array


def encode_ball(packet: GameTickPacket, inverted: bool) -> ndarray:
    array = np.array([
        packet.game_ball.physics.location.x,
        packet.game_ball.physics.location.y,
        packet.game_ball.physics.location.z,

        packet.game_ball.physics.velocity.x,
        packet.game_ball.physics.velocity.y,
        packet.game_ball.physics.velocity.z,

        packet.game_ball.physics.angular_velocity.x,
        packet.game_ball.physics.angular_velocity.y,
        packet.game_ball.physics.angular_velocity.z
    ], dtype=np.float32)

    if inverted:
        array = invert_ball_data(array)

    return array


def encode_boost(packet: GameTickPacket, inverted: bool) -> ndarray:
    array = np.empty(34, dtype=np.float32)

    for i in range(34):
        array[i] = packet.game_boosts[i].timer

    if inverted:
        array = invert_boost_data(array)

    return array


class Seer(BaseAgent):

    def __init__(self, name, team, index):
        print("Seer Loading...")
        super().__init__(name, team, index)
        self.tick_skip = 8
        self.ticks = 8  # # So we take an action the first tick
        self.prev_time = 0

        if self.index == 0:
            self.inverted = False
            self.opponent_index = 1
        else:
            self.inverted = True
            self.opponent_index = 0

        self.device = 'cpu'
        self.filename = "./Seer/Seer.pt"

        self.model = Seer_Network()
        state_dict = torch.load(self.filename, map_location=torch.device(self.device))
        self.model.load_state_dict(state_dict)
        self.model.eval()

        self.controls = SimpleControllerState()
        self.agent_latest_wheel_contact: float = 0.0
        self.opponent_latest_wheel_contact: float = 0.0

        self.agent_demo_timer = 0.0
        self.opponent_demo_timer = 0.0
        self.last_packet_time_demo = 0.0

        self.prev_action = None

        self.state = None
        self.reset_states()
        print("Seer Ready!")

    def initialize_agent(self):
        pass

    def reset_states(self):
        self.state = (torch.zeros(1, 1, 512, device=self.device, requires_grad=False), torch.zeros(1, 1, 512, device=self.device, requires_grad=False))
        self.prev_action = np.array([1.0, 2.0, 2.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32)

    def get_flips(self, packet: GameTickPacket):

        if packet.game_cars[self.index].has_wheel_contact:
            self.agent_latest_wheel_contact = packet.game_info.seconds_elapsed

        if packet.game_cars[self.opponent_index].has_wheel_contact:
            self.opponent_latest_wheel_contact = packet.game_info.seconds_elapsed

        agent_flip_timeout = (packet.game_info.seconds_elapsed - self.agent_latest_wheel_contact) > flip_timeout and packet.game_cars[self.index].jumped
        opponent_flip_timeout = (packet.game_info.seconds_elapsed - self.opponent_latest_wheel_contact) > flip_timeout and packet.game_cars[self.opponent_index].jumped

        agent_flip = not packet.game_cars[self.index].double_jumped and not agent_flip_timeout
        opponent_flip = not packet.game_cars[self.opponent_index].double_jumped and not opponent_flip_timeout

        return agent_flip, opponent_flip

    def get_demo_timers(self, packet: GameTickPacket):

        delta = packet.game_info.seconds_elapsed - self.last_packet_time_demo

        self.last_packet_time_demo = packet.game_info.seconds_elapsed

        if packet.game_cars[self.index].is_demolished:
            self.agent_demo_timer += delta
        else:
            self.agent_demo_timer = 0.0

        if packet.game_cars[self.opponent_index].is_demolished:
            self.opponent_demo_timer += delta
        else:
            self.opponent_demo_timer = 0.0

        return self.agent_demo_timer, self.opponent_demo_timer

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:

        cur_time = packet.game_info.seconds_elapsed
        delta = cur_time - self.prev_time
        self.prev_time = cur_time

        ticks_elapsed = delta * 120
        self.ticks += ticks_elapsed

        if not packet.game_info.is_round_active:
            self.controls.throttle = 0.0
            self.controls.steer = 0.0
            self.controls.yaw = 0.0
            self.controls.pitch = 0.0
            self.controls.roll = 0.0
            self.controls.boost = False
            self.controls.handbrake = False
            self.controls.jump = False
            self.reset_states()
            return self.controls

        if self.ticks >= self.tick_skip:
            self.ticks = 0
            self.update_controls(packet)

        return self.controls

    def update_controls(self, packet: GameTickPacket):

        agent_flip, opponent_flip = self.get_flips(packet)
        agent_demo_timer, opponent_demo_timer = self.get_demo_timers(packet)
        input_array = self.packet_to_array(packet, self.index, self.opponent_index, agent_flip, opponent_flip, agent_demo_timer, opponent_demo_timer, self.inverted)

        with torch.no_grad():
            input_tensor = torch.tensor(input_array.reshape((1, -1)), dtype=torch.float32, device=self.device, requires_grad=False)
            episode_starts = torch.zeros(1, dtype=torch.float32, device=self.device, requires_grad=False)
            actions, values, log_prob, self.state = self.model(input_tensor, self.state, episode_starts, True)
            actions = actions.numpy()

        self.update_controller_from_action(actions)

    def packet_to_array(self, packet: GameTickPacket, agent_index: int, opponent_index: int, agent_has_flip: bool, opponent_has_flip: bool, agent_demo_timer: float, opponent_demo_timer: float,
                        inverted: bool) -> ndarray:
        player_0 = encode_player(packet, agent_index, agent_has_flip, agent_demo_timer, inverted)
        player_1 = encode_player(packet, opponent_index, opponent_has_flip, opponent_demo_timer, inverted)
        boost = encode_boost(packet, inverted)
        ball = encode_ball(packet, inverted)

        prev_action_encoding = get_action_encoding(self.prev_action.reshape(1, -1))

        x_train = impute_features(player_0, player_1, boost, ball, prev_action_encoding.reshape(-1)).reshape(1, -1)

        return x_train

    def update_controller_from_action(self, actions: ndarray):
        actions = actions[0]

        self.prev_action = actions

        steer_yaw = actions[1] * 0.5 - 1.0

        self.controls.throttle = actions[0] - 1.0
        self.controls.steer = steer_yaw
        self.controls.pitch = actions[2] * 0.5 - 1.0
        self.controls.yaw = steer_yaw
        self.controls.roll = actions[3] - 1.0

        self.controls.jump = actions[4]
        self.controls.boost = actions[5]
        self.controls.handbrake = actions[6]
