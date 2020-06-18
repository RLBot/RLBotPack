import time

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, Physics, Vector3, GameInfoState
from rlbot.utils.structures.ball_prediction_struct import BallPrediction
from rlbot.utils.structures.game_data_struct import GameTickPacket

# PARAMETERS:

# How high the ball is on kickoff.
KICKOFF_BALL_HEIGHT = 700

# World Z gravity. Positive is upwards.
WORLD_GRAVITY = -0.00001  # Basically nothing.


class ZeroG(BaseScript):
    def __init__(self):
        super().__init__("Zero G Mutator")

    def start(self):
        while True:
            time.sleep(0.5)

            # Update packet
            packet: GameTickPacket = self.get_game_tick_packet()

            if not packet.game_info.is_round_active:
                continue

            self.set_game_state(GameState(game_info=GameInfoState(world_gravity_z=WORLD_GRAVITY)))

            # Renders ball prediction.
            ball_prediction: BallPrediction = self.get_ball_prediction_struct()
            self.renderer.begin_rendering()
            sparse_slices = [step.physics.location for step in ball_prediction.slices[::10]]
            self.renderer.draw_polyline_3d(sparse_slices, self.renderer.cyan())
            self.renderer.end_rendering()

            # Places the ball in the air on kickoff.
            if packet.game_info.is_kickoff_pause and round(packet.game_ball.physics.location.z) != KICKOFF_BALL_HEIGHT:
                ball_state = BallState(Physics(location=Vector3(z=KICKOFF_BALL_HEIGHT), velocity=Vector3(0, 0, 0)))
                self.set_game_state(GameState(ball=ball_state))


if __name__ == "__main__":
    zero_g_mutator = ZeroG()
    zero_g_mutator.start()
