import traceback
import random
from typing import Dict
from rlbot.agents.hivemind.drone_agent import DroneAgent
from rlbot.agents.hivemind.python_hivemind import PythonHivemind
from rlbot.utils.structures.bot_input_struct import PlayerInput
from rlbot.utils.structures.game_data_struct import GameTickPacket

# Dummy agent to call request MyHivemind.
from gamemodes import run_1v1, run_hivemind
from objects import CarObject, BoostObject, BallObject, GoalObject, GameObject, Vector3
from utils import distance


class Drone(DroneAgent):
    hive_path = __file__
    hive_key = 'TheGame'
    hive_name = 'Reddit'


class MyHivemind(PythonHivemind):

    def __init__(self, agent_metadata_queue, quit_event, options):
        super().__init__(agent_metadata_queue, quit_event, options)
        self.logger.info('Initialised!')
        self.team: int = -1

        # A list of cars for both teammates and opponents
        self.friends: [CarObject] = []
        self.foes: [CarObject] = []
        # This holds the carobjects for our agent
        self.drones: [CarObject] = []
        self.ball: BallObject = BallObject()
        self.game: GameObject = GameObject()
        # A list of boosts
        self.boosts: [BoostObject] = []
        # goals
        self.friend_goal: GoalObject = None
        self.foe_goal: GoalObject = None
        # Game time
        self.time: float = 0.0
        self.odd_tick = 0
        # Whether or not GoslingAgent has run its get_ready() function
        self.ready: bool = False
        # a flag that tells us when kickoff is happening
        self.kickoff_flag: bool = False
        self.prev_kickoff_flag: bool = False
        self.conceding: bool = False
        # If true we will go for more stuff
        # Initialized as true since we are always desperate
        self.desperate = False

    def initialize_hive(self, packet: GameTickPacket) -> None:
        # Find out team by looking at packet.
        # drone_indices is a set, so you cannot just pick first element.
        index = next(iter(self.drone_indices))
        self.team = packet.game_cars[index].team
        self.drones = [CarObject(i, packet) for i in self.drone_indices]
        # goals
        self.friend_goal = GoalObject(self.team)
        self.foe_goal = GoalObject(not self.team)

    def get_ready(self, packet: GameTickPacket):
        # Preps all of the objects that will be updated during play
        field_info = self.get_field_info()
        for i in range(field_info.num_boosts):
            boost = field_info.boost_pads[i]
            self.boosts.append(BoostObject(i, boost.location, boost.is_full_boost))
        self.refresh_player_lists(packet)
        self.ball.update(packet)
        self.ready = True

    def refresh_player_lists(self, packet: GameTickPacket):
        # makes new friend/foe lists
        # Useful to keep separate from get_ready because humans can join/leave a match
        drone_indices = [drone.index for drone in self.drones]
        self.friends = [CarObject(i, packet) for i in range(packet.num_cars) if
                        packet.game_cars[i].team == self.team and i not in drone_indices]
        self.foes = [CarObject(i, packet) for i in range(packet.num_cars) if packet.game_cars[i].team != self.team]

    def line(self, start: Vector3, end: Vector3, color=None):
        color = color if color is not None else self.renderer.grey()
        self.renderer.draw_line_3d(start.copy(), end.copy(),
                                   self.renderer.create_color(255, *color) if type(color) in {list, tuple} else color)

    def preprocess(self, packet: GameTickPacket):
        # Calling the update functions for all of the objects
        if packet.num_cars != len(self.friends) + len(self.foes) + len(self.drones):
            self.refresh_player_lists(packet)
        for car in self.friends:
            car.update(packet)
        for car in self.foes:
            car.update(packet)
        for pad in self.boosts:
            pad.update(packet)
        for drone in self.drones:
            drone.update(packet)
        self.desperate = sum([car.goals for car in self.foes]) > sum([car.goals for car in self.friends]) + 1
        self.ball.update(packet)
        self.game.update(packet)
        self.time = packet.game_info.seconds_elapsed
        self.odd_tick += 1
        if self.odd_tick > 3:
            self.odd_tick = 0
        self.prev_kickoff_flag = self.kickoff_flag
        self.kickoff_flag = self.game.kickoff and self.game.round_active
        if not self.prev_kickoff_flag and self.kickoff_flag:
            for drone in self.drones:
                drone.clear()
        for drone in self.drones:
            drone.on_side = (drone.location - self.friend_goal.location).magnitude() < (
                    self.ball.location - self.friend_goal.location).magnitude()
            drone.ball_prediction_struct = self.get_ball_prediction_struct()
        for friend in self.friends:
            friend.on_side = (friend.location - self.friend_goal.location).magnitude() < (
                    self.ball.location - self.friend_goal.location).magnitude()
        for foe in self.foes:
            foe.on_side = (foe.location - self.friend_goal.location).magnitude() < (
                    self.ball.location - self.friend_goal.location).magnitude()
        ball = self.ball.location
        sorted_by_dist = sorted([*self.friends, *self.drones], key=lambda bot: distance(bot.location, ball))
        sorted_by_dist_on_side = [bot for bot in sorted_by_dist if bot.on_side]
        if len(sorted_by_dist_on_side) > 0:
            sorted_by_dist_on_side[0].closest = True
        if len(sorted_by_dist_on_side) > 1:
            sorted_by_dist_on_side[1].second_closest = True
        self.conceding = False
        ball_prediction = self.get_ball_prediction_struct()
        for i in range(ball_prediction.num_slices):
            prediction_slice = ball_prediction.slices[i]
            physics = prediction_slice.physics
            if physics.location.y * self.side() > 5120:
                self.conceding = True
                break
        # Tells us when to go for kickoff

    def get_outputs(self, packet: GameTickPacket) -> Dict[int, PlayerInput]:
        # Get ready, then preprocess
        if not self.ready:
            self.get_ready(packet)
        self.preprocess(packet)
        self.renderer.begin_rendering()
        # Run our strategy code
        self.run()
        # run the routine on the end of the stack
        for drone in self.drones:
            if len(drone.stack) > 0:
                drone.stack[-1].run(drone, self)
        self.renderer.end_rendering()
        # send our updated controller back to rlbot
        # return self.controller
        return {drone.index: drone.controller for drone in self.drones}

    def debug_stack(self):
        # Draws the stack on the screen
        white = self.renderer.white()
        offset = 0
        for i in range(len(self.drones)):
            self.renderer.draw_string_2d(10, 50 + 50 * offset, 3, 3, "Drone: " + str(i), white)
            offset += 1
            for j in range(len(self.drones[i].stack) - 1, -1, -1):
                text = self.drones[i].stack[j].__class__.__name__
                self.renderer.draw_string_2d(10, 50 + 50 * offset, 3, 3, text, white)
                offset += 1

    def run(self):
        # Used to run test scenerio's
        # if self.game.round_active:
        #     run_test(self)
        if len(self.drones) == 1 and len(self.friends) == 0:
            run_1v1(self)
        else:
            run_hivemind(self)

    def side(self) -> float:
        # returns -1 for blue team and 1 for orange team
        if self.team == 0:
            return -1
        return 1
