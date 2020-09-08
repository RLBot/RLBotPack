from strategy.base_ccp import BaseCaptain
from strategy.players import *
from physics.math.vector3 import Vec3


class Status:
    RUNNING = 0


class KickoffCaptain(BaseCaptain):
    """"
    This class assigns the roles (tactics) to the bots in the current team.
    Which performs the kickoff.

    All drones are accessible with self.drones.
    """

    COVER_RATIO = 0.85
    BALL_MAX_VELOCITY = 300  # If the velocity of the ball is higher than this, we stop the kickoff routine

    def __init__(self):
        self.state = Status.RUNNING
        self.prev_action_was_kickoff = True
        self.first_contact = False
        self.second_drone_following = False
        # print('Init kickoff')

        # assign tasks to players
        # get distance to ball
        dists_ball = [(self.world.calc_dist_to_ball(drone.car), i) for i, drone in enumerate(self.drones)]
        dists_ball = sorted(dists_ball, key=lambda x: x[0])  # sort by distance
        # print(dists_ball)

        # closest drone do kickoff
        self.drones[dists_ball[0][1]].assign(KickoffGosling())
        self.drones[dists_ball[0][1]].kickoff_taker = True

        # second closest go behind kickoff-captain
        if len(self.drones) > 1:
            self.drones[dists_ball[1][1]].assign(Cover(distance_ratio=self.COVER_RATIO))

        # third get boost
        if len(self.drones) > 2:
            self.drones[dists_ball[2][1]].assign(Shadowing())

    def step(self) -> bool:
        """
        Step in kickoff, check if we need to reassign any bots.
        Return if the kickoff is over.

        :return: Done flag, true if finished
        :rtype: bool
        """
        # Loop over all the drones in this team
        for drone in self.drones:
            done = drone.step()

            if getattr(drone, 'following_kickoff', False) and self.first_contact:
                velocity = Vec3.from_other_vec(self.world.ball.physics.velocity).magnitude()
                if velocity < self.BALL_MAX_VELOCITY:
                    drone.assign(Dribble(self.world.ball.physics.location))  # shoot the ball
                else:
                    # print('Kickoff ended 2')
                    return True
                drone.following_kickoff = False

            # If state returns true if the state is not pending anymore (fail or success).
            if done:
                # check if the kickoff captain is done
                if getattr(drone, 'kickoff_taker', False):
                    self.first_contact = True
                    if not self.second_drone_following:
                        # print('Kickoff ended 1')
                        return True  # no drone following kickoff complete
                    else:
                        drone.assign(GetBoost())  # kickoff taker gets boost
                        continue

                # Next drone go to ball, third drone should drive to the ball
                drone.assign(Dribble(self.world.ball.physics.location))

        # This play never ends
        return False
