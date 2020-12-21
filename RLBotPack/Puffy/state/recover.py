from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from state.state import State
import math

from rlutilities.simulation import Car, Ball, Field, Game
from rlutilities.linear_algebra import vec3, orthogonalize, project, norm, look_at, dot, normalize, atan2, rotate2, flatten



# TODO: aim target velocity to where it should go in the future
# TODO: parameter to see if it wants extra speed -> wavedash
# TODO: diagonal wavedash
# TODO: aim down when landing on top curve part
# TODO: check how close you are to ceiling to save boost
# TODO: retrain network to accept a recent dodge parameter somehow
# TODO: boost in target direction
# TODO: add air dash to dash towards wall


class Recover(State):
	"""
	Will attempt to recover the car from an aerial. Returns a controller or None if car is recovered.
	"""
	def __init__(self, agent: BaseAgent, forceLandDirection = None, *args):
		super().__init__(agent, *args)
		self.ceilingJumpState = 0
		self.ceilingJumpStartTick = 0
		self.recoveryActive = True
		self.forceLandDirection = forceLandDirection



	def tick(self, packet: GameTickPacket) -> bool:

		if not self.recoveryActive:
			return False

		GRAVITY = vec3(0, 0, packet.game_info.world_gravity_z)
		DOWN = normalize(GRAVITY)

		# TODO: this should be a parameter or something
		boostUsefullnessTreshold = 0.7

		self.controller.jump = False

		if self.ceilingJumpState == 1:
			if self.agent.currentTick - self.ceilingJumpStartTick > 6:
				self.controller.jump = False
				self.ceilingJumpState = 2
			return True
		elif self.ceilingJumpState == 2:
			self.controller.jump = True
			self.ceilingJumpState = 0
			return True

		# If this is true, the car is considered to be recovered.
		if self.agent.car.on_ground and self.agent.currentTick - self.agent.lastJumpTick > 28:
			if self.agent.car.position[2] < 2044 - 17 * 1.5:
				return False
			else:
				# on ceiling, jump down
				if self.ceilingJumpState == 0 and self.agent.car.velocity[2] <= 0:
					self.controller.jump = True
					self.controller.yaw = 0
					self.controller.pitch = 0
					self.controller.roll = 0
					self.ceilingJumpStartTick = self.agent.currentTick
					self.ceilingJumpState = 1

					return True



		# Find landing point
		landPosition = vec3(0, 0, 0)
		landVelocity = vec3(0, 0, 0)
		landBottomDirection = vec3(0, 0, 0)
		airTime = self.agent.car.nextApproxCollision(landPosition, landVelocity, landBottomDirection)

		aimToBoost = airTime > boostUsefullnessTreshold and self.agent.car.boost > 0


		# TODO: mix landing velocity and target velocity
		if self.forceLandDirection:
			landVelocity = self.forceLandDirection
		else:
			landVelocity = orthogonalize(landVelocity, landBottomDirection)


		downAngle = dot(landBottomDirection, DOWN)
		nextIsCeiling = downAngle > 0.5
		nextIsGround = downAngle < -0.5
		if nextIsCeiling:
			landVelocity = orthogonalize(self.agent.car.forward(), landBottomDirection)

		landVelocityUnit = normalize(landVelocity)
		# self.agent.draw.vector(landPosition, landVelocityUnit * 750, self.agent.draw.pink)

		# TODO: this time constraint is just an estimate.. :P
		if not nextIsCeiling\
			and airTime > .65 + math.sqrt(2 * max(0, self.agent.car.position[2] - 17.01) / -packet.game_info.world_gravity_z) \
			and not self.agent.car.double_jumped:
			# dodge to cancel momentum
			atan2(self.agent.car.forward())
			rotate2(landVelocity, atan2(self.agent.car.forward()))
			direction = flatten(rotate2(landVelocity, atan2(self.agent.car.forward())))
			direction = direction / max(direction[0], direction[1])

			self.controller.yaw = 0
			self.controller.roll = direction[1]
			self.controller.pitch = direction[0]
			self.controller.throttle = 1
			self.controller.jump = True
			self.controller.boost = False
			# print("DOING AIR DASH")
			return True


		upAngle = dot(self.agent.car.up(), landBottomDirection)
		if aimToBoost and nextIsGround and airTime > 0.15 + 0.2 * (1 + dot(self.agent.car.forward(), landVelocityUnit)) + 0.3 * (1 + upAngle):
			self.agent.reorientML.target_orientation = look_at(DOWN, landVelocity)
		elif aimToBoost and nextIsCeiling and airTime > 0.3 + 0.35 * (1 + upAngle):
			self.agent.reorientML.target_orientation = look_at(DOWN * -1, landVelocity)
		else:
			WAVEDASHANGLE = 30 / 180 * math.pi
			MAXDODGEBEFORELANDTIME = 20.5 / 120
			doWaveDash = False
			if not nextIsCeiling and not self.agent.car.double_jumped and airTime - MAXDODGEBEFORELANDTIME < self.agent.maxDodgeTick:
				
				waveDashLandVelocity = flatten(landVelocity)
				waveDashLandVelocity += normalize(waveDashLandVelocity) * 500
				if norm(waveDashLandVelocity) > 2300:
					waveDashLandVelocity *= 2300 / norm(waveDashLandVelocity)
				# TODO: decide if vertical momentum is more important
				if norm(waveDashLandVelocity) > norm(landVelocity) + 100:
					doWaveDash = True
			if doWaveDash:
				landVelocity = waveDashLandVelocity
				landVelocityUnit = normalize(landVelocity)

				waveDashDirection = landVelocityUnit*math.cos(WAVEDASHANGLE) + landBottomDirection*math.sin(WAVEDASHANGLE)
				self.agent.reorientML.target_orientation = look_at(waveDashDirection, landBottomDirection)

				currentWaveDashAngle = dot(landBottomDirection, normalize(project(\
					self.agent.car.up(), landBottomDirection)\
					+ project(self.agent.car.up(), landVelocityUnit)\
				))
				dodgeBeforeLandTime = 6.5 / 120\
					+ 14 / 120 * min(1, (1 - currentWaveDashAngle) / (1 - math.cos(WAVEDASHANGLE)))\
					- 8 / 120 * (dot(DOWN, self.agent.car.up()) / 2 + 0.5) # TODO: this term should probably depend on speed towards landing surface
				
				# print(dot(landBottomDirection, self.agent.car.up()) > (1 - 1.5 * (1 - math.cos(WAVEDASHANGLE))), dot(landVelocityUnit, self.agent.car.up()) )
				if airTime < dodgeBeforeLandTime\
					and currentWaveDashAngle > (1 - 1.5 * (1 - math.cos(WAVEDASHANGLE)))\
					and dot(landVelocityUnit, self.agent.car.up()) < 0:
					self.controller.yaw = 0
					self.controller.roll = 0
					self.controller.pitch = -1
					self.controller.throttle = 1
					self.controller.jump = True
					# print("DOING WAVEDASH")
					return True
			else:
				self.agent.reorientML.target_orientation = look_at(landVelocity, landBottomDirection)


		# TODO train my own ML network that 1. prioritizes landing wheels down over in the right direction 2. doesnt care so much about having no angular velocity, instead give it air time

		# TODO do a wavedash


		self.agent.reorientML.step(1/self.agent.FPS)
		self.controller.yaw = self.agent.reorientML.controls.yaw
		self.controller.pitch = self.agent.reorientML.controls.pitch
		if upAngle < 0 and abs(self.agent.reorientML.controls.roll) < 0.1:
			self.controller.roll = math.copysign(1, self.agent.reorientML.controls.roll)
			self.controller.throttle = 1
		else:
			self.controller.roll = self.agent.reorientML.controls.roll
			forwardAngle = dot(self.agent.car.forward(), landBottomDirection)
			if abs(upAngle) > .4 or abs(forwardAngle) > 0.9 or airTime > 0.1:
				self.controller.throttle = math.copysign(1, forwardAngle)
			else:
				self.controller.throttle = 0

		nextTouchDirection = dot(self.agent.car.forward(), DOWN * -1 if nextIsCeiling else DOWN)
		boostUsefullness = 0 if nextTouchDirection < 0.3 or self.agent.lastDodgeTick + .5 + .65*120 > self.agent.currentTick else nextTouchDirection * airTime

		# TODO: decide how urgent the car needs to be somewhere
		# TODO: maybe boost forward a little bit too?
		self.controller.boost = boostUsefullness > boostUsefullnessTreshold
		self.controller.handbrake = nextIsCeiling


		# print(f"YAW  {round(self.controller.yaw, 1)}\tPITCH {round(self.controller.pitch, 1)}\tROLL {round(self.reorientML.controls.roll, 1)}\tTHROTTLE {round(self.controller.throttle, 1)}")



		return True
