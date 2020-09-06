from physics.control import *
from physics.math import Orientation3, Vec3


class PointPD(BaseController):
    """"For controlling the position and orientation of a drone.

    :param drone: The drone agent
    :type drone: Drone
    """

    def get_controls(self, orientation: Orientation3, target: Orientation3, direction: float = 1):
        """"Controls a drone to a position and orientation.

        :param orientation: The current orientation of the drone.
        :type orientation: Orientation3
        :param target: The target orientation for this drone.
        :type target: Orientation3
        :param direction: Whether the car is moving forward or backwards.
        :type direction: float
        """
        # TODO: WIP. On hold - Not part of Milestone 1
