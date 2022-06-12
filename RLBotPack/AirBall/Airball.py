from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3 as Vec3, Rotator

from LinAlg import Vector3
import math


def cube(location, size):
    return [
        Vector3(-size, -size, -size) + location,
        Vector3(-size, -size, size) + location,
        Vector3(-size, size, size) + location,
        Vector3(size, size, size) + location,
        Vector3(size, size, -size) + location,
        Vector3(-size, size, -size) + location,
        Vector3(-size, -size, -size) + location,
        Vector3(size, -size, -size) + location,
        Vector3(size, -size, size) + location,
        Vector3(-size, -size, size) + location,
        Vector3(-size, size, size) + location,
        Vector3(-size, size, -size) + location,
        Vector3(size, size, -size) + location,
        Vector3(size, -size, -size) + location,
        Vector3(size, -size, size) + location,
        Vector3(size, size, size) + location,
    ]


def side(team):
    if team:
        return 1
    return -1


def sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    return 0


def cap(x, low, high):
    if x < low:
        return low
    elif x > high:
        return high
    else:
        return x


def defender_spawns(team):
    return [
        CarState(
            physics=Physics(
                location=Vec3(-2300, 500 * side(team), 18),
                velocity=Vec3(0, 0, 0),
                rotation=Rotator(0, (math.pi / 2) - (math.pi * team) + (0.4 * side(team)), 0),
                angular_velocity=Vec3(0, 0, 0)),
            boost_amount=100,
            jumped=None,
            double_jumped=None
        ),
        CarState(
            physics=Physics(
                location=Vec3(0, 500 * side(team), 18),
                velocity=Vec3(0, 0, 0),
                rotation=Rotator(0, (math.pi / 2) - (math.pi * team), 0),
                angular_velocity=Vec3(0, 0, 0)),
            boost_amount=100,
            jumped=None,
            double_jumped=None
        ),
        CarState(
            physics=Physics(
                location=Vec3(2300, 500 * side(team), 18),
                velocity=Vec3(0, 0, 0),
                rotation=Rotator(0, (math.pi / 2) - (math.pi * team) - (0.4 * side(team)), 0),
                angular_velocity=Vec3(0, 0, 0)),
            boost_amount=100,
            jumped=None,
            double_jumped=None
        )
    ]


def attacker_spawns(team):
    return [
        CarState(
            physics=Physics(
                location=Vec3(-600, 5350 * side(team), 18),
                velocity=Vec3(0, 0, 0),
                rotation=Rotator(0, (math.pi / 2) - (math.pi * team) + (0.3 * side(team)), 0),
                angular_velocity=Vec3(0, 0, 0)),
            boost_amount=100,
            jumped=None,
            double_jumped=None
        ),
        CarState(
            physics=Physics(
                location=Vec3(0, 5300 * side(team), 18),
                velocity=Vec3(0, 0, 0),
                rotation=Rotator(0, (math.pi / 2) - (math.pi * team), 0),
                angular_velocity=Vec3(0, 0, 0)),
            boost_amount=100,
            jumped=None,
            double_jumped=None
        ),
        CarState(
            physics=Physics(
                location=Vec3(600, 5350 * side(team), 18),
                velocity=Vec3(0, 0, 0),
                rotation=Rotator(0, (math.pi / 2) - (math.pi * team) - (0.3 * side(team)), 0),
                angular_velocity=Vec3(0, 0, 0)),
            boost_amount=100,
            jumped=None,
            double_jumped=None
        )
    ]


def ball_spawn(attacking_team):
    return BallState(
        physics=Physics(
            location=Vec3(0, 2000 * side(attacking_team), 93),
            velocity=Vec3(0, 0, 0),
            angular_velocity=Vec3(0, 0, 0)),
        )


class Boost:
    def __init__(self, location: Vector3):
        self.location = location
        self.dot_target = self.location.copy() + Vector3(0, 0, 150)
        self.dot_location = self.location + Vector3(0, 0, 100)
        self.collected = False

    def reset(self):
        self.dot_target = self.location.copy() + Vector3(0, 0, 150)
        self.dot_location = self.location + Vector3(0, 0, 100)
        self.collected = False

    def update(self, s):
        direction, distance = (self.dot_target - self.dot_location).normalize(True)
        self.dot_location += (direction * (distance / 35))
        if abs(self.location.y) > 100 and sign(self.location.y) != side(s.half):
            size = cap(100 - distance, 25, 100)
            s.renderer.draw_polyline_3d(cube(self.dot_location, size), s.renderer.yellow())
            s.renderer.draw_polyline_3d(cube(self.dot_location + Vector3(0, 0, 1), size), s.renderer.yellow())
            s.renderer.draw_polyline_3d(cube(self.dot_location + Vector3(1, 0, 0), size), s.renderer.yellow())
            s.renderer.draw_polyline_3d(cube(self.dot_location + Vector3(0, 1, 0), size), s.renderer.yellow())

    @staticmethod
    def from_struct(boost_pad):
        location = boost_pad.Location()
        location = Vector3(
            location.X(),
            location.Y(),
            location.Z()
        )
        return Boost(location)


class Car:
    def __init__(self, index, packet=None):
        self.location = Vector3(0, 0, 0)
        self.velocity = Vector3(0, 0, 0)
        self.index = index
        self.team = 0
        if packet is not None:
            self.update(packet)

    def update(self, packet):
        car = packet.game_cars[self.index]
        self.location.data = [car.physics.location.x, car.physics.location.y, car.physics.location.z]
        self.velocity.data = [car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z]
        self.team = car.team


class Ball:
    def __init__(self):
        self.location = Vector3(0, 0, 0)
        self.velocity = Vector3(0, 0, 0)
        self.last_touch_time = -1
        self.last_touch_team = 0

    def update(self, packet):
        ball = packet.game_ball
        self.location.data = [ball.physics.location.x, ball.physics.location.y, ball.physics.location.z]
        self.velocity.data = [ball.physics.velocity.x, ball.physics.velocity.y, ball.physics.velocity.z]
        self.last_touch_time = ball.latest_touch.time_seconds
        self.last_touch_team = ball.latest_touch.team


class Airball(BaseScript):

    def __init__(self):
        super().__init__("Airball")
        info = self.game_interface.get_field_info()
        self.boosts = [Boost.from_struct(info.BoostPads(i)) for i in range(info.BoostPadsLength()) if info.BoostPads(i).IsFullBoost()]
        self.players = []
        self.ball = Ball()

        # On-screen message
        self.status = "Getting Ready..."
        # Which team is currently attacking
        self.half = 0
        # Rotates player kickoff positions
        self.player_rotation = 0
        # Keeps track of points scored in the current play
        self.attackers_score = 0
        # State of the current play
        self.play_state = 0  # countdown, live, reset
        # Times the kickoff countdown
        self.state_timer = -1
        # Times the match
        self.time = -1
        # Flag to begin a new play
        self.need_new_play = True
        # Where everything gets teleported to during the countdown
        self.countdown_state = None

    def new_play(self, packet):
        # Check for the round being active - otherwise we might start a play during the goal reset time
        if packet.game_info.is_round_active:
            # Announce to the world what we're doing
            self.status = "New Play!"
            print("New Play!")
            # Increment player rotation to keep things mixed up
            self.player_rotation += 1
            # Reset the boosts so that they're not collected
            for boost in self.boosts:
                boost.reset()
            self.play_state = 0
            self.state_timer = self.time
            countdown_cars = {}
            # Determine the spawn locations to be used
            attackers = attacker_spawns(self.half)
            defenders = defender_spawns(not self.half)
            # Assign the players to spawn locations
            for player in self.players:
                if player.team == self.half:
                    countdown_cars[player.index] = attackers.pop(self.player_rotation % len(attackers))
                else:
                    countdown_cars[player.index] = defenders.pop(self.player_rotation % len(defenders))
            # This will be used to hold the cars in place during countdown
            self.countdown_state = GameState(ball=ball_spawn(self.half), cars=countdown_cars)
            self.set_game_state(self.countdown_state)
        else:
            # If the round isn't active, we set this flag and keep trying to make a new play until we can
            self.need_new_play = True

    def kickoff_ball(self):
        ball_state = BallState(
            physics=Physics(
                location=Vec3(0, 2000 * side(self.half), 100),
                velocity=Vec3(0, 1500 * side(self.half), 700)
            )
        )
        self.set_game_state(GameState(ball=ball_state))

    def try_score(self, packet):
        if self.attackers_score > 0:
            if packet.game_info.is_round_active:
                self.attackers_score -= 1
                ball_state = BallState(
                    physics=Physics(
                        location=Vec3(0, -5400 * side(self.half), 0)
                    )
                )
                self.set_game_state(GameState(ball=ball_state))
        else:
            self.new_play(packet)

    def run(self):
        while True:
            packet = self.wait_game_tick_packet()

            # Pre-process the packet
            if len(self.players) != packet.num_cars:
                self.players = [Car(i, packet) for i in range(packet.num_cars)]
            else:
                for player in self.players:
                    player.update(packet)

                    # If this player is an attacker we check to see if they are close to any collectable boosts
                    if self.play_state == 1 and player.team == self.half:
                        for boost in self.boosts:
                            player_close = (boost.location - player.location).magnitude() < 165
                            on_side = abs(boost.location.y) > 100 and sign(boost.location.y) != side(self.half)
                            if not boost.collected and player_close and on_side:
                                boost.collected = True
                                # the cube runs off into the goal
                                boost.dot_target = Vector3(0, 5200 * side(not self.half), 300)
                                self.attackers_score += 1
                                print("Points: %s" % self.attackers_score)

            self.renderer.begin_rendering()
            for boost in self.boosts:
                boost.update(self)

            self.time = packet.game_info.seconds_elapsed
            self.ball.update(packet)

            # Master logic
            if self.need_new_play:
                print("Needed a new play")
                self.need_new_play = False
                self.new_play(packet)

            # Halftime Logic - triggers when there's 150 seconds remaining
            elif self.half == 0 and packet.game_info.game_time_remaining <= 150:
                print("Halftime!")
                self.half = 1
                self.attackers_score = 0
                self.state_timer = self.time
                self.new_play(packet)

            # State Logic
            # Countdown
            elif self.play_state == 0:
                self.set_game_state(self.countdown_state)
                if self.time > 3 + self.state_timer:
                    print("Kickoff begins!")
                    self.play_state = 1
                    self.kickoff_ball()
                else:
                    time_till_start = 3 + self.state_timer - self.time
                    self.status = str(int(time_till_start) + 1)
            # Play is live
            elif self.play_state == 1:
                if self.time < 5 + self.state_timer:
                    self.status = "Go!"
                else:
                    self.status = "Play is live! Cubes Collected: %s/2" % self.attackers_score
                if self.ball.location[2] < 100:
                    self.status = "Play Ended: Ball touched the ground"
                    print("Ball touched the ground")
                    self.play_state = 2
                    self.try_score(packet)

                elif abs(self.ball.location[1]) > 5175:
                    self.status = "Play Ended: Ball was about to be scored"
                    print("Ball was about to be scored!")
                    self.play_state = 2
                    self.try_score(packet)
                else:
                    pass  # self.slow_ball()
            # Play is being scored/reset
            elif self.play_state == 2:
                self.try_score(packet)

            # We draw the text a lot so that it looks good
            self.renderer.draw_string_2d(20, 20, 2, 2, self.status, self.renderer.yellow())
            self.renderer.draw_string_2d(20, 20, 2, 2, self.status, self.renderer.yellow())
            self.renderer.draw_string_2d(20, 20, 2, 2, self.status, self.renderer.yellow())
            self.renderer.draw_string_2d(20, 20, 2, 2, self.status, self.renderer.yellow())
            self.renderer.end_rendering()


if __name__ == "__main__":
    script = Airball()
    script.run()
