
import math

from rlutilities.simulation import Ball, Field, Game, Car
from rlutilities.linear_algebra import vec3, norm, atan2, rotate2, look_at, dot, normalize


from rlutilities.mechanics import Drive as RLUDrive



class PID:

	@staticmethod
	def fromAngle(car: Car, angle: float):

		ANGLETERM = 3.5
		ANGULARTERM = -0.3
		angleP = max(-2, min(2, ANGLETERM * angle))
		angleD = ANGULARTERM * car.angular_velocity[2]

		return min(1, max(-1, angleP + angleD))


	@staticmethod
	def toPoint(car: Car, target: vec3):

		direction = normalize(target - car.position)

		turnAngleAmount = math.acos(max(-1, min(1, dot(car.forward(), direction))))

		rotateToZeroAngle = -atan2(direction)
		
		towardsZeroVector = rotate2(car.forward(), rotateToZeroAngle)
		turnDirection = math.copysign(1 , -towardsZeroVector[1])

		return PID.fromAngle(car, turnAngleAmount * turnDirection)
	

	@staticmethod
	def toPointReverse(car: Car, target: vec3):

		direction = normalize(target - car.position)

		turnAngleAmount = math.acos(max(-1, min(1, -dot(car.forward(), direction))))

		rotateToZeroAngle = -atan2(direction)
		
		towardsZeroVector = rotate2(car.forward(), rotateToZeroAngle+math.pi)
		turnDirection = math.copysign(1 , towardsZeroVector[1])

		ANGLETERM = 3.5
		ANGULARTERM = -0.3
		angleP = turnDirection * min(2, ANGLETERM * turnAngleAmount)
		angleD = ANGULARTERM * car.angular_velocity[2]


		return min(1, max(-1, angleP + angleD))


	@staticmethod
	def align(car: Car, target: vec3, direction: vec3):

		turnAngleAmount = math.acos(dot(car.forward(), direction))
		rotateToZeroAngle = -atan2(direction)
		posOffset = rotate2(target - car.position, rotateToZeroAngle)
		
		towardsZeroVector = rotate2(car.forward(), rotateToZeroAngle)
		turnDirection = math.copysign(1 ,-towardsZeroVector[1])
		
		turnRadius = 1 / RLUDrive.max_turning_curvature(norm(car.velocity))

		ANGLETERM = 10
		ANGULARTERM = -0.3
		CORRECTIONTERM = 1/40
		angleP = turnDirection * min(2, ANGLETERM * turnAngleAmount)
		angleD = ANGULARTERM * car.angular_velocity[2]

		finalOffset = posOffset[1] + turnDirection * turnRadius / .85 * (1 - math.cos(turnAngleAmount))
		offsetCorrection = CORRECTIONTERM * finalOffset

		return min(1, max(-1, angleP + angleD + offsetCorrection))