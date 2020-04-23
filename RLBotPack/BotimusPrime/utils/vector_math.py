from rlutilities.linear_algebra import vec3, norm, normalize, dot, mat3, angle_between, vec2, xy
from rlutilities.simulation import Car, Ball


def to_vec3(obj) -> vec3:
    if isinstance(obj, vec3):
        return obj
    elif isinstance(obj, vec2):
        return vec3(obj)
    elif hasattr(obj, "position"):
        return obj.position
    elif hasattr(obj, "x"):
        return vec3(obj.x, obj.y, obj.z)
    elif hasattr(obj, "X"):
        return vec3(obj.X, obj.Y, obj.Z)


def ground(pos) -> vec3:
    pos = to_vec3(pos)
    return vec3(pos[0], pos[1], 0)


def distance(obj1, obj2) -> float:
    return norm(to_vec3(obj1) - to_vec3(obj2))


def ground_distance(obj1, obj2) -> float:
    return norm(ground(obj1) - ground(obj2))


def direction(source, target) -> vec3:
    return normalize(to_vec3(target) - to_vec3(source))


def ground_direction(source, target) -> vec3:
    return normalize(ground(target) - ground(source))


def local(car: Car, pos: vec3) -> vec3:
    return dot(to_vec3(pos) - car.position, car.orientation)


def world(car: Car, pos: vec3) -> vec3:
    return car.position + dot(car.orientation, to_vec3(pos))


def angle_to(car: Car, target: vec3, backwards=False) -> float:
    return abs(angle_between(xy(car.forward()) * (-1 if backwards else 1), ground_direction(car.position, target)))


def forward(mat: mat3) -> vec3:
    return vec3(mat[0, 0], mat[1, 0], mat[2, 0])


def align(pos: vec3, ball: Ball, goal: vec3):
    return max(
        dot(ground_direction(pos, ball), ground_direction(ball, goal)),
        dot(ground_direction(pos, ball), ground_direction(ball, goal + vec3(800, 0, 0))),
        dot(ground_direction(pos, ball), ground_direction(ball, goal - vec3(800, 0, 0)))
    )


def nearest_point(pos: vec3, points: list):
    return min(points, key=lambda p: distance(pos, p))


def farthest_point(pos: vec3, points: list):
    return max(points, key=lambda p: distance(pos, p))
