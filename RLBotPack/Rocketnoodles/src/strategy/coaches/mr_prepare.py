from strategy.base_ccp import BaseCoach
from strategy.captains import *
from strategy.players import Prepare


class MrPrepare(BaseCoach):
    """"This class calls the captain that makes all drones prepare to attack."""

    def __init__(self):

        # Initial role assignment!
        for drone in self.drones:
            drone.flush_actions()
            drone.assign(Prepare())

    def step(self):
        """Return current state containing status.

        :return: Current State.
        :rtype: bool
        """
        # Loop over all the drones in this team
        for drone in self.drones:
            done = drone.step()

            # If state returns true if the state is not pending anymore (fail or success).
            if done:
                drone.assign(Prepare())
