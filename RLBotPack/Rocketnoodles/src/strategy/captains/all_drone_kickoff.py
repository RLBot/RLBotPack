from strategy.base_ccp import BaseCaptain
from strategy.players import *


class Status:
    RUNNING = 0


class AllDroneKickoff(BaseCaptain):
    """"Assigns the Kickoff Player to every drone in the team."""

    def __init__(self):
        self.state = Status.RUNNING

        # Initial role assignment!
        for drone in self.drones:
            drone.flush_actions()
            drone.assign(KickoffGosling())

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
                return True

        # This play never ends
        return False
