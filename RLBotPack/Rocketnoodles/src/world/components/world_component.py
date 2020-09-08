from abc import ABC, abstractmethod


class WorldComponent(ABC):
    """"Base component for the world model."""

    @abstractmethod
    def update(self, *args, **kwargs):
        """"Update function for this component."""
