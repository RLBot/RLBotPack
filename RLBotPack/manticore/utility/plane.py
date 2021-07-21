from typing import List

from utility.rlmath import argmin
from utility.vec import Vec3, dot


class Plane:
    def __init__(self, offset: Vec3, normal: Vec3):
        self.offset = offset
        self.normal = normal


def dist_to_plane(pos: Vec3, plane: Plane) -> float:
    return abs(dot(pos - plane.offset, plane.normal))


def project_onto_normal(pos: Vec3, normal: Vec3) -> Vec3:
    dist = dot(pos, normal)
    antidote = -dist * normal
    return pos + antidote


def project_onto_plane(pos: Vec3, plane: Plane) -> Vec3:
    return project_onto_normal(pos - plane.offset, plane.normal) + plane.offset


def project_onto_nearest(pos: Vec3, planes: List[Plane]) -> Vec3:
    closest, _ = argmin(planes, lambda p: dist_to_plane(pos, p))
    return project_onto_plane(pos, closest)


def intersects_normal(src: Vec3, dest: Vec3, plane_normal: Vec3) -> bool:
    # Also, if one of the points are on the plane, true is returned
    return dot(src, plane_normal) * dot(dest, plane_normal) <= 0


def intersects_plane(src: Vec3, dest: Vec3, plane: Plane) -> bool:
    return intersects_normal(src - plane.offset, dest - plane.offset, plane.normal)
