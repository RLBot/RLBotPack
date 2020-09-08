from strategy.base_ccp import BaseCoach
from strategy.captains import *
from strategy.players import Cover


class MrCover(BaseCoach):
    """"This class calls the captain that makes all drones cover, standing between the ball and your own goal."""

    def __init__(self):

        # Initial role assignment!
        for drone in self.drones:
            drone.flush_actions()
            drone.assign(Cover())

    def step(self):
        """Return current state containing status.

        :return: Current State.
        :rtype: bool
        """
        for drone in self.drones:
            done = drone.step()  # If state returns true if the state is not pending anymore (fail or success).

            if done:
                drone.assign(Cover())
