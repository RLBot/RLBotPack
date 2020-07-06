from GoslingUtils.objects import *
from src.Kickoff import *
from src.Defending import *
from src.Attacking import *
from src.GetBoost import *
from src.Fun_Stuff import *


# This file is for strategy

# TODO
#   Should bot go for aerial
#   Is ball in position to be aerialed
#   make jump_shot hit the ball faster
#   dont flip at ground shots (except 50/50's)
#   wall shots
class CodenameCryo(GoslingAgent):
    def initialize_agent(self):
        super().initialize_agent()
        self.allow_reset = False
        self.state = Kickoff()
        self.short_shot_initiation = 0
        self.cheat = False
        self.cheat_attack_time = 0
        self.full_team = self.friends + [self.me]
        self.last = -1
        self.my_last_score = -1
        self.foe_last_score = -1
        self.aerialing = False
        self.stopped_aerial = False

    def run(agent):
        agent.debug_rendering()
        # """
        # celebrations
        if agent.my_last_score != agent.my_score and agent.my_last_score != -1:
            agent.stack.clear()
            agent.state = Celebration(True)
        elif agent.foe_last_score != agent.foe_score and agent.foe_last_score != -1:
            agent.stack.clear()
            agent.state = Celebration(False)
        agent.my_last_score = agent.my_score
        agent.foe_last_score = agent.foe_score

        # reset bot on kick-off
        if agent.kickoff_flag and agent.allow_reset:
            agent.stack.clear()
            agent.state = Kickoff()
            agent.short_shot_initiation = 0
            agent.cheat_attack_time = 0
            agent.aerialing = False
            agent.stopped_aerial = False
            agent.allow_reset = False

        if not agent.kickoff_flag and not agent.allow_reset:
            agent.allow_reset = True

        # prevent being stuck in short shot for too long
        if len(agent.stack) > 0:
            if type(agent.stack[-1]) == short_shot and agent.short_shot_initiation == 0:
                agent.short_shot_initiation = agent.time
        if len(agent.stack) > 0:
            if type(agent.stack[-1]) != short_shot and agent.short_shot_initiation:
                agent.short_shot_initiation = 0
            elif type(agent.stack[-1]) == short_shot and (
                    agent.time - agent.short_shot_initiation) > 5 and agent.short_shot_initiation:
                agent.pop()
                agent.short_shot_initiation = 0

        # prevent double commits
        if len(agent.stack) > 0 and (not is_ball_going_towards_goal(agent) or (
                not is_second_closest(agent) and not is_closest(agent, agent.me, True))) and not agent.cheat and not agent.me.airborne:
            if type(agent.stack[-1]) == short_shot or type(agent.stack[-1]) == aerial_shot or type(
                    agent.stack[-1]) == jump_shot:
                if not is_closest(agent, agent.me, True):
                    if abs(agent.ball.location[0]) >= 1500 or abs(agent.ball.location[1]) <= 3800:
                        agent.stack.clear()
                    if not is_second_closest(agent):
                        agent.stack.clear()

        agent.state.run(agent)
        if not agent.me.airborne:
            next = agent.state.next_state(agent)
            if next != type(agent.state).__name__:
                agent.stack.clear()
                agent.state = agent.determine_state(next)
        """
        # testing code
        #if type(agent.state) != Kickoff:
        #    agent.clear()
        print(agent.foes[0].location)
        agent.clear()
        #if not len(agent.stack):
         #   agent.push(demo(1))
        #yaw2 = atan2(agent.foes[0].orientation[1][0], agent.foes[0].orientation[0][0])
        #print(str(agent.foes[0].location[0]), str(agent.foes[0].location[1]), str(yaw2))
        
        #"""

    def determine_state(agent, name):
        if name == "Attacking":
            return Attacking()
        elif name == "Defending":
            return Defending()
        elif name == "GetBoost":
            return GetBoost()
        else:
            print("error in determining state")
            print(name)
            return Attacking()

    def debug_rendering(agent):
        # debug rendering
        color = [0, 255, 0]
        # agent.renderer.draw_string_3d(agent.me.location, 2, 2, str(agent.me.velocity[0]), agent.renderer.create_color(255, *color))
        if type(agent.state) == Attacking:
            color = [255, 0, 0]
        if type(agent.state) == Defending:
            color = [0, 0, 255]
        agent.renderer.draw_string_2d(10 + (250 * agent.index), 100, 2, 2,
                                      type(agent.state).__name__, agent.renderer.create_color(255, *color))
