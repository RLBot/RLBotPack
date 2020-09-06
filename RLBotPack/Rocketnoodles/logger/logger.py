import math
import json

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from RLUtilities.Simulation import Input
from RLUtilities.controller_input import controller


class PythonExample(BaseAgent):

    def __init__(self, name, team, index):
        self.count = 0
        self.recording = False
        self.start_time = 0
        self.outfile = None
        self.frame_info = []

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:

        if controller.L1 == 1:

            if self.recording == False:
                self.frame_info = []
                self.recording = True
                self.start_time = packet.game_info.seconds_elapsed

            self.frame_info.append({
                "time": packet.game_info.seconds_elapsed - self.start_time,
                "ball": {
                    "location": [
                        packet.game_ball.physics.location.x,
                        packet.game_ball.physics.location.y,
                        packet.game_ball.physics.location.z
                    ],
                    "velocity": [
                        packet.game_ball.physics.velocity.x,
                        packet.game_ball.physics.velocity.y,
                        packet.game_ball.physics.velocity.z
                    ],
                    "rotator": [
                        packet.game_ball.physics.rotation.pitch,
                        packet.game_ball.physics.rotation.yaw,
                        packet.game_ball.physics.rotation.roll
                    ],
                    "angular_velocity": [
                        packet.game_ball.physics.angular_velocity.x,
                        packet.game_ball.physics.angular_velocity.y,
                        packet.game_ball.physics.angular_velocity.z
                    ]
                },
                "car": {
                    "location": [
                        packet.game_cars[0].physics.location.x,
                        packet.game_cars[0].physics.location.y,
                        packet.game_cars[0].physics.location.z
                    ],
                    "velocity": [
                        packet.game_cars[0].physics.velocity.x,
                        packet.game_cars[0].physics.velocity.y,
                        packet.game_cars[0].physics.velocity.z
                    ],
                    "rotator": [
                        packet.game_cars[0].physics.rotation.pitch,
                        packet.game_cars[0].physics.rotation.yaw,
                        packet.game_cars[0].physics.rotation.roll
                    ],
                    "angular_velocity": [
                        packet.game_cars[0].physics.angular_velocity.x,
                        packet.game_cars[0].physics.angular_velocity.y,
                        packet.game_cars[0].physics.angular_velocity.z
                    ],
                    "boost": packet.game_cars[0].boost,
                    "jumped": packet.game_cars[0].jumped,
                    "double_jumped": packet.game_cars[0].double_jumped,
                    "is_supersonic": packet.game_cars[0].is_super_sonic,
                    "has_wheel_contact": packet.game_cars[0].has_wheel_contact
                },
                "input": {
                    "throttle": controller.throttle,
                    "steer": controller.steer,
                    "pitch": controller.pitch,
                    "yaw": controller.yaw,
                    "roll": controller.roll,
                    "jump": controller.jump,
                    "boost": controller.boost,
                    "handbrake": controller.handbrake
                }
            })

        else:
            if self.recording == True:
                with open(f"data_{self.count}.json", "w") as outfile:
                    json.dump(self.frame_info, outfile)
                self.recording = False
                self.count += 1

        return controller.get_output()
