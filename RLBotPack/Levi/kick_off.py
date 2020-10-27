import random

from RLUtilities.LinearAlgebra import vec3, normalize
from RLUtilities.Maneuvers import Drive, AirDodge

from util import get_closest_small_pad, sign, distance_2d, z0


def init_kick_off(agent):
    if abs(agent.info.my_car.pos[0]) < 250:
        pad = get_closest_small_pad(agent)
        target = vec3(pad.pos[0], pad.pos[1], pad.pos[2]) - sign(agent.team) * vec3(0, 500, 0)
        agent.drive = Drive(agent.info.my_car, target, 2400)
        agent.kickoffStart = "Center"
    elif abs(agent.info.my_car.pos[0]) < 1000:
        target = agent.info.ball.pos
        agent.drive = Drive(agent.info.my_car, target, 2400)
        agent.kickoffStart = "offCenter"
    else:
        if random.choice([True, False]):
            pad = get_closest_small_pad(agent)
            vec3_pad = vec3(pad.pos[0], pad.pos[1], pad.pos[2])
            car_to_pad = vec3_pad - agent.info.my_car.pos
            target = agent.info.my_car.pos + 1 * car_to_pad
            agent.drive = Drive(agent.info.my_car, target, 2300)
            agent.kickoffStart = "Diagonal_Scrub"
        else:
            target = agent.info.ball.pos
            agent.drive = Drive(agent.info.my_car, target, 2400)
            agent.kickoffStart = "Diagonal"
    agent.step = "Drive"
    agent.drive.step(agent.FPS)
    agent.controls = agent.drive.controls


def kick_off(agent):
    if agent.kickoffStart == "Diagonal_Scrub":
        if agent.step == "Drive":
            agent.drive.step(agent.FPS)
            agent.controls = agent.drive.controls
            if agent.drive.finished:
                agent.step = "Dodge1"
                # target = agent.info.ball.pos
                target = normalize(z0(agent.info.my_car.forward())) * 1000
                agent.dodge = AirDodge(agent.info.my_car, 0.075, target)
        elif agent.step == "Dodge1":
            agent.dodge.step(agent.FPS)
            agent.controls = agent.dodge.controls
            if agent.dodge.finished:
                agent.step = "Steer"
                target = agent.info.ball.pos
                agent.drive = Drive(agent.info.my_car, target, 1399)
        elif agent.step == "Steer":
            agent.drive.step(agent.FPS)
            agent.controls = agent.drive.controls
            if agent.info.my_car.on_ground:
                agent.drive.target_speed = 2400
            if distance_2d(agent.info.ball.pos, agent.info.my_car.pos) < 750:
                agent.step = "Dodge2"
                agent.dodge = AirDodge(agent.info.my_car, 0.075, agent.info.ball.pos)
        elif agent.step == "Dodge2":
            agent.dodge.step(agent.FPS)
            agent.controls = agent.dodge.controls
            if agent.dodge.finished and agent.info.my_car.on_ground:
                agent.step = "Catching"
    elif agent.kickoffStart == "Diagonal":
        if agent.step == "Drive":
            agent.drive.step(agent.FPS)
            agent.controls = agent.drive.controls
            if distance_2d(agent.info.ball.pos, agent.info.my_car.pos) < 850:
                agent.step = "Dodge"
                agent.dodge = AirDodge(agent.info.my_car, 0.075, agent.info.ball.pos)
        elif agent.step == "Dodge":
            agent.dodge.step(agent.FPS)
            agent.controls = agent.dodge.controls
            if agent.dodge.finished and agent.info.my_car.on_ground:
                agent.step = "Catching"
    elif agent.kickoffStart == "Center":
        if agent.step == "Drive":
            agent.drive.step(agent.FPS)
            agent.controls = agent.drive.controls
            if agent.drive.finished:
                agent.step = "Dodge1"
                agent.dodge = AirDodge(agent.info.my_car, 0.075, agent.info.ball.pos)
        elif agent.step == "Dodge1":
            agent.dodge.step(agent.FPS)
            agent.controls = agent.dodge.controls
            agent.controls.boost = 0
            if agent.dodge.finished and agent.info.my_car.on_ground:
                agent.step = "Steer"
                target = agent.info.ball.pos + sign(agent.team) * vec3(0, 850, 0)
                agent.drive = Drive(agent.info.my_car, target, 2400)
        elif agent.step == "Steer":
            agent.drive.step(agent.FPS)
            agent.controls = agent.drive.controls
            if agent.drive.finished:
                agent.step = "Dodge2"
                agent.dodge = AirDodge(agent.info.my_car, 0.075, agent.info.ball.pos)
        elif agent.step == "Dodge2":
            agent.dodge.step(agent.FPS)
            agent.controls = agent.dodge.controls
            if agent.dodge.finished and agent.info.my_car.on_ground:
                agent.step = "Catching"
    elif agent.kickoffStart == "offCenter":
        if agent.step == "Drive":
            agent.drive.step(agent.FPS)
            agent.controls = agent.drive.controls
            if agent.info.my_car.boost < 15 or agent.drive.finished:
                agent.step = "Dodge1"
                agent.dodge = AirDodge(agent.info.my_car, 0.075, agent.info.ball.pos)
        elif agent.step == "Dodge1":
            agent.dodge.step(agent.FPS)
            agent.controls = agent.dodge.controls
            agent.controls.boost = 0
            if agent.dodge.finished and agent.info.my_car.on_ground:
                agent.step = "Steer"
                target = agent.info.ball.pos
                agent.drive = Drive(agent.info.my_car, target, 2400)
        elif agent.step == "Steer":
            agent.drive.step(agent.FPS)
            agent.controls = agent.drive.controls
            if distance_2d(agent.info.ball.pos, agent.info.my_car.pos) < 850:
                agent.step = "Dodge2"
                agent.dodge = AirDodge(agent.info.my_car, 0.075, agent.info.ball.pos)
        elif agent.step == "Dodge2":
            agent.dodge.step(agent.FPS)
            agent.controls = agent.dodge.controls
            if agent.dodge.finished and agent.info.my_car.on_ground:
                agent.step = "Catching"
