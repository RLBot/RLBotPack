from strategy.base_ccp import BaseCoach
from strategy.captains import *


class State:
    RUNNING = 0


class MrIntercept(BaseCoach):
    """"Selects exclusively the AllDroneIntercept captain."""

    def __init__(self):
        self.state = State.RUNNING
        self.current = AllDroneIntercept()

    def step(self):
        # Implement your state switches here!
        if self.state == State.RUNNING:
            done = self.current.step()

            # Trivial state switching to the same state with the same play
            if done:
                self.state = State.RUNNING
                self.current = AllDroneIntercept()
