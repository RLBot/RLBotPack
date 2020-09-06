from gosling.routines import *
from gosling.utils import defaultPD, defaultThrottle
from gosling.objects import GoslingAgent


class GameConstants:
    MAX_SPEED_BOOST = 2300


class KickoffGosling:
    """ Drive towards the ball and dodge towards it when close. """

    FLIP_DISTANCE = 650
    TARGET_OFFSET_FROM_CENTER = 200

    def run(self, agent: GoslingAgent):
        """ Run kickoff routine.

        :param agent: Gosling agent.
        """
        target = agent.ball.location + Vector3(0, self.TARGET_OFFSET_FROM_CENTER * side(agent.team), 0)

        local_target = agent.me.local(target - agent.me.location)
        defaultPD(agent, local_target)
        defaultThrottle(agent, GameConstants.MAX_SPEED_BOOST)

        if local_target.magnitude() < self.FLIP_DISTANCE:
            agent.pop()
            agent.push(flip(agent.me.local(agent.foe_goal.location - agent.me.location)))
