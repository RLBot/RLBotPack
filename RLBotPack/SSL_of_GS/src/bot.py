from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState
import random, math


class MyBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()
        self.travel_distance = 0
        self.pos = Vec3(0, 0, 0)

    def initialize_agent(self):
        # Set up information about the boost pads now that the game is active and the info is available
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:

        self.boost_pad_tracker.update_boost_status(packet)

        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls
        
        def predict_ball(t):
            ball_in_future = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + t)
            if ball_in_future is not None:
                return ball_in_future
            else:
                return packet.game_ball
        
        def intersect_time(speed):
            best_spd = math.inf
            for i in range(1, 301):
                time_location = Vec3(predict_ball(i / 60).physics.location)
                if (time_location - car_location).length() * 60 / i <= speed:
                    return i / 60
            return 5

        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)
        ball_location_gs = Vector3(packet.game_ball.physics.location)
        ball_velocity = Vec3(packet.game_ball.physics.velocity)
        ball_prediction = self.get_ball_prediction_struct()
        target_location = ball_location
        send_location = Vec3(0, 10240 * (0.5 - self.team), 300)
        if car_location.z == 0:
            self.pos = car_location

        self.renderer.draw_line_3d(self.pos, (target_location - self.pos) / (target_location - self.pos).length() * self.travel_distance, self.renderer.white())
        self.renderer.draw_string_3d(self.pos, 1, 1, f'Speed: {car_velocity.length():.1f}', self.renderer.white())
        self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)

        controls = SimpleControllerState()
        controls.steer = steer_toward_target(my_car, target_location)
        controls.throttle = 0
        if packet.game_info.is_round_active == True:
            self.travel_distance += 2300 / 60
        else:
            self.travel_distance = 0
        if (self.pos - ball_location).length() <= self.travel_distance and ball_location.y / send_location.y <= 1:
            ball_velout = -ball_velocity
            v = -(ball_location - send_location) / (ball_location - send_location).length() * 2300
            tp = (ball_velout + v) / (ball_velout + v).length() * 2300
            p = ball_location - tp / tp.length() * 100
            self.travel_distance = 0
            # Intentional weakness
            if random.random() <= 0.125:
                side = random.choice([1, -1])
                p = ball_location + Vec3(-v.x * side, 0, v.z * side) / 2300 * 150
                self.travel_distance = -11500
            car_state = CarState(physics = Physics(location = Vector3(p.x, p.y, p.z), velocity = Vector3(v.x, v.y, v.z)))
            gs = GameState(cars={self.index: car_state})
            self.set_game_state(gs)
            self.pos = Vec3(packet.game_cars[self.index].physics.location)
        elif packet.game_info.is_round_active == True and self.travel_distance >= 0:
            p = self.pos + (ball_location - self.pos) / (ball_location - self.pos).length() * (self.travel_distance - 200)
            car_state = CarState(physics = Physics(location = Vector3(p.x, p.y, p.z), velocity = Vector3(0, 0, 0)))
            gs = GameState(cars={self.index: car_state})
            self.set_game_state(gs)
        else:
            self.pos = Vec3(packet.game_cars[self.index].physics.location)
        if packet.game_info.is_round_active == False:
            self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Compliments_WhatASave)
        return controls
