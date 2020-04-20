from GoslingUtils.utils import *
from math import atan2

class sad_react():
    def run(self, agent):
        agent.controller.jump = True if not agent.me.airborne else False
        local_target = agent.me.local(agent.me.velocity.flatten())
        up = agent.me.local(Vector3(0, 0, -1))  # where "up" is in local coordinates
        target_angles = [
            math.atan2(local_target[2], local_target[0]),  # angle required to pitch towards target
            math.atan2(local_target[1], local_target[0]),  # angle required to yaw towards target
            math.atan2(up[1], up[2])]  # angle required to roll upright
        # Once we have the angles we need to rotate, we feed them into PD loops to determing the controller inputs
        agent.controller.steer = steerPD(target_angles[1], 0)
        agent.controller.pitch = steerPD(target_angles[0], agent.me.angular_velocity[1] / 4)
        agent.controller.yaw = steerPD(target_angles[1], -agent.me.angular_velocity[2] / 4)
        agent.controller.roll = steerPD(target_angles[2], agent.me.angular_velocity[0] / 2)
        # Returns the angles, which can be useful for other purposes
        return target_angles


class pog():
    def run(self, agent):
        local_target = agent.me.local(agent.me.velocity.flatten())
        up = agent.me.local(Vector3(0, 0, -1))
        target_angles = [
            math.atan2(local_target[2], local_target[0]),
            math.atan2(local_target[1], local_target[0]),
            math.atan2(up[1], up[2])]
        agent.controller.steer = steerPD(target_angles[1], 0)
        agent.controller.pitch = steerPD(target_angles[0], agent.me.angular_velocity[1] / 4)
        #agent.controller.yaw = steerPD(target_angles[1], -agent.me.angular_velocity[2] / 4)
        #agent.controller.roll = steerPD(target_angles[2], agent.me.angular_velocity[0] / 2)
        agent.controller.yaw = 1
        agent.controller.roll = -1
        agent.controller.boost = True if agent.me.forward[2] > 0 else False
        agent.controller.jump = True if not agent.me.airborne else False


class Celebration:
    def __init__(self, good):
        self.good = good

    def run(self, agent):
        if not len(agent.stack):
            if self.good:
                agent.push(pog())
            else:
                agent.push(sad_react())
        agent.debug_stack()

    def next_state(self, agent):
        return "Celebration"