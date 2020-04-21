from GoslingUtils.routines import *
from src.utils import *
from GoslingUtils.objects import boost_object

class State:
    def __init__(self):
        pass


class GetBoost(State):
    def __init__(self):
        self.target = None

    def run(self, agent):
        if len(agent.stack) < 1 or type(agent.stack[-1]) == goto:
            if len(agent.stack): agent.pop()
            self.target = self.closest_full_boost(agent)
            if type(self.target) == Vector3:
                agent.push(goto(self.target, agent.ball.location))
            else:
                agent.push(goto_boost(self.target, agent.ball.location))
        agent.debug_stack()

    def next_state(self, agent):
        #rogue boost pad fix
        if type(self.target) == boost_object and abs(self.target.location[0]) < 3000:
            print("found rogue boost pad")
            return "Defending"
        # if ((boost_location.x() == 0 and boost_location.y() == 0) or boost_index == -1) return "Defending";
        if (is_ball_going_towards_goal(agent) and agent.ball.velocity.magnitude() > 600) or are_no_bots_back(agent) or is_ball_centering(agent, True):
            return "Defending"
        if len(agent.friends) == 1 and not is_closest(agent, agent.me, True) and agent.me.boost < 24:
            if agent.ball.location[1] * side(agent.team) > 4000:
                return "Defending"
            return "GetBoost"
        if len(agent.friends) >= 2 and not is_second_closest(agent) and agent.me.boost < 24:
            if agent.ball.location[1] * side(agent.team) > 4000:
                return "Defending"
            return "GetBoost"
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
            if boost.index != bp:
                print("REEEEEEEEEEEEEE")
            if not boost.active:
                continue
            if ((boost.location[1] > agent.ball.location[1] and agent.team == 0) or
                    (boost.location[1] < agent.ball.location[1] and agent.team == 1)):
                continue
            if abs(boost.location[0]) < 3000:
                print("@Tarehart there are ghost boosts!")
                continue
            if (agent.me.location - boost.location).magnitude() < closest_distance:
                closest_distance = (agent.me.location - boost.location).magnitude()
                closest_index = bp

        if closest_index != -1:
            return agent.boosts[closest_index]
        else:
            return agent.friend_goal.location
