
class UtilitySystem:
    def __init__(self, choices, prev_bias=0.15):
        self.choices = choices
        self.current_best_index = -1
        self.prev_bias = prev_bias

    def evaluate(self, bot):
        best_index = -1
        best_score = 0
        # Find best choice
        for i, ch in enumerate(self.choices):
            score = ch.utility(bot)
            if i == self.current_best_index:
                score += self.prev_bias  # was previous best choice bias
            if score > best_score:
                best_score = score
                best_index = i

        if best_index != self.current_best_index:
            self.reset_current()

        # New choice
        self.current_best_index = best_index
        choice = self.choices[self.current_best_index]
        # Can choice be evaluated further? - this allows nested UtilitySystems
        evaluate_method = getattr(choice, "evaluate", None)
        if callable(evaluate_method):
            choice = evaluate_method(bot)
        return choice

    def reset_current(self):
        # Reset the current choice if it has a reset method
        if self.current_best_index != -1:
            reset_method = getattr(self.choices[self.current_best_index], "reset", None)
            if callable(reset_method):
                reset_method()

    def reset(self):
        self.reset_current()
        self.current_best_index = -1
