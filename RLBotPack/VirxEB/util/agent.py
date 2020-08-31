from __future__ import annotations

import itertools
import math
from time import time_ns
from dataclasses import dataclass
from enum import Enum
from traceback import print_exc
from typing import List, Tuple

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState

from gui import Gui
from match_comms import MatchComms
from prediction import Prediction


class Playstyle(Enum):
    Defensive = -1
    Neutral = 0
    Offensive = 1


class VirxERLU(BaseAgent):
    # Massive thanks to ddthj/GoslingAgent (GitHub repo) for the basis of VirxERLU
    def initialize_agent(self):
        self.tournament = True
        self.startup_time = time_ns()

        self.debug = [[], []]
        self.debugging = not self.tournament
        self.debug_lines = True
        self.debug_3d_bool = True
        self.debug_stack_bool = True
        self.debug_2d_bool = False
        self.show_coords = False
        self.debug_ball_path = False
        self.debug_ball_path_precision = 10
        self.debug_vector = Vector()
        self.disable_driving = False
        self.goalie = False
        self.air_bud = False
        self.aerials = True

        if not self.tournament:
            self.gui = Gui(self)
            self.print("Starting the GUI...")
            self.gui.start()

        self.predictions = {
            "closest_enemy": 0,
            "own_goal": False,
            "goal": False,
            "ball_struct": None,
            "team_from_goal": (),
            "team_to_ball": (),
            "self_from_goal": 0,
            "self_to_ball": 0,
            "was_down": False,
            "done": False
        }

        self.prediction = Prediction(self)
        self.print("Starting the predictive service...")
        self.prediction.start()
        self.match_comms = None

        self.print("Building game information")

        mutators = self.get_match_settings().MutatorSettings()

        gravity = [
            Vector(z=-650),
            Vector(z=-325),
            Vector(z=-1137.5),
            Vector(z=-3250)
        ]

        base_boost_accel = 991 + (2/3)

        boost_accel = [
            base_boost_accel,
            base_boost_accel * 1.5,
            base_boost_accel * 2,
            base_boost_accel * 10
        ]

        self.gravity = gravity[mutators.GravityOption()]
        self.boost_accel = boost_accel[mutators.BoostStrengthOption()]

        self.friends = ()
        self.foes = ()
        self.me = car_object(self.index)
        self.ball_to_goal = -1

        self.ball = ball_object()
        self.game = game_object()

        self.boosts = ()

        self.friend_goal = goal_object(self.team)
        self.foe_goal = goal_object(not self.team)

        self.stack = []
        self.time = 0

        self.ready = False

        self.controller = SimpleControllerState()

        self.kickoff_flag = False
        self.kickoff_done = True
        self.shooting = False
        self.odd_tick = 0
        self.best_shot_value = 92

        self.future_ball_location_slice = 180

        self.playstyles = Playstyle
        self.playstyle = self.playstyles.Neutral
        self.can_shoot = None
        self.shot_weight = -1
        self.shot_time = -1
        self.last_ball_location = Vector(z=93)

    def retire(self):
        # Stop the currently running threads
        if not self.tournament:
            self.gui.stop()

        if len(self.friends) > 0:
            self.match_comms.stop()

        self.prediction.stop()

    @staticmethod
    def is_hot_reload_enabled():
        # The tkinter GUI isn't compatible with hot reloading
        # Use the Continue and Spawn option in the GUI instead
        return False

    def get_ready(self, packet):
        field_info = self.get_field_info()
        self.boosts = tuple(boost_object(i, boost.location, boost.is_full_boost) for i, boost in enumerate(field_info.boost_pads))
        self.refresh_player_lists(packet)
        self.ball.update(packet)

        foe_team = -1 if self.team == 1 else 1
        team = -foe_team

        self.defensive_shots = (
            (self.foe_goal.left_post, self.foe_goal.right_post),
            (Vector(4096, foe_team * 3968, 1900), Vector(2944, foe_team * 5120, 1900)),
            (Vector(-4096, foe_team * 3968, 1900), Vector(-2944, foe_team * 5120, 1900))
        )

        self.panic_shots = (
            (Vector(3100 * team, team * 3620, 1000), Vector(3100 * team, team * 5120, 1000)),
            (Vector(-3100 * team, team * 3620, 1000), Vector(-3100 * team, team * 5120, 1000))
        )

        self.offensive_shots = (
            (self.foe_goal.left_post, self.foe_goal.right_post),
            (Vector(foe_team * 893, foe_team * 5120, 100), Vector(foe_team * 893, foe_team * 4720, 320)),
            (Vector(-foe_team * 893, foe_team * 5120, 100), Vector(-foe_team * 893, foe_team * 4720, 320))
        )

        self.best_shot = (Vector(foe_team * 650, foe_team * 5125, 320), Vector(-foe_team * 650, foe_team * 5125, 320))

        self.max_shot_weight = 4

        self.best_shot_value = round((92.75 + min(self.me.hitbox) / 2) * 0.99, 4)
        self.print(f"Best shot value: {self.best_shot_value}")

        self.init()

        self.ready = True

        load_time = (time_ns() - self.startup_time) / 1e+6
        team = "Blue" if self.team == 0 else "Red"
        print(f"{self.name} ({team}): Built game info in {load_time} milliseconds")

    def refresh_player_lists(self, packet):
        # Useful to keep separate from get_ready because humans can join/leave a match
        self.friends = tuple(car_object(i, packet) for i in range(packet.num_cars) if packet.game_cars[i].team is self.team and i != self.index)
        self.foes = tuple(car_object(i, packet) for i in range(packet.num_cars) if packet.game_cars[i].team != self.team)
        self.me = car_object(self.index, packet)

        if len(self.friends) > 0 and self.match_comms is None:
            self.match_comms = MatchComms(self)
            self.print("Starting the match communication handler...")
            self.match_comms.start()

    def push(self, routine):
        self.stack.append(routine)

    def pop(self):
        return self.stack.pop()

    def line(self, start, end, color=None):
        if self.debugging and self.debug_lines:
            color = color if color is not None else self.renderer.grey()
            self.renderer.draw_line_3d(start.copy(), end.copy(), self.renderer.create_color(255, *color) if type(color) in {list, tuple} else color)

    def polyline(self, vectors, color=None):
        if self.debugging and self.debug_lines:
            color = color if color is not None else self.renderer.grey()
            vectors = tuple(vector.copy() for vector in vectors)
            self.renderer.draw_polyline_3d(vectors, self.renderer.create_color(255, *color) if type(color) in {list, tuple} else color)

    def print(self, item):
        if not self.tournament:
            team = "Blue" if self.team == 0 else "Red"
            print(f"{self.name} ({team}): {item}")

    def dbg_3d(self, item):
        self.debug[0].append(str(item))

    def dbg_2d(self, item):
        self.debug[1].append(str(item))

    def clear(self):
        self.shooting = False
        self.shot_weight = -1
        self.shot_time = -1
        self.stack = []

    def is_clear(self):
        return len(self.stack) < 1

    def preprocess(self, packet):
        if packet.num_cars != len(self.friends)+len(self.foes)+1:
            self.refresh_player_lists(packet)

        set(map(lambda car: car.update(packet), self.friends))
        set(map(lambda car: car.update(packet), self.foes))
        set(map(lambda pad: pad.update(packet), self.boosts))

        self.ball.update(packet)
        self.me.update(packet)
        self.game.update(self.team, packet)
        self.time = self.game.time
        self.gravity = self.game.gravity

        # When a new kickoff begins we empty the stack
        if not self.kickoff_flag and self.game.round_active and self.game.kickoff:
            self.kickoff_done = False
            self.clear()

        # Tells us when to go for kickoff
        self.kickoff_flag = self.game.round_active and self.game.kickoff
        self.ball_to_goal = self.friend_goal.location.flat_dist(self.ball.location)

        self.predictions['ball_struct'] = self.get_ball_prediction_struct()
        self.prediction.event.set()

        self.odd_tick += 1

        if self.odd_tick > 3:
            self.odd_tick = 0

    def get_output(self, packet):
        try:
            # Reset controller
            self.controller.__init__()

            # Get ready, then preprocess
            if not self.ready:
                self.get_ready(packet)

            self.preprocess(packet)

            if self.me.demolished:
                if not self.is_clear():
                    self.clear()
            elif self.game.round_active and self.predictions['done']:
                self.dbg_3d(self.playstyle.name)
                try:
                    self.run()  # Run strategy code; This is a very expensive function to run
                except Exception:
                    print(self.name)
                    print_exc()

                if self.debugging:
                    if self.debug_3d_bool:
                        if self.debug_stack_bool:
                            self.debug[0] = itertools.chain(self.debug[0], ("STACK:",), (item.__class__.__name__ for item in reversed(self.stack)))

                        self.renderer.draw_string_3d(self.me.location.tuple(), 2, 2, "\n".join(self.debug[0]), self.renderer.team_color(alt_color=True))

                        self.debug[0] = []

                    if self.debug_2d_bool:
                        if self.show_coords:
                            self.debug[1].insert(0, str(self.me.location.int()))

                        if not self.is_clear() and self.stack[0].__class__.__name__ in {'Aerial', 'jump_shot', 'block_ground_shot', 'double_jump'}:
                            self.dbg_2d(round(self.stack[0].intercept_time - self.time, 4))

                        self.renderer.draw_string_2d(20, 300, 2, 2, "\n".join(self.debug[1]), self.renderer.team_color(alt_color=True))
                        self.debug[1] = []

                    if self.debug_ball_path and self.predictions['ball_struct'] is not None:
                        self.polyline(tuple(Vector(ball_slice.physics.location.x, ball_slice.physics.location.y, ball_slice.physics.location.z) for ball_slice in self.predictions['ball_struct'].slices[::self.debug_ball_path_precision]))
                else:
                    self.debug = [[], []]

                # run the routine on the end of the stack
                if not self.is_clear():
                    self.stack[-1].run(self)

                if self.is_clear() or self.stack[0].__class__.__name__ not in {'Aerial', 'jump_shot', 'block_ground_shot', 'double_jump'}:
                    self.shooting = False
                    self.shot_weight = -1
                    self.shot_time = -1

            return SimpleControllerState() if self.disable_driving else self.controller
        except Exception:
            print(self.name)
            print_exc()
            return SimpleControllerState()

    def handle_match_comm(self, msg):
        pass

    def test(self):
        pass

    def run(self):
        pass

    def handle_quick_chat(self, index, team, quick_chat):
        pass

    def init(self):
        pass


class car_object:
    # The carObject, and kin, convert the gametickpacket in something a little friendlier to use,
    # and are updated by GoslingAgent as the game runs
    def __init__(self, index, packet=None):
        self.location = Vector()
        self.orientation = Matrix3()
        self.velocity = Vector()
        self.angular_velocity = Vector()
        self.demolished = False
        self.airborne = False
        self.supersonic = False
        self.jumped = False
        self.doublejumped = False
        self.boost = 0
        self.index = index

        if packet is not None:
            car = packet.game_cars[self.index]
            self.hitbox = hitbox_object(car.hitbox.length, car.hitbox.width, car.hitbox.height)
            self.offset = Vector(car.hitbox_offset.x, car.hitbox_offset.y, car.hitbox_offset.z)
            self.update(packet)
        else:
            self.hitbox = hitbox_object()
            self.offset = Vector()

    def local(self, value):
        # Generic localization
        return self.orientation.dot(value)

    def local_velocity(self, velocity=None):
        # Returns the velocity of an item relative to the car
        # x is the velocity forwards (+) or backwards (-)
        # y is the velocity to the left (-) or right (+)
        # z if the velocity upwards (+) or downwards (-)
        if velocity is None:
            velocity = self.velocity

        return self.local(velocity)

    def local_location(self, location):
        # Returns the location of an item relative to the car
        # x is how far the location is forwards (+) or backwards (-)
        # y is how far the location is to the left (-) or right (+)
        # z is how far the location is upwards (+) or downwards (-)
        return self.local(location - self.location)

    def update(self, packet):
        car = packet.game_cars[self.index]
        self.location = Vector(car.physics.location.x, car.physics.location.y, car.physics.location.z)
        self.velocity = Vector(car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z)
        self.orientation = Matrix3(car.physics.rotation.pitch, car.physics.rotation.yaw, car.physics.rotation.roll)
        self.angular_velocity = self.orientation.dot(car.physics.angular_velocity)
        self.demolished = car.is_demolished
        self.airborne = not car.has_wheel_contact
        self.supersonic = car.is_super_sonic
        self.jumped = car.jumped
        self.doublejumped = car.double_jumped
        self.boost = car.boost

    @property
    def forward(self):
        # A vector pointing forwards relative to the cars orientation. Its magnitude == 1
        return self.orientation.forward

    @property
    def left(self):
        # A vector pointing left relative to the cars orientation. Its magnitude == 1
        return self.orientation.left

    @property
    def up(self):
        # A vector pointing up relative to the cars orientation. Its magnitude == 1
        return self.orientation.up


class hitbox_object:
    def __init__(self, length=0, width=0, height=0):
        self.length = length
        self.width = width
        self.height = height

    def __getitem__(self, index):
        return (self.length, self.width, self.height)[index]


class ball_object:
    def __init__(self):
        self.location = Vector()
        self.velocity = Vector()
        self.latest_touched_time = 0
        self.latest_touched_team = 0

    def update(self, packet):
        ball = packet.game_ball
        self.location = Vector(ball.physics.location.x, ball.physics.location.y, ball.physics.location.z)
        self.velocity = Vector(ball.physics.velocity.x, ball.physics.velocity.y, ball.physics.velocity.z)
        self.latest_touched_time = ball.latest_touch.time_seconds
        self.latest_touched_team = ball.latest_touch.team


class boost_object:
    def __init__(self, index, location, large):
        self.index = index
        self.location = Vector(location.x, location.y, location.z)
        self.active = True
        self.large = large

    def update(self, packet):
        self.active = packet.game_boosts[self.index].is_active


class goal_object:
    # This is a simple object that creates/holds goalpost locations for a given team (for soccer on standard maps only)
    def __init__(self, team):
        team = 1 if team == 1 else -1
        self.location = Vector(0, team * 5120, 320)  # center of goal line
        # Posts are closer to x=893, but this allows the bot to be a little more accurate
        self.left_post = Vector(team * 800, team * 5125, 320)
        self.right_post = Vector(-team * 800, team * 5125, 320)


class game_object:
    # This object holds information about the current match
    def __init__(self):
        self.time = 0
        self.time_remaining = 0
        self.overtime = False
        self.round_active = False
        self.kickoff = False
        self.match_ended = False
        self.friend_score = 0
        self.foe_score = 0
        self.gravity = Vector()

    def update(self, team, packet):
        game = packet.game_info
        self.time = game.seconds_elapsed
        self.time_remaining = game.game_time_remaining
        self.overtime = game.is_overtime
        self.round_active = game.is_round_active
        self.kickoff = game.is_kickoff_pause
        self.match_ended = game.is_match_ended
        self.friend_score = packet.teams[team].score
        self.foe_score = packet.teams[not team].score
        self.gravity.z = game.world_gravity_z


class Matrix3:
    # The Matrix3's sole purpose is to convert roll, pitch, and yaw data from the gametickpacket into an orientation matrix
    # An orientation matrix contains 3 Vector's
    # Matrix3[0] is the "forward" direction of a given car
    # Matrix3[1] is the "left" direction of a given car
    # Matrix3[2] is the "up" direction of a given car
    # If you have a distance between the car and some object, ie ball.location - car.location,
    # you can convert that to local coordinates by dotting it with this matrix
    # ie: local_ball_location = Matrix3.dot(ball.location - car.location)
    def __init__(self, pitch=0, yaw=0, roll=0):
        CP = math.cos(pitch)
        SP = math.sin(pitch)
        CY = math.cos(yaw)
        SY = math.sin(yaw)
        CR = math.cos(roll)
        SR = math.sin(roll)
        # List of 3 vectors, each descriping the direction of an axis: Forward, Left, and Up
        self.data = [
            Vector(CP*CY, CP*SY, SP),
            Vector(CY*SP*SR-CR*SY, SY*SP*SR+CR*CY, -CP*SR),
            Vector(-CR*CY*SP-SR*SY, -CR*SY*SP+SR*CY, CP*CR)
        ]
        self.forward, self.left, self.up = self.data

    def __getitem__(self, key):
        return self.data[key]

    def dot(self, vector):
        return Vector(self.forward.dot(vector), self.left.dot(vector), self.up.dot(vector))


# With this new setup, Vector supports 1D, 2D and 3D Vectors, as well as calculations between them
@dataclass
class Vector:
    # These values can be ints or floats, with their defaults being 0
    # This means that Vector3(0, 0, 0) is now Vector()
    x: float = 0
    y: float = 0
    z: float = 0

    def __eq__(self, value):
        # Vector's can be compared with:
        # - Another Vector, in which case True will be returned if they have the same values
        # - A list/tuple, in which case True will be returned if they have the same values
        # - A single value, in which case True will be returned if the Vector's length matches the value
        if hasattr(value, "x"):
            return self.tuple() == (value.x, value.y, value.z)

        if isinstance(value, tuple):
            return self.tuple() == value

        if isinstance(value, list):
            return self.list() == value

        return self.magnitude() == value

    def __getitem__(self, value):
        return self.tuple()[value]

    def __str__(self):
        # Vector's can be printed to console
        return f"({self.x}, {self.y}, {self.z})"

    def __add__(self, value):
        if hasattr(value, "x"):
            return Vector(self.x+value.x, self.y+value.y, self.z+value.z)
        return Vector(self.x+value, self.y+value, self.z+value)
    __radd__ = __add__

    def __sub__(self, value):
        if hasattr(value, "x"):
            return Vector(self.x-value.x, self.y-value.y, self.z-value.z)
        return Vector(self.x-value, self.y-value, self.z-value)
    __rsub__ = __sub__

    def __neg__(self):
        return Vector(-self.x, -self.y, -self.z)

    def __mul__(self, value):
        if hasattr(value, "x"):
            return Vector(self.x*value.x, self.y*value.y, self.z*value.z)
        return Vector(self.x*value, self.y*value, self.z*value)
    __rmul__ = __mul__

    def __truediv__(self, value):
        if hasattr(value, "x"):
            return Vector(self.x/value.x, self.y/value.y, self.z/value.z)
        return Vector(self.x/value, self.y/value, self.z/value)
    __rtruediv__ = __truediv__

    def int(self) -> Vector:
        return Vector(int(self.x), int(self.y), int(self.z))

    def tuple(self) -> Tuple[float]:
        return (self.x, self.y, self.z)

    def list(self) -> List[float]:
        return [self.x, self.y, self.z]

    # Linear algebra functions

    def magnitude(self) -> float:
        # Magnitude() returns the length of the vector
        return math.sqrt(self.dot(self))

    def normalize(self, return_magnitude=False) -> List[Vector, float] or Vector:
        # Normalize() returns a Vector that shares the same direction but has a length of 1
        # Normalize(True) can also be used if you'd like the length of this Vector (used for optimization)
        magnitude = self.magnitude()
        if magnitude != 0:
            if return_magnitude:
                return Vector(self.x/magnitude, self.y/magnitude, self.z/magnitude), magnitude
            return Vector(self.x/magnitude, self.y/magnitude, self.z/magnitude)
        if return_magnitude:
            return Vector(), 0
        return Vector()

    def dot(self, value: Vector) -> float:
        return self.x*value.x + self.y*value.y + self.z*value.z

    def cross(self, value: Vector) -> Vector:
        return Vector((self.y*value.z) - (self.z*value.y), (self.z*value.x) - (self.x*value.z), (self.x*value.y) - (self.y*value.x))

    def flatten(self) -> Vector:
        # Sets Z (Vector[2]) to 0, making the Vector 2D
        return Vector(self.x, self.y, 0)

    def copy(self) -> Vector:
        # Returns a copy of this Vector
        return Vector(*self.tuple())

    def angle2D(self, value: Vector) -> float:
        # Returns the 2D angle between this Vector and another Vector in radians
        return self.flatten().angle(value.flatten())

    def angle(self, value: Vector) -> Vector:
        # Returns the angle between this Vector and another Vector in radians
        return math.acos(max(min(self.normalize().dot(value.normalize()), 1), -1))

    def rotate(self, angle: float) -> Vector:
        # Rotates this Vector by the given angle in radians
        # Note that this is only 2D, in the x and y axis
        return Vector((math.cos(angle)*self.x) - (math.sin(angle)*self.y), (math.sin(angle)*self.x) + (math.cos(angle)*self.y), self.z)

    def clamp2D(self, start: Vector, end: Vector) -> Vector:
        # Similar to integer clamping, Vector's clamp2D() forces the Vector's direction between a start and end Vector
        # Such that Start < Vector < End in terms of clockwise rotation
        # Note that this is only 2D, in the x and y axis
        s = self.normalize()
        right = s.dot(end.cross(Vector(z=-1))) < 0
        left = s.dot(start.cross(Vector(z=-1))) > 0
        if (right and left) if end.dot(start.cross(Vector(z=-1))) > 0 else (right or left):
            return self
        if start.dot(s) < end.dot(s):
            return end
        return start

    def clamp(self, start: Vector, end: Vector) -> Vector:
        # This extends clamp2D so it also clamps the vector's z
        s = self.clamp2D(start, end)
        start_z = min(start.z, end.z)
        end_z = max(start.z, end.z)

        if s.z < start_z:
            s.z = start_z
        elif s.z > end_z:
            s.z = end_z

        return s

    def dist(self, value: Vector) -> float:
        # Distance between 2 vectors
        return (self - value).magnitude()

    def flat_dist(self, value: Vector) -> float:
        # Distance between 2 vectors on a 2D plane
        return value.flatten().dist(self.flatten())

    def cap(self, low: float, high: float) -> Vector:
        # Caps all values in a Vector between 'low' and 'high'
        return Vector(*(max(min(item, high), low) for item in self.tuple()))
