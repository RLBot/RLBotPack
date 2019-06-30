import math

from RLUtilities.Maneuvers import AirDodge, AerialTurn, Jump, look_at
from RLUtilities.LinearAlgebra import *
from RLUtilities.Simulation import *
from RLUtilities.GameInfo import GameInfo

from utils.vector_math import *
from utils.math import *
from utils.misc import *
from utils.intercept import Intercept, AerialIntercept
from utils.arena import Arena

from tools.drawing import DrawingTool

class Maneuver:

    def __init__(self, car):
        self.car: Car = car
        self.controls: Input = Input()
        self.finished: bool = False

    def step(self, dt: float):
        pass

    def render(self, draw: DrawingTool):
        pass