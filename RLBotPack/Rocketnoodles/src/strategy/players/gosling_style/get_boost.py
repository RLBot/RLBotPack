from gosling.utils import defaultPD, defaultThrottle
from gosling.objects import Vector3, GoslingAgent, boost_object
from typing import Optional, Tuple


class GameConstants:
    MAX_SPEED_BOOST = 2300


class GetBoost:
    """Drives towards the nearest active boost in the specified area. If no active boost is found, waits on the nearest
    pad. Only considers large boost pads.

    :param which_boost: Which region of the map to drive to. Either blue, red, mid, any
    :type which_boost: str"""

    MINIMUM_BOOST_LEVEL = 90
    BOOST_MAP = {
        'blue': [3, 4],
        'red': [29, 30],
        'mid': [15, 18],
        'any': [3, 4, 15, 18, 29, 30]
    }

    def __init__(self, which_boost: str = 'any'):
        self.which_boost = which_boost
        self.agent: Optional[GoslingAgent] = None

    def run(self, agent: GoslingAgent):
        """Runs the routine, setting the controls on the agent.

        :param agent: The agent on which the controls will be set.
        :type agent: GoslingAgent
        """
        self.agent = agent
        boost_pad, brake_upon_destination = self._get_closest_boost_pad()
        self._drive_to_boost_pad(boost_pad, brake_upon_destination)
        self._boost_filled()

    def _get_boost_areas(self):
        # 3, 4, 15, 18, 29, 30 find closest active
        if self.which_boost == 'blue':
            return ['blue', 'mid']
        elif self.which_boost == 'red':
            return ['red', 'mid']
        elif self.which_boost == 'mid':
            return ['mid', 'blue', 'red']
        elif self.which_boost == 'any':
            return ['any']
        else:
            raise ValueError(f"which_boost cannot be {self.which_boost}")

    def _get_closest_boost_pad(self) -> Tuple[boost_object, bool]:
        for area in self._get_boost_areas():
            distances = {((self.agent.me.location - self.agent.boosts[pad_index].location).magnitude()): pad_index
                         for pad_index in self.BOOST_MAP[area] if self.agent.boosts[pad_index].active}
            if len(distances) > 0:
                boost_pad = distances[min(distances.keys())]
                brake_upon_destination = False
                break
        else:
            distances = {((self.agent.me.location - self.agent.boosts[pad_index].location).magnitude()): pad_index
                         for pad_index in self.BOOST_MAP[self._get_boost_areas()[0]]}
            boost_pad = distances[min(distances.keys())]
            brake_upon_destination = True
        return boost_pad, brake_upon_destination

    def _drive_to_boost_pad(self, boost_pad: boost_object, brake_upon_destination: bool):
        # Driving towards selected boost
        target = self.agent.boosts[boost_pad].location  # dont forget to remove this!
        local_target = self.agent.me.local(target - self.agent.me.location)
        defaultPD(self.agent, local_target)
        if brake_upon_destination:
            speed = min(GameConstants.MAX_SPEED_BOOST, (self.agent.me.location - target).magnitude())
        else:
            speed = GameConstants.MAX_SPEED_BOOST
        defaultThrottle(self.agent, speed)

    def _boost_filled(self) -> bool:
        minimum_boost_level = self.MINIMUM_BOOST_LEVEL
        if self.agent.me.boost >= minimum_boost_level:
            self.agent.pop()
            defaultThrottle(self.agent, 0)
            return True
        return False
