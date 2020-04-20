from GoslingUtils.routines import *
from src.utils import *


class State:
    def __init__(self):
        pass


class GetBoost(State):
    def __init__(self):
        pass

    def run(self, agent):
        if len(agent.stack) < 1:
            agent.push(goto_boost(self.closest_full_boost(agent), agent.ball.location))
        agent.debug_stack()

    def generate_stack(self, agent):
        pass

    def next_state(self, agent):
        # if ((boost_location.x() == 0 and boost_location.y() == 0) or boost_index == -1) return "Defending";
        if is_ball_going_towards_goal(agent) and agent.ball.velocity.magnitude() > 600:
            return "Defending"
        if (agent.me.boost < 36 and not is_closest(agent, agent.me) and
                (agent.me.location - agent.ball.location).magnitude() > 2000):
            if not(len(agent.friends) >= 1 and is_closest(agent, agent.me, True)):
                return "GetBoost"
        if agent.team == 1:
            if agent.ball.location[1] > 4000:
                return "Defending"
            if agent.ball.velocity[1] > 300:
                if abs(agent.ball.velocity[0]) < agent.ball.velocity[1]:
                    return "Defending"
                elif agent.ball.location[1] > 0:
                    return "Defending"
            if agent.ball.location[1] < -3500 and not is_closest(agent,  agent.me, True):
                return "Attacking"

        if agent.team == 0:
            if agent.ball.location[1] < -4000:
                return "Defending"
            if agent.ball.velocity[1] < -300:
                if abs(agent.ball.velocity[0]) < abs(agent.ball.velocity[1]):
                    return "Defending"
                elif agent.ball.location[1] < 0:
                    return "Defending"
            if agent.ball.location[1] > 3500 and not is_closest(agent,  agent.me, True):
                return "Attacking"

        if agent.me.boost > 90:
            return "Attacking"
        return "GetBoost"


    def closest_full_boost(self, agent):
        closest_distance = 9999999
        boost_index = [3, 4, 15, 18, 29, 30]
        closest_index = -1
        for bp in boost_index:
            boost = agent.boosts[bp]
            if not boost.active:
                continue
            if ((boost.location[1] > agent.ball.location[1] and agent.team == 0) or
                    (boost.location[1] < agent.ball.location[1] and agent.team == 1)):
                continue
            if (agent.me.location - boost.location).magnitude() < closest_distance:
                closest_distance = (agent.me.location - boost.location).magnitude()
                closest_index = bp

        return agent.boosts[closest_index]
