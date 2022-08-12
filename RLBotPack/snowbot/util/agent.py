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
from rlbot.messages.flat import MatchSettings
from rlbot.utils.structures.game_data_struct import GameTickPacket

# If you're putting your bot in the botpack, or submitting to a tournament, make this True!
TOURNAMENT_MODE = False

# Make False to enable hot reloading, at the cost of the GUI
EXTRA_DEBUGGING = True

if not TOURNAMENT_MODE and EXTRA_DEBUGGING:
    from gui import Gui


class VirxERLU(StandaloneBot):
    # Massive thanks to ddthj/GoslingAgent (GitHub repo) for the basis of VirxERLU
    # VirxERLU on VirxEC Showcase -> https://virxerlu.virxcase.dev/
    # Wiki -> https://github.com/VirxEC/VirxERLU/wiki
    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.tournament = TOURNAMENT_MODE
        self.extra_debugging = EXTRA_DEBUGGING
        self.true_name = re.split(r' \(\d+\)$', self.name)[0]

        self.debug = [[], []]
        self.debugging = not self.tournament
        self.debug_lines = True
        self.debug_3d_bool = True
        self.debug_stack_bool = True
        self.debug_2d_bool = self.name == self.true_name
        self.show_coords = False
        self.debug_ball_path = False
        self.debug_ball_path_precision = 10
        self.disable_driving = False

    def initialize_agent(self):
        self.startup_time = time_ns()

        T = datetime.now()
        T = T.strftime("%Y-%m-%d %H;%M")

        error_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "errors")

        if not os.path.isdir(error_folder):
            os.mkdir(error_folder)

        self.traceback_file = (
            os.path.join(error_folder),
            f"-traceback ({T}).txt"
        )

        if not self.tournament and self.extra_debugging:
            self.gui = Gui(self)
            self.print("Starting the GUI...")
            self.gui.start()

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
        self.ball_radius = 92.75

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
        self.odd_tick = -1
        self.delta_time = 1 / 120
        self.last_sent_tmcp_packet = None
        # self.sent_tmcp_packet_times = {}

        self.future_ball_location_slice = 180
        self.balL_prediction_struct = None

    def retire(self):
        # Stop the currently running threads
        if not self.tournament and self.extra_debugging:
            self.gui.stop()

    def is_hot_reload_enabled(self):
        # The tkinter GUI isn't compatible with hot reloading
        # Use the Continue and Spawn option in the RLBotGUI instead
        return not self.extra_debugging

    def get_ready(self, packet):
        field_info = self.get_field_info()
        self.boosts = tuple(boost_object(i, field_info.boost_pads[i].location, field_info.boost_pads[i].is_full_boost) for i in range(field_info.num_boosts))
        if len(self.boosts) != 34:
            print(f"There are {len(self.boosts)} boost pads! @Tarehart REEEEE!")
            for i, boost in enumerate(self.boosts):
                print(f"{boost.location} ({i})")

        self.refresh_player_lists(packet)
        self.ball.update(packet)

        self.init()

        load_time = (time_ns() - self.startup_time) / 1e+6
        print(f"{self.name}: Built game info in {load_time} milliseconds")

        self.ready = True

    def refresh_player_lists(self, packet):
        match_settings = self.get_match_settings()
        # Useful to keep separate from get_ready because humans can join/leave a match
        self.friends = tuple(car_object(i, packet) for i in range(packet.num_cars) if packet.game_cars[i].team is self.team and i != self.index)
        self.foes = tuple(car_object(i, packet) for i in range(packet.num_cars) if packet.game_cars[i].team != self.team)
        self.me = car_object(self.index, packet)

        try:
            true_name = match_settings.PlayerConfigurations(self.index).Name()
            self.true_name = true_name
        except Exception:
            print(f"{self.name}: I appear to have been forcefully pushed into a match! How rude.")

    def push(self, routine):
        self.stack.append(routine)

    def pop(self):
        return self.stack.pop()

    def line(self, start, end, color=None):
        if self.debugging and self.debug_lines:
            self.renderer.begin_rendering()
            color = color if color is not None else self.renderer.grey()
            self.renderer.draw_line_3d(start.copy(), end.copy(), self.renderer.create_color(255, *color) if type(color) in {list, tuple} else color)
            self.renderer.end_rendering()

    def polyline(self, vectors, color=None):
        if self.debugging and self.debug_lines:
            self.renderer.begin_rendering()
            color = color if color is not None else self.renderer.grey()
            vectors = tuple(vector.copy() for vector in vectors)
            self.renderer.draw_polyline_3d(vectors, self.renderer.create_color(255, *color) if type(color) in {list, tuple} else color)
            self.renderer.end_rendering()

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

    def preprocess(self, packet: GameTickPacket):
        if packet.num_cars != len(self.friends)+len(self.foes)+1 or self.odd_tick == 0:
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

        self.ball_radius = self.ball.shape.hitbox.diameter if self.ball.shape.type in {1, 2} else (sum(self.ball.shape.hitbox.length, self.ball.shape.hitbox.width, self.ball.shape.hitbox.height) / 3)
        self.ball_radius /= 2

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

        if self.matchcomms_root is not None:
            while 1:
                try:
                    msg = self.matchcomms.incoming_broadcast.get_nowait()
                except Exception:
                    break

                try:
                    if msg.get('tmcp_version') is not None:
                        if msg.get("team") == self.team and msg.get("index") != self.index:
                            self.handle_tmcp_packet(msg)
                    else:
                        self.handle_match_comm(msg)
                except Exception:
                    print_exc()

    def is_shooting(self):
        stack_routine_name = '' if self.is_clear() else self.stack[0].__class__.__name__
        return stack_routine_name in {'Aerial', 'jump_shot', 'double_jump', 'ground_shot', 'short_shot'}

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
                self.shooting = self.is_shooting()

                try:
                    self.run()  # Run strategy code; This is a very expensive function to run
                except Exception:
                    t_file = os.path.join(self.traceback_file[0], self.name+self.traceback_file[1])
                    print(f"ERROR in {self.name}; see '{t_file}'")
                    print_exc(file=open(t_file, "a"))

                try:
                    tmcp_packet = self.create_tmcp_packet()

                    # if we haven't sent a packet, OR
                    # the last packet we sent isn't out current packet AND either the action types are different OR either the time difference is greater than 0.1 or target is different
                    if self.last_sent_tmcp_packet is None or self.tmcp_packet_is_different(tmcp_packet):
                        self.matchcomms.outgoing_broadcast.put_nowait(tmcp_packet)
                        self.last_sent_tmcp_packet = tmcp_packet

                        # t = math.floor(self.time)
                        # if self.sent_tmcp_packet_times.get(t) is None:
                        #     self.sent_tmcp_packet_times[t] = 1
                        # else:
                        #     self.sent_tmcp_packet_times[t] += 1
                except Exception:
                    t_file = os.path.join(self.traceback_file[0], self.name+"-TMCP"+self.traceback_file[1])
                    print(f"ERROR in {self.name} with sending TMCP packet; see '{t_file}'")
                    print_exc(file=open(t_file, "a"))

                # run the routine on the end of the stack
                if not self.is_clear():
                    try:
                        r_name = self.stack[-1].__class__.__name__
                        self.stack[-1].run(self)
                    except Exception:
                        t_file = os.path.join(self.traceback_file[0], r_name+self.traceback_file[1])
                        print(f"ERROR in {self.name}'s {r_name} routine; see '{t_file}'")
                        print_exc(file=open(t_file, "a"))

                if self.debugging:
                    self.renderer.begin_rendering()
                    if self.debug_3d_bool:
                        if self.debug_stack_bool:
                            self.debug[0] = itertools.chain(self.debug[0], ("STACK:",), (item.__class__.__name__ for item in reversed(self.stack)))

                        self.renderer.draw_string_3d(tuple(self.me.location), 2, 2, "\n".join(self.debug[0]), self.renderer.team_color(alt_color=True))

                    if self.show_coords:
                        car = self.me

                        self.debug[1].insert(0, f"Hitbox: {round(self.me.hitbox)}")
                        self.debug[1].insert(0, f"Location: {round(self.me.location)}")

                        center = car.location
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
                        # if len(self.sent_tmcp_packet_times) > 0:
                        #     avg_tmcp_packets = sum(self.sent_tmcp_packet_times.values()) / len(self.sent_tmcp_packet_times)

                        #     self.debug[1].insert(0, f"Avg. TMCP packets / sec: {avg_tmcp_packets}")

                        if self.delta_time != 0:
                            self.debug[1].insert(0, f"TPS: {round(1 / self.delta_time)}")

                        if not self.is_clear() and self.stack[0].__class__.__name__ in {'Aerial', 'jump_shot', 'ground_shot', 'double_jump'}:
                            self.dbg_2d(round(self.stack[0].intercept_time - self.time, 4))

                        self.renderer.draw_string_2d(20, 300, 2, 2, "\n".join(self.debug[1]), self.renderer.team_color(alt_color=True))

                    if self.debug_ball_path and self.ball_prediction_struct is not None:
                        self.polyline(tuple(Vector(ball_slice.physics.location.x, ball_slice.physics.location.y, ball_slice.physics.location.z) for ball_slice in self.ball_prediction_struct.slices[::self.debug_ball_path_precision]))
                    self.renderer.end_rendering()

                self.debug = [[], []]

            return SimpleControllerState() if self.disable_driving else self.controller
        except Exception:
            t_file = os.path.join(self.traceback_file[0], "VirxERLU"+self.traceback_file[1])
            print(f"ERROR with VirxERLU in {self.name}; see '{t_file}' and please report the bug at 'https://github.com/VirxEC/VirxERLU/issues'")
            print_exc(file=open(t_file, "a"))
            return SimpleControllerState()

    def get_minimum_game_time_to_ball(self):
        # It is recommended that you override this
        return -1

    def tmcp_packet_is_different(self, tmcp_packet):
        # If you're looking to overwrite this, you might want to do a version check

        # If the packets are the same
        if self.last_sent_tmcp_packet == tmcp_packet:
            return False

        action_type = tmcp_packet["action"]["type"]

        # if the action types aren't the same
        if self.last_sent_tmcp_packet["action"]["type"] != action_type:
            return True

        if action_type == "BALL":
            dir1 = Vector(*self.last_sent_tmcp_packet["action"]["direction"])
            dir2 = Vector(*tmcp_packet["action"]["direction"])
            return abs(self.last_sent_tmcp_packet["action"]["time"] - tmcp_packet["action"]["time"]) >= 0.1 or dir1.magnitude() != dir2.magnitude() or dir1.angle(dir2) > 0.5

        if action_type == "READY":
            return abs(self.last_sent_tmcp_packet["action"]["time"] - tmcp_packet["action"]["time"]) >= 0.1

        if action_type == "BOOST":
            return self.last_sent_tmcp_packet["action"]["target"] != tmcp_packet["action"]["target"]

        if action_type == "DEMO":
            return abs(self.last_sent_tmcp_packet["action"]["time"] - tmcp_packet["action"]["time"]) >= 0.1 or self.last_sent_tmcp_packet["action"]["target"] != tmcp_packet["action"]["target"]

        # Right now, this is only for DEFEND
        return False

    def create_tmcp_packet(self):
        # https://github.com/RLBot/RLBot/wiki/Team-Match-Communication-Protocol
        # don't worry about duplicate packets - this is handled automatically
        tmcp_packet = {
            "tmcp_version": [1, 0],
            "index": self.index,
            "team": self.team
        }

        # If you're looking to overwrite this, you might want to do a version check

        if self.is_clear():
            tmcp_packet["action"] = {
                "type": "READY",
                "time": -1
            }
            return tmcp_packet

        stack_routine_name = self.stack[0].__class__.__name__

        if stack_routine_name in {'Aerial', 'jump_shot', 'ground_shot', 'double_jump', 'short_shot'}:
            tmcp_packet["action"] =  {
                "type": "BALL",
                "time": -1 if stack_routine_name == 'short_shot' else self.stack[0].intercept_time,
                "direction": [0, 0, 0] if stack_routine_name == 'short_shot' or self.stack[0].shot_vector is None else list(self.stack[0].shot_vector)
            }
            return tmcp_packet

        if stack_routine_name == "goto_boost":
            tmcp_packet["action"] = {
                "type": "BOOST",
                "target": self.stack[0].boost.index
            }
            return tmcp_packet

        # by default, VirxERLU can't demo bots
        tmcp_packet["action"] = {
            "type": "READY",
            "time": self.get_minimum_game_time_to_ball()
        }
        return tmcp_packet

    @DeprecationWarning
    def get_tmcp_action(self, tmcp_version):
        # don't use this - overwrite create_tmcp_packet instead
        return None

    def handle_tmcp_packet(self, packet):
        # https://github.com/RLBot/RLBot/wiki/Team-Match-Communication-Protocol

        for friend in self.friends:
            if friend.index == packet['index']:
                friend.tmcp_action = packet['action']

    def handle_match_comm(self, msg):
        pass

    def run(self):
        pass

    def handle_quick_chat(self, index, team, quick_chat):
        pass

    def init(self):
        pass


class car_object:
    # objects convert the gametickpacket in something a little friendlier to use
    # and are automatically updated by VirxERLU as the game runs
    def __init__(self, index, packet=None, match_settings: MatchSettings=None):
        self.location = Vector()
        self.orientation = Matrix3()
        self.velocity = Vector()
        self._local_velocity = Vector()
        self.angular_velocity = Vector()
        self.demolished = False
        self.airborne = False
        self.supersonic = False
        self.jumped = False
        self.doublejumped = False
        self.boost = 0
        self.index = index
        self.tmcp_action = None
        self.true_name = None
        self.land_time = 0

        if match_settings is not None:
            try:
                self.true_name = match_settings.PlayerConfigurations(index).Name()
            except Exception:
                pass

        if packet is not None:
            car = packet.game_cars[self.index]

            self.name = car.name
            if self.true_name is None: self.true_name = re.split(r' \(\d+\)$', self.name)[0]  # e.x. 'ABot (12)' will instead be just 'ABot'
            self.team = car.team
            self.hitbox = hitbox_object(car.hitbox.length, car.hitbox.width, car.hitbox.height, Vector(car.hitbox_offset.x, car.hitbox_offset.y, car.hitbox_offset.z))

            self.update(packet)

            return

        self.name = None
        self.true_name = None
        self.team = -1
        self.hitbox = hitbox_object()

    def local(self, value):
        # Generic localization
        return self.orientation.dot(value)

    def global_(self, value):
        # Converts a localized vector to a global vector
        return self.orientation.g_dot(value)

    def local_velocity(self, velocity=None):
        # Returns the velocity of an item relative to the car
        # x is the velocity forwards (+) or backwards (-)
        # y is the velocity to the right (+) or left (-)
        # z if the velocity upwards (+) or downwards (-)
        if velocity is None:
            return self._local_velocity

        return self.local(velocity)

    def local_location(self, location):
        # Returns the location of an item relative to the car
        # x is how far the location is forwards (+) or backwards (-)
        # y is the velocity to the right (+) or left (-)
        # z is how far the location is upwards (+) or downwards (-)
        return self.local(location - self.location)

    def global_location(self, location):
        # Converts a localized location to a global location
        return self.global_(location) + self.location

    def local_flatten(self, value):
        # Flattens a vector relative to the car
        return self.global_(self.local(value).flatten())

    def local_flatten_location(self, location):
        # Flattens a location relative to the car
        return self.global_location(self.local_location(location).flatten())

    def get_raw(self, agent, force_on_ground=False):
        return (
            tuple(self.location),
            tuple(self.velocity),
            (tuple(self.forward), tuple(self.right), tuple(self.up)),
            tuple(self.angular_velocity),
            int(self.demolished),
            int(self.airborne and not force_on_ground),
            int(self.supersonic),
            int(self.jumped),
            int(self.doublejumped),
            self.boost if agent.boost_amount != 'unlimited' else 255,
            self.index,
            tuple(self.hitbox),
            tuple(self.hitbox.offset)
        )

    def update(self, packet: GameTickPacket):
        car = packet.game_cars[self.index]
        car_phy = car.physics
        self.location = Vector.from_vector(car_phy.location)
        self.velocity = Vector.from_vector(car_phy.velocity)
        self._local_velocity = self.local(self.velocity)
        self.orientation = Matrix3.from_rotator(car_phy.rotation)
        self.angular_velocity = self.orientation.dot((car_phy.angular_velocity.x, car_phy.angular_velocity.y, car_phy.angular_velocity.z))
        self.demolished = car.is_demolished
        self.airborne = not car.has_wheel_contact
        self.supersonic = car.is_super_sonic
        self.jumped = car.jumped
        self.doublejumped = car.double_jumped
        self.boost = car.boost

        if self.airborne and car.has_wheel_contact:
            self.land_time = packet.game_info.seconds_elapsed

    @property
    def rotation(self):
        return self.orientation.rotation

    @property
    def pitch(self):
        return self.orientation.pitch

    @property
    def yaw(self):
        return self.orientation.yaw

    @property
    def roll(self):
        return self.orientation.roll

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

    # len(self)
    def __len__(self):
        return 3  # this is a 3 dimensional vector, so we return 3

    # str(self)
    def __str__(self):
        # Vector's can be printed to console
        return f"[{self.length} {self.width} {self.height}]"

    # repr(self)
    def __repr__(self):
        return f"hitbox_object(length={self.length}, width={self.width}, height={self.height})"

    # round(self)
    def __round__(self, decimals=0) -> hitbox_object:
        # Rounds all of the values
        return hitbox_object(*(round(euler_angle) for euler_angle in self))


class hitbox_sphere:
    def __init__(self, diameter=92.75):
        self.diameter = diameter


class hitbox_cylinder:
    def __init__(self, diameter=92.75, height=92.75):
        self.diameter = diameter
        self.height = height


class last_touch:
    def __init__(self):
        self.location = Vector()
        self.normal = Vector()
        self.time = -1
        self.car = None

    def update(self, packet):
        touch = packet.game_ball.latest_touch
        self.location = Vector.from_vector(touch.hit_location)
        self.normal = Vector.from_vector(touch.hit_normal)
        self.time = touch.time_seconds
        self.car = car_object(touch.player_index, packet)


class ball_shape:
    def __init__(self):
        self.type = -1
        self.hitbox = None

    def update(self, packet: GameTickPacket):
        shape = packet.game_ball.collision_shape
        self.type = shape.type

        if self.type == 0:
            self.hitbox = hitbox_object(shape.box.length, shape.box.width, shape.box.height)
        elif self.type == 1:
            self.hitbox = hitbox_sphere(shape.sphere.diameter)
        elif self.type == 2:
            self.hitbox = hitbox_cylinder(shape.cylinder.diameter, shape.cylinder.height)


class ball_object:
    def __init__(self):
        self.location = Vector()
        self.velocity = Vector()
        self.last_touch = last_touch()
        self.shape = ball_shape()

    def get_raw(self):
        return (
            tuple(self.location),
            tuple(self.velocity)
        )

    def update(self, packet: GameTickPacket):
        ball = packet.game_ball
        self.location = Vector.from_vector(ball.physics.location)
        self.velocity = Vector.from_vector(ball.physics.velocity)
        self.last_touch.update(packet)
        self.shape.update(packet)


class boost_object:
    def __init__(self, index, location, large):
        self.index = index
        self.location = Vector.from_vector(location)
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
        self.game_speed = 1

    def update(self, team, packet: GameTickPacket):
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
        self.game_speed = game.game_speed


class Matrix3:
    # The Matrix3's sole purpose is to convert roll, pitch, and yaw data from the gametickpacket into an orientation matrix
    # An orientation matrix contains 3 Vector's
    # Matrix3[0] is the "forward" direction of a given car
    # Matrix3[1] is the "right" direction of a given car
    # Matrix3[2] is the "up" direction of a given car
    # If you have a distance between the car and some object, ie ball.location - car.location,
    # you can convert that to local coordinates by dotting it with this matrix
    # ie: local_ball_location = Matrix3.dot(ball.location - car.location)
    # to convert from local coordinates back to global coordinates:
    # global_ball_location = Matrix3.g_dot(local_ball_location) + car_location
    def __init__(self, pitch=0, yaw=0, roll=0, simple=False):
        self.pitch = pitch
        self.yaw = yaw
        self.roll = roll

        if simple:
            self._np = np.array(((0, 0, 0), (0, 0, 0), (0, 0, 0)))
            self.rotation = (Vector(), Vector(), Vector())
            return

        CP = math.cos(self.pitch)
        SP = math.sin(self.pitch)
        CY = math.cos(self.yaw)
        SY = math.sin(self.yaw)
        CR = math.cos(self.roll)
        SR = math.sin(self.roll)
        # List of 3 vectors, each descriping the direction of an axis: Forward, Left, and Up
        self._np = np.array((
            (CP*CY, CP*SY, SP),
            (CY*SP*SR-CR*SY, SY*SP*SR+CR*CY, -CP*SR),
            (-CR*CY*SP-SR*SY, -CR*SY*SP+SR*CY, CP*CR)
        ))

        self.rotation = tuple(Vector(*item) for item in self._np)

    @property
    def forward(self):
        return self.rotation[0]

    @property
    def right(self):
        return self.rotation[1]

    @property
    def up(self):
        return self.rotation[2]

    @DeprecationWarning
    @property
    def data(self):
        return self.rotation

    def __getitem__(self, key):
        return self.rotation[key]

    def __str__(self):
        return f"[{self.forward}\n {self.right}\n {self.up}]"

    @staticmethod
    def from_rotator(rotator) -> Matrix3:
        return Matrix3(rotator.pitch, rotator.yaw, rotator.roll)

    @staticmethod
    def from_direction(direction: Vector, up: Vector) -> Matrix3:
        # once again, big thanks to Chip and his RLU
        # https://github.com/samuelpmish/RLUtilities/blob/develop/inc/linear_algebra/math.h

        mat = Matrix3(simple=True)
        forward = direction.normalize()
        up = forward.cross(up.cross(forward)).normalize()
        right = up.cross(forward).normalize()

        # generate the orientation matrix
        mat._np = np.array((tuple(forward), tuple(right), tuple(up)))
        mat.rotation = (forward, right, up)

        # generate the pitch/yaw/roll
        mat.pitch = math.atan2(mat.forward.z, Vector(mat.forward.x, mat.forward.y).magnitude())
        mat.yaw = math.atan2(mat.forward.y, mat.forward.x)
        mat.roll = math.atan2(-mat.right.z, mat.up.z)

        return mat

    def dot(self, vec: Vector) -> Vector:
        if hasattr(vec, "_np"):
            vec = vec._np
        return Vector(np_arr=self._np.dot(vec))

    def g_dot(self, vec: Vector) -> Vector:
        if hasattr(vec, "_np"):
            vec = vec._np
        return Vector(np_arr=self._np[0].dot(vec[0]) + self._np[1].dot(vec[1]) + self._np[2].dot(vec[2]))

    def det(self):
        return np.linalg.det(self._np).item()

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
        return Vector(*(max(min(item, high), low) for item in self._np))

    def midpoint(self, value: Vector) -> Vector:
        # Midpoint of the 2 vectors
        if hasattr(value, "_np"):
            value = value._np
        return Vector(np_arr=(self._np + value) / 2)

    def scale(self, value: float) -> Vector:
        # Returns a vector that has the same direction but with a value as the magnitude
        return self.normalize() * value
