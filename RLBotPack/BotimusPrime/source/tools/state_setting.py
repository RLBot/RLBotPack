from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState


class StateSettingTool:
    def __init__(self, agent):
        self.agent = agent
        self.begin()

    def begin(self):
        self.car = CarState(Physics(Vector3(), Rotator(), Vector3(), Vector3()))
        self.opponent = CarState(Physics(Vector3(), Rotator(), Vector3(), Vector3()))
        self.ball = BallState(Physics(Vector3()))
        self.gameinfo = GameInfoState()
        self._changed = False
    
    def execute(self):
        if self._changed:
            self.agent.set_game_state(GameState(
                ball=self.ball,
                cars={self.agent.index: self.car},
                game_info=self.gameinfo
            ))
            self.begin()

    def car_stop(self):
        self._changed = True
        self.car.physics.angular_velocity = Vector3(0, 0, 0)
        self.car.physics.velocity = Vector3(0, 0, 0)
        self.car.physics.rotation = Rotator(0, None, 0)

    def ball_stop(self):
        self._changed = True
        self.ball.physics.angular_velocity = Vector3(0, 0, 0)
        self.ball.physics.velocity = Vector3(0, 0, 0)

    def set_car_location(self, pos):
        self._changed = True
        self.car.physics.location.x = pos[0]
        self.car.physics.location.y = pos[1]
        self.car.physics.location.z = pos[2]

    def set_ball_location(self, pos):
        self._changed = True
        self.ball.physics.location.x = pos[0]
        self.ball.physics.location.y = pos[1]
        self.ball.physics.location.z = pos[2]


    def warp_ball_above_car(self, car_pos, additional_height=0):
        self._changed = True
        self.ball.physics.location = Vector3(car_pos[0], car_pos[1], 60 + 92 + additional_height)
        self.ball_stop()

    def warp_car_to_floor(self):
        self._changed = True
        self.car_stop()
        self.car.physics.location.z = 20

    def reset_jump(self):
        self._changed = True
        self.car.double_jumped = 0
        self.car.jumped = 0

    def game_speed(self, speed=1):
        self._changed = True
        self.gameinfo.game_speed = speed
