from util import routines, tools, utils
from util.agent import VirxERLU, Vector


class Bot(VirxERLU):
    # If your bot encounters an error, VirxERLU will do it's best to keep your bot from crashing.
    # VirxERLU uses a stack system for it's routines. A stack is a first-in, last-out system. The stack is a list of routines.
    # VirxERLU on VirxEC Showcase -> https://virxerlu.virxcase.dev/
    # Wiki -> https://github.com/VirxEC/VirxERLU/wiki
    def init(self):
        # This is a shot between the opponent's goal posts
        # NOTE When creating these, it must be a tuple of (left_target, right_target)
        self.foe_goal_shot = (self.foe_goal.left_post, self.foe_goal.right_post)

    def run(self):
        # If the stack is clear
        if self.is_clear():
            # If the kickoff is done
            if self.kickoff_done:
                # If we have more than 36 boost
                if self.me.boost >= 36:
                    shot = None
                    # If the ball is on the enemy's side of the field, or slightly on our side
                    if self.ball.location.y * utils.side(self.team) < 640:
                        # Find a shot on target - disable double_jump and jump_shot if we're airborne
                        shot = tools.find_shot(self, self.foe_goal_shot, can_double_jump=not self.me.airborne, can_jump=not self.me.airborne)

                    # If we're behind the ball and we couldn't find a shot on target
                    if shot is None and self.ball.location.y * utils.side(self.team) < self.me.location.y * utils.side(self.team):
                        # Find any shot - disable double_jump and jump_shot if we're airborne
                        shot = tools.find_any_shot(self, can_double_jump=not self.me.airborne, can_jump=not self.me.airborne)

                    # If we found a shot
                    if shot is not None:
                        # Shoot
                        self.push(shot)
                    # If ball is in our half
                    elif self.ball.location.y * utils.side(self.team) > 640:
                        # Retreat back to the net
                        self.push(routines.retreat())
                    # If the ball isn't in our half
                    else:
                        # Shadow
                        self.push(routines.shadow())
                # If we have less than 36 boost
                else:
                    # Get a list of all of the large, active boosts
                    boosts = (boost for boost in self.boosts if boost.active and boost.large)
                    # Get the closest
                    closest_boost = min(boosts, key=lambda boost: boost.location.dist(self.me.location))
                    # Goto the nearest boost
                    self.push(routines.goto_boost(closest_boost))

            # If the kickoff isn't done
            else:
                # Push a generic kickoff to the stack
                self.push(routines.generic_kickoff())
        # If we're shooting (and we want to run this at 30tps)
        elif self.shooting and self.odd_tick == 0:
            shot = None
            # If the ball is on the enemy's side of the field, or slightly on our side
            if self.ball.location.y * utils.side(self.team) < 640:
                # Find a shot on target that's faster than our current shot - disable double_jump and jump_shot if we're airborne
                shot = tools.find_shot(self, self.foe_goal_shot, can_double_jump=not self.me.airborne, can_jump=not self.me.airborne)

            # If we found a shot
            if shot is not None:
                # Get the current shot's name (ex jump_shot, double_jump or Aerial)
                current_shot_name = self.stack[0].__class__.__name__
                # Get the new shot's name
                new_shot_name = shot.__class__.__name__

                # If the shots are the same type
                if new_shot_name is current_shot_name:
                    # Update the existing shot with the new information
                    self.stack[0].update(shot, self.best_shot_value)
                # If the shots are of different types
                else:
                    # Clear the stack
                    self.clear()
                    # Shoot
                    self.push(shot)

    def demolished(self):
        # If the stack isn't clear
        if not self.is_clear():
            # Clear the stack
            self.clear()