from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState
from rlbot.utils.structures.quick_chats import QuickChats

from state.speedFlip import SpeedFlip
from state.halfFlip import HalfFlip
import math

from rlutilities.simulation import Ball, Field, Game
from rlutilities.linear_algebra import vec3, norm, atan2, rotate2, look_at

from drive.pid import PID


###########################################################################
#                                                                         #
#         Please do not modify, study, or engineer my kickoffs!!          #
#       They are not encrypted for security reasons, but they are         #
#        Provided without any license granting open source rights.        #
#      I provided them For humans to enjoy playing against and will       #
#    fully release them once Bottleneck reaches a more completed state.   #
#                                                                         #
###########################################################################

TOURNAMENT_MODE = False

class Kickoff(SpeedFlip):
	def __init__(self, agent: BaseAgent):
		super().__init__(agent)

		self.first = True

		self.kickoffCar = None
		self.followCar = None
		self.closestKickoffCars = None
		self.furthestDefendCars = None

		self.startTime = math.inf
		self.isDiagonalKickoff = False
		self.isSemiDiagonalKickoff = False
		self.isStraightKickoff = False
		self.hasUnJumped = False
		self.riskyStrat = True
		self.alternateDiagonalKickoff = True



	def tick(self, packet: GameTickPacket) -> bool:

		if self.agent.currentTick - self.startTime > 2.8 * 120:
			print("Kickoff stuck!!")
			return False

		# TODO: if 2 of these bots in same team and on diagonal positions:
		# both do kickoff initially until it can be decided which of the enemies does the kickoff.

		# if self.first:
		#     self.first = False
		#     self.agent.set_game_state(GameState(ball=BallState(Physics(position=Vector3(0, 5300, 100)))))


		myTeam = self.agent.car.team

		if not TOURNAMENT_MODE:
			for i, car in enumerate(self.agent.packet.game_cars[:self.agent.game.num_cars]):
				if car.team != myTeam and car.is_bot:
					return False
			

		myGoalPosition = None
		for goal in self.agent.get_field_info().goals:
			if goal.team_num == myTeam:
				myGoalPosition = vec3(goal.location.x, goal.location.y, goal.location.z)
				break

		
		isBallInCenter = packet.game_ball.physics.location.x == 0 and packet.game_ball.physics.location.y == 0


		# TODO: wait for https://github.com/RLBot/RLBot/issues/486
		if not packet.game_info.is_round_active and isBallInCenter:

			if self.closestKickoffCars == None:



				# figure out who does what
				lowestKickoffDistance = math.inf
				for i, car in enumerate(self.agent.game.cars[:self.agent.game.num_cars]):
					if car.team == myTeam:
						kickoffDistance = round(norm(car.position - self.agent.game.ball.position))
						if kickoffDistance + 5 <= lowestKickoffDistance:
							lowestKickoffDistance = kickoffDistance
							self.closestKickoffCars = [i]
						elif abs(kickoffDistance - lowestKickoffDistance) <= 5:
							self.closestKickoffCars.append(i)

			
				if len(self.closestKickoffCars) == 1:
					self.kickoffCar = self.closestKickoffCars[0]
					print(f"[{self.agent.index}] kickoff car is {self.kickoffCar}, alone")
				else:
					self.kickoffCar = self.closestKickoffCars[0]
					print(f"[{self.agent.index}] kickoff car is {self.kickoffCar} of {self.closestKickoffCars}")
					if self.agent.index == self.kickoffCar:
						self.agent.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_IGotIt)
					else:
						self.agent.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_TakeTheShot)

					
					# TODO: implement quick chat based kickoff, see https://github.com/RLBot/RLBot/issues/486
					# # print("multiple kickoff cars:", self.closestKickoffCars, self.agent.index)
					# if self.agent.index in self.closestKickoffCars:
					# 	print(f"[{self.agent.index}] send quickchat: {QuickChats.Information_IGotIt}")
					# 	self.agent.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_IGotIt)

						


			if self.kickoffCar != None and self.furthestDefendCars == None:
				highestDefendDistance = 0
				for i, car in enumerate(self.agent.game.cars[:self.agent.game.num_cars]):
					if car.team == myTeam and i != self.kickoffCar:
						defendDistance = round(norm(car.position - myGoalPosition))
						if defendDistance - 5 >= highestDefendDistance:
							highestDefendDistance = defendDistance
							self.furthestDefendCars = [i]
						elif abs(defendDistance - highestDefendDistance) <= 5:
							self.furthestDefendCars.append(i)

				if self.furthestDefendCars == None:
					self.furthestDefendCars = []
					print(f"[{self.agent.index}] no followup cars")
				elif len(self.furthestDefendCars) == 1:
					self.followCar = self.furthestDefendCars[0]
					print(f"[{self.agent.index}] followup car is {self.followCar}, alone")
				else:
					self.followCar = self.furthestDefendCars[0]
					print(f"[{self.agent.index}] followup car is {self.followCar} of {self.furthestDefendCars}")
					if self.agent.index == self.followCar:
						self.agent.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_InPosition)
					else:
						self.agent.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_Defending)
					# TODO: implement quick chat based kickoff, see https://github.com/RLBot/RLBot/issues/486
					# if self.agent.index in self.furthestDefendCars:
					# 	print(f"[{self.agent.index}] send quickchat: {QuickChats.Information_Defending}")
					# 	self.agent.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_Defending)


		if self.agent.index == self.kickoffCar:
			return self.kickoffTick(packet)
		elif self.agent.index == self.followCar:
			return self.followTick(packet)
		else:
			return self.defendTick(packet, myGoalPosition)




	def handle_quick_chat(self, index, team, quick_chat):
		if team == self.agent.car.team:
			if quick_chat == QuickChats.Information_IGotIt and self.kickoffCar == None and index in self.closestKickoffCars:
				self.kickoffCar = index
				# print(f"[{self.agent.index}] kickoff car is {self.kickoffCar}")
				if self.agent.index in self.closestKickoffCars:
					print(f"[{self.agent.index}] send quickchat: {QuickChats.Information_TakeTheShot}")
					self.agent.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_TakeTheShot)
			elif quick_chat == QuickChats.Information_InPosition and self.followCar == None and self.furthestDefendCars != None and index in self.furthestDefendCars:
				self.followCar = index
				# print(f"[{self.agent.index}] defend car is {self.followCar}")
				if self.agent.index in self.furthestDefendCars and self.agent.index not in self.closestKickoffCars:
					print(f"[{self.agent.index}] send quickchat: {QuickChats.Information_Defending}")
					self.agent.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_Defending)





	def kickoffTick(self, packet: GameTickPacket) -> bool:
		
		isBallInCenter = packet.game_ball.physics.location.x == 0 and packet.game_ball.physics.location.y == 0

		carToBallDistance = norm(self.agent.car.position - self.agent.game.ball.position)

		# if at any point something goes wrong and i'll be way too late, cancel the kickoff early.
		if isBallInCenter:
			for car in self.agent.game.cars[:self.agent.game.num_cars]:
				if car.team != self.agent.car.team and norm(car.position - self.agent.game.ball.position) + 200 < carToBallDistance:
					print("kickoff failed!! big problems..")
					self.agent.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Apologies_Cursing)
					return False

		speed = norm(self.agent.car.velocity)

		self.controller.throttle = 1
		self.controller.boost = speed < 2300 - 991.666 / 120 * (1 if self.controller.boost else 10) and self.agent.car.boost > 0
		
		if speed < 10:
			self.startTime = self.agent.currentTick
			self.isDiagonalKickoff = abs(self.agent.car.position[0]) >= 1024
			self.isSemiDiagonalKickoff = abs(abs(self.agent.car.position[0]) - 256) < 128
			self.isStraightKickoff = not self.isDiagonalKickoff and not self.isSemiDiagonalKickoff
			if self.isSemiDiagonalKickoff: # force speedflip direction to pick up boost
				self.speedFlipDirection = math.copysign(1, self.agent.car.position[0] * (2*self.agent.car.team-1))
				self.speedFlipMaxTurnTicks = 15

			self.riskyStrat = True

		
		if self.speedFlipState == 0 and self.isDiagonalKickoff and self.alternateDiagonalKickoff:
			self.alternateDiagonalKickoff = False
			for car in self.agent.game.cars[:self.agent.game.num_cars]:
				if car.team != self.agent.car.team:
					if norm(car.position - self.agent.game.ball.position) < carToBallDistance + 150:
						try:
							crossWithYAxis = (car.position[1] - self.agent.game.ball.position[1] - (car.position[0] - self.agent.game.ball.position[0]) / car.velocity[0] * car.velocity[1]) * (2*car.team-1)
							if crossWithYAxis > 300:
								self.alternateDiagonalKickoff = True
								break
						except ZeroDivisionError:
							self.alternateDiagonalKickoff = True
							break



		target = self.agent.game.ball.position
		


		# LOGIC TO CANCEL THE RISKY STRAT

		if self.riskyStrat:
			if self.isDiagonalKickoff:

				# check if enemy car is also doing a fast strat
				if carToBallDistance < 1500:
					for car in self.agent.game.cars[:self.agent.game.num_cars]:
						if car.team != self.agent.car.team:
							try:
								enemyTime = norm(car.position - self.agent.game.ball.position) / norm(car.velocity)
								myTime = carToBallDistance / norm(self.agent.car.velocity)
								lead = enemyTime - myTime
								if lead < 0.09:
									self.riskyStrat = False
									break
							except ZeroDivisionError:
								pass
			else:

				for car in self.agent.game.cars[:self.agent.game.num_cars]:
					if car.team != self.agent.car.team:
						# if the enemy car jumped, fall back to safe strat immediately
						if norm(car.position - self.agent.game.ball.position) < 1500 and car.position[2] > 20:
							self.riskyStrat = False
							break

						lead = norm(car.position - self.agent.game.ball.position) - carToBallDistance

						# if enemy car is too far, it also has to fall back to safe strat instead of reacting to it
						if lead < 1500 and (norm(target - self.agent.car.position) < 525 and lead > 460):
							self.riskyStrat = False
							break


		# LOGIC TO ADJUST THE TARGET TO AIM THE BALL

		if self.riskyStrat:
			if self.isDiagonalKickoff:
				if self.alternateDiagonalKickoff:
					# aim for the wall to make a pass
					target += vec3(math.copysign(100, self.agent.car.position[0]), 0, 0)
				else:
					# aim straight for the goal
					if carToBallDistance > 1000:
						target += vec3(0, 190 * (self.agent.car.team*2-1), 0)
					else:
						target += vec3(math.copysign(3, self.agent.car.position[0]), 140 * (self.agent.car.team*2-1), 0)
			else:
				if self.isSemiDiagonalKickoff:
					offset = 29
				else:
					offset = 26
				target += vec3(math.copysign(offset, self.agent.car.position[0]), 0, 0)

		else:
			target += vec3(0, 90 * (self.agent.car.team*2-1), 0)
		
	
		# force to pick up boost
		if self.isSemiDiagonalKickoff and abs(self.agent.car.position[1]) > 1700:
			self.speedFlipTarget = vec3(0, 1800 * (2*self.agent.car.team-1), 70)
		else:
			self.speedFlipTarget = target




		# always drive straight at start
		if speed < 550:
			self.controller.steer = 0
			self.controller.jump = False
			return True

		else:

			carAngle = -atan2(self.agent.car.forward())
			self.controller.steer = min(1, max(-1, 5 * atan2(rotate2(target - self.agent.car.position, carAngle))))

			if super().tick(packet):
				return True

			else:
				
				if self.riskyStrat:
					if self.isDiagonalKickoff:
						maxJumpDistance = 210
					elif self.isSemiDiagonalKickoff:
						maxJumpDistance = 230
					else:
						maxJumpDistance = 242
					self.controller.jump = carToBallDistance < maxJumpDistance

					return isBallInCenter
				
				else:
					self.agent.reorientML.target_orientation = look_at(self.agent.game.ball.position - self.agent.car.position, vec3(0, 0, 1))
					self.agent.reorientML.step(1/self.agent.FPS)
					self.controller.yaw = self.agent.reorientML.controls.yaw
					self.controller.pitch = self.agent.reorientML.controls.pitch
					self.controller.roll = self.agent.reorientML.controls.roll

					if isBallInCenter:	
						if norm(target - self.agent.car.position) < 525:
							if not self.hasUnJumped:
								jump = self.agent.game.ball.position[2] > self.agent.car.position[2]
								if self.controller.jump and not jump:
									self.hasUnJumped = True
								self.controller.jump = jump
					else:
						
						if speed < 2200:
							for car in self.agent.game.cars[:self.agent.game.num_cars]:
								if car.team != self.agent.car.team:
									if norm(car.position - self.agent.game.ball.position) < 1000:

										if not self.hasUnJumped:
											self.controller.jump = False
											self.hasUnJumped = True
										elif self.controller.jump == False:
											self.controller.jump = True
											self.controller.pitch = -1
											self.controller.yaw = 0
										else:
											return False

										break

						# if no enemies have been found nearby, no need to dodge into the ball again
						return False

					return True




	def followTick(self, packet: GameTickPacket) -> bool:

		isBallInCenter = packet.game_ball.physics.location.x == 0 and packet.game_ball.physics.location.y == 0
		if not isBallInCenter:
			return False

		self.controller.boost = False
		self.controller.throttle = 1

		target = self.agent.game.ball.position
		if self.agent.car.boost < 40 and abs(self.agent.car.position[1]) > 2816 and norm(self.agent.car.position - self.agent.game.cars[self.kickoffCar].position) > 1500:
			target = vec3(math.copysign(144 - 10, self.agent.car.position[0]), 2816, 0)

		self.controller.steer = PID.toPoint(self.agent.car, target)
		return True



	def defendTick(self, packet: GameTickPacket, myGoalPosition: vec3) -> bool:

		speed = norm(self.agent.car.velocity)
		
		if speed < 10:
			self.startTime = self.agent.currentTick
			self.isDiagonalKickoff = abs(self.agent.car.position[0]) >= 1024
			self.isSemiDiagonalKickoff = abs(abs(self.agent.car.position[0]) - 256) < 128
			self.isStraightKickoff = not self.isDiagonalKickoff and not self.isSemiDiagonalKickoff

		self.controller.boost = False
		self.controller.pitch = 0
		self.controller.yaw = 0
		self.controller.roll = 0

		if self.isStraightKickoff:
			self.controller.steer = 0
			if abs(self.agent.car.position[1]) > 4444 and self.controller.throttle != -1:
				self.controller.throttle = 1
			else:
				if self.agent.car.velocity[1] * (2*self.agent.car.team-1) < 0 or abs(self.agent.car.position[1]) < 4466:
					self.controller.throttle = -1
				else:
					return self.agent.stateMachine.changeStateAndContinueTick(HalfFlip, packet, True, True)
		elif self.isSemiDiagonalKickoff:
			self.controller.throttle = -1
			if abs(self.agent.car.position[1]) < 3940:
				self.controller.steer = -math.copysign(1, self.agent.car.position[0]) * (2*self.agent.car.team-1)
			else:
				self.controller.steer = PID.toPointReverse(self.agent.car, vec3(0, math.copysign(5400, self.agent.car.position[1]), 0))
				if abs(self.agent.car.position[1]) > 3990 and self.controller.steer * math.copysign(1, self.agent.car.position[0]) * (2*self.agent.car.team-1) < 0.1:
					return self.agent.stateMachine.changeStateAndContinueTick(HalfFlip, packet, True, True)
			return True
		else:
			self.controller.throttle = -1
			self.controller.steer = PID.toPointReverse(self.agent.car, vec3(math.copysign(3072, self.agent.car.position[0]), math.copysign(4096, self.agent.car.position[1]), 0))
			if abs(self.agent.car.position[1]) < 2650 or self.controller.steer * math.copysign(1, self.agent.car.position[0]) * (2*self.agent.car.team-1) < -0.1:
				return True
			return self.agent.stateMachine.changeStateAndContinueTick(HalfFlip, packet)

		return True

		# return self.agent.stateMachine.changeStateAndContinueTick(HalfFlip, packet)

