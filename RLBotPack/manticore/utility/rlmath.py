import math


# returns sign of x, and 0 if x == 0
def sign0(x) -> float:
    return x and (1, -1)[x < 0]


def sign(x) -> float:
    return (1, -1)[x < 0]


def clip(x, minimum, maximum):
    return min(max(minimum, x), maximum)


def clip01(x) -> float:
    return clip(x, 0, 1)


def lerp(a, b, t: float):
    return (1 - t) * a + t * b


def inv_lerp(a, b, v) -> float:
    return a if b - a == 0 else (v - a) / (b - a)


def remap(prev_low, prev_high, new_low, new_high, v) -> float:
    out = inv_lerp(prev_low, prev_high, v)
    out = lerp(new_low, new_high, out)
    return out


def fix_ang(ang: float) -> float:
    """
    Transforms the given angle into the range -pi...pi
    """
    return ((ang + math.pi) % math.tau) - math.pi


def is_closer_to_goal_than(a, b, team_index):
    """ Returns true if a is closer than b to goal owned by the given team """
    return (a.y < b.y, a.y > b.y)[team_index]


def argmax(list, score_func=None):
    """
    If a score function is provided, the element with the highest score AND the score is returned.
    If not, the index of highest element in the list is returned.
    If the list is empty, None is returned.
    """
    if len(list) == 0:
        return None
    scores = list if score_func is None else [score_func(e) for e in list]
    best_index = 0
    best_score = scores[0]
    for i, score in enumerate(scores):
        if score > best_score:
            best_index = i
            best_score = score
    if score_func is None:
        return best_index
    return list[best_index], best_score


def argmin(list, score_func=None):
    """
    If a score function is provided, the element with the lowest score AND the score is returned.
    If not, the index of lowest element in the list is returned.
    If the list is empty, None is returned.
    """
    if len(list) == 0:
        if score_func is None:
            return None
        return None, 0
    scores = list if score_func is None else [score_func(e) for e in list]
    best_index = 0
    best_score = scores[0]
    for i, score in enumerate(scores):
        if score < best_score:
            best_index = i
            best_score = score
    if score_func is None:
        return best_index
    return list[best_index], best_score


# Unit tests
if __name__ == "__main__":
    assert clip(12, -2, 2) == 2
    assert clip(-20, -5, 3) == -5

