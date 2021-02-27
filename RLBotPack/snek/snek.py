import time

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.game_state_util import *
from rlbot.utils.structures.game_data_struct import GameTickPacket

from find_turn import find_turn
from settings import TURN_COOLDOWN
from utilities.info import GameInfo
from utilities.vec import dot, axis_to_rotation, rotation_to_euler, looking_in_dir, xy


class Snek(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.info = GameInfo(index, team)
        self.last_turn_time = 0
        self.controls = SimpleControllerState()
        self.controls.throttle = 1
        self.controls.boost = 1

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        self.info.read_packet(packet)

        car = self.info.my_car
        ball = self.info.ball

        car_state = CarState()
        car_state.boost_amount = 100

        if ball.pos.x == 0 and ball.pos.y == 0:
            # Kickoff
            self.last_turn_time = time.time()
            euler = rotation_to_euler(looking_in_dir(xy(ball.pos - car.pos)))
            car_state.physics = Physics(
                rotation=Rotator(pitch=euler.x, roll=0, yaw=euler.y)
            )

        else:

            turn = find_turn(self)

            if self.can_turn() and turn is not None and turn.axis is not None:
                self.last_turn_time = time.time()
                mat = axis_to_rotation(turn.axis)
                new_vel = dot(mat, car.vel)
                new_rot = dot(mat, car.rot)
                euler = rotation_to_euler(new_rot)
                car_state.physics = Physics(
                    velocity=Vector3(new_vel[0], new_vel[1], new_vel[2]),
                    rotation=Rotator(pitch=euler.x, roll=0, yaw=euler.y)
                )

        game_state = GameState(cars={self.index: car_state})
        self.set_game_state(game_state)

        return self.controls

    def can_turn(self) -> bool:
        return self.last_turn_time + TURN_COOLDOWN < time.time()

    def time_till_turn(self) -> float:
        return self.last_turn_time + TURN_COOLDOWN - time.time()
