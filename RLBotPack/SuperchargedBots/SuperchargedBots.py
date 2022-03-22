from __future__ import annotations

import configparser
import math
import os
from threading import Thread
from traceback import print_exc
from typing import List

import numpy as np
from rlbot.agents.base_script import BaseScript
from rlbot.messages.flat.PlayerInputChange import PlayerInputChange
from rlbot.socket.socket_manager import SocketRelay
from rlbot.utils.game_state_util import (BallState, CarState, GameState,
                                         Physics, Vector3)
from rlbot.utils.structures.game_data_struct import GameTickPacket

BOOST_ACCEL = 991 + 2/3
BOOST_CONSUMPTION = 33 + 1/3
DEFAULT_CAR = {
    "boosting": False,
    "steering": False,
    "total_boost": BOOST_CONSUMPTION,
    "last_boost": BOOST_CONSUMPTION
}

def cap(x, low, high):
    return low if x < low else (high if x > high else x)


class SuperchargedBots(BaseScript):
    def __init__(self):
        super().__init__("SuperchargedBots")
        self.packet = None
        self.last_packet_time = -1
        self.time = 0
        self.delta_time = -1
        self.tracker = {}
        self.last_ball_touch_time = -1

    def set_config(self, path):
        self.config = configparser.ConfigParser()
        self.config.read(path)

    def get_bool_from_config(self, section, option):
        return True if self.config.get(section, option).lower() in {"true", "1"} else False

    def get_float_from_config(self, section, option):
        return float(self.config.get(section, option))

    def get_int_from_config(self, section, option):
        return int(self.get_float_from_config(section, option))

    def main(self):
        self.set_config(os.path.join(os.path.dirname(os.path.realpath(__file__)), "SuperchargedBots.cfg"))

        self.teams = []

        if self.get_bool_from_config("Options", "help_blue_team"):
            self.teams.append(0)
        print(f"SuperchargedBots: help_blue_team = {0 in self.teams}")

        if self.get_bool_from_config("Options", "help_orange_team"):
            self.teams.append(1)
        print(f"SuperchargedBots: help_orange_team = {1 in self.teams}")

        self.bots_only = self.get_bool_from_config("Options", "bots_only")
        print(f"SuperchargedBots: bots_only = {self.bots_only}")

        self.bonus_boost_accel_percent = self.get_float_from_config("Options", "bonus_boost_accel_percent") / 100
        print(f"SuperchargedBots: bonus_boost_accel_percent = {self.bonus_boost_accel_percent * 100}%")

        self.bonus_boost_tank = self.get_int_from_config("Options", "bonus_boost_tank")
        print(f"SuperchargedBots: bonus_boost_tank = {self.bonus_boost_tank}")

        self.minimum_boost = self.get_int_from_config("Options", "minimum_boost")
        print(f"SuperchargedBots: minimum_boost = {self.minimum_boost}")

        self.bonus_hit_percent = self.get_int_from_config("Options", "bonus_hit_percent")
        print(f"SuperchargedBots: bonus_hit_percent = {self.bonus_hit_percent}")

        self.demo_helper = self.get_bool_from_config("Options", "demo_helper")
        print(f"SuperchargedBots: demo_helper = {self.demo_helper}")

        self.socket_relay = SocketRelay()
        self.socket_relay.player_input_change_handlers.append(self.input_change)

        self.non_blocking_socket_relay = Thread(target=self.socket_relay.connect_and_run, args=(False, True, False))
        self.non_blocking_socket_relay.start()

        while 1:
            try:
                self.packet: GameTickPacket = self.wait_game_tick_packet()
                
                time = self.packet.game_info.seconds_elapsed
                self.delta_time = time - self.time
                self.time = time

                supercharged_bots = []
                cars = dict()

                for car_index in range(self.packet.num_cars):
                    car = self.packet.game_cars[car_index]

                    if (self.bots_only and not car.is_bot) or car.team not in self.teams:
                        continue

                    if car.name not in self.tracker:
                        self.tracker[car.name] = DEFAULT_CAR.copy()

                    supercharged_bots.append(car.name)

                    if not self.packet.game_info.is_round_active:
                        continue

                    if self.packet.game_info.is_kickoff_pause:
                        self.tracker[car.name]['total_boost'] = BOOST_CONSUMPTION
                        self.tracker[car.name]['last_boost'] = BOOST_CONSUMPTION
                        continue

                    velocity = None

                    if self.demo_helper:
                        for other_car_index in range(self.packet.num_cars):
                            other_car = self.packet.game_cars[other_car_index]

                            if car.team == other_car.team:
                                continue

                            car_location = Vector.from_vector(car.physics.location)
                            other_car_location = Vector.from_vector(other_car.physics.location)

                            if car_location.flat_dist(other_car_location) < 200 and abs(Vector.from_vector(car.physics.velocity).angle(other_car_location - car_location)) < 0.5:
                                velocity = Vector.from_vector(car.physics.velocity).flatten().scale(2300)

                    if self.tracker[car.name]['boosting']:
                        if not self.tracker[car.name]['steering'] and (car.boost > self.minimum_boost):
                            CP = math.cos(car.physics.rotation.pitch)
                            SP = math.sin(car.physics.rotation.pitch)
                            CY = math.cos(car.physics.rotation.yaw)
                            SY = math.sin(car.physics.rotation.yaw)
                            forward = Vector(CP*CY, CP*SY, SP)
                            if velocity is None:
                                velocity = Vector.from_vector(car.physics.velocity) + forward * (BOOST_ACCEL * self.delta_time * self.bonus_boost_accel_percent)

                        self.tracker[car.name]['total_boost'] -= BOOST_CONSUMPTION * self.delta_time * (100 / self.bonus_boost_tank)

                    boost_amount = None

                    if car.boost > self.minimum_boost and car.boost > self.tracker[car.name]['last_boost']:
                        self.tracker[car.name]['total_boost'] += car.boost - self.tracker[car.name]['last_boost']
                    elif car.boost < self.minimum_boost:
                        self.tracker[car.name]['total_boost'] = self.minimum_boost
                    
                    self.tracker[car.name]['total_boost'] = cap(self.tracker[car.name]['total_boost'], 0, 100)
                    floored_boost = math.floor(self.tracker[car.name]['total_boost'])
                    if floored_boost != car.boost:
                        boost_amount = floored_boost
                    self.tracker[car.name]['last_boost'] = car.boost if boost_amount is None else boost_amount

                    if velocity is None and boost_amount is None:
                        continue

                    cars[car_index] = CarState(
                        Physics(
                            velocity=None if velocity is None else Vector3(*velocity)
                        ),
                        boost_amount=boost_amount
                    )

                last_ball_touch = self.packet.game_ball.latest_touch
                ball = None

                if last_ball_touch.time_seconds > self.last_ball_touch_time:
                    if (last_ball_touch.time_seconds - self.last_ball_touch_time) > 0.5:
                        if not self.bots_only or self.packet.game_cars[last_ball_touch.player_index].is_bot:
                            if last_ball_touch.team in self.teams:
                                bonus_hit_multiplier = self.bonus_hit_percent / 100 + 1
                                ball_velocity = Vector.from_vector(self.packet.game_ball.physics.velocity) * Vector(bonus_hit_multiplier, bonus_hit_multiplier, 1 / bonus_hit_multiplier)
                                ball = BallState(physics=Physics(
                                    velocity=Vector3(*ball_velocity)
                                ))

                    self.last_ball_touch_time = last_ball_touch.time_seconds

                game_state = GameState()

                if cars:
                    game_state.cars = cars

                if ball is not None:
                    game_state.ball = ball    

                self.set_game_state(game_state)

                if self.last_packet_time == -1 or self.time - self.last_packet_time >= 0.1:
                    self.matchcomms.outgoing_broadcast.put_nowait({
                        "supercharged_bots": supercharged_bots,
                        "supercharged_config": {
                            "bonus_boost_accel_percent": self.bonus_boost_accel_percent,
                            "bonus_boost_tank": self.bonus_boost_tank,
                            "minimum_boost": self.minimum_boost,
                            "bonus_hit_percent": self.bonus_hit_percent,
                            "demo_helper": self.demo_helper,
                        }
                    })
            except Exception:
                print_exc()

    def input_change(self, change: PlayerInputChange, seconds: float, frame_num: int):
        try:
            game_car = self.packet.game_cars[change.PlayerIndex()]

            if game_car.name not in self.tracker:
                return

            controller_state = change.ControllerState()
            self.tracker[game_car.name]['boosting'] = controller_state.Boost()
            self.tracker[game_car.name]['steering'] = (game_car.has_wheel_contact and controller_state.Steer() > 0.2) or (not game_car.has_wheel_contact and (controller_state.Yaw() > 0.2 or controller_state.Pitch() > 0.2))
        except Exception:
            print_exc()


# Vector supports 1D, 2D and 3D Vectors, as well as calculations between them
# Arithmetic with 1D and 2D lists/tuples aren't supported - just set the remaining values to 0 manually
# With this new setup, Vector is much faster because it's just a wrapper for numpy
class Vector:
    def __init__(self, x: float = 0, y: float = 0, z: float = 0, np_arr=None):
        # this is a private property - this is so all other things treat this class like a list, and so should you!
        self._np = np.array([x, y, z]) if np_arr is None else np_arr

    def __getitem__(self, index):
        return self._np[index].item()

    def __setitem__(self, index, value):
        self._np[index] = value

    @property
    def x(self):
        return self._np[0].item()

    @x.setter
    def x(self, value):
        self._np[0] = value

    @property
    def y(self):
        return self._np[1].item()

    @y.setter
    def y(self, value):
        self._np[1] = value

    @property
    def z(self):
        return self._np[2].item()

    @z.setter
    def z(self, value):
        self._np[2] = value

    # self == value
    def __eq__(self, value):
        if isinstance(value, float) or isinstance(value, int):
            return self.magnitude() == value

        if hasattr(value, "_np"):
            value = value._np
        return (self._np == value).all()

    # len(self)
    def __len__(self):
        return 3  # this is a 3 dimensional vector, so we return 3

    # str(self)
    def __str__(self):
        # Vector's can be printed to console
        return f"[{self.x} {self.y} {self.z}]"

    # repr(self)
    def __repr__(self):
        return f"Vector(x={self.x}, y={self.y}, z={self.z})"

    # -self
    def __neg__(self):
        return Vector(np_arr=self._np * -1)

    # self + value
    def __add__(self, value):
        if hasattr(value, "_np"):
            value = value._np
        return Vector(np_arr=self._np+value)
    __radd__ = __add__

    # self - value
    def __sub__(self, value):
        if hasattr(value, "_np"):
            value = value._np
        return Vector(np_arr=self._np-value)

    def __rsub__(self, value):
        return -self + value

    # self * value
    def __mul__(self, value):
        if hasattr(value, "_np"):
            value = value._np
        return Vector(np_arr=self._np*value)
    __rmul__ = __mul__

    # self / value
    def __truediv__(self, value):
        if hasattr(value, "_np"):
            value = value._np
        return Vector(np_arr=self._np/value)

    def __rtruediv__(self, value):
        return self * (1 / value)

    # round(self)
    def __round__(self, decimals=0) -> Vector:
        # Rounds all of the values
        return Vector(np_arr=np.around(self._np, decimals=decimals))

    @staticmethod
    def from_vector(vec) -> Vector:
        return Vector(vec.x, vec.y, vec.z)

    def magnitude(self) -> float:
        # Returns the length of the vector
        return np.linalg.norm(self._np).item()

    def _magnitude(self) -> np.float64:
        # Returns the length of the vector in a numpy float 64
        return np.linalg.norm(self._np)

    def dot(self, value: Vector) -> float:
        # Returns the dot product of two vectors
        if hasattr(value, "_np"):
            value = value._np
        return self._np.dot(value).item()

    def cross(self, value: Vector) -> Vector:
        # Returns the cross product of two vectors
        if hasattr(value, "_np"):
            value = value._np
        return Vector(np_arr=np.cross(self._np, value))

    def copy(self) -> Vector:
        # Returns a copy of the vector
        return Vector(*self._np)

    def normalize(self, return_magnitude=False) -> List[Vector, float] or Vector:
        # normalize() returns a Vector that shares the same direction but has a length of 1
        # normalize(True) can also be used if you'd like the length of this Vector (used for optimization)
        magnitude = self._magnitude()
        if magnitude != 0:
            norm_vec = Vector(np_arr=self._np / magnitude)
            if return_magnitude:
                return norm_vec, magnitude.item()
            return norm_vec
        if return_magnitude:
            return Vector(), 0
        return Vector()

    def _normalize(self) -> np.ndarray:
        # Normalizes a Vector and returns a numpy array
        magnitude = self._magnitude()
        if magnitude != 0:
            return self._np / magnitude
        return np.array((0, 0, 0))

    def flatten(self) -> Vector:
        # Sets Z (Vector[2]) to 0, making the Vector 2D
        return Vector(self._np[0], self._np[1])

    def angle2D(self, value: Vector) -> float:
        # Returns the 2D angle between this Vector and another Vector in radians
        return self.flatten().angle(value.flatten())

    def angle(self, value: Vector) -> float:
        # Returns the angle between this Vector and another Vector in radians
        dp = np.dot(self._normalize(), value._normalize()).item()
        return math.acos(-1 if dp < -1 else (1 if dp > 1 else dp))

    def rotate2D(self, angle: float) -> Vector:
        # Rotates this Vector by the given angle in radians
        # Note that this is only 2D, in the x and y axis
        return Vector((math.cos(angle)*self.x) - (math.sin(angle)*self.y), (math.sin(angle)*self.x) + (math.cos(angle)*self.y), self.z)

    def clamp2D(self, start: Vector, end: Vector) -> Vector:
        # Similar to integer clamping, Vector's clamp2D() forces the Vector's direction between a start and end Vector
        # Such that Start < Vector < End in terms of clockwise rotation
        # Note that this is only 2D, in the x and y axis
        s = self._normalize()
        right = np.dot(s, np.cross(end._np, (0, 0, -1))) < 0
        left = np.dot(s, np.cross(start._np, (0, 0, -1))) > 0
        if (right and left) if np.dot(end._np, np.cross(start._np, (0, 0, -1))) > 0 else (right or left):
            return self
        if np.dot(start._np, s) < np.dot(end._np, s):
            return end
        return start

    def clamp(self, start: Vector, end: Vector) -> Vector:
        # This extends clamp2D so it also clamps the vector's z
        s = self.clamp2D(start, end)

        if s.z < start.z:
            s = s.flatten().scale(1 - start.z)
            s.z = start.z
        elif s.z > end.z:
            s = s.flatten().scale(1 - end.z)
            s.z = end.z

        return s

    def dist(self, value: Vector) -> float:
        # Distance between 2 vectors
        if hasattr(value, "_np"):
            value = value._np
        return np.linalg.norm(self._np - value).item()

    def flat_dist(self, value: Vector) -> float:
        # Distance between 2 vectors on a 2D plane
        return value.flatten().dist(self.flatten())

    def cap(self, low: float, high: float) -> Vector:
        # Caps all values in a Vector between 'low' and 'high'
        return Vector(np_arr=np.clip(self._np, low, high))

    def midpoint(self, value: Vector) -> Vector:
        # Midpoint of the 2 vectors
        if hasattr(value, "_np"):
            value = value._np
        return Vector(np_arr=(self._np + value) / 2)

    def scale(self, value: float) -> Vector:
        # Returns a vector that has the same direction but with a value as the magnitude
        return self.normalize() * value


if __name__ == "__main__":
    SuperchargedBots = SuperchargedBots()
    SuperchargedBots.main()
