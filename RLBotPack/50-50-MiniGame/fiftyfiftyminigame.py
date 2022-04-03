import numpy as np

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState


class FiftyFiftyMiniGame(BaseScript):
    '''
    FiftyFiftyMiniGame is a RLBot script
    the goal it to be the first to touch the ball outside the center circle
    it is designed for 1v1 and works best with the 'disable goal reset' mutator active
    both players spawn in the center circle with a slightly randomized rotation
    '''
    def __init__(self):
        super().__init__("FiftyFiftyMiniGame")
        self.game_phase = 0
        self.goal_scored = 0
        self.scoreDiff_prev = 0
        self.prev_ticks = 0
        self.ticks = 0
        self.disable_goal_reset = False
        self.pause_time = 0.5 # Can increase to 1-2s if hard coded kickoffs are causing issues
        self.cur_time = 0
        self.first_kickoff = True

    def run(self):
        while True:
            # when packet available
            packet = self.wait_game_tick_packet()

            # updating packet and tick count
            packet = self.get_game_tick_packet()
            self.cur_time = packet.game_info.seconds_elapsed
            self.ticks += 1

            # check if 'disable goal reset' mutator is active
            if self.ticks == 1:
                match_settings = self.get_match_settings()
                mutators = match_settings.MutatorSettings()
                if mutators.RespawnTimeOption() == 3:
                    self.disable_goal_reset = True

            '''phase 0''' # setup round
            if self.game_phase == 0 and packet.game_info.is_kickoff_pause:
                self.setup_newround(packet)

            # same as above, but custom built for 'disable goal reset' mutator active
            if self.disable_goal_reset == True:
                self.setup_newround_DGR(packet)

            # pause for 'pause_time' then resume
            if self.game_phase == -1 and self.cur_time - self.prev_time < self.pause_time:
                self.set_game_state(self.game_state)
            elif self.game_phase == -1:
                self.game_phase = 1

            '''phase 1''' # ball remains in circle
            if self.game_phase == 1 and np.linalg.norm(np.array([packet.game_ball.physics.location.x, packet.game_ball.physics.location.y, packet.game_ball.physics.location.z]) - np.array([0, 0, 97])) > 1200:
                phase2_time = packet.game_info.seconds_elapsed
                self.game_phase = 2

            '''phase 2''' # after ball leaves circle, next touch wins. Increment score and reset phase
            if self.game_phase == 2 and packet.game_ball.latest_touch.time_seconds > phase2_time:
                if packet.game_ball.latest_touch.team == 0:
                    ball_y_side = 1
                else:
                    ball_y_side = -1
                ball_state = BallState(Physics(location=Vector3(0, 5500 * ball_y_side, 325)))
                self.set_game_state(GameState(ball=ball_state))
                self.game_phase = 0
            
            # phase 2(special case): when goal scored with no further touches, reset phase
            if self.game_phase == 2 and packet.game_info.is_kickoff_pause and packet.game_ball.latest_touch.time_seconds <= phase2_time:
                self.game_phase = 0
            

    def setup_newround_DGR(self, packet):
        # check if goal in last tick
        teamScores = tuple(map(lambda x: x.score, packet.teams))
        scoreDiff = max(teamScores) - min(teamScores)

        # setup round
        if scoreDiff != self.scoreDiff_prev:
            self.setup_newround(packet)
            self.scoreDiff_prev = scoreDiff


    def setup_newround(self, packet):
        car_states = {}
        yaw, yaw_mir = self.yaw_randomizor()
        for p in range(packet.num_cars):
            car = packet.game_cars[p]
            if car.team == 0:
                car_state = CarState(boost_amount=100, physics=Physics(location=Vector3(0, -1000, 17), rotation=Rotator(yaw=yaw, pitch=0, roll=0), velocity=Vector3(0, 0, 0),
                        angular_velocity=Vector3(0, 0, 0)))
                car_states[p] = car_state
            elif car.team == 1:
                car_state = CarState(boost_amount=100, physics=Physics(location=Vector3(0, 1000, 17), rotation=Rotator(yaw=yaw_mir, pitch=0, roll=0), velocity=Vector3(0, 0, 0),
                        angular_velocity=Vector3(0, 0, 0)))
                car_states[p] = car_state
        ball_state = BallState(Physics(location=Vector3(0, 0, 93)))
        self.game_state = GameState(ball=ball_state, cars=car_states)
        self.set_game_state(self.game_state)
        self.prev_time = self.cur_time
        self.game_phase = -1


    def yaw_randomizor(self):
        if not self.first_kickoff: # First kickoff will always be straight
            # yaw will have 5 possible values from pi*.25 to pi.75. Straght kickoffs weighted higher
            rand1 = np.random.random()
            if rand1 < 1/7:
                yaw = np.pi * 0.25
            elif rand1 < 2/7:
                yaw = np.pi * 0.375
            elif rand1 < 5/7:
                yaw = np.pi * 0.5
            elif rand1 < 6/7:
                yaw = np.pi * 0.625
            elif rand1 < 7/7:
                yaw = np.pi * 0.75
            # 50% parallel/mirrored yaw compared to other team
            if np.random.random() < 0.5:
                yaw_mir = yaw-np.pi
            else:
                yaw_mir = -yaw
            return yaw, yaw_mir
        else:
            self.first_kickoff = False
            yaw = np.pi * 0.5
            yaw_mir = -yaw
            return yaw, yaw_mir


# You can use this __name__ == '__main__' thing to ensure that the script doesn't start accidentally if you
# merely reference its module from somewhere
if __name__ == "__main__":
    script = FiftyFiftyMiniGame()
    script.run()
