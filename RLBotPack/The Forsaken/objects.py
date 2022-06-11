from __future__ import annotations

import math
from enum import Enum
from typing import TYPE_CHECKING, Union

import rlbot.utils.structures.game_data_struct as game_data_struct
from rlbot.utils.structures.bot_input_struct import PlayerInput

if TYPE_CHECKING:
    from rlbot.utils.structures.game_data_struct import GameTickPacket
    from hive import MyHivemind


class CarObject:
    # The carObject, and kin, convert the gametickpacket in something a little friendlier to use,
    # and are updated by GoslingAgent as the game runs
    def __init__(self, index: int, packet: GameTickPacket = None):
        self.location: Vector3 = Vector3(0, 0, 0)
        self.orientation: Matrix3 = Matrix3(0, 0, 0)
        self.velocity: Vector3 = Vector3(0, 0, 0)
        self.angular_velocity: [] = [0, 0, 0]
        self.demolished: bool = False
        self.airborne: bool = False
        self.supersonic: bool = False
        self.jumped: bool = False
        self.doublejumped: bool = False
        self.team: int = 0
        self.boost: float = 0
        self.index: int = index
        self.controller: PlayerInput = PlayerInput()
        # A list that acts as the routines stack
        self.stack: [] = []
        self.action: Action = Action.Shadowing
        self.on_side: bool = False
        self.closest: bool = False
        self.second_closest: bool = False
        self.time = 0
        self.delta_time = 1 / 120
        self.boost_accel = 991 + (2 / 3)
        self.gravity = Vector3(0, 0, -650)
        self.goals = 0
        self.ball_prediction_struct = None
        if packet is not None:
            car = packet.game_cars[self.index]
            self.team = car.team
            self.hitbox = Hitbox(car.hitbox.length, car.hitbox.width, car.hitbox.height, Vector3(car.hitbox_offset))
            self.update(packet)

    def local(self, value: Vector3) -> Vector3:
        # Shorthand for self.orientation.dot(value)
        return self.orientation.dot(value)

    def local_location(self, location):
        # Returns the location of an item relative to the car
        # x is how far the location is forwards (+) or backwards (-)
        # y is the velocity to the left (+) or right (-)
        # z is how far the location is upwards (+) or downwards (-)
        return self.local(location - self.location)

    def local_velocity(self, velocity=None):
        # Returns the velocity of an item relative to the car
        # x is the velocity forwards (+) or backwards (-)
        # y is the velocity to the left (+) or right (-)
        # z if the velocity upwards (+) or downwards (-)
        if velocity is None:
            velocity = self.velocity
        return self.local(velocity)

    def update(self, packet: GameTickPacket):
        car = packet.game_cars[self.index]
        self.location.data = [car.physics.location.x, car.physics.location.y, car.physics.location.z]
        self.velocity.data = [car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z]
        self.orientation = Matrix3(car.physics.rotation.pitch, car.physics.rotation.yaw, car.physics.rotation.roll)
        self.angular_velocity = self.orientation.dot(
            [car.physics.angular_velocity.x, car.physics.angular_velocity.y, car.physics.angular_velocity.z]).data
        self.demolished = car.is_demolished
        self.airborne = not car.has_wheel_contact
        self.supersonic = car.is_super_sonic
        self.jumped = car.jumped
        self.doublejumped = car.double_jumped
        self.boost = car.boost
        # Reset controller
        self.controller = PlayerInput()
        self.closest = False
        self.second_closest: bool = False
        self.delta_time = packet.game_info.seconds_elapsed - self.time
        self.time = packet.game_info.seconds_elapsed
        self.goals = car.score_info.goals

    def get_raw(self, force_on_ground=False):
        return (
            tuple(self.location),
            tuple(self.velocity),
            (tuple(self.forward), tuple(self.right), tuple(self.up)),
            tuple(self.angular_velocity),
            1 if self.demolished else 0,
            1 if self.airborne and not force_on_ground else 0,
            1 if self.supersonic else 0,
            1 if self.jumped else 0,
            1 if self.doublejumped else 0,
            self.boost,
            self.index,
            tuple(self.hitbox),
            tuple(self.hitbox.offset)
        )

    @property
    def forward(self) -> Vector3:
        # A vector pointing forwards relative to the cars orientation. Its magnitude is 1
        return self.orientation.forward

    @property
    def right(self) -> Vector3:
        # A vector pointing left relative to the cars orientation. Its magnitude is 1
        return self.orientation.right

    @property
    def up(self) -> Vector3:
        # A vector pointing up relative to the cars orientation. Its magnitude is 1
        return self.orientation.up

    def push(self, routine: Routine):
        # Shorthand for adding a routine to the stack
        self.stack.append(routine)

    def pop(self):
        # Shorthand for removing a routine from the stack, returns the routine
        return self.stack.pop()

    def clear(self):
        # Shorthand for clearing the stack of all routines
        self.stack = []


class Hitbox:
    def __init__(self, length=0, width=0, height=0, offset=None):
        self.length = length
        self.width = width
        self.height = height

        if offset is None:
            offset = Vector3()
        self.offset = offset

    def __getitem__(self, index):
        return (self.length, self.width, self.height)[index]


class BallObject:
    def __init__(self):
        self.location: Vector3 = Vector3(0, 0, 0)
        self.velocity: Vector3 = Vector3(0, 0, 0)
        self.latest_touched_time: float = 0
        self.latest_touched_team: float = 0

    def update(self, packet: GameTickPacket):
        ball = packet.game_ball
        self.location.data = [ball.physics.location.x, ball.physics.location.y, ball.physics.location.z]
        self.velocity.data = [ball.physics.velocity.x, ball.physics.velocity.y, ball.physics.velocity.z]
        self.latest_touched_time = ball.latest_touch.time_seconds
        self.latest_touched_team = ball.latest_touch.team


class BoostObject:
    def __init__(self, index, location, large):
        self.index: int = index
        self.location: Vector3 = Vector3(location.x, location.y, location.z)
        self.active: bool = True
        self.large: bool = large

    def update(self, packet: GameTickPacket):
        self.active = packet.game_boosts[self.index].is_active


class GoalObject:
    # This is a simple object that creates/holds goalpost locations for a given team (for soccer on standard maps only)
    def __init__(self, team: int):
        team = 1 if team == 1 else -1
        self.location: Vector3 = Vector3(0, team * 5100, 320)  # center of goal line
        # Posts are closer to x=750, but this allows the bot to be a little more accurate
        self.left_post: Vector3 = Vector3(team * 850, team * 5100, 320)
        self.right_post: Vector3 = Vector3(-team * 850, team * 5100, 320)


class GameObject:
    # This object holds information about the current match
    def __init__(self):
        self.time: float = 0
        self.time_remaining: float = 0
        self.overtime: bool = False
        self.round_active: bool = False
        self.kickoff: bool = False
        self.match_ended: bool = False

    def update(self, packet: GameTickPacket):
        game = packet.game_info
        self.time = game.seconds_elapsed
        self.time_remaining = game.game_time_remaining
        self.overtime = game.is_overtime
        self.round_active = game.is_round_active
        self.kickoff = game.is_kickoff_pause
        self.match_ended = game.is_match_ended


class Matrix3:
    # The Matrix3's sole purpose is to convert roll, pitch,
    # and yaw data from the gametickpaket into an orientation matrix
    # An orientation matrix contains 3 Vector3's
    # Matrix3[0] is the "forward" direction of a given car
    # Matrix3[1] is the "left" direction of a given car
    # Matrix3[2] is the "up" direction of a given car
    # If you have a distance between the car and some object, ie ball.location - car.location,
    # you can convert that to local coordinates by dotting it with this matrix
    # ie: local_ball_location = Matrix3.dot(ball.location - car.location)
    def __init__(self, pitch, yaw, roll):
        cp = math.cos(pitch)
        sp = math.sin(pitch)
        cy = math.cos(yaw)
        sy = math.sin(yaw)
        cr = math.cos(roll)
        sr = math.sin(roll)
        # List of 3 vectors, each describing the direction of an axis: Forward, Left, and Up
        self.data: [Vector3] = [
            Vector3(cp * cy, cp * sy, sp),
            Vector3(cy * sp * sr - cr * sy, sy * sp * sr + cr * cy, -cp * sr),
            Vector3(-cr * cy * sp - sr * sy, -cr * sy * sp + sr * cy, cp * cr)]
        self.forward: Vector3
        self.right: Vector3
        self.up: Vector3
        self.forward, self.right, self.up = self.data

    def __getitem__(self, key: int) -> Vector3:
        return self.data[key]

    def dot(self, vector) -> Vector3:
        return Vector3(self.forward.dot(vector), self.right.dot(vector), self.up.dot(vector))


class Vector3:
    # This is the backbone of Gosling Utils. The Vector3 makes it easy to store positions,
    # velocities, etc and perform vector math
    # A Vector3 can be created with:
    # - Anything that has a __getitem__ (lists, tuples, Vector3's, etc)
    # - 3 numbers
    # - A gametickpacket vector
    def __init__(self, *args):
        if hasattr(args[0], "__getitem__"):
            self.data = list(args[0])
        elif isinstance(args[0], game_data_struct.Vector3):
            self.data = [args[0].x, args[0].y, args[0].z]
        elif isinstance(args[0], game_data_struct.Rotator):
            self.data = [args[0].pitch, args[0].yaw, args[0].roll]
        elif len(args) == 3:
            self.data = list(args)
        else:
            raise TypeError("Vector3 unable to accept %s" % args)

    # Property functions allow you to use `Vector3.x` vs `Vector3[0]`
    @property
    def x(self) -> float:
        return self.data[0]

    @x.setter
    def x(self, value: float):
        self.data[0] = value

    @property
    def y(self) -> float:
        return self.data[1]

    @y.setter
    def y(self, value: float):
        self.data[1] = value

    @property
    def z(self) -> float:
        return self.data[2]

    @z.setter
    def z(self, value: float):
        self.data[2] = value

    def __getitem__(self, key: int) -> float:
        # To access a single value in a Vector3, treat it like a list
        # ie: to get the first (x) value use: Vector3[0]
        # The same works for setting values
        return self.data[key]

    def __setitem__(self, key: int, value: float):
        self.data[key] = value

    def __str__(self) -> str:
        # Vector3's can be printed to console
        return str(self.data)

    __repr__ = __str__

    def __eq__(self, value: object) -> bool:
        # Vector3's can be compared with:
        # - Another Vector3, in which case True will be returned if they have the same values
        # - A list, in which case True will be returned if they have the same values
        # - A single value, in which case True will be returned if the Vector's length matches the value
        if isinstance(value, Vector3):
            return self.data == value.data
        elif isinstance(value, list):
            return self.data == value
        else:
            return self.magnitude() == value

    # Vector3's support most operators (+-*/)
    # If using an operator with another Vector3, each dimension will be independent
    # ie x+x, y+y, z+z
    # If using an operator with only a value, each dimension will be affected by that value
    # ie x+v, y+v, z+v
    def __add__(self, value: Union[Vector3, float]) -> Vector3:
        if isinstance(value, Vector3):
            return Vector3(self[0] + value[0], self[1] + value[1], self[2] + value[2])
        return Vector3(self[0] + value, self[1] + value, self[2] + value)

    __radd__ = __add__

    def __sub__(self, value: Union[Vector3, float]) -> Vector3:
        if isinstance(value, Vector3):
            return Vector3(self[0] - value[0], self[1] - value[1], self[2] - value[2])
        return Vector3(self[0] - value, self[1] - value, self[2] - value)

    __rsub__ = __sub__

    def __neg__(self):
        return Vector3(-self[0], -self[1], -self[2])

    def __mul__(self, value: Union[Vector3, float]) -> Vector3:
        if isinstance(value, Vector3):
            return Vector3(self[0] * value[0], self[1] * value[1], self[2] * value[2])
        return Vector3(self[0] * value, self[1] * value, self[2] * value)

    __rmul__ = __mul__

    def __truediv__(self, value: Union[Vector3, float]) -> Vector3:
        if isinstance(value, Vector3):
            return Vector3(self[0] / value[0], self[1] / value[1], self[2] / value[2])
        return Vector3(self[0] / value, self[1] / value, self[2] / value)

    def __rtruediv__(self, value: Vector3) -> Vector3:
        if isinstance(value, Vector3):
            return Vector3(value[0] / self[0], value[1] / self[1], value[2] / self[2])
        raise TypeError("unsupported rtruediv operands")

    def magnitude(self) -> float:
        # Magnitude() returns the length of the vector
        return math.sqrt((self[0] * self[0]) + (self[1] * self[1]) + (self[2] * self[2]))

    def normalize(self, return_magnitude: bool = False) -> Union[Vector3, (Vector3, float)]:
        # Normalize() returns a Vector3 that shares the same direction but has a length of 1.0
        # Normalize(True) can also be used if you'd like the length of this Vector3 (used for optimization)
        magnitude = self.magnitude()
        if magnitude != 0:
            if return_magnitude:
                return Vector3(self[0] / magnitude, self[1] / magnitude, self[2] / magnitude), magnitude
            return Vector3(self[0] / magnitude, self[1] / magnitude, self[2] / magnitude)
        if return_magnitude:
            return Vector3(0, 0, 0), 0
        return Vector3(0, 0, 0)

    # Linear algebra functions
    def dot(self, value: Vector3) -> float:
        return self[0] * value[0] + self[1] * value[1] + self[2] * value[2]

    def cross(self, value: Vector3) -> Vector3:
        return Vector3((self[1] * value[2]) - (self[2] * value[1]), (self[2] * value[0]) - (self[0] * value[2]),
                       (self[0] * value[1]) - (self[1] * value[0]))

    def flatten(self) -> Vector3:
        # Sets Z (Vector3[2]) to 0
        return Vector3(self[0], self[1], 0)

    def render(self) -> []:
        # Returns a list with the x and y values, to be used with pygame
        return [self[0], self[1]]

    def copy(self) -> Vector3:
        # Returns a copy of this Vector3
        return Vector3(self.data[:])

    def angle2D(self, value: Vector3) -> float:
        # Returns the angle between this Vector3 and another Vector3
        return math.acos(round(self.flatten().normalize().dot(value.flatten().normalize()), 4))

    def angle3D(self, value: Vector3) -> float:
        # Returns the angle between this Vector3 and another Vector3
        return math.acos(round(self.normalize().dot(value.normalize()), 4))

    def rotate(self, angle: float) -> Vector3:
        # Rotates this Vector3 by the given angle in radians
        # Note that this is only 2D, in the x and y axis
        return Vector3((math.cos(angle) * self[0]) - (math.sin(angle) * self[1]),
                       (math.sin(angle) * self[0]) + (math.cos(angle) * self[1]), self[2])

    def clamp(self, start, end):
        # Similar to integer clamping, Vector3's clamp() forces the Vector3's direction between a start and end Vector3
        # Such that Start < Vector3 < End in terms of clockwise rotation
        # Note that this is only 2D, in the x and y axis
        s = self.normalize()
        right = s.dot(end.cross((0, 0, -1))) < 0
        left = s.dot(start.cross((0, 0, -1))) > 0
        if (right and left) if end.dot(start.cross((0, 0, -1))) > 0 else (right or left):
            return self
        if start.dot(s) < end.dot(s):
            return end
        return start

    def dist(self, other: Vector3) -> float:
        # Distance between 2 vectors
        return math.sqrt((self[0] - other[0]) ** 2 + (self[1] - other[1]) ** 2 + (self[2] - other[2]) ** 2)

    def flat_dist(self, other: Vector3) -> float:
        # Distance between 2 vectors
        return math.sqrt((self[0] - other[0]) ** 2 + (self[1] - other[1]) ** 2)


class Routine:
    def run(self, drone: CarObject, agent: MyHivemind):
        pass


class Action(Enum):
    Going = 0
    Shadowing = 1
    Boost = 2
    Nothing = 3
    Cheating = 4
    Backpost = 5
