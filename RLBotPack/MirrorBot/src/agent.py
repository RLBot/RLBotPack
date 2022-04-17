import threading

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.ControllerState import ControllerState
from rlbot.messages.flat.PlayerInputChange import PlayerInputChange
from rlbot.socket.socket_manager import SocketRelay
from rlbot.utils.game_state_util import Vector3, Rotator, Physics, CarState, GameState, BallState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from rlutilities.linear_algebra import vec3, mat3, rotation_to_euler, dot, look_at
from rlutilities.simulation import Game, Car


def vec3_to_vector3(v: vec3) -> Vector3:
    return Vector3(v.x, v.y, v.z)


def mat3_to_rotator(mat: mat3) -> Rotator:
    pyr = rotation_to_euler(mat)
    return Rotator(pyr.x, pyr.y, pyr.z)


def car_to_car_state(car: Car) -> CarState:
    return CarState(physics=Physics(
        location=vec3_to_vector3(car.position),
        rotation=mat3_to_rotator(car.orientation),
        velocity=vec3_to_vector3(car.velocity),
        angular_velocity=vec3_to_vector3(car.angular_velocity),
    ), boost_amount=car.boost)


def cstate_to_simple_cstate(controls: ControllerState) -> SimpleControllerState:
    return SimpleControllerState(
        throttle=controls.Throttle(),
        steer=controls.Steer(),
        pitch=controls.Pitch(),
        yaw=controls.Yaw(),
        roll=controls.Roll(),
        jump=controls.Jump(),
        boost=controls.Boost(),
        handbrake=controls.Handbrake(),
        use_item=controls.UseItem(),
    )


mirror_x = mat3(
    -1, 0, 0,
    0, 1, 0,
    0, 0, 1,
)
mirror_y = mat3(
    1, 0, 0,
    0, -1, 0,
    0, 0, 1,
)
mirror_xy = mat3(
    -1, 0, 0,
    0, -1, 0,
    0, 0, 1,
)
mirror_matrices = [mirror_x, mirror_y, mirror_xy]


class Mirror(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.game = Game()
        self.target_index = None
        self.mirror_matrix = None
        self.impossible_ball = False

        self.socket_man = SocketRelay()
        self.socket_man.player_input_change_handlers.append(self.track_target_inputs)
        self.target_controls: SimpleControllerState = None
        self.socket_thread = None

    def track_target_inputs(self, change: PlayerInputChange, seconds: float, frame_num: int):
        if change.PlayerIndex() == self.target_index:
            self.target_controls = cstate_to_simple_cstate(change.ControllerState())
            if self.mirror_matrix is not mirror_xy:
                self.target_controls.steer *= -1

    def run_socket_relay(self):
        self.socket_man.connect_and_run(wants_quick_chat=False, wants_game_messages=True, wants_ball_predictions=False)

    def initialize_agent(self):
        self.game.set_mode("soccar")
        self.game.read_field_info(self.get_field_info())
        self.socket_thread = threading.Thread(target=self.run_socket_relay)
        self.socket_thread.start()

    def find_mirror_target(self, packet: GameTickPacket):
        self.target_index = None
        self.impossible_ball = False

        # if it's a 1v1 against a mirror bot
        if packet.num_cars == 2 and self.team != packet.game_cars[1 - self.index].team:
            self.target_index = 1 - self.index
            self.mirror_matrix = mirror_y
            self.impossible_ball = True
            return

        team_mirror_index_counter = -1
        # find a car on own team that is not a mirror bot
        # and also find our index among team mirror bots
        for i in range(packet.num_cars):
            car = packet.game_cars[i]
            if car.team == self.team:
                if "mirror" in car.name.lower() and car.is_bot:
                    team_mirror_index_counter += 1
                    if i == self.index:
                        self.mirror_matrix = mirror_matrices[team_mirror_index_counter]
                else:
                    self.target_index = i

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        self.game.read_packet(packet)

        if packet.game_info.is_round_active:
            self.find_mirror_target(packet)

        if self.target_index is not None and packet.game_info.is_round_active:
            mirrored_target = Car(self.game.cars[self.target_index])
            mirrored_target.position = dot(self.mirror_matrix, mirrored_target.position)
            mirrored_target.orientation = look_at(
                dot(self.mirror_matrix, mirrored_target.forward()),
                dot(self.mirror_matrix, mirrored_target.up()),
            )
            mirrored_target.velocity = dot(self.mirror_matrix, mirrored_target.velocity)
            mirrored_target.angular_velocity = dot(self.mirror_matrix, mirrored_target.angular_velocity)
            if self.mirror_matrix is not mirror_xy:
                mirrored_target.angular_velocity *= -1
            mirrored_target.boost = mirrored_target.boost

            game_state = GameState(cars={self.index: car_to_car_state(mirrored_target)})

            if self.impossible_ball:
                game_state.ball = BallState(Physics(
                    location=Vector3(y=0),
                    velocity=Vector3(y=0),
                ))

            self.set_game_state(game_state)

        return self.target_controls or SimpleControllerState()
