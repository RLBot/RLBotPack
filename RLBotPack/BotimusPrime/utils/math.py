
def sign(x) -> int:
    return 1 if x >= 0 else -1


def clamp(x, low, high) -> float:
    return max(min(x, high), low)


def clamp01(x) -> float:
    return clamp(x, 0, 1)


def clamp11(x) -> float:
    return clamp(x, -1, 1)


def abs_clamp(x, limit) -> float:
    return clamp(x, -limit, limit)


def nonzero(value) -> float:
    return max(value, 0.000001)


def range_map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
