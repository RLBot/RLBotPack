from __future__ import annotations

import random
from copy import copy
from typing import TYPE_CHECKING

from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Rotator
from rlbot.utils.game_state_util import Vector3 as RLBot3

from objects import Action, TestState
from routines import DiagonalKickoff, GotoBoost, OffCenterKickoff, CenterKickoff, Shadow
from tools import push_shot, setup_3s_kickoff, setup_2s_kickoff, setup_other_kickoff
from utils import closest_boost

if TYPE_CHECKING:
    from hive import MyHivemind


def run_1v1(agent: MyHivemind):
    agent.debug_stack()
    drone = agent.drones[0]
    if agent.kickoff_flag and len(drone.stack) < 1:
        if abs(drone.location.x) < 250:
            drone.push(CenterKickoff())
            drone.action = Action.Going
        elif abs(drone.location.x) < 1000:
            drone.push(OffCenterKickoff())
            drone.action = Action.Going
        else:
            drone.push(DiagonalKickoff())
            drone.action = Action.Going
    elif not agent.kickoff_flag:
        if len(drone.stack) < 1 or drone.action == Action.Shadowing:
            if drone.on_side or agent.conceding:
                push_shot(drone, agent)
        if len(drone.stack) < 1:
            drone.push(Shadow(agent.ball.location))
            drone.action = Action.Shadowing


def run_hivemind(agent: MyHivemind):
    agent.debug_stack()
    if agent.kickoff_flag and all(len(drone.stack) < 1 for drone in agent.drones):
        if len(agent.friends + agent.drones) == 3:
            setup_3s_kickoff(agent)
        elif len(agent.friends + agent.drones) == 2:
            setup_2s_kickoff(agent)
        else:
            setup_other_kickoff(agent)
    elif not agent.kickoff_flag:
        for drone in agent.drones:
            drones = copy(agent.drones)
            drones.remove(drone)
            team = agent.friends + drones
            if len(drone.stack) < 1 or drone.action == Action.Shadowing:
                if drone.on_side and drone.closest or agent.conceding:
                    push_shot(drone, agent)
            if len(drone.stack) < 1:
                if drone.action == Action.Going:
                    if any(teammate.on_side for teammate in team):
                        drone.push(GotoBoost(closest_boost(agent, drone.location)))
                        drone.action = Action.Boost
                    else:
                        drone.push(Shadow(agent.ball.location))
                        drone.action = Action.Shadowing
                elif drone.action == Action.Shadowing:
                    drone.push(Shadow(agent.ball.location))
                    drone.action = Action.Shadowing
                elif drone.action == Action.Boost:
                    drone.push(Shadow(agent.ball.location))
                    drone.action = Action.Shadowing


def run_test(agent: MyHivemind):
    agent.debug_stack()
    next_state = agent.test_state
    if agent.test_state == TestState.Reset:
        agent.test_time = agent.time

        b_position = RLBot3(random.uniform(-1500, 1500),
                            random.uniform(2500, 3500),
                            random.uniform(300, 500))

        b_velocity = RLBot3(random.uniform(-300, 300),
                            random.uniform(-100, 100),
                            random.uniform(900, 1000))

        ball_state = BallState(physics=Physics(
            location=b_position,
            velocity=b_velocity,
            rotation=Rotator(0, 0, 0),
            angular_velocity=RLBot3(0, 0, 0)
        ))

        # this just initializes the car and ball
        # to different starting points each time
        c_position = RLBot3(b_position.x, 0 * random.uniform(-1500, -1000), 25)

        # c_position = Vector3(200, -1000, 25)
        car_state = CarState(physics=Physics(
            location=c_position,
            velocity=RLBot3(0, 800, 0),
            rotation=Rotator(0, 1.6, 0),
            angular_velocity=RLBot3(0, 0, 0)
        ), boost_amount=100)

        agent.set_game_state(GameState(
            ball=ball_state,
            cars={agent.drones[0].index: car_state})
        )

        next_state = TestState.Wait
    elif agent.test_state == TestState.Wait:
        if agent.time - agent.test_time > 0.2:
            next_state = TestState.Init
    elif agent.test_state == TestState.Init:
        push_shot(agent.drones[0], agent)
        next_state = TestState.Running
    elif agent.test_state == TestState.Running:
        if agent.time - agent.test_time > 5:
            next_state = TestState.Reset
            agent.drones[0].clear()
    agent.test_state = next_state
