import math
import random
from time import sleep

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, CarState, Physics, Vector3, BallState, Rotator

from vec import Vec3


class Tron(BaseScript):
    def __init__(self):
        super().__init__("SideSwipe")
        self.is_kickoff = False
        self.is_replay = True
        self.last_score = (0, 0)

    def run(self):
        while True:
            packet = self.wait_game_tick_packet()

            ball_pos = Vec3(packet.game_ball.physics.location)

            car_states = {}
            for index in range(packet.num_cars):
                car = packet.game_cars[index]
                pos = Vec3(car.physics.location)
                vel = Vec3(car.physics.velocity)
                new_pos = pos.yz()
                new_vel = vel.yz()
                car_state = CarState(Physics(location=new_pos.desired(), velocity=new_vel.desired()))
                car_states[index] = car_state

            if ball_pos.x == 0 and ball_pos.y == 0 and 90 < ball_pos.z < 96 and packet.game_info.is_kickoff_pause:
                # Kickoff
                if not self.is_kickoff:
                    # It was not kickoff previous frame

                    car_states = self.setup_kickoff(packet)

                self.is_kickoff = True
                self.is_replay = False
            else:
                self.is_kickoff = False

            ball = packet.game_ball
            pos = Vec3(ball.physics.location)
            vel = Vec3(ball.physics.velocity)

            ball_state = BallState(Physics(location=pos.yz().desired(), velocity=vel.yz().desired()))

            game_state = GameState(cars=car_states, ball=ball_state)
            if not self.is_replay:
                self.set_game_state(game_state)

            new_score = (packet.teams[0].score, packet.teams[1].score)
            if new_score != self.last_score:
                self.is_replay = True
                self.last_score = new_score

    def setup_kickoff(self, packet):

        kickoff_pos_mapping = [
            # Normal, new as dist
            (Vec3(2048, -2560), 3000),  # Left corner
            (Vec3(-2048, -2560), 3500),  # Right corner
            (Vec3(256.0, -3840), 4000),  # Back left
            (Vec3(-256.0, -3840), 4500),  # Back right
            (Vec3(0, -4608), 5000),  # Far back
        ]

        car_states = {}
        for index in range(packet.num_cars):
            car = packet.game_cars[index]
            tsign = 1 if car.team == 0 else -1
            for (kickoff_pos, dist) in kickoff_pos_mapping:
                car_pos = tsign * Vec3(car.physics.location.x, car.physics.location.y)
                if (car_pos - kickoff_pos).shorter_than(20):
                    new_pos = Vec3(0, -tsign * dist, 25)
                    break

            yaw = tsign * math.pi / 2.0

            car_state = CarState(Physics(location=new_pos.desired(), rotation=Rotator(yaw=yaw)))
            car_states[index] = car_state
        return car_states


if __name__ == "__main__":
    script = Tron()
    script.run()
