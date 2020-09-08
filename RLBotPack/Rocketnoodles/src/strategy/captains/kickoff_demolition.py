from strategy.base_ccp import BaseCaptain
from strategy.players import *


class Status:
    RUNNING = 0


class KickoffDemolition(BaseCaptain):
    """"
    This class assigns the roles (tactics) to the bots in the current team.

    All drones are accessible with self.drones.
    Set the tactic using Drone.set_tactic(TACTIC_INSTANCE).
    """

    def __init__(self):
        self.state = Status.RUNNING
        self.prev_action_was_kickoff = True

        # Initial role assignment!
        for drone in self.drones:
            drone.assign(KickoffGosling())

    def step(self):
        """Return current state containing status.

        :return: Current State.
        :rtype: State
        """
        # Loop over all the drones in this team
        for drone in self.drones:
            done = drone.step()

            # If state returns true if the state is not pending anymore (fail or success).
            if done:

                # Switch between kickoffs and demos
                if self.prev_action_was_kickoff:
                    drone.assign(Demolition(drone))
                    # print("Assigned Demo")
                    self.prev_action_was_kickoff = False
                else:
                    drone.assign(KickoffGosling())
                    # print("Assigned Kickoff")
                    self.prev_action_was_kickoff = True

        # This play never ends
        return False
