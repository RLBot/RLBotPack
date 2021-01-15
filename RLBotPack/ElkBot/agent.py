from __future__ import annotations

import itertools
import math
import os
import re
from datetime import datetime
from time import time_ns
from traceback import print_exc
from typing import List, Tuple

import numpy as np
from rlbot.agents.base_agent import SimpleControllerState
from rlbot.agents.standalone.standalone_bot import StandaloneBot, run_bot

TOURNAMENT_MODE = False
# Make False to enable hot reloading
EXTRA_DEBUGGING = False

if not TOURNAMENT_MODE:
    from gui import Gui
    from match_comms import MatchComms


class VirxERLU(StandaloneBot):
    # Massive thanks to ddthj/GoslingAgent (GitHub repo) for the basis of VirxERLU
    # VirxERLU on VirxEC Showcase -> https://virxerlu.virxcase.dev/
    # Wiki -> https://github.com/VirxEC/VirxERLU/wiki
    def initialize_agent(self):
        self.tournament = TOURNAMENT_MODE
        self.extra_debugging = EXTRA_DEBUGGING
        self.startup_time = time_ns()
        self.true_name = re.split(r' \(\d+\)$', self.name)[0]

        self.debug = [[], []]
        self.debugging = not self.tournament
        self.debug_lines = True
        self.debug_3d_bool = True
        self.debug_stack_bool = True
        self.debug_2d_bool = False
        self.show_coords = False
        self.debug_ball_path = False
        self.debug_ball_path_precision = 10
        self.disable_driving = False

        T = datetime.now()
        T = T.strftime("%Y-%m-%d %H;%M")

        self.traceback_file = (
            os.getcwd(),
            f"-traceback ({T}).txt"
        )

        if not self.tournament and self.extra_debugging:
            self.gui = Gui(self)
            self.print("Starting the GUI...")
            self.gui.start()

            if self.matchcomms_root is not None:
                self.match_comms = MatchComms(self)
                self.print("Starting the match communication handler...")
                self.match_comms.start()

        self.print("Building game information")

        match_settings = self.get_match_settings()
        mutators = match_settings.MutatorSettings()

        gravity = (
            Vector(z=-650),
            Vector(z=-325),
            Vector(z=-1137.5),
            Vector(z=-3250)
        )

        base_boost_accel = 991 + (2/3)

        boost_accel = (
            base_boost_accel,
            base_boost_accel * 1.5,
            base_boost_accel * 2,
            base_boost_accel * 10
        )

        boost_amount = (
            "default",
            "unlimited",
            "slow recharge",
            "fast recharge",
            "no boost"
        )

        game_mode = (
            "soccer",
            "hoops",
            "dropshot",
            "hockey",
            "rumble",
            "heatseeker"
        )

        self.gravity = gravity[mutators.GravityOption()]
        self.boost_accel = boost_accel[mutators.BoostStrengthOption()]
        self.boost_amount = boost_amount[mutators.BoostOption()]
        self.game_mode = game_mode[match_settings.GameMode()]

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
        self.best_shot_value = 92.75
        self.odd_tick = -1
        self.delta_time = 1 / 120

        self.future_ball_location_slice = 180
        self.balL_prediction_struct = None

    def retire(self):
        # Stop the currently running threads
        if not self.tournament and self.extra_debugging:
            self.gui.stop()

            if self.matchcomms_root is not None:
                self.match_comms.stop()

    def is_hot_reload_enabled(self):
        # The tkinter GUI isn't compatible with hot reloading
        # Use the Continue and Spawn option in the RLBotGUI instead
        return not self.extra_debugging

    def get_ready(self, packet):
        field_info = self.get_field_info()
        self.boosts = tuple(boost_object(i, boost.location, boost.is_full_boost) for i, boost in enumerate(field_info.boost_pads))
        self.refresh_player_lists(packet)
        self.ball.update(packet)

        self.init()

        load_time = (time_ns() - self.startup_time) / 1e+6
        print(f"{self.name}: Built game info in {load_time} milliseconds")

        self.ready = True

    def refresh_player_lists(self, packet):
        # Useful to keep separate from get_ready because humans can join/leave a match
        self.friends = tuple(car_object(i, packet) for i in range(packet.num_cars) if packet.game_cars[i].team is self.team and i != self.index)
        self.foes = tuple(car_object(i, packet) for i in range(packet.num_cars) if packet.game_cars[i].team != self.team)
        self.me = car_object(self.index, packet)

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

    def sphere(self, location, radius, color=None):
        if self.debugging and self.debug_lines:
            x = Vector(x=radius)
            y = Vector(y=radius)
            z = Vector(z=radius)

            diag = Vector(1.0, 1.0, 1.0).scale(radius).x
            d1 = Vector(diag, diag, diag)
            d2 = Vector(-diag, diag, diag)
            d3 = Vector(-diag, -diag, diag)
            d4 = Vector(-diag, diag, -diag)

            self.line(location - x, location + x, color)
            self.line(location - y, location + y, color)
            self.line(location - z, location + z, color)
            self.line(location - d1, location + d1, color)
            self.line(location - d2, location + d2, color)
            self.line(location - d3, location + d3, color)
            self.line(location - d4, location + d4, color)

    def print(self, item):
        if not self.tournament:
            print(f"{self.name}: {item}")

    def dbg_3d(self, item):
        self.debug[0].append(str(item))

    def dbg_2d(self, item):
        self.debug[1].append(str(item))

    def clear(self):
        self.shooting = False
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

        self.delta_time = self.game.time - self.time
        self.time = self.game.time
        self.gravity = self.game.gravity

        # When a new kickoff begins we empty the stack
        if not self.kickoff_flag and self.game.round_active and self.game.kickoff:
            self.kickoff_done = False
            self.clear()

        # Tells us when to go for kickoff
        self.kickoff_flag = self.game.round_active and self.game.kickoff

        self.ball_to_goal = self.friend_goal.location.flat_dist(self.ball.location)

        self.odd_tick += 1

        if self.odd_tick > 3:
            self.odd_tick = 0

        self.ball_prediction_struct = self.get_ball_prediction_struct()

        if self.tournament and self.matchcomms_root is not None:
            while 1:
                try:
                    msg = self.agent.matchcomms.incoming_broadcast.get_nowait()
                except Exception:
                    break
                
                try:
                    self.handle_match_comm(msg)
                except Exception:
                    print_exc()

    def get_output(self, packet):
        try:
            # Reset controller
            self.controller.__init__(use_item=True)

            # Get ready, then preprocess
            if not self.ready:
                self.get_ready(packet)

            self.preprocess(packet)

            if self.me.demolished:
                if not self.is_clear():
                    self.clear()
            elif self.game.round_active:
                stack_routine_name = '' if self.is_clear() else self.stack[0].__class__.__name__
                if stack_routine_name in {'Aerial', 'jump_shot', 'double_jump', 'ground_shot', 'short_shot'}:
                    self.shooting = True
                else:
                    self.shooting = False

                try:
                    self.run()  # Run strategy code; This is a very expensive function to run
                except Exception as e:
                    print(f"ERROR in {self.name}:")
                    print_exc()

                # run the routine on the end of the stack
                if not self.is_clear():
                    try:
                        r_name = self.stack[-1].__class__.__name__
                        self.stack[-1].run(self)
                    except Exception as e:
                        print(f"ERROR in {self.name}:")
                        print_exc()

                if self.debugging:
                    if self.debug_3d_bool:
                        if self.debug_stack_bool:
                            self.debug[0] = itertools.chain(self.debug[0], ("STACK:",), (item.__class__.__name__ for item in reversed(self.stack)))

                        self.renderer.draw_string_3d(tuple(self.me.location), 2, 2, "\n".join(self.debug[0]), self.renderer.team_color(alt_color=True))

                        self.debug[0] = []

                    if self.show_coords:
                        self.debug[1].insert(0, f"Hitbox: [{self.me.hitbox.length} {self.me.hitbox.width} {self.me.hitbox.height}]")
                        self.debug[1].insert(0, f"Location: {round(self.me.location)}")

                        car = self.me
                        center = car.local(car.hitbox.offset) + car.location
                        top = car.up * (car.hitbox.height / 2)
                        front = car.forward * (car.hitbox.length / 2)
                        right = car.right * (car.hitbox.width / 2)

                        bottom_front_right = center - top + front + right
                        bottom_front_left = center - top + front - right
                        bottom_back_right = center - top - front + right
                        bottom_back_left = center - top - front - right
                        top_front_right = center + top + front + right
                        top_front_left = center + top + front - right
                        top_back_right = center + top - front + right
                        top_back_left = center + top - front - right

                        hitbox_color = self.renderer.team_color(alt_color=True)

                        self.polyline((top_back_left, top_front_left, top_front_right, bottom_front_right, bottom_front_left, top_front_left), hitbox_color)
                        self.polyline((bottom_front_left, bottom_back_left, bottom_back_right, top_back_right, top_back_left, bottom_back_left), hitbox_color)
                        self.line(bottom_back_right, bottom_front_right, hitbox_color)
                        self.line(top_back_right, top_front_right, hitbox_color)

                    if self.debug_2d_bool:
                        if self.delta_time != 0:
                            self.debug[1].insert(0, f"TPS: {round(1 / self.delta_time)}")

                        if not self.is_clear() and self.stack[0].__class__.__name__ in {'Aerial', 'jump_shot', 'ground_shot', 'double_jump'}:
                            self.dbg_2d(round(self.stack[0].intercept_time - self.time, 4))

                        self.renderer.draw_string_2d(20, 300, 2, 2, "\n".join(self.debug[1]), self.renderer.team_color(alt_color=True))
                        self.debug[1] = []

                    if self.debug_ball_path and self.ball_prediction_struct is not None:
                        self.polyline(tuple(Vector(ball_slice.physics.location.x, ball_slice.physics.location.y, ball_slice.physics.location.z) for ball_slice in self.ball_prediction_struct.slices[::self.debug_ball_path_precision]))
                else:
                    self.debug = [[], []]

            return SimpleControllerState() if self.disable_driving else self.controller
        except Exception as e:
            print(f"ERROR in {self.name}:")
            print_exc()
            return SimpleControllerState()

    def handle_match_comm(self, msg):
        pass

    def run(self):
        pass

    def handle_quick_chat(self, index, team, quick_chat):
        pass

    def init(self):
        pass


class car_object:
    # The carObject, and kin, convert the gametickpacket in something a little friendlier to use,
    # and are updated by VirxERLU as the game runs
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

            self.name = car.name
            self.true_name = re.split(r' \(\d+\)$', self.name)[0]
            self.team = car.team
            self.hitbox = hitbox_object(car.hitbox.length, car.hitbox.width, car.hitbox.height, Vector(car.hitbox_offset.x, car.hitbox_offset.y, car.hitbox_offset.z))
            self.offset = self.hitbox.offset  # please use self.hitbox.offset and not self.offset
            
            self.update(packet)

            return

        self.name = None
        self.true_name = None
        self.team = -1
        self.hitbox = hitbox_object()
        self.offset = self.hitbox.offset

    def local(self, value):
        # Generic localization
        return self.orientation.dot(value)

    def local_velocity(self, velocity=None):
        # Returns the velocity of an item relative to the car
        # x is the velocity forwards (+) or backwards (-)
        # y is the velocity to the left (+) or right (-)
        # z if the velocity upwards (+) or downwards (-)
        if velocity is None:
            velocity = self.velocity

        return self.local(velocity)

    def local_location(self, location):
        # Returns the location of an item relative to the car
        # x is how far the location is forwards (+) or backwards (-)
        # y is the velocity to the left (+) or right (-)
        # z is how far the location is upwards (+) or downwards (-)
        return self.local(location - self.location)

    def get_raw(self, agent, force_on_ground=False):
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
            self.boost if agent.boost_amount != 'unlimited' else 255,
            self.index,
            tuple(self.hitbox),
            tuple(self.hitbox.offset)
        )

    def update(self, packet):
        car = packet.game_cars[self.index]
        car_phy = car.physics
        self.location = Vector(car_phy.location.x, car_phy.location.y, car_phy.location.z)
        self.velocity = Vector(car_phy.velocity.x, car_phy.velocity.y, car_phy.velocity.z)
        self.orientation = Matrix3(car_phy.rotation.pitch, car_phy.rotation.yaw, car_phy.rotation.roll)
        self.angular_velocity = self.orientation.dot((car_phy.angular_velocity.x, car_phy.angular_velocity.y, car_phy.angular_velocity.z))
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
    def right(self):
        # A vector pointing left relative to the cars orientation. Its magnitude == 1
        return self.orientation.right

    @property
    def up(self):
        # A vector pointing up relative to the cars orientation. Its magnitude == 1
        return self.orientation.up


class hitbox_object:
    def __init__(self, length=0, width=0, height=0, offset=None):
        self.length = length
        self.width = width
        self.height = height

        if offset is None:
            offset = Vector()
        self.offset = offset

    def __getitem__(self, index):
        return (self.length, self.width, self.height)[index]


class last_touch:
    def __init__(self):
        self.location = Vector()
        self.normal = Vector()
        self.time = -1
        self.car = None
    
    def update(self, packet):
        touch = packet.game_ball.latest_touch
        self.location = touch.hit_location
        self.normal = touch.hit_normal
        self.time = touch.time_seconds
        self.car = car_object(touch.player_index, packet)


class ball_object:
    def __init__(self):
        self.location = Vector()
        self.velocity = Vector()
        self.latest_touched_time = 0
        self.latest_touched_team = 0

    def get_raw(self):
        return (
            tuple(self.location),
            tuple(self.velocity)
        )

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
        self.location = Vector(0, team * 5120, 321.3875)  # center of goal line
        # Posts are closer to x=893, but this allows the bot to be a little more accurate
        self.left_post = Vector(team * 800, team * 5120, 321.3875)
        self.right_post = Vector(-team * 800, team * 5120, 321.3875)


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
    def __init__(self, pitch=0, yaw=0, roll=0):
        CP = math.cos(pitch)
        SP = math.sin(pitch)
        CY = math.cos(yaw)
        SY = math.sin(yaw)
        CR = math.cos(roll)
        SR = math.sin(roll)
        # List of 3 vectors, each descriping the direction of an axis: Forward, Left, and Up
        self.data = (
            Vector(CP*CY, CP*SY, SP),
            Vector(CY*SP*SR-CR*SY, SY*SP*SR+CR*CY, -CP*SR),
            Vector(-CR*CY*SP-SR*SY, -CR*SY*SP+SR*CY, CP*CR)
        )
        self.forward, self.right, self.up = self.data

    def __getitem__(self, key):
        return self.data[key]

    def __str__(self):
        return f"[{self.forward}\n{self.right}\n{self.up}]"

    def dot(self, vector):
        return Vector(self.forward.dot(vector), self.right.dot(vector), self.up.dot(vector))

    def det(self):
        return self[0][0] * self[1][1] * self[2][2] + self[0][1] * self[1][2] * self[2][0] + \
               self[0][2] * self[1][0] * self[2][1] - self[0][0] * self[1][2] * self[2][1] - \
               self[0][1] * self[1][0] * self[2][2] - self[0][2] * self[1][1] * self[2][0]


# Vector supports 1D, 2D and 3D Vectors, as well as calculations between them
# Arithmetic with 1D and 2D lists/tuples aren't supported - just set the remaining values to 0 manually
# With this new setup, Vector is much faster because it's just a wrapper for numpy
class Vector:
    def __init__(self, x: float = 0, y: float = 0, z: float = 0):
        # this is a private property - this is so all other things treat this class like a list, and so should you!
        self._np = np.array([x, y, z])

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
        return Vector(*(self._np * -1))

    # self + value
    def __add__(self, value):
        if hasattr(value, "_np"):
            value = value._np
        return Vector(*(self._np+value))
    __radd__ = __add__

    # self - value
    def __sub__(self, value):
        if hasattr(value, "_np"):
            value = value._np
        return Vector(*(self._np-value))

    def __rsub__(self, value):
        return -self + value

    # self * value
    def __mul__(self, value):
        if hasattr(value, "_np"):
            value = value._np
        return Vector(*(self._np*value))
    __rmul__ = __mul__

    # self / value
    def __truediv__(self, value):
        if hasattr(value, "_np"):
            value = value._np
        return Vector(*(self._np/value))

    def __rtruediv__(self, value):
        return self * (1 / value)

    # round(self)
    def __round__(self, decimals=0) -> Vector:
        # Rounds all of the values
        return Vector(*np.around(self._np, decimals=decimals))

    def magnitude(self) -> float:
        # Returns the length of the vector
        return np.linalg.norm(self._np).item()

    def dot(self, value: Vector) -> float:
        # Returns the dot product of two vectors
        if hasattr(value, "_np"):
            value = value._np
        return np.dot(self._np, value).item()

    def cross(self, value: Vector) -> Vector:
        # Returns the cross product of two vectors
        if hasattr(value, "_np"):
            value = value._np
        return Vector(*np.cross(self._np, value))

    def copy(self) -> Vector:
        # Returns a copy of the vector
        return Vector(*self._np)

    def normalize(self, return_magnitude=False) -> List[Vector, float] or Vector:
        # normalize() returns a Vector that shares the same direction but has a length of 1
        # normalize(True) can also be used if you'd like the length of this Vector (used for optimization)
        magnitude = self.magnitude()
        if magnitude != 0:
            norm_vec = Vector(*(self._np / magnitude))
            if return_magnitude:
                return norm_vec, magnitude
            return norm_vec
        if return_magnitude:
            return Vector(), 0
        return Vector()

    def flatten(self) -> Vector:
        # Sets Z (Vector[2]) to 0, making the Vector 2D
        return Vector(self._np[0], self._np[1])

    def angle2D(self, value: Vector) -> float:
        # Returns the 2D angle between this Vector and another Vector in radians
        return self.flatten().angle(value.flatten())

    def angle(self, value: Vector) -> float:
        # Returns the angle between this Vector and another Vector in radians
        return math.acos(max(min(np.dot(self.normalize()._np, value.normalize()._np).item(), 1), -1))

    def rotate(self, angle: float) -> Vector:
        # Rotates this Vector by the given angle in radians
        # Note that this is only 2D, in the x and y axis
        return Vector((math.cos(angle)*self.x) - (math.sin(angle)*self.y), (math.sin(angle)*self.x) + (math.cos(angle)*self.y), self.z)

    def clamp2D(self, start: Vector, end: Vector) -> Vector:
        # Similar to integer clamping, Vector's clamp2D() forces the Vector's direction between a start and end Vector
        # Such that Start < Vector < End in terms of clockwise rotation
        # Note that this is only 2D, in the x and y axis
        s = self.normalize()._np
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
        start_z = min(start.z, end.z)
        end_z = max(start.z, end.z)

        if s.z < start_z:
            s.z = start_z
        elif s.z > end_z:
            s.z = end_z

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
        return Vector(*(max(min(item, high), low) for item in self._np))

    def midpoint(self, value: Vector) -> Vector:
        # Midpoint of the 2 vectors
        if hasattr(value, "_np"):
            value = value._np
        return Vector(*((self._np + value) / 2))

    def scale(self, value: float) -> Vector:
        # Returns a vector that has the same direction but with a value as the magnitude
        return self.normalize() * value
