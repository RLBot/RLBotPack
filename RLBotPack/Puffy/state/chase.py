from rlbot.agents.base_agent import BaseAgent
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.orientation import Orientation
from util.vec import Vec3
import util.const


from state.recover import Recover
import math



class Chase(Recover):
	def __init__(self, agent: BaseAgent): 
		super().__init__(agent)
		self.attachedTicks = 0


	def tick(self, packet: GameTickPacket) -> bool:
		
		if super().tick(packet):
			return True

		myCar = packet.game_cars[self.agent.index]
		if self.agent.spikeWatcher.carrying_car == myCar:
			self.attachedTicks += 1
			if self.attachedTicks > 14:
				return False
		else:
			self.attachedTicks = 0
		
		targetSide = 1 - 2*myCar.team

		carDirection = -myCar.physics.rotation.yaw
		carLocation = Vec3(myCar.physics.location)
		carVelocity = Vec3(myCar.physics.velocity)
		carSpeed = carVelocity.length()
		ballLocation = Vec3(packet.game_ball.physics.location)
		ballVelocity = Vec3(packet.game_ball.physics.velocity)
		ballFutureTime = 1 / 60

		ball_prediction = self.agent.get_ball_prediction_struct()
		
		closestTeamCarDistance = 9999999
		bestCar = None
		for j in range(0, packet.num_cars):
			car = packet.game_cars[j]
			distance = (ballLocation - Vec3(car.physics.location)).length()
			if car.team == myCar.team and distance < closestTeamCarDistance and not car.is_demolished:
				closestTeamCarDistance = distance
				bestCar = car # initialise it in case ball prediction isnt productive

		if ball_prediction is not None:
			for i in range(0, ball_prediction.num_slices):
				prediction_slice = ball_prediction.slices[i]
				if prediction_slice.physics.location.z - max(prediction_slice.physics.velocity.z / 60, 0) < 100:
					possibleBallFutureTime = (i + 1) / 60
					possibleBallLocation = Vec3(prediction_slice.physics.location)
					for j in range(0, packet.num_cars):
						car = packet.game_cars[j]
						if car.team == myCar.team and not car.is_demolished:
							if ((ballLocation - Vec3(car.physics.location)).flat().length() - 200) / possibleBallFutureTime <= 2300:
								ballFutureTime = possibleBallFutureTime
								ballLocation = possibleBallLocation
								ballVelocity = Vec3(prediction_slice.physics.velocity)
								bestCar = car
								break
					else:
						continue
					break

		shadowing = bestCar != myCar and (self.agent.spikeWatcher.carrying_car is None or self.agent.spikeWatcher.carrying_car.team == myCar.team)
		if shadowing:
			ballLocation.y -= 1250 * targetSide

		ballToCarAbsoluteLocation = (ballLocation - carLocation).flat()
		ballToCarLocation = ballToCarAbsoluteLocation.rotate_2D(carDirection)
		ballToCarVelocity = (ballVelocity - carVelocity).flat().rotate_2D(carDirection)
		angle = ballToCarLocation.atan2()
		
		driveDistance = (ballLocation - carLocation).flat().length()
		if self.agent.spikeWatcher.carrying_car is None or self.agent.spikeWatcher.carrying_car.team == myCar.team:
			targetSpeed = max(driveDistance, 0) / ballFutureTime
			targetThrottle = (targetSpeed - Vec3(myCar.physics.velocity).length()) / 300
			targetThrottle = max(min((ballFutureTime - .25) * .8, (abs(ballToCarLocation.x) - 700) / 1500), targetThrottle)
			targetThrottle = min(1, targetThrottle)
		else:
			targetThrottle = 1
		
		steer = min(2, max(-2, 4 * angle))
		# if ballToCarLocation.length() < 1000:
		# 	steer += 0.005 * ballToCarVelocity.y

		self.controller.steer = min(1, max(-1, steer))
		frontOrBehind = 1 - math.fabs(angle) / (math.pi if ballToCarLocation.flat().length() > 500 else math.pi / 2) # allow backwards if close
		turnThrottle = min(1, max(-1, math.copysign(.2, frontOrBehind) + frontOrBehind)) if driveDistance < 750 else 1
		self.controller.throttle = targetThrottle * turnThrottle
		
		minimumSpeedRequired = 2300 - 991.667/120 * (1 if self.controller.boost else 10)
		wantToBoost = frontOrBehind > .9 and self.controller.throttle > .9 and ballToCarLocation.x > 700
		self.controller.boost = (carSpeed < minimumSpeedRequired) and myCar.boost > 0 and wantToBoost

		return True
