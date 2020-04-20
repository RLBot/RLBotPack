from GoslingUtils.objects import *
from src.Kickoff import *
from src.Defending import *
from src.Attacking import *
from src.GetBoost import *


#This file is for strategy

# TODO  test transition without stack clear
#       add demo code next to stealing boost

class CodenameCryo(GoslingAgent):
    def initialize_agent(self):
        super().initialize_agent()
        self.allow_reset = False
        self.state = Kickoff()
        self.short_shot_initiation = 0
        self.cheat = False
        self.cheat_attack_time = 0
        self.full_team = self.friends + [self.me]

    def run(agent):
        # color = [0,0,255]
        # agent.renderer.draw_string_3d(agent.me.location, 2, 2, str(agent.me.velocity[0]), agent.renderer.create_color(255, *color))
        # reset bot on kick-off
        if agent.kickoff_flag and agent.allow_reset:
            agent.stack.clear()
            agent.state = Kickoff()
            agent.short_shot_initiation = 0
            agent.cheat_attack_time = 0
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
            elif type(agent.stack[-1]) == short_shot and (agent.time - agent.short_shot_initiation) > 5 and agent.short_shot_initiation:
                agent.pop()
                agent.short_shot_initiation = 0

        # prevent double commits
        if len(agent.stack) > 0 and not is_ball_going_towards_goal(agent) and not agent.cheat:
            if type(agent.stack[-1]) == short_shot or type(agent.stack[-1]) == aerial_shot or type(agent.stack[-1]) == jump_shot:
                if not is_closest(agent, agent.me, True):
                    if abs(agent.ball.location[0]) >= 1500 or abs(agent.ball.location[1]) <= 3800:
                        agent.stack.clear()

        agent.state.run(agent)

        next = agent.state.next_state(agent)
        if next != type(agent.state).__name__:
            agent.stack.clear()
            agent.state = agent.determine_state(next)

    def determine_state(self, name):
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

