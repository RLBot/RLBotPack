from gosling.utils import side
from strategy.base_ccp import BaseCoach
from strategy.captains import *
from physics.math import Vec3


class State:
    KICKOFF = 0
    ATTACKING = 1
    DEFENDING = 2
    state = ["Kickoff", "Attacking", "Defending"]


class InGameConstants:
    MAX_BALL_VELOCITY = 6000  # According to the wiki the maximum velocity of the ball is 6000
    MAX_BALL_POSITION = 5120  # According to the wiki the goals are located at y = 5120 or -5120


class TripleRotations(BaseCoach):
    """"Rotation between three captains: Attack, Defense and Kickoff. Coach for Milestone 1."""

    def __init__(self):
        self.state = State.KICKOFF

        self.current = KickoffCaptain()
        self.team = self.drones[0].team
        self.opp_team = 1 if self.team == 0 else 0

        self.side = side(self.team)

        # Tunable parameters - weights, used for deciding if we have the opportunity to attack
        self.weight_closest = 1
        self.weight_velocity = 6
        self.weight_position = 10

        # Tunable thresholds for switching, this prevents switching back and forth too often
        self.threshold_defense = -0.2
        self.threshold_offense = 0.1

    def step(self):
        """
        Determine if the state of the game switched enough that another captain should take control.
        :return:
        """
        done = self.current.step()

        total_score = self._calculate_attack_score()

        # Switch to kickoff whenever there is a kickoff
        if self.world.packet.game_info.is_kickoff_pause:
            new_state = State.KICKOFF
            if new_state != self.state:
                self.current = KickoffCaptain()

        # Switch to attack immediately after the kickoff.
        elif self.state == State.KICKOFF and done:
            new_state = State.ATTACKING
            self.current = Attack()
            print(f'Coach Triple: Switched to {State.state[new_state]}')

        # Switch to defending if the threat becomes too big.
        elif total_score < self.threshold_defense:
            new_state = State.DEFENDING
            if new_state != self.state:
                print(f'Coach Triple: Switched to {State.state[new_state]}')
                self.current = Defense()

        # Switch to attacking if the situation becomes more favourable.
        elif total_score >= self.threshold_offense:
            new_state = State.ATTACKING
            if new_state != self.state:
                print(f'Coach Triple: Switched to {State.state[new_state]}')
                self.current = Attack()
        else:
            new_state = self.state
        self.state = new_state

    def _calculate_attack_score(self) -> float:
        # Determine if we are closer to the ball or the opponent
        dist_us = 1.0 * (10 ** 10)
        dist_opp = 1.0 * (10 ** 10)
        ball_pos = Vec3.from_other_vec(self.world.ball.physics.location)
        for car in self.world.teams[self.opp_team].cars:
            vec_to_ball = ball_pos - Vec3.from_other_vec(car.physics.location)
            dist_opp = min(vec_to_ball.magnitude(), dist_opp)
        for car in self.world.teams[self.team].cars:
            vec_to_ball = ball_pos - Vec3.from_other_vec(car.physics.location)
            dist_us = min(vec_to_ball.magnitude(), dist_us)
        enemy_closer = dist_opp < dist_us

        if enemy_closer:
            closer_score = -1
        else:
            closer_score = 1

        # Calculate the ball speed towards the enemy goal and the position of the ball and turn them into a point value
        v_ball_score = - self.world.ball.physics.velocity.y * self.side / InGameConstants.MAX_BALL_VELOCITY
        ball_pos_score = - self.world.ball.physics.location.y * self.side / InGameConstants.MAX_BALL_POSITION

        # Calculate the total score by assigning a specific weight to each of the score values.
        total_score = (closer_score * self.weight_closest + v_ball_score * self.weight_velocity +
                       ball_pos_score * self.weight_position) / (self.weight_closest +
                                                                 self.weight_velocity + self.weight_position)
        return total_score
