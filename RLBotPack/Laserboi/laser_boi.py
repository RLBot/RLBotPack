from config import *

from threading import Thread
from typing import List
from time import sleep
from dataclasses import dataclass
import math
import random

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import CarState, GameState, BallState, Physics, Vector3
from rlbot.utils.structures.game_data_struct import Vector3 as DrawVector3, PlayerInfo

from rlbot_action_server.bot_action_broker import BotActionBroker, run_action_server, find_usable_port
from rlbot_action_server.bot_holder import set_bot_action_broker
from rlbot_action_server.models import BotAction, AvailableActions, ActionChoice, ApiResponse
from rlbot_action_server.formatting_utils import highlight_player_name
from rlbot_twitch_broker_client import Configuration, RegisterApi, ApiClient, ActionServerRegistration
from rlbot_twitch_broker_client.defaults import STANDARD_TWITCH_BROKER_PORT
from urllib3.exceptions import MaxRetryError

from rlutilities.linear_algebra import vec3, norm
from rlutilities.simulation import Field, Game, ray as Ray

from util.vec import Vec3
from util.orientation import Orientation, look_at_orientation


BALL_RADIUS = 93.15
HITBOX_HALF_WIDTHS = Vec3(59.00368881, 42.09970474, 18.07953644)
HITBOX_OFFSET = Vec3(13.97565993, 0.0, 20.75498772)

PUSH_STRENGTH_BALL = BASE_PUSH_STRENGTH * 4
PUSH_STRENGTH_BALL_ANGULAR = BASE_PUSH_STRENGTH * 20
PUSH_STRENGTH_CAR = BASE_PUSH_STRENGTH * 3
PUSH_STRENGTH_CAR_ANGULAR = BASE_PUSH_STRENGTH * 0.85

SET_LASER_BOI = 'setLaserBoi'
PLAYER_NAME = 'playerName'

@dataclass
class Push:
	velocity: Vec3
	angular_velocity: Vec3
	def __init__(self):
		self.velocity = Vec3(0, 0, 0)
		self.angular_velocity = Vec3(0, 0, 0)

@dataclass
class Laser:
	laserType: int
	time_remaining: float

def toVector3(v: 'Vec3'):
	return Vector3(v.x, v.y, v.z)

def toDrawVector3(v: 'Vec3'):
	return DrawVector3(v.x, v.y, v.z)
	
def toRLU(v: 'Vec3') -> 'vec3':
	return vec3(v.x, v.y, v.z)
	
def fromRLU(v: 'vec3') -> 'Vec3':
	return Vec3(v[0], v[1], v[2])


if TWITCH_CHAT_INTERACTION:
	class MyActionBroker(BotActionBroker):
		def __init__(self, script):
			self.script = script

		def get_actions_currently_available(self) -> List[AvailableActions]:
			return self.script.get_actions_currently_available()

		def set_action(self, choice: ActionChoice):
			self.script.process_choice(choice.action)
			return ApiResponse(200, f"{choice.action.description}")




class Laserboi(BaseScript):

	def __init__(self):
		super().__init__("Laser_boi")
		if TWITCH_CHAT_INTERACTION:
			self.action_broker = MyActionBroker(self)
		self.known_players: List[PlayerInfo] = []
		self.game = Game()
		self.game.set_mode("soccar")
		self.car_lasers = { 								}
		self.last_seconds_elapsed = 0
		self.forces = {}
		self.lastScore = 0
		self.isKickoff = -3
		self.isPaused = True
		self.boostContent = {}
		self.boost = {}

		self.lastFullSecond = 0
		self.ticksThisSecond = 0

	def heartbeat_connection_attempts_to_twitch_broker(self, port):
		if TWITCH_CHAT_INTERACTION:
			register_api_config = Configuration()
			register_api_config.host = f"http://127.0.0.1:{STANDARD_TWITCH_BROKER_PORT}"
			twitch_broker_register = RegisterApi(ApiClient(configuration=register_api_config))
			while True:
				print("shit is running!")
				try:
					twitch_broker_register.register_action_server(
						ActionServerRegistration(base_url=f"http://127.0.0.1:{port}"))
				except MaxRetryError:
					self.logger.warning('Failed to register with twitch broker, will try again...')
				sleep(10)

	def process_choice(self, choice: BotAction):
		if TWITCH_CHAT_INTERACTION:
			if choice.action_type != SET_LASER_BOI:
				return

			player_index = self.get_player_index_by_name(choice.data[PLAYER_NAME])
			if player_index is None:
				return

			if not ALLOW_MULTIPLE_AT_ONCE:
				self.car_lasers.clear()
			self.car_lasers[player_index] = Laser(0, LASER_DURATION)


	def start(self):
		
		if TWITCH_CHAT_INTERACTION:
			port = find_usable_port(9097)
			Thread(target=run_action_server, args=(port,), daemon=True).start()
			set_bot_action_broker(self.action_broker)  # This seems to only work after the bot hot reloads once, weird.

			Thread(target=self.heartbeat_connection_attempts_to_twitch_broker, args=(port,), daemon=True).start()

		while True:
			sleep(0)
			packet = self.wait_game_tick_packet()
			
			raw_players = [self.game_tick_packet.game_cars[i]
						   for i in range(packet.num_cars)]
			self.known_players = [p for p in raw_players if p.name]
			if self.last_seconds_elapsed == packet.game_info.seconds_elapsed:
				continue
			elapsed_now = packet.game_info.seconds_elapsed - self.last_seconds_elapsed
			self.last_seconds_elapsed = packet.game_info.seconds_elapsed

			ball_pos = Vec3(packet.game_ball.physics.location)
			ball_vel = Vec3(packet.game_ball.physics.velocity)
			ball_ang = Vec3(packet.game_ball.physics.angular_velocity)

			self.ticksThisSecond += 1
			if int(packet.game_info.seconds_elapsed) != self.lastFullSecond:
				print("ticks this second:", self.ticksThisSecond)
				self.ticksThisSecond = 0
				self.lastFullSecond = int(packet.game_info.seconds_elapsed)

			if TWITCH_CHAT_INTERACTION:
				self.car_lasers = {k:v for k, v in self.car_lasers.items() if v.time_remaining >= 0}
			else:
				self.car_lasers = {}
				for i in range(packet.num_cars):
					self.car_lasers[i] = Laser(0, math.inf)

			if packet.teams[0].score - packet.teams[1].score != self.lastScore:
				self.isPaused = True
				self.lastScore = packet.teams[0].score - packet.teams[1].score
				self.isKickoff = 0
			elif packet.game_ball.physics.location.x == 0 and packet.game_ball.physics.location.y == 0 and packet.game_ball.physics.velocity.x == 0 and packet.game_ball.physics.velocity.y == 0:
				self.isKickoff += elapsed_now
				if self.isKickoff >= 4:
					self.isPaused = False
			
			ballTouchers = []
			random.seed(a=int(packet.game_info.seconds_elapsed / .14))

			if DURING_BOOST_ONLY:
				boosting = {}
				boostContent = {}
				for i in range(packet.num_cars):
					car = packet.game_cars[i]
					boosting[i] = i in self.boostContent and (6 if self.boostContent[i] > car.boost or (self.boostContent[i] < car.boost and self.boosting[i]) else max(0, self.boosting[i] - 1))
					boostContent[i] = car.boost
				self.boosting = boosting
				self.boostContent = boostContent

			for index in range(packet.num_cars):
				car = packet.game_cars[index]
				car_pos = Vec3(car.physics.location)
				car_ori = Orientation(car.physics.rotation)

				self.renderer.begin_rendering(str(index) + "Lb")
				
				if index in self.car_lasers:
					laser = self.car_lasers[index]
					if not packet.game_cars[index].is_demolished and (not DURING_BOOST_ONLY or self.boosting[index]):# and not self.isPaused:
						if not self.isPaused:
							laser.time_remaining -= elapsed_now
						if laser.time_remaining >= 0:
							for leftRight in (-1, 1):
								startPoint = car_pos + car_ori.forward * 63 - leftRight * car_ori.right * 26 + car_ori.up * 3
								direction = car_ori.forward.orthogonalize(Vec3(0, 0, 1)).normalized() if car.has_wheel_contact and abs(car_ori.up.dot(Vec3(0, 0, 1))) > 0.999 else car_ori.forward

								for bounce in range(BOUNCE_SEGMENTS):
									closest = math.inf
									closestTarget = None
									toBall = Vec3(packet.game_ball.physics.location) - car_pos
									toBallProj = toBall.project(direction)
									toBallOrth = toBall - toBallProj
									toCollisionOrth = toBallOrth
									endVector = direction
									if toBallOrth.length() <= BALL_RADIUS and toBallProj.dot(direction) > 0:
										closestTarget = -1
										closest = toBallProj.length() - math.sqrt(BALL_RADIUS**2 - toBallOrth.length()**2)
										ballTouchers.append(index)

									for otherIndex in range(packet.num_cars):
										if otherIndex == index:
											continue
										other_car = packet.game_cars[otherIndex]
										other_car_pos = Vec3(other_car.physics.location)
										other_car_ori = Orientation(other_car.physics.rotation)

										v_local = other_car_ori.dot2(startPoint - (other_car_pos + other_car_ori.dot1(HITBOX_OFFSET)) + 15 * other_car_ori.up)
										d_local = other_car_ori.dot2(direction)
										def lineFaceCollision(i):
											offset = Vec3(0, 0, 0)
											offset[i] = math.copysign(HITBOX_HALF_WIDTHS[i], -d_local[i])
											collisionPoint = v_local - offset
											try:
												distance = -collisionPoint[i] / d_local[i]
											except ZeroDivisionError:
												return None
											if distance < 0:
												return None
											collisionPoint += d_local * distance
											for j in range(i == 0, 3 - (i == 2), 1 + (i == 1)):
												if abs(collisionPoint[j]) > HITBOX_HALF_WIDTHS[j]:
													return None
											collisionPoint[i] = offset[i]
											return distance
										distance = lineFaceCollision(0) or lineFaceCollision(1) or lineFaceCollision(2)
										if distance is not None:
											collisionPoint = startPoint + distance * direction
											toCollisionOrth = (collisionPoint - startPoint).orthogonalize(direction)
											if distance < closest:
												closest = distance
												closestTarget = otherIndex


									if closestTarget is not None:
										if closestTarget not in self.forces:
											self.forces[closestTarget] = Push()
										self.forces[closestTarget].velocity += direction * elapsed_now
										try:
											self.forces[closestTarget].angular_velocity += toCollisionOrth * -1 * direction / toCollisionOrth.length()**2 * elapsed_now
										except ZeroDivisionError:
											pass
										pass
									else:
										# simulate raycast closest
										length = 100000
										startPointRLU = toRLU(startPoint)
										directionRLU = toRLU(direction)
										ray = Ray(startPointRLU, directionRLU * length)
										while closest >= length + .2:
											closest = length
											newStartPointRLU, mirrorDirectionRLU = ray.start, ray.direction
											ray = Field.raycast_any(Ray(startPointRLU, directionRLU * (length - .1)))
											length = norm(ray.start - startPointRLU)
										mirrorDirection = fromRLU(mirrorDirectionRLU)
										newStartPoint = fromRLU(newStartPointRLU)
										newDirection = direction - 2 * direction.dot(mirrorDirection) * mirrorDirection
										endVector = direction * 0.6 - mirrorDirection * 0.4
									
									R = 4
									COLORSPIN = 2
									SCATTERSPIN = 0.75

									dir_ori = look_at_orientation(direction, Vec3(0, 0, 1))
									dir_ori.right *= R
									dir_ori.up *= R
									end_ori = look_at_orientation(endVector, Vec3(0, 0, 1))
									scatterStartFirst = startPoint + closest * direction

									for i in range(LASERLINES):
										i = i / LASERLINES * 2 * math.pi
										offset = dir_ori.right * math.sin(i) + dir_ori.up * math.cos(i)
										color = self.renderer.create_color(255, 
											int(255 * (0.5 + 0.5 * math.sin(car.physics.rotation.roll + leftRight * i + (COLORSPIN * packet.game_info.seconds_elapsed)))),
											int(255 * (0.5 + 0.5 * math.sin(car.physics.rotation.roll + leftRight * i + (COLORSPIN * packet.game_info.seconds_elapsed + 2 / 3 * math.pi)))),
											int(255 * (0.5 + 0.5 * math.sin(car.physics.rotation.roll + leftRight * i + (COLORSPIN * packet.game_info.seconds_elapsed + 4 / 3 * math.pi))))
										)
										self.renderer.native_draw_line_3d(self.renderer.builder, color, toDrawVector3(startPoint + offset), toDrawVector3(scatterStartFirst + offset))
									
									for _ in range(SCATTERLINES):
										r = random.uniform(0, 2 * math.pi)
										c = leftRight * r - (SCATTERSPIN - COLORSPIN) * packet.game_info.seconds_elapsed
										i = car.physics.rotation.roll + r - leftRight * (SCATTERSPIN) * packet.game_info.seconds_elapsed
										# c = random.uniform(0, 2 * math.pi)
										color = self.renderer.create_color(255, 
											int(255 * (0.5 + 0.5 * math.sin(c))),
											int(255 * (0.5 + 0.5 * math.sin(c + 2 / 3 * math.pi))),
											int(255 * (0.5 + 0.5 * math.sin(c + 4 / 3 * math.pi)))
										)
										length = 15 * random.expovariate(1)
										scatterStart = scatterStartFirst + dir_ori.right * math.sin(i) + dir_ori.up * math.cos(i)
										scatterEnd = scatterStart + end_ori.dot1(Vec3(-length, length * math.sin(i), length * math.cos(i)))
										self.renderer.native_draw_line_3d(self.renderer.builder, color, toDrawVector3(scatterStart), toDrawVector3(scatterEnd))

									if closestTarget is not None:
										break
									else:
										startPoint, direction = newStartPoint + 0.1 * newDirection, newDirection

				self.renderer.end_rendering()

			ballState = None
			if -1 in self.forces:
				if not self.isPaused:
					ballState = BallState(
						# latest_touch=Touch(player_name=packet.game_cars[random.choice(ballTouchers)].name),
						physics=Physics(
							velocity=toVector3(ball_vel + self.forces[-1].velocity * PUSH_STRENGTH_BALL),
							angular_velocity=toVector3(ball_ang + self.forces[-1].angular_velocity * PUSH_STRENGTH_BALL_ANGULAR)
						)
					)
				del self.forces[-1]
			carStates = {}
			for i, force in self.forces.items():
				carStates[i] = CarState(physics=Physics(
					velocity=toVector3(Vec3(packet.game_cars[i].physics.velocity) + self.forces[i].velocity * PUSH_STRENGTH_CAR),
					angular_velocity=toVector3(Vec3(packet.game_cars[i].physics.angular_velocity) + self.forces[i].angular_velocity * PUSH_STRENGTH_CAR_ANGULAR)
				))
			self.forces.clear()
			self.set_game_state(GameState(cars=carStates, ball=ballState))
			
				
			

	def get_player_index_by_name(self, name: str):
		for i in range(self.game_tick_packet.num_cars):
			car = self.game_tick_packet.game_cars[i]
			if car.name == name:
				return i
		return None

	def get_actions_currently_available(self) -> List[AvailableActions]:
		actions = []
		for player in self.known_players:
			actions.append(BotAction(description=f'Make {highlight_player_name(player)} the laser boi',
									 action_type=SET_LASER_BOI,
									 data={PLAYER_NAME: player.name}))
		return [AvailableActions("Laserboi", None, actions)]


if __name__ == '__main__':
	laserboi = Laserboi()
	laserboi.start()



