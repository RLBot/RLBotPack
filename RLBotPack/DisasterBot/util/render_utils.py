import numpy as np


def render_local_line_3d(renderer, local_line, origin_loc, origin_rot_matrix, color):
    """Uses renderer.draw_line_3d to draw a line from local coordinates."""
    point1 = origin_rot_matrix.dot(local_line[0]) + origin_loc
    point2 = origin_rot_matrix.dot(local_line[1]) + origin_loc
    renderer.draw_line_3d(point1, point2, color)


def render_hitbox(renderer, my_loc, my_rot, color, hitbox_corner, hitbox_offset):
    """Uses the renderer to draw a wireframe view of the car's hitbox."""

    signs = ([1, 1, 1], [-1, -1, 1], [-1, 1, -1], [1, -1, -1])

    for s in signs:
        point = hitbox_corner * np.array(s)
        for i in range(3):
            ss = np.array([1, 1, 1])
            ss[i] *= -1
            line = np.array([point + hitbox_offset, point * ss + hitbox_offset])
            render_local_line_3d(renderer, line, my_loc, my_rot, color)


def render_car_text(renderer, car, text_list, text_color, text_size=2, spacing=20):
    """Uses the renderer to draw a list of texts at the location of the car."""

    top_offset = np.array([0, 0, 1]) * len(text_list) * spacing + car.rotation_matrix[:, 1] * spacing * 2

    for i, text in enumerate(text_list):
        renderer.draw_string_3d(car.location + top_offset, text_size, text_size, text, text_color)
        top_offset[2] -= spacing
