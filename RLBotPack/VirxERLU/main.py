from util import routines, tools, utils
from util.agent import Vector, VirxERLU


class Bot(VirxERLU):
    # If the bot encounters an error, VirxERLU will do it's best to keep the bot from crashing.
    # VirxERLU uses a stack system for it's routines. A stack is a first-in, last-out system of routines.
    # VirxERLU on VirxEC Showcase -> https://virxerlu.virxcase.dev/
    # Questions? Want to be notified about VirxERLU updates? Join my Discord -> https://discord.gg/5ARzYRD2Na
    # Wiki -> https://github.com/VirxEC/VirxERLU/wiki
    def init(self):
        # NOTE This method is ran only once, and it's when the bot starts up

        # This is a shot between the opponent's goal posts
        # NOTE When creating these, it must be a tuple of (left_target, right_target)
        self.foe_goal_shot = (self.foe_goal.left_post, self.foe_goal.right_post)
        # NOTE If you want to shoot the ball anywhere BUT between to targets, then make a tuple like (right_target, left_target) - I call this an anti-target

    def run(self):
        # NOTE This method is ran every tick

        # If the kickoff isn't done
        if not self.kickoff_done:
            # If the stack is clear
            if self.is_clear():
                # Push a generic kickoff to the stack
                # TODO make kickoff routines for each of the 5 kickoffs positions
                self.push(routines.generic_kickoff())

            # we don't want to do anything else during our kickoff
            return

        # If the stack if clear and we're in the air
        if self.is_clear() and self.me.airborne:
            # Recover - This routine supports floor, wall, and ceiling recoveries, as well as recovering towards a target
            self.push(routines.recovery())

            # we've made our decision and we don't want to run anything else
            return

        # If we have less than 36 boost
        # TODO this bot will go for boost no matter what - this is AWFUL, especially in a 1v1!
        if self.me.boost < 36:
            # If the stack is clear
            if self.is_clear():
                # Get a list of all of the large, active boosts
                boosts = tuple(boost for boost in self.boosts if boost.active and boost.large)

                # if there's at least one large and active boost
                if len(boosts) > 0:
                    # Get the closest boost
                    closest_boost = min(boosts, key=lambda boost: boost.location.dist(self.me.location))
                    # Goto the nearest boost
                    self.push(routines.goto_boost(closest_boost))

            # we've made our decision and we don't want to run anything else
            if not self.is_clear():
                return

        # if the stack is clear, then run the following - otherwise, if the stack isn't empty, then look for a shot every 4th tick while the other routine is running
        if self.is_clear() or self.odd_tick == 0:
            shot = None

            # TODO we might miss the net, even when using a target - make a pair of targets that are small than the goal so we have a better chance of scoring!
            # If the ball is on the enemy's side of the field, or slightly on our side
            if self.ball.location.y * utils.side(self.team) < 640:
                # Find a shot, on target - double_jump, jump_shot, and ground_shot  are automatically disabled if we're airborne
                shot = tools.find_shot(self, self.foe_goal_shot)

            # TODO Using an anti-target here could be cool - do to this, pass in a target tuple that's (right_target, left_target) (instead of (left, right)) into tools.find_shot (NOT tools.find_any_shot)
            # TODO When possible, we might want to take a little bit more time to shot the ball anywhere in the opponent's end - this target should probably be REALLY LONG AND HIGH!
            # If we're behind the ball and we couldn't find a shot on target
            if shot is None and self.ball.location.y * utils.side(self.team) < self.me.location.y * utils.side(self.team):
                # Find a shot, but without a target - double_jump, jump_shot, and ground_shot are automatically disabled if we're airborne
                shot = tools.find_any_shot(self)

            # If we found a shot
            if shot is not None:
                # If the stack is clear
                if self.is_clear():
                    # Shoot
                    self.push(shot)
                # If the stack isn't clear
                else:
                    # Get the current shot's name (ex jump_shot, double_jump, ground_shot or Aerial) as a string
                    current_shot_name = self.stack[0].__class__.__name__
                    # Get the new shot's name as a string
                    new_shot_name = shot.__class__.__name__

                    # If the shots are the same type
                    if new_shot_name is current_shot_name:
                        # Update the existing shot with the new information
                        self.stack[0].update(shot)
                    # If the shots are of different types
                    else:
                        # Clear the stack
                        self.clear()
                        # Shoot
                        self.push(shot)

                # we've made our decision and we don't want to run anything else
                return

        # TODO this setup is far from ideal - a custom shadow/retreat routine is probably best for the bot...
        # Make sure to put custom routines in a separate file from VirxERLU routines, so you can easily update VirxERLU to newer versions.
        # If the stack is still clear
        if self.is_clear():
            # If ball is in our half
            if self.ball.location.y * utils.side(self.team) > 640:
                retreat_routine = routines.retreat()
                # Check if the retreat routine is viable
                if retreat_routine.is_viable(self):
                    # Retreat back to the net
                    self.push(retreat_routine)
            # If the ball isn't in our half
            else:
                shadow_routine = routines.shadow()
                # Check if the shadow routine is viable
                if shadow_routine.is_viable(self):
                    # Shadow
                    self.push(shadow_routine)

        # If we get here, then we are doing our kickoff, nor can we shoot, nor can we retreat or shadow - so let's just wait!

    def demolished(self):
        # NOTE This method is ran every tick that your bot it demolished

        # If the stack isn't clear
        if not self.is_clear():
            # Clear the stack
            self.clear()

    def handle_match_comm(self, msg):
        # NOTE This is for handling any incoming match communications

        # All match comms are Python objects
        if msg.get('team') is self.team:
            self.print(msg)

    def handle_quick_chat(self, index, team, quick_chat):
        # NOTE This is for handling any incoming quick chats

        # See https://github.com/RLBot/RLBot/blob/master/src/main/flatbuffers/rlbot.fbs#L376 for a list of all quick chats
        if self.team is team:
            self.print(quick_chat)
