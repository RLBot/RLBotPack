from typing import Callable


def initialize_generator(func: Callable):
    """initializes a generator by calling next on it once"""

    def result(self):
        gen = func(self)
        next(gen)
        return gen

    return result
