import math
import time
from typing import Optional

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.game_state_util import *
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.info import GameInfo
from util.rlmath import argmax
from util.vec import dot, axis_to_rotation, rotation_to_euler, normalize, looking_in_dir, xy, Vec3


ARTIFICIAL_UNLIMITED_BOOST = True
TURN_COOLDOWN = 0.3
VERTICAL_TURNS = True


class Turn:
    def __init__(self, dir: Vec3, axis: Optional[Vec3]):
        self.dir = dir
        self.axis = axis


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

        halfpi = math.pi / 2
        car = self.info.my_car
        ball = self.info.ball

        car_state = CarState()
        if ARTIFICIAL_UNLIMITED_BOOST:
            car_state.boost_amount = 100

        if ball.pos.x == 0 and ball.pos.y == 0:
            # Kickoff
            self.last_turn_time = time.time()
            euler = rotation_to_euler(looking_in_dir(xy(ball.pos - car.pos)))
            car_state.physics = Physics(
                rotation=Rotator(pitch=euler.x, roll=0, yaw=euler.y)
            )

        elif self.last_turn_time + TURN_COOLDOWN < time.time():

            turns = [
                Turn(car.forward, None),
                Turn(car.left, car.up * halfpi),
                Turn(-car.left, car.up * -halfpi)
            ] if not VERTICAL_TURNS else [
                Turn(car.forward, None),
                Turn(car.left, car.up * halfpi),
                Turn(-car.left, car.up * -halfpi),
                Turn(car.up * 0.25, car.left * -halfpi),
                Turn(-car.up, car.left * halfpi),
            ]

            # In practise, this offset has little impact
            ball_pos_with_offset = ball.pos + normalize(self.info.opp_goal.pos - ball.pos) * -60
            delta_n = normalize(ball_pos_with_offset - car.pos)

            turn, _ = argmax(turns, lambda turn: dot(turn.dir, delta_n))

            if turn.axis is not None:
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
