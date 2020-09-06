from strategy.base_ccp import BaseCaptain
from strategy.players import *


class Status:
    RUNNING = 0


class AllDroneIntercept(BaseCaptain):
    """"Assigns the Intercept Player to every drone in the team."""

    def __init__(self):
        self.state = Status.RUNNING

        # Initial role assignment!
        for drone in self.drones:
            drone.flush_actions()
            drone.assign(Intercept())

    def step(self):
        """Return current state containing status.

        :return: Current State. True if play ends.
        :rtype: bool
        """
        # Loop over all the drones in this team
        for drone in self.drones:
            done = drone.step()

            # If state returns true if the state is not pending anymore (fail or success).
            if done:
                drone.assign(Intercept())

        # This play never ends
        return False
