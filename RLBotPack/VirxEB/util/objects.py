import itertools
import math
from dataclasses import dataclass
from enum import Enum
from traceback import print_exc
from typing import SupportsFloat

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState

from gui import Gui
from util.prediction import Prediction


class Playstyle(Enum):
    Defensive = -1
    Neutral = 0
    Offensive = 1


class GoslingAgent(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.print("Initalizing 2 threads...")
        self.gui = Gui(self)
        self.prediction = Prediction(self)

    def initialize_agent(self):
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
        self.game = game_object(not self.team)

        self.boosts = ()

        self.friend_goal = goal_object(self.team)
        self.foe_goal = goal_object(not self.team)

        self.stack = []
        self.time = 0

        self.ready = False

        self.controller = SimpleControllerState()

        self.kickoff_flag = False
        self.kickoff_done = False

        self.last_time = 0
        self.my_score = 0
        self.foe_score = 0

        self.playstyles = Playstyle
        self.playstyle = self.playstyles.Neutral

        self.can_shoot = None
        self.shooting = False
        self.shot_weight = -1
        self.shot_time = -1
        self.panic = False

        self.odd_tick = 0  # Use this for thing that can be run at 30 or 60 tps instead of 120

        self.debug = [[], []]
        self.debugging = False
        self.debug_lines = True
        self.debug_3d_bool = True
        self.debug_stack_bool = True
        self.debug_2d_bool = False
        self.show_coords = False
        self.debug_ball_path = False
        self.debug_ball_path_precision = 10

        self.disable_driving = False

        self.print("Starting the GUI...")
        self.gui.start()

        self.print("Starting the predictive service...")
        self.predictions = {
            "closest_enemy": 0,
            "own_goal": False,
            "goal": False,
            "ball_struct": None,
            "teammates_from_goal": (),
            "teammates_to_ball": (),
            "self_from_goal": 0,
            "self_to_ball": 0
        }

        self.prediction.start()

    @staticmethod
    def is_hot_reload_enabled():
        return True

    def get_ready(self, packet):
        field_info = self.get_field_info()
        self.boosts = tuple(boost_object(i, boost.location, boost.is_full_boost) for i, boost in enumerate(field_info.boost_pads))
        self.refresh_player_lists(packet)
        self.ball.update(packet)

        foe_team = -1 if self.team == 1 else 1

        self.defensive_shots = (
            (
                (self.foe_goal.left_post, self.foe_goal.right_post),  # Weight -> 3
                (Vector(3100, foe_team * 3250, 100), Vector(2900, foe_team * 3250, 100)),  # Weight -> 2
                (Vector(-3100, foe_team * 3250, 100), Vector(-2900, foe_team * 3250, 100)),  # Weight -> 2
            ),
            (
                (Vector(-3600, z=100), Vector(-2900, z=100)),  # Weight -> 1
                (Vector(3600, z=100), Vector(2900, z=100)),  # Weight -> 1
            )
        )

        # (self.friend_goal.right_post, self.friend_goal.left_post) => Weight -> 0
        # Short short => Weight -> -1

        self.offensive_shots = (
            (self.foe_goal.left_post, self.foe_goal.right_post),  # Weight -> 3
            (Vector(foe_team * 893, foe_team * 5120, 100), Vector(foe_team * 893, foe_team * 4720, 320)),  # Weight -> 2
            (Vector(-foe_team * 893, foe_team * 5120, 100), Vector(-foe_team * 893, foe_team * 4720, 320))  # Weight -> 2
        )

        self.max_shot_weight = 3

        self.init()

        self.ready = True

    def refresh_player_lists(self, packet):
        # Useful to keep separate from get_ready because humans can join/leave a match
        self.friends = tuple(car_object(i, packet) for i in range(packet.num_cars) if packet.game_cars[i].team is self.team and i != self.index)
        self.foes = tuple(car_object(i, packet) for i in range(packet.num_cars) if packet.game_cars[i].team != self.team)

    def push(self, routine):
        self.stack.append(routine)

    def pop(self):
        return self.stack.pop()

    def line(self, start, end, color=None):
        if self.debugging and self.debug_lines:
            color = color if color is not None else self.renderer.grey()

            if isinstance(start, Vector):
                start = start.copy().tuple()

            if isinstance(end, Vector):
                end = end.copy().tuple()

            self.renderer.draw_line_3d(start, end, color if type(color) != list else self.renderer.create_color(255, *color))

    def print(self, item):
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
        self.game.update(packet)
        self.time = self.game.time

        # When a new kickoff begins we empty the stack
        if not self.kickoff_flag and self.game.round_active and self.game.kickoff:
            self.kickoff_done = False
            self.clear()

        # Tells us when to go for kickoff
        self.kickoff_flag = self.game.round_active and self.game.kickoff
        self.ball_to_goal = self.friend_goal.location.flat_dist(self.ball.location)

        if self.odd_tick % 2 == 0:  # This is ran @ 60 tps
            self.predictions['ball_struct'] = self.get_ball_prediction_struct()

        if self.odd_tick == 0:  # This is ran @ 30 tps
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

            if self.game.round_active:
                self.run()  # Run strategy code; This is a very expensive function to run

                # run the routine on the end of the stack
                if not self.is_clear():
                    self.stack[-1].run(self)

            if self.debugging:
                if self.debug_3d_bool:
                    if self.debug_stack_bool:
                        self.debug[0] = itertools.chain(self.debug[0], ("STACK:",), (item.__class__.__name__ for item in reversed(self.stack)))

                    self.renderer.draw_string_3d(self.me.location.tuple(), 2, 2, "\n".join(self.debug[0]), self.renderer.team_color(alt_color=True))

                    self.debug[0] = []

                if self.debug_2d_bool:
                    if self.show_coords:
                        self.debug[1].insert(0, str(self.me.location.int()))

                    self.renderer.draw_string_2d(20, 300, 2, 2, "\n".join(self.debug[1]), self.renderer.team_color(alt_color=True))
                    self.debug[1] = []
            else:
                self.debug = [[], []]

            if self.disable_driving:
                return SimpleControllerState()
            else:
                return self.controller
        except Exception as err:
            print(err)
            print_exc()
            return SimpleControllerState()

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
        self.orientation = Matrix3(0, 0, 0)
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
            self.update(packet)

    def local(self, value):
        return self.orientation.dot(value)

    def update(self, packet):
        car = packet.game_cars[self.index]
        self.location.x, self.location.y, self.location.z = car.physics.location.x, car.physics.location.y, car.physics.location.z
        self.velocity.x, self.velocity.y, self.velocity.z = car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z
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


class ball_object:
    def __init__(self):
        self.location = Vector()
        self.velocity = Vector()
        self.latest_touched_time = 0
        self.latest_touched_team = 0

    def update(self, packet):
        ball = packet.game_ball
        self.location.x, self.location.y, self.location.z = ball.physics.location.x, ball.physics.location.y, ball.physics.location.z
        self.velocity.x, self.velocity.y, self.velocity.z = ball.physics.velocity.x, ball.physics.velocity.y, ball.physics.velocity.z
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
        self.location = Vector(0, team * 5100, 320)  # center of goal line
        # Posts are closer to x=750, but this allows the bot to be a little more accurate
        self.left_post = Vector(team * 725, team * 5100, 320)
        self.right_post = Vector(-team * 725, team * 5100, 320)


class game_object:
    # This object holds information about the current match
    def __init__(self, team):
        self.time = 0
        self.time_remaining = 0
        self.overtime = False
        self.round_active = False
        self.kickoff = False
        self.match_ended = False

        team_side = 1 if team == 1 else -1
        self.foe_left_field = Vector(team_side * 800, team_side * 5200, 320)
        self.foe_right_field = Vector(-team_side * 800, team_side * 5200, 320)

    def update(self, packet):
        game = packet.game_info
        self.time = game.seconds_elapsed
        self.time_remaining = game.game_time_remaining
        self.overtime = game.is_overtime
        self.round_active = game.is_round_active
        self.kickoff = game.is_kickoff_pause
        self.match_ended = game.is_match_ended


class Matrix3:
    # The Matrix3's sole purpose is to convert roll, pitch, and yaw data from the gametickpaket into an orientation matrix
    # An orientation matrix contains 3 Vector's
    # Matrix3[0] is the "forward" direction of a given car
    # Matrix3[1] is the "left" direction of a given car
    # Matrix3[2] is the "up" direction of a given car
    # If you have a distance between the car and some object, ie ball.location - car.location,
    # you can convert that to local coordinates by dotting it with this matrix
    # ie: local_ball_location = Matrix3.dot(ball.location - car.location)
    def __init__(self, pitch, yaw, roll):
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


# With this new setup, Vector supports 2D and 3D Vectors, as well as calculations between them
@dataclass
class Vector:
    # These values can be ints or floats, with thier defaults being 0
    # This means that Vector3(0, 0, 0) is now Vector()
    x: SupportsFloat = 0
    y: SupportsFloat = 0
    z: SupportsFloat = 0

    def __eq__(self, value):
        # Vector's can be compared with:
        # - Another Vector, in which case True will be returned if they have the same values
        # - A list/tuple, in which case True will be returned if they have the same values
        # - A single value, in which case True will be returned if the Vector's length matches the value
        if hasattr(value, "x"):
            return self.tuple() == (value.x, value.y, value.z)

        if isinstance(value, list) or isinstance(value, tuple):
            return self.tuple() == value

        return self.magnitude() == value

    # Vector's support most operators (+-*/)
    # If using an operator with another Vector, each dimension will be independent
    # ie x+x, y+y, z+z
    # If using an operator with only a value, each dimension will be affected by that value
    # ie x+v, y+v, z+v

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

    def __rtruediv__(self, value):
        if hasattr(value, "x"):
            return Vector(value.x/self.x, value.y/self.y, value.z/self.z)
        raise TypeError("unsupported rtruediv operands")

    def int(self):
        return Vector(int(self.x), int(self.y), int(self.z))

    def tuple(self):
        return (self.x, self.y, self.z)

    def list(self):
        return [self.x, self.y, self.z]

    def magnitude(self):
        # Magnitude() returns the length of the vector
        return math.sqrt((self.x ** 2) + (self.y ** 2) + (self.z ** 2))

    def normalize(self, return_magnitude=False):
        # Normalize() returns a Vector that shares the same direction but has a length of 1.0
        # Normalize(True) can also be used if you'd like the length of this Vector (used for optimization)
        magnitude = self.magnitude()
        if magnitude != 0:
            if return_magnitude:
                return Vector(self.x/magnitude, self.y/magnitude, self.z/magnitude), magnitude
            return Vector(self.x/magnitude, self.y/magnitude, self.z/magnitude)
        if return_magnitude:
            return Vector(), 0
        return Vector()

    def norm(self):
        # Returns the Euclidean length of the given vector
        # This isn't related to normalize!
        return math.sqrt(self.dot(self))

    # Linear algebra functions

    def dot(self, value):
        return self.x*value.x + self.y*value.y + self.z*value.z

    def cross(self, value):
        return Vector((self.y*value.z) - (self.z*value.y), (self.z*value.x) - (self.x*value.z), (self.x*value.y) - (self.y*value.x))

    def flatten(self):
        # Sets Z (Vector[2]) to 0, making the Vector 2D
        return Vector(self.x, self.y, 0)

    def render(self):
        # Returns a list with the x and y values, to be used with pygame
        return (self.x, self.y)

    def copy(self):
        # Returns a copy of this Vector
        return Vector(*self.tuple())

    def angle(self, value):
        # Returns the 2D angle between this Vector and another Vector
        return math.acos(round(self.flatten().normalize().dot(value.flatten().normalize()), 4))

    def angle3D(self, value):
        # Returns the angle between this Vector and another Vector
        # return math.acos(round(self.normalize().dot(value.normalize()), 4))
        return math.acos(max(min(self.normalize().dot(value.normalize()), 1), -1))

    def rotate(self, angle):
        # Rotates this Vector by the given angle in radians
        # Note that this is only 2D, in the x and y axis
        return Vector((math.cos(angle)*self.x) - (math.sin(angle)*self.y), (math.sin(angle)*self.x) + (math.cos(angle)*self.y), self.z)

    def clamp(self, start, end):
        # Similar to integer clamping, Vector's clamp() forces the Vector's direction between a start and end Vector
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

    def dist(self, value):
        # Distance between 2 vectors
        return (self - value).magnitude()

    def flat_dist(self, value):
        # Distance between 2 vectors on a 2D plane
        return value.flatten().dist(self.flatten())

    def cap(self, low, high):
        # Caps all values in a Vector between 'low' and 'high'
        return Vector(*(max(min(item, high), low) for item in self.tuple()))
