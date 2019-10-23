from maneuvers.kit import *

from maneuvers.strikes.dodge_shot import DodgeShot
from maneuvers.strikes.strike import Strike

class CloseShot(DodgeShot):

    max_base_height = 180

    def configure(self, intercept: Intercept):
        
        self.target[0] = signclamp(self.intercept.ground_pos[0], 400)
        super().configure(intercept)
