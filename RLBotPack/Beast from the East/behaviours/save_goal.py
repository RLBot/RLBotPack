from rlbot.agents.base_agent import SimpleControllerState

from behaviours.moves import AimCone
from behaviours.utsystem import Choice
from util import predict
from util.info import Field, Ball
from util.rlmath import sign, clip
from util.vec import Vec3, norm


class SaveGoal(Choice):
    def __init__(self, bot):
        team_sign = bot.info.team_sign
        self.own_goal_right = Vec3(-820 * team_sign, 5120 * team_sign, 0)
        self.own_goal_left = Vec3(820 * team_sign, 5120 * team_sign, 0)
        self.aim_cone = None
        self.ball_to_goal_right = None
        self.ball_to_goal_left = None

    def utility(self, bot) -> float:
        team_sign = bot.info.team_sign
        ball = bot.info.ball

        ball_to_goal = bot.info.own_goal - ball.pos
        too_close = norm(ball_to_goal) < Field.GOAL_WIDTH / 2 + Ball.RADIUS

        hits_goal_prediction = predict.will_ball_hit_goal(bot)
        hits_goal = hits_goal_prediction.happens and sign(ball.vel.y) == team_sign and hits_goal_prediction.time < 3

        return hits_goal or too_close

    def exec(self, bot) -> SimpleControllerState:

        car = bot.info.my_car
        ball = bot.info.ball

        hits_goal_prediction = predict.will_ball_hit_goal(bot)
        reach_time = clip(predict.time_till_reach_ball(car, ball), 0, hits_goal_prediction.time - 0.5)
        reachable_ball = predict.ball_predict(bot, reach_time)
        self.ball_to_goal_right = self.own_goal_right - reachable_ball.pos
        self.ball_to_goal_left = self.own_goal_left - reachable_ball.pos
        self.aim_cone = AimCone(self.ball_to_goal_left, self.ball_to_goal_right)

        self.aim_cone.draw(bot, reachable_ball.pos, r=200, g=0, b=160)

        shoot_controls = bot.shoot.with_aiming(bot, self.aim_cone, reach_time)

        if not bot.shoot.can_shoot:
            # Go home
            return bot.drive.go_home(bot)
        else:
            return shoot_controls
