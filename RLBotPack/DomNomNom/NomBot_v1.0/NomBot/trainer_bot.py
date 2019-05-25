from utils import main, sanitize_output_vector, EasyGameState, MAX_CAR_SPEED, BALL_RADIUS
if __name__ == '__main__':
    main()  # blocking

import imp
from quicktracer import trace

from vector_math import *
import mimic_bot
import scorer
import student_agents
import marvin_atbab

NUM_FRAMES_TO_WAIT_FOR_BAKKES_RESET = 5

class Agent(mimic_bot.Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.frames_until_scoring = NUM_FRAMES_TO_WAIT_FOR_BAKKES_RESET
        self.student = None

    def on_mimic_reset(self):
        self.frames_until_scoring = NUM_FRAMES_TO_WAIT_FOR_BAKKES_RESET
        # target_pos = Vec3(0,0,0)
        target_pos = Vec3(0,0,0)
        target_vel = normalize(Vec3(1,0,0)) * MAX_CAR_SPEED
        target_pos -= normalize(target_vel) * BALL_RADIUS * 0.5
        self.scorer = scorer.PosVelScorer(target_pos, target_vel)
        # self.student = student_agents.DriveToPosAndVel(target_pos, target_vel)
        # self.student = student_agents.TheoreticalPhysicist()
        # self.student = student_agents.InterceptBallWithVel(target_vel)
        # self.student = marvin_atbab.Agent(self.name, self.team, self.index)
        # self.student = student_agents.InterceptBallTowardsEnemyGoal()
        # self.student = student_agents.AirStabilizerTowardsBall()
        # self.student = student_agents.CompositeStudent()
        # self.student = student_agents.FlipTowardsBall()
        # self.student = student_agents.OffenderDefenderWaiter()
        self.student = student_agents.NomBot_v1()

    # Override
    def decide_on_action(self, action_dict, time_in_history, game_tick_packet):
        if not self.student:
            return [0]*8
        if self.frames_until_scoring:
            self.frames_until_scoring -= 1
            return [0]*8
        s = EasyGameState(game_tick_packet, self.team, self.index)
        self.scorer.update(s)
        # trace(self.scorer.get_score())
        output_vector = self.student.get_output_vector(s)
        # output_vector = self.student.get_output_vector(game_tick_packet)
        return sanitize_output_vector(output_vector)

