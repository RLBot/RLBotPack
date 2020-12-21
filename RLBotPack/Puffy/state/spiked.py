from rlbot.agents.base_agent import BaseAgent
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.orientation import Orientation
from util.vec import Vec3
import util.const
 
from state.recover import Recover
import math 


WALLDRIVEHEIGHT = 1650

WALLCHAINDASHFIRST = 8
WALLCHAINDASHSECOND = 20

class Spiked(Recover):
	def __init__(self, agent: BaseAgent): 
		super().__init__(agent)
		self.recoveryActive = False
		self.readyToDunkTicks = 0
		self.dunkedTicks = 0
		self.lastBalltowardsGoalVelocity = -100000
		self.releaseFrames = 0 
		self.wallChainDashFrames = 0
		self.stuckFrames = 0


	def tick(self, packet: GameTickPacket) -> bool:
		myCar = packet.game_cars[self.agent.index]		
		if self.agent.spikeWatcher.carrying_car != myCar:
			return False
		targetSide = 1 - 2*myCar.team
			
		self.controller.boost = False
		self.controller.use_item = False
		self.controller.jump = False
		self.controller.pitch = 0
		self.controller.roll = 0
		self.controller.yaw = 0

		targetSpeed = 2400
		
		carOrientation = Orientation(myCar.physics.rotation)
		relativeBallPosition = carOrientation.relative_location(Vec3(myCar.physics.location), Vec3(packet.game_ball.physics.location))
		onCurvedWallSection = abs(myCar.physics.location.x + .3 * myCar.physics.velocity.x) + abs(myCar.physics.location.y + .3 * myCar.physics.velocity.y) > 7850 and abs(abs(myCar.physics.location.x + .3 * myCar.physics.velocity.x) - 4096 - (abs(myCar.physics.location.y + .3 * myCar.physics.velocity.y) - 5120)) > 925

		if self.dunkedTicks > 0:
			self.dunkedTicks += 1
			if self.dunkedTicks > 120 * .65:
				print("Dunk failed")
				self.recoveryActive = True
				if super().tick(packet):
					return True
				self.agent.stateMachine.restartStateAndContinueTick(packet)
			ballTowardsGoalVelocity = packet.game_ball.physics.velocity.y * targetSide
			if ballTowardsGoalVelocity < self.lastBalltowardsGoalVelocity and self.lastBalltowardsGoalVelocity > 10:
				self.releaseFrames += 1
				if self.releaseFrames > 5:
					self.controller.use_item = True
			self.lastBalltowardsGoalVelocity = ballTowardsGoalVelocity
			return True
		else:
			self.releaseFrames = 0

		if relativeBallPosition.z < 93.15 - 17 - 20:
			self.stuckFrames += 1
			if self.stuckFrames > 5:
				print("ball is attached to the bottom")
				self.controller.use_item = True
				return True
		else:
			self.stuckFrames = 0

		if self.readyToDunkTicks > 0:
			self.readyToDunkTicks += 1
			if self.readyToDunkTicks > 120 * .65:
				print("predunk failed")
				self.recoveryActive = True
				if super().tick(packet):
					return True
				self.agent.stateMachine.restartStateAndContinueTick(packet)
			spinX = relativeBallPosition.x
			if Vec3(0, relativeBallPosition.y, relativeBallPosition.z).length() > 125:
				spinX = max(0, spinX)
			if not myCar.has_wheel_contact and self.wallChainDashFrames == 0 and abs(packet.game_ball.physics.location.x) < 920 - max(0, min(120, 2 * spinX)):
				print("dunking")
				self.controller.yaw = 0
				spinDirection = Vec3(-spinX, relativeBallPosition.y + math.copysign(20, relativeBallPosition.y + math.copysign(20, carOrientation.forward.x * carOrientation.up.y)), 0).normalized()
				self.controller.pitch = spinDirection.x
				self.controller.roll = spinDirection.y
				self.controller.jump = True
				self.dunkedTicks = 1
				return True

		# todo: check if opponents are near and perform shot if so

		wallDriveHeight = WALLDRIVEHEIGHT + min(0, myCar.physics.location.z - packet.game_ball.physics.location.z)
		
		targetPosition = None
		targetDirection = None
		onWall = myCar.physics.location.z > 75 and (myCar.has_wheel_contact or self.wallChainDashFrames > 0)

		if onWall:
			allowChainWallDash = True
			if self.wallChainDashFrames > 0:
				self.wallChainDashFrames -= 1
				if self.wallChainDashFrames > WALLCHAINDASHSECOND:
					self.controller.pitch = 1
				elif self.wallChainDashFrames == WALLCHAINDASHSECOND:
					# print("second chain")
					self.controller.jump = True
					self.controller.pitch = -.75
					self.controller.roll = math.copysign(1, carOrientation.right.z)

			if math.fabs(myCar.physics.location.y) - math.fabs(myCar.physics.location.x) > 5120 - 4096:
				if myCar.physics.location.y * targetSide > 0: # opponent back wall
					maxHorizontal = 850 + min(0, (myCar.physics.location.y - packet.game_ball.physics.location.y) * math.copysign(1, myCar.physics.location.y))
					targetX = min(maxHorizontal, max(-maxHorizontal, packet.game_ball.physics.location.x))
					if math.fabs(myCar.physics.location.x) > 2750:
						targetPosition = Vec3(targetX, myCar.physics.location.y, wallDriveHeight)
					else:
						originalTargetPosition = Vec3(targetX, myCar.physics.location.y, 640 - 90 + min(0, myCar.physics.location.z - packet.game_ball.physics.location.z))
						targetPosition = Vec3(originalTargetPosition)
						foundGap = False
						try:
							while True:
								arrivalTime = (Vec3(myCar.physics.location) - targetPosition).length() / Vec3(myCar.physics.velocity).length()
								foundGap = True
								for carIndex in range(packet.num_cars):
									car = packet.game_cars[carIndex]
									if car.team != myCar.team:
										carFuturePos = Vec3(car.physics.location) + arrivalTime * Vec3(car.physics.velocity)
										# print(round((carFuturePos - targetPosition).length()))
										if (carFuturePos - targetPosition).length() < 500:
											foundGap = False
											break
								if foundGap:
									break
								else:
									# print(targetPosition.x, "is occupied")
									targetPosition.x += math.copysign(100, carOrientation.forward.x) # scan step
									#exclude last node on other side
									if targetPosition.x + math.copysign(100, carOrientation.forward.x) != min(maxHorizontal, max(-maxHorizontal, targetPosition.x + math.copysign(100, carOrientation.forward.x))):
										break
						except ZeroDivisionError:
							foundGap = False
						if not foundGap:
							# print("scan failed")
							targetPosition = originalTargetPosition
						# print("going for ", targetPosition.x)

					enemyGoalDistance = (Vec3(myCar.physics.location) - Vec3(targetX, 5120 * targetSide, min(643, packet.game_ball.physics.location.z))).length()
					if enemyGoalDistance < 250:
						if self.readyToDunkTicks == 0:
							self.readyToDunkTicks = 1
					else:
						self.readyToDunkTicks = 0
					allowChainWallDash = enemyGoalDistance > 1000
					targetSpeed = min(2400, 1100 - max(0, min(300, relativeBallPosition.x)) + max(0, enemyGoalDistance - 300) / 250 * 1100)
				else: # self back wall
					targetDirection = Vec3(math.copysign(1, myCar.physics.location.x), 0, 0)
			else:
				targetDirection = Vec3(0, targetSide, 0)
			invertDirection = 1
			if targetDirection is not None:
				invertDirection = math.copysign(1, carOrientation.relative_direction(targetDirection).x)
				targetHeight = wallDriveHeight - 500 if invertDirection < 0 else wallDriveHeight
				targetDirection += Vec3(0, 0, min(.5, max(-.5, (targetHeight - myCar.physics.location.z) / 200 - myCar.physics.velocity.z / 1000)))
		else:
			#print("off wall")
			self.wallChainDashFrames = 0
			if myCar.has_wheel_contact:
				self.readyToDunkTicks = 0
			targetDirection = Vec3(math.copysign(1, myCar.physics.location.x), .55 * targetSide, 0)

			

		if targetPosition is not None:
			targetDirection = (targetPosition - Vec3(myCar.physics.location)).normalized() * 2.5
		relativeTargetDirection = carOrientation.relative_direction(targetDirection)
		if relativeTargetDirection.x < 0:
			relativeTargetDirection.y = math.copysign(1, relativeTargetDirection.y)
		self.controller.steer = min(1, max(-1, relativeTargetDirection.y))

		
		if onWall and\
			allowChainWallDash and\
			myCar.has_wheel_contact and\
			invertDirection == 1 and\
			self.wallChainDashFrames == 0 and\
			abs(self.controller.steer) < .2 and\
			carOrientation.forward.z < .6 and\
			not onCurvedWallSection and\
			Vec3(myCar.physics.velocity).length() < 2200:
				# print("chain")
				self.controller.jump = True
				self.wallChainDashFrames = WALLCHAINDASHSECOND + WALLCHAINDASHFIRST
		
		self.controller.throttle = min(1, max(-1, (targetSpeed - Vec3(myCar.physics.velocity).length()) / 100))

		return True
