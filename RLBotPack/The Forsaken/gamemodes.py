from __future__ import annotations

from copy import copy
from typing import TYPE_CHECKING

from kickoffs import setup_3s_kickoff, setup_2s_kickoff, setup_other_kickoff
from objects import Action
from routines import KickOff, GotoBoost, Shadow
from tools import find_any_shot, find_shot
from utils import closest_boost

if TYPE_CHECKING:
    from hive import MyHivemind
    from objects import CarObject


def run_1v1(agent: MyHivemind):
    agent.debug_stack()
    drone: CarObject = agent.drones[0]
    if agent.kickoff_flag and len(drone.stack) < 1:
        drone.push(KickOff())
        drone.action = Action.Going
    elif not agent.kickoff_flag:
        if len(drone.stack) < 1 or drone.action == Action.Shadowing:
            if drone.on_side or agent.conceding:
                shot = find_shot(drone, (agent.foe_goal.left_post, agent.foe_goal.right_post))
                if shot is not None:
                    shot = find_shot(drone, (agent.foe_goal.left_post, agent.foe_goal.right_post))
                if shot is not None:
                    drone.push(shot)
                    drone.action = Action.Going
                else:
                    my_shot = find_any_shot(drone)
                    enemy_shot = find_any_shot(agent.foes[0])
                    if my_shot is not None:
                        if enemy_shot is None:
                            drone.push(my_shot)
                            drone.action = Action.Going
                        elif my_shot.intercept_time < enemy_shot.intercept_time or agent.desperate:
                            drone.push(my_shot)
                            drone.action = Action.Going
        if len(drone.stack) < 1:
            drone.push(Shadow())
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
            empty_stack = len(drone.stack) < 1 and drone.on_side and drone.closest
            should_go = (
                                drone.action == Action.Shadowing) and drone.on_side and drone.closest
            conceding = (agent.conceding and not any(teammate.on_side for teammate in team)) or (
                    agent.conceding and drone.on_side and drone.closest)
            cheating = drone.action == Action.Cheating
            if empty_stack or should_go or conceding or cheating:
                if empty_stack or drone.stack[0].__class__.__name__ not in ["GroundShot", "JumpShot", "DoubleJump"]:
                    shot = find_any_shot(drone)
                    if shot is not None:
                        drone.push(shot)
                        drone.action = Action.Going
            if len(drone.stack) < 1:
                if drone.action == Action.Going:
                    if any(teammate.on_side for teammate in team) and drone.boost < 66:
                        drone.push(GotoBoost(closest_boost(agent, drone.location)))
                        drone.action = Action.Boost
                    else:
                        drone.push(Shadow())
                        drone.action = Action.Shadowing
                elif drone.action == Action.Shadowing:
                    if all(teammate.on_side for teammate in team) and drone.boost < 66:
                        drone.push(GotoBoost(closest_boost(agent, drone.location)))
                        drone.action = Action.Boost
                    else:
                        drone.push(Shadow())
                        drone.action = Action.Shadowing
                elif drone.action == Action.Boost:
                    drone.push(Shadow())
                    drone.action = Action.Shadowing
