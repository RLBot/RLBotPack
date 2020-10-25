import math
import numpy as np


def norm(vec: np.ndarray):
    return math.sqrt(math.pow(vec[0], 2) + math.pow(vec[1], 2) + math.pow(vec[2], 2))


def dot(vec: np.ndarray, vec2: np.ndarray):
    return vec[0] * vec2[0] + vec[1] * vec2[1] + vec[2] * vec2[2]


def cross(vec: np.ndarray, vec2: np.ndarray):
    return np.cross(vec, vec2)


def normalize(vec: np.ndarray):
    """Returns a normalized vector of norm 1."""
    return vec / max(norm(vec), 1e-8)


def flatten(vec: np.ndarray):
    new_vec = vec.copy()
    new_vec[2] = 0
    return new_vec


def normalize_batch(vec: np.ndarray):
    return vec / np.maximum(np.linalg.norm(vec, axis=-1), 1e-8)


def angle_between_vectors(vec1: np.ndarray, vec2: np.ndarray):
    """Provides angle between 2 vectors in radians"""
    return math.acos(dot(normalize(vec1), normalize(vec2)))


def optimal_intercept_vector(collider_location: np.ndarray, collider_velocity: np.ndarray, target_location: np.ndarray):
    """Provides vector for correcting an object's velocity vector towards the target vector"""
    target_dir = normalize(target_location - collider_location)
    correct_vel = dot(collider_velocity, target_dir) * target_dir
    incorrect_vel = collider_velocity - correct_vel
    extra_vel = math.sqrt(math.pow(6000, 2) - math.pow(norm(incorrect_vel), 2))
    return target_dir * extra_vel - incorrect_vel
