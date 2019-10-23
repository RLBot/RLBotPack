from rlutilities.linear_algebra import vec3, norm, normalize, dot, cross, mat3, angle_between, inv

def loc(obj) -> vec3:
    if hasattr(obj, "position"):
        return obj.position
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
    return dot(loc(pos) - car.position, car.orientation)

def world(car, pos) -> vec3:
    return car.position + dot(car.orientation, loc(pos))

def angle_to(car, target, backwards = False) -> float:
    return abs(angle_between(car.forward() * (-1 if backwards else 1), direction(car.position, target)))

def facing(mat: mat3) -> vec3:
    # return vec3(mat[0, 0], mat[0, 1], mat[0, 2])
    return vec3(mat[0, 0], mat[1, 0], mat[2, 0])