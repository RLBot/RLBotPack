from RLUtilities.LinearAlgebra import vec3
from utils.math import signclamp


class Arena:

    size = vec3(4096, 5120, 2044)

    @classmethod
    def clamp(cls, pos: vec3, offset: float = 0) -> vec3:
        return vec3(
            signclamp(pos[0], cls.size[0] - offset),
            signclamp(pos[1], cls.size[1] - offset),
            pos[2]
        )

    @classmethod
    def inside(cls, pos: vec3, offset: float = 0) -> bool:
        return abs(pos[0]) < cls.size[0] - offset and abs(pos[1]) < cls.size[1] - offset
