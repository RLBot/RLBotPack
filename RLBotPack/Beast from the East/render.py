from rlmath import *


# This renderer replaces the framework renderer, and allows me to disable any rendering,
# and thus saving some CPU power. Not all methods are included
class FakeRenderer:
    def __init__(self):
        pass

    def begin_rendering(self):
        pass

    def end_rendering(self):
        pass

    def create_color(self, a, r, g, b):
        pass

    def draw_string_2d(self, x, y, scale_x, scale_y, text, color):
        pass

    def draw_rect_3d(self, location, width, height, fill, color):
        pass

    def draw_string_3d(self, location, scale_x, scale_y, text, color):
        pass

    def draw_line_3d(self, start, end, color):
        pass

    def draw_polyline_3d(self, vectors, color):
        pass


def draw_ball_path(bot, duration, step_size):
    ball_prediction = bot.get_ball_prediction_struct()
    if ball_prediction is not None and duration > 0 and step_size > 0:
        time_passed = 0
        steps_taken = 0
        locations = [ball_prediction.slices[0].physics.location]
        while time_passed < duration and steps_taken + step_size < ball_prediction.num_slices:
            steps_taken += step_size
            time_passed += step_size * 0.016666
            locations.append(ball_prediction.slices[steps_taken].physics.location)

        if steps_taken > 0:
            bot.renderer.draw_polyline_3d(locations, bot.renderer.create_color(255, 255, 0, 0))


def draw_circle(bot, center: Vec3, normal: Vec3, radius: float, pieces: int):
    # Construct the arm that will be rotated
    arm = normalize(cross(normal, center)) * radius
    angle = 2 * math.pi / pieces
    rotation_mat = axis_to_rotation(angle * normalize(normal))
    points = [center + arm]

    for i in range(pieces):
        arm = dot(rotation_mat, arm)
        points.append(center + arm)

    bot.renderer.draw_polyline_3d(points, bot.renderer.orange())


def draw_bezier(bot, points, time_step=0.05):
    time = 0
    last_point = points[0]
    while time < 1:
        time += time_step
        current_point = bezier(time, points)
        bot.renderer.draw_line_3d(last_point, current_point, bot.renderer.create_color(255, 180, 255, 210))
        last_point = current_point
