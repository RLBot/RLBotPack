from gosling.routines import side
from gosling.utils import defaultPD, defaultThrottle
from strategy.base_ccp import BasePlayer
from rlbot.agents.base_agent import SimpleControllerState
from rlbot.utils.structures.game_data_struct import Vector3


class Demolition(BasePlayer):
    """ A 1v1 kickoff. Drive towards the ball and dodge towards it. """

    def __init__(self, drone):
        super().__init__(drone)
        self.index = drone.index

    def step(self):
        """Run step behaviour returns whether the current entity is finished.

        :return: Controller for the corresponding car and a flag indicating whether it is finished.
        :rtype: (SimpleControllerState, bool)
        """
        target = self.world.ball.physics.location + Vector3(0, 200 * side(self.world.teams[self.index]), 0)
        local_target = self.world.me.local(target - self.world.me.location)
        defaultPD(self.world, local_target)
        defaultThrottle(self.world, 2300)

        # I think you need self.drone.physics.location
        return SimpleControllerState(), False
