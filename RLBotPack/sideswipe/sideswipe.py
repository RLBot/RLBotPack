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
        indexes = list(range(5))
        index_shuffle_table = {}
        for i in range(5):
            s = random.choice(indexes)
            indexes.remove(s)
            index_shuffle_table[i] = s

        next_blue = 0
        next_orange = 0
        car_states = {}
        for index in range(packet.num_cars):
            car = packet.game_cars[index]
            pos_index = index_shuffle_table[next_blue] if car.team == 0 else index_shuffle_table[next_orange]
            y = 5000 - pos_index * 500

            if car.team == 0:
                kickoff_pos = Vec3(0, -y, 25)
                yaw = math.pi / 2.0
                next_blue += 1
            else:
                kickoff_pos = Vec3(0, y, 25)
                yaw = -math.pi / 2.0
                next_orange += 1

            car_state = CarState(Physics(location=kickoff_pos.desired(), rotation=Rotator(yaw=yaw)))
            car_states[index] = car_state
        return car_states


if __name__ == "__main__":
    script = Tron()
    script.run()
