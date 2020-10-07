from typing import List

from rlbot.agents.base_agent import SimpleControllerState

from utility.rlmath import argmax


class UtilityState:
    def utility_score(self, bot) -> float:
        raise NotImplementedError

    def run(self, bot) -> SimpleControllerState:
        raise NotImplementedError

    def repeat_bias(self, bot) -> float:
        return 0.1

    def begin(self, bot):
        pass

    def end(self, bot):
        pass


class UtilitySystem:

    def __init__(self, states: List[UtilityState]):
        self.options = states
        self.last_chosen_state = None
        assert len(states) > 0, "Utility system has no options"

    def get_best_state(self, bot):

        def score(state: UtilityState):
            if state != self.last_chosen_state:
                return state.utility_score(bot)
            return state.utility_score(bot) + state.repeat_bias(bot)

        best_option, _ = argmax(self.options, score)

        if self.last_chosen_state != best_option:
            if self.last_chosen_state is not None:
                self.last_chosen_state.end(bot)
            best_option.begin(bot)

        self.last_chosen_state = best_option

        return best_option

    def reset(self):
        self.last_chosen_state.end()
        self.last_chosen_state = None
