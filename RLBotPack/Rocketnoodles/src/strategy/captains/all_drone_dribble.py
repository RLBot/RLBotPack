from strategy.base_ccp import BaseCaptain
from strategy.players import *
from physics.math import Vec3


class Status:
    RUNNING = 0


class AllDroneDribble(BaseCaptain):
    """"Assigns the Dribble player to every drone in the team."""

    def __init__(self):
        self.state = Status.RUNNING
        self.goal_target = Vec3(0, 5250, 350)

        # Initial role assignment!
        for drone in self.drones:
            drone.assign(Dribble(self.goal_target))

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
                drone.assign(Dribble(self.goal_target))

        # This play never ends
        return False
