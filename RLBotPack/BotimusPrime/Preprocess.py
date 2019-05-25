from Objects import *
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket, FieldInfoPacket
import time


def preprocess(self, data: GameTickPacket):

    self.output = SimpleControllerState()

    #ball object
    ball.location = Vector3(data.game_ball.physics.location)
    ball.velocity = Vector3(data.game_ball.physics.velocity)
    ball.av = Vector3(data.game_ball.physics.angular_velocity)
    ball.rotation = ball.velocity.to_rotation()

    #this bot object
    car = data.game_cars[self.index]
    self.location = Vector3(car.physics.location)
    self.rotation.set_from_rotator(car.physics.rotation)
    self.velocity = Vector3(car.physics.velocity)

    self.on_ground = car.has_wheel_contact
    self.boost = car.boost
    self.supersonic = car.is_super_sonic
    self.speed = self.velocity.size

    #other bots
    self.opponents = list()
    self.teammates = list()
    for car in data.game_cars:
        if car.name == self.name:
            continue
        
        bot = GameObject()
        bot.location = Vector3(car.physics.location)
        bot.rotation.set_from_rotator(car.physics.rotation)
        bot.velocity = Vector3(car.physics.velocity)

        bot.on_ground = car.has_wheel_contact
        bot.boost = car.boost
        bot.supersonic = car.is_super_sonic
        bot.speed = self.velocity.size

        if car.team == self.team:
            self.teammates.append(bot)
        else:
            self.opponents.append(bot)

    #boosts
    self.boost_pads = data.game_boosts
    self.boost_locations = self.get_field_info().boost_pads
