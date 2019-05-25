from .vector_math import *
# from quicktracer import trace

# Note: "score" in this file is not scoring a goal, but an arbitrary reward

class Scorer(object):
    def update(s):
        pass
    def get_score(self):
        return 0.0

def rms_deviation_from_diffs(diffs):
    deviation = 0
    for diff in diffs:
        deviation += mag(diff)
    return sqrt(deviation)

class PosVelScorer(Scorer):
    """docstring for PosVel"""
    def __init__(self, target_pos, target_vel):
        self.target_pos = target_pos
        self.target_vel = target_vel
        self.best_score = float('-inf')
    def update(self, s):
        diffs = [
            1.0 * (self.target_pos - s.car.pos),
            0.1 * (self.target_vel - s.car.vel),
        ]
        # trace(-sqrt(mag(diffs[0])))
        # trace(-sqrt(mag(diffs[1])))
        score = -rms_deviation_from_diffs(diffs)
        self.best_score = max(self.best_score, score)
    def get_score(self):
        return self.best_score
