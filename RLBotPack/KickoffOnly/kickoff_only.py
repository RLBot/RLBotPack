import time

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, Physics, Vector3
from rlbot.utils.structures.game_data_struct import GameTickPacket

RESET_DELAY = 0.5  # seconds
BALL_OFFSET = 1 # gets added on top of the ball radius


class KickoffOnly(BaseScript):
    def __init__(self):
        super().__init__("Kickoff Only")
        self.delay_start_time = 0
        self.handled = False

    def main(self):
        while 1:
            packet: GameTickPacket = self.wait_game_tick_packet()

            # Places the ball in the air on kickoff.
            if packet.game_info.is_round_active:
                if packet.game_info.is_kickoff_pause:
                    self.delay_start_time = packet.game_info.seconds_elapsed
                    continue

                if packet.game_info.seconds_elapsed - self.delay_start_time < RESET_DELAY or abs(packet.game_ball.physics.location.y) < BALL_OFFSET + packet.game_ball.collision_shape.sphere.diameter / 2:
                    self.handled = False
                    continue

                if self.handled:
                    continue

                ball_y_side = -1 if packet.game_ball.physics.location.y < 0 else 1
                ball_state = BallState(Physics(location=Vector3(0, 5500 * ball_y_side, 325), velocity=Vector3(0, 0, 0), angular_velocity=Vector3(0, 0, 0)))
                self.set_game_state(GameState(ball=ball_state))
                self.handled = True


if __name__ == "__main__":
    zero_g_mutator = KickoffOnly()
    zero_g_mutator.main()
