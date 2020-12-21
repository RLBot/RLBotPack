from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from state.state import State
import math

from rlutilities.simulation import Ball, Field, Game
from rlutilities.linear_algebra import vec3
from rlutilities.linear_algebra import vec3, orthogonalize, project, norm, look_at, dot, normalize, atan2, rotate2, flatten
import random


class CelebrationMidGame(State):
	def __init__(self, agent: BaseAgent):
		super().__init__(agent)
		self.direction = 1 if random.random() > 0.5 else -1


	def tick(self, packet: GameTickPacket) -> bool:
		if self.agent.car.on_ground:
			self.controller.jump = not self.controller.jump
			self.controller.throttle = 1
			return True
		else:
			self.controller.jump = self.agent.car.velocity[2] > 100
			self.controller.boost = dot(self.agent.car.forward(), vec3(0, 0, -1)) * dot(self.agent.car.velocity, vec3(0, 0, -1)) < 0
			self.controller.throttle = self.controller.boost and self.agent.car.position[2] > 150
		

		hitbox = self.agent.car.hitbox()
		target = normalize(flatten(dot(self.agent.car.orientation, hitbox.half_width)))
		tmp = vec3(-hitbox.half_width[1], 0, 0)
		target = dot(self.agent.car.orientation, tmp) + vec3(0, 0, -hitbox.half_width[0])
		

		# self.agent.draw.vector(self.agent.car.position, target)

		self.agent.reorientML.target_orientation = look_at(target, self.direction * self.agent.car.left() if abs(self.agent.car.velocity[2]) < 20 else self.agent.car.velocity)
		
		self.agent.reorientML.step(1/self.agent.FPS)
		self.controller.yaw = self.agent.reorientML.controls.yaw
		self.controller.pitch = self.agent.reorientML.controls.pitch
		self.controller.roll = self.agent.reorientML.controls.roll



		return True
