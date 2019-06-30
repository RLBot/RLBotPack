from RLUtilities.LinearAlgebra import vec3, norm, normalize, euler_rotation, dot, cross, mat3, angle_between, inv

def loc(obj) -> vec3:
    if hasattr(obj, "pos"):
        return obj.pos
    elif hasattr(obj, "x"):
        return vec3(obj.x, obj.y, obj.z)
    elif hasattr(obj, "X"):
        return vec3(obj.X, obj.Y, obj.Z)
    return obj

def ground(pos) -> vec3:
    pos = loc(pos)
    return vec3(pos[0], pos[1], 0)

def distance(obj1, obj2) -> float:
    return norm(loc(obj1) - loc(obj2))

def ground_distance(obj1, obj2) -> float:
    return norm(ground(obj1) - ground(obj2))

def direction(source, target) -> vec3:
    return normalize(loc(target) - loc(source))

def ground_direction(source, target) -> vec3:
    return normalize(ground(target) - ground(source))

def local(car, pos) -> vec3:
    return dot(loc(pos) - car.pos, car.theta)

def world(car, pos) -> vec3:
    return car.pos + dot(car.theta, loc(pos))

def angle_to(car, target, backwards = False) -> float:
    return abs(angle_between(car.forward() * (-1 if backwards else 1), direction(car.pos, target)))