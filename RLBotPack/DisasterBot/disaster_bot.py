import sys
import pathlib

from skeleton import SkeletonAgent
from policy.tournament_policy import TournamentPolicy


class DisasterBot(SkeletonAgent):
    def __init__(self, name, team, index):
        sys.path.insert(0, str(pathlib.Path(__file__).parent.absolute()))

        super(DisasterBot, self).__init__(name, team, index)
        self.policy = TournamentPolicy(self, rendering_enabled=False)

    def get_controls(self):

        action = self.policy.get_action(self.game_data)
        controls = action.get_controls(self.game_data)

        return controls
