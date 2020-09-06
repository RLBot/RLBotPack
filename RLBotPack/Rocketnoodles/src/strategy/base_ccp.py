from abc import ABC, abstractmethod
from rlbot.agents.base_agent import SimpleControllerState
from typing import Tuple
from world.world import World


class SharedInfo:
    """This class is used to share the world and drone info on all CCP levels."""
    world: World = None  # World model
    drones = []


class BaseCCP(ABC, SharedInfo):
    """"Abstract template for entities in the CCP model."""

    @abstractmethod
    def step(self) -> bool:
        """Run step behaviour returns whether the current entity is finished.

        :return: Done flag.
        :rtype: bool
        """


class BaseCoach(BaseCCP):
    """"Abstract template for coach level strategy classes. This level controls what the global goal of the team is
    and what play will be made by the captain level."""

    @abstractmethod
    def step(self) -> bool:
        """Run step behaviour returns whether the current entity is finished.

        :return: Done flag.
        :rtype: bool
        """


class BaseCaptain(BaseCCP):
    """"Abstract template for captain level strategy classes. This level gives roles to individual cars."""

    @abstractmethod
    def step(self) -> bool:
        """Run step behaviour returns whether the current entity is finished.

        :return: Done flag.
        :rtype: bool
        """


class BasePlayer(BaseCCP):
    """"Abstract template for player level strategy classes. Defines individual player moves."""

    def __init__(self, drone):
        self._own_drone_idx = drone.index
        super().__init__()

    @property
    def drone(self):
        """"Returns a reference to your own car from the world model.

        :return: Car component of the world model for the car matching this player routine instance. """
        return self.world.allies[self._own_drone_idx]

    @abstractmethod
    def step(self) -> Tuple[SimpleControllerState, bool]:
        """Run step behaviour returns whether the current entity is finished.

        :return: Controller for the corresponding car and a flag indicating whether it is finished.
        :rtype: (SimpleControllerState, bool)
        """
