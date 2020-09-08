from strategy.base_ccp import BaseCaptain
from strategy.players import *


class Status:
    RUNNING = 0


class AllDroneShadow(BaseCaptain):
    """" This class assigns the play shadowing to all the bots in the current team. """

    def __init__(self):
        self.state = Status.RUNNING
        # print("init all drone shadow")

        # Initial role assignment!
        for drone in self.drones:
            drone.assign(Shadowing())

        self.toggle = 1

    def step(self):
        """Return current state containing status.

        :return: Current State.
        :rtype: State
        """
        # Loop over all the drones in this team
        for drone in self.drones:
            done = drone.step()

            # If we have reached the position we wanted to shadow to, we wait so we are ready for a shot on goal.
            if done:
                if self.toggle == 1:
                    # print("Wait")
                    drone.assign(Wait(seconds=5))
                else:
                    # print("Shadowing")
                    drone.assign(Shadowing())
                self.toggle *= -1

        # This play never ends
        return False
