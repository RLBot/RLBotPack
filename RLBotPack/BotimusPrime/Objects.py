from Unreal import Rotator, Vector3

class GameObject:
    def __init__(self):
        self.location = Vector3()
        self.rotation = Rotator()
        self.velocity = Vector3()


ball = GameObject()

blue_goal = GameObject()
orange_goal = GameObject()

ball.radius = 93
ball.av = Vector3()
arena_x, arena_y, arena_z = 8200, 10280, 2050
arena = Vector3(4100, 5140, 2050)
center = Vector3(0,0,0)

goal_dimensions = Vector3(892,5120,642)

blue_goal.location = Vector3(0, -5120, 0)
blue_goal.left_post = Vector3(892, -5120, 0)
blue_goal.right_post = Vector3(-892, -5120, 0)

orange_goal.location = Vector3(0, 5120, 0)
orange_goal.left_post = Vector3(-892, 5120, 0)
orange_goal.right_post = Vector3(892, 5120, 0)