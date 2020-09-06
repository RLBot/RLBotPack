from physics.simulations.base_sim import BaseSim
from rlbot.utils.structures.ball_prediction_struct import Slice, BallPrediction
from typing import Callable, Optional

# field length(5120) + ball radius(93) = 5213 however that results in false positives
GOAL_THRESHOLD = 5235

# We will jump this number of frames when looking for a moment where the ball is inside the goal.
# Big number for efficiency, but not so big that the ball could go in and then back out during that
# time span. Unit is the number of frames in the ball prediction, and the prediction is at 60 frames per second.
GOAL_SEARCH_INCREMENT = 20


class Ball(BaseSim):
    """Ball simulation class. """

    @staticmethod
    def get_ball_prediction() -> BallPrediction:
        """"Gets the BallPrediction object from Rlbot.

        :return: The BallPrediction object by Rlbot.
        :rtype: BallPrediction"""
        return Ball.agent.get_ball_prediction_struct()

    @staticmethod
    def find_slice_at_time(game_time: float) -> Optional[Slice]:
        """This will find the future position of the ball at the specified time. The returned
        Slice object will also include the ball's velocity, etc.

        :param game_time: The time for which the Slice will be returned.
        :type game_time: float
        :return: Information about the ball in a future timestamp.
        :rtype: Slice, optional
        """
        ball_prediction = Ball.get_ball_prediction()

        start_time = ball_prediction.slices[0].game_seconds
        approx_index = int((game_time - start_time) * 60)  # We know that there are 60 slices per second.
        if 0 <= approx_index < ball_prediction.num_slices:
            return ball_prediction.slices[approx_index]
        return None

    @staticmethod
    def predict_future_goal() -> Optional[Slice]:
        """Analyzes the ball prediction to see if the ball will enter one of the goals. Only works on standard arenas.
        Will return the first ball slice which appears to be inside the goal, or None if it does not enter a goal.

        :return: Information about the ball in a future timestamp.
        :rtype: Slice, optional
        """
        return Ball.find_matching_slice(0, lambda s: abs(s.physics.location.y) >= GOAL_THRESHOLD,
                                        search_increment=20)

    @staticmethod
    def find_matching_slice(start_index: int, predicate: Callable[[Slice], bool],
                            search_increment: int = 1) -> Optional[Slice]:
        """Tries to find the first slice in the ball prediction which satisfies the given predicate. For example,
        you could find the first slice below a certain height. Will skip ahead through the packet by search_increment
        for better efficiency, then backtrack to find the exact first slice.

        :param start_index: At how many steps in the future the algorithm starts checking.
        :type start_index: float
        :param predicate: A predicate for which a slice must satisfy the boolean.
        :type predicate: Callable[[Slice], bool]
        :param search_increment: The increment at which the future predictions are checked for the given predicate.
        :type search_increment: int
        :return: Information about the ball in a future timestamp.
        :rtype: Slice, optional
        """
        ball_prediction = Ball.get_ball_prediction()

        for coarse_index in range(start_index, ball_prediction.num_slices, search_increment):
            if predicate(ball_prediction.slices[coarse_index]):
                for j in range(max(start_index, coarse_index - search_increment), coarse_index):
                    ball_slice = ball_prediction.slices[j]
                    if predicate(ball_slice):
                        return ball_slice
        return None
