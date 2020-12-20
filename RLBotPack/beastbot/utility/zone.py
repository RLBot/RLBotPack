from utility.vec import Vec3


class Zone:
    def __contains__(self, point: Vec3) -> bool:
        raise NotImplementedError


class Zone2d(Zone):
    def __init__(self, corner_a: Vec3, corner_b: Vec3):
        self.corner_min = Vec3(min(corner_a.x, corner_b.x), min(corner_a.y, corner_b.y), 0)
        self.corner_max = Vec3(max(corner_a.x, corner_b.x), max(corner_a.y, corner_b.y), 0)

    def __contains__(self, point: Vec3) -> bool:
        return self.corner_min.x <= point.x <= self.corner_max.x \
               and self.corner_min.y <= point.y <= self.corner_max.y


class Zone3d(Zone):
    def __init__(self, corner_a: Vec3, corner_b: Vec3):
        self.corner_min = Vec3(min(corner_a.x, corner_b.x), min(corner_a.y, corner_b.y), min(corner_a.z, corner_b.z))
        self.corner_max = Vec3(max(corner_a.x, corner_b.x), max(corner_a.y, corner_b.y), max(corner_a.z, corner_b.z))

    def __contains__(self, point: Vec3) -> bool:
        return self.corner_min.x <= point.x <= self.corner_max.x \
               and self.corner_min.y <= point.y <= self.corner_max.y \
               and self.corner_min.z <= point.z <= self.corner_max.z
