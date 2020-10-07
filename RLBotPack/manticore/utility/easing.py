from utility.rlmath import clip01


def lin_fall(x, max):
    """f(0)=1. Linear fall off. Hits 0 at max."""
    return clip01((max - x) / x)


def ease_out(t, d):
    """Curvy at the end. When d=0.5 it's a slow start. When d=2.0 it's a fast start."""
    return 1 - (1 - t) ** d


def ease_in(t, d):
    """Curvy at the start. When d=0.5 it's a slow end. When d=2.0 it's a fast end."""
    return 1 - ease_out(1 - t, d)
