from utils import main, mag, normalize, vec2angle, clockwise90degrees, closest180, clamp, clamp01, clamp11, lerp, tau, URotationToRadians
if __name__ == '__main__':
    main()  # blocking

import math
import numpy as np
from controller_input import controller
# from quicktracer import trace




class Agent:
    def __init__(self, name, team, index):
        self.name = name
        self.team = team  # 0 towards positive goal, 1 towards negative goal.
        self.index = index
        self.last_circle_facing_angle = 0


    def get_output_vector(self, game_tick_packet):
        my_car = game_tick_packet.gamecars[self.index]

        player_pos = np.array([
            my_car.Location.X,
            my_car.Location.Y,
        ])
        player_vel = np.array([
            my_car.Velocity.X,
            my_car.Velocity.Y,
        ])
        pitch = URotationToRadians * float(my_car.Rotation.Pitch)
        yaw = URotationToRadians * float(my_car.Rotation.Yaw)
        player_facing_dir = np.array([
            math.cos(pitch) * math.cos(yaw),
            math.cos(pitch) * math.sin(yaw)
        ])
        player_right = -clockwise90degrees(player_facing_dir)

        # score should be positive if going counter clockwise
        target_pos = np.array([0, 0])
        circle_outward = player_pos - target_pos
        circle_outward_dir = normalize(circle_outward)
        circle_forward_dir = clockwise90degrees(circle_outward_dir)
        drifting_score = player_vel.dot(player_right)
        going_around_target_score = circle_forward_dir.dot(player_vel)
        score = going_around_target_score * drifting_score

        steer = controller.fSteer
        steer = round(steer)
        # trace(drifting_score)
        # trace(-steer)
        # trace(player_pos)

        circle_facing_dir = np.array([
            player_facing_dir.dot(circle_outward_dir),
            player_facing_dir.dot(circle_forward_dir),
        ])

        # trace(player_facing_dir.dot(circle_forward_dir))
        # trace(player_facing_dir.dot(circle_outward_dir))
        circle_facing_angle = vec2angle(circle_facing_dir)  # 0=outward, tau/4=forward
        # trace(circle_facing_angle)

        boost = 1

        outward_dist = mag(circle_outward)
        steer_dist_inner = 400 if boost else 0
        steer_dist_outer = 2500 if boost else 1500
        should_hard_steer = 1-clamp01((outward_dist - steer_dist_inner) / (steer_dist_outer - steer_dist_inner))
        # trace(outward_dist)
        # trace(should_hard_steer)
        # trace(outward_dist-steer_dist_inner)
        desired_angle = lerp(tau*.37, tau*.51, should_hard_steer)

        if controller.hat_toggle_north:
            return [
                controller.fThrottle,
                steer,
                controller.fPitch,
                controller.fYaw,
                controller.fRoll,
                controller.bJump,
                controller.bBoost,
                controller.bHandbrake,
            ]



        steer = closest180(circle_facing_angle - desired_angle) * 4
        turning_rate = my_car.AngularVelocity.Z
        PID_vel_thingy = 0.8 if boost else 0.5
        steer -= PID_vel_thingy * turning_rate  # PID loop, essentially

        return [
            1.0,    # fThrottle
            clamp11(steer),   # fSteer
            0.0,    # fPitch
            0.0,    # fYaw
            0.0,    # fRoll
            0,      # bJump
            boost,      # bBoost
            1       # bHandbrake
        ]

