import math
import numpy as np

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState


# Extending the BaseScript class is purely optional. It's just convenient / abstracts you away from
# some strange classes like GameInterface
class FiftyFiftyMiniGame(BaseScript):
    def __init__(self):
        super().__init__("FiftyFiftyMiniGame")
        self.game_phase = 0
        self.goal_scored = 0
        self.scoreDiff_prev = 0
        self.prev_ticks = 0
        self.ticks = 0


    def run(self):
        while True:
            # when packet available
            packet = self.wait_game_tick_packet()

            # updating packet and tick count
            packet = self.get_game_tick_packet()
            self.ticks += 1

            # phase 0: setup round
            if self.game_phase == 0 and packet.game_info.is_kickoff_pause:
                self.setup_newround(packet)
                self.game_phase = 1

            # same as above, but custom built for 'disable goal reset'
            self.setup_newround_DGR(packet)

            # phase 1: ball remains in circle
            if self.game_phase == 1 and np.linalg.norm(np.array([packet.game_ball.physics.location.x, packet.game_ball.physics.location.y, packet.game_ball.physics.location.z]) - np.array([0, 0, 97])) > 1200:
                phase2_time = packet.game_info.seconds_elapsed
                self.game_phase = 2

            # phase 2: after ball has left circle, next touch wins. Increment score and reset phase
            if self.game_phase == 2 and packet.game_ball.latest_touch.time_seconds > phase2_time:
                if packet.game_ball.latest_touch.team == 0:
                    ball_y_side = 1
                else:
                    ball_y_side = -1
                ball_state = BallState(Physics(location=Vector3(0, 5500 * ball_y_side, 325)))
                self.set_game_state(GameState(ball=ball_state))
                self.game_phase = 0
            
            # phase 2(special case): when goal scored with no further touches, increment score and reset phase
            if self.game_phase == 2 and packet.game_info.is_kickoff_pause and packet.game_ball.latest_touch.time_seconds <= phase2_time:
                self.game_phase = 0


    def setup_newround_DGR(self, packet):
        # check if goal in last tick
        teamScores = tuple(map(lambda x: x.score, packet.teams))
        scoreDiff = max(teamScores) - min(teamScores)

        # setup round and pause
        if self.game_phase == 0 and scoreDiff != self.scoreDiff_prev:                  
            self.setup_newround(packet)
            self.scoreDiff_prev = scoreDiff
            self.prev_ticks = self.ticks
            self.game_phase = -1
            self.set_game_state(GameState(game_info=GameInfoState(paused=True)))
            
        # wait then resume
        if self.game_phase == -1 and self.ticks - self.prev_ticks == 60:
            self.set_game_state(GameState(game_info=GameInfoState(paused=False)))
            self.game_phase = 1


    def setup_newround(self, packet):
        car_states = {}
        for p in range(packet.num_cars):
            car = packet.game_cars[p]
            if car.team == 0:
                yaw = math.pi / 2.0
                car_state = CarState(boost_amount=100, physics=Physics(location=Vector3(0, -1000, 17), rotation=Rotator(yaw=yaw, pitch=0, roll=0), velocity=Vector3(0, 0, 0),
                        angular_velocity=Vector3(0, 0, 0)))
                car_states[p] = car_state
            elif car.team == 1:
                yaw = math.pi / -2.0
                car_state = CarState(boost_amount=100, physics=Physics(location=Vector3(0, 1000, 17), rotation=Rotator(yaw=yaw, pitch=0, roll=0), velocity=Vector3(0, 0, 0),
                        angular_velocity=Vector3(0, 0, 0)))
                car_states[p] = car_state
        ball_state = BallState(Physics(location=Vector3(0, 0, 97)))
        game_state = GameState(ball=ball_state, cars=car_states)
        self.set_game_state(game_state)

# You can use this __name__ == '__main__' thing to ensure that the script doesn't start accidentally if you
# merely reference its module from somewhere
if __name__ == "__main__":
    script = FiftyFiftyMiniGame()
    script.run()
