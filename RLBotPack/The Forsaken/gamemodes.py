from __future__ import annotations

from copy import copy
from typing import TYPE_CHECKING

from objects import Action
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
        on_side = (drone.location - agent.friend_goal.location).magnitude() < (
                agent.ball.location - agent.friend_goal.location).magnitude()
        if len(drone.stack) < 1:
            if drone.action == Action.Going:
                if on_side and (drone.location - agent.ball.location).magnitude() < 2000:
                    push_shot(drone, agent)
                if len(drone.stack) < 1:
                    drone.push(Shadow(agent.ball.location))
                    drone.action = Action.Shadowing
            elif drone.action == Action.Shadowing:
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
            if len(drone.stack) < 1:
                if drone.action == Action.Going:
                    if drone.on_side and drone.closest or agent.conceding:
                        push_shot(drone, agent)
                    if len(drone.stack) < 1:
                        if any(teammate.on_side for teammate in team):
                            drone.push(GotoBoost(closest_boost(agent, drone.location)))
                            drone.action = Action.Boost
                        else:
                            drone.push(Shadow(agent.ball.location))
                            drone.action = Action.Shadowing
                elif drone.action == Action.Shadowing:
                    if drone.on_side and drone.closest or agent.conceding:
                        push_shot(drone, agent)
                    if len(drone.stack) < 1:
                        drone.push(Shadow(agent.ball.location))
                        drone.action = Action.Shadowing
                elif drone.action == Action.Boost:
                    drone.push(Shadow(agent.ball.location))
                    drone.action = Action.Shadowing
            elif drone.action == Action.Shadowing:
                if drone.on_side and drone.closest or agent.conceding:
                    push_shot(drone, agent)
