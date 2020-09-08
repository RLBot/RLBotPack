from abc import ABC


class BaseSim(ABC):
    """"Template for object simulations."""

    world = None  # For retrieving information about the world
    agent = None  # For agent only functions provided by RLBot
