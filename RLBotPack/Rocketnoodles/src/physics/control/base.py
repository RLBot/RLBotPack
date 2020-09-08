from abc import ABC, abstractmethod
from strategy.drone import Drone


class BaseController(ABC):
    """"Base template for controllers.

    :param drone: The drone agent
    :type drone: Drone
    """

    def __init__(self, drone: Drone):
        self.drone = drone

    @abstractmethod
    def get_controls(self, *args):
        """"Sets controls on a drone to what you are controlling."""
