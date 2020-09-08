from strategy.base_ccp import BaseCaptain
from strategy.players import *


class Status:
    RUNNING = 0


class AllDroneDemo(BaseCaptain):
    """Assigns the Demo Player to every drone in the team."""

    def __init__(self):
        self.state = Status.RUNNING

        # Initial role assignment!
        for drone in self.drones:
            drone.assign(Demolition(drone))

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
                drone.assign(Demolition(drone))

        # This play never ends
        return False
