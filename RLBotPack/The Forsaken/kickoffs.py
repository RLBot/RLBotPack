from __future__ import annotations

from typing import TYPE_CHECKING

from objects import Action
from routines import KickOff, GotoBoost, Shadow, Goto
from utils import closest_boost

if TYPE_CHECKING:
    from hive import MyHivemind


def setup_2s_kickoff(agent: MyHivemind):
    x_pos = [round(drone.location.x) for drone in agent.drones]
    x_pos.extend([round(friend.location.x) for friend in agent.friends])
    if sorted(x_pos) == [-2048, 2048]:
        for drone in agent.drones:
            if round(drone.location.x) == agent.side() * -2048:
                drone.push(KickOff())
                drone.action = Action.Going
            elif round(drone.location.x) == agent.side() * 2048:
                drone.push(Shadow())
                drone.action = Action.Shadowing
    elif sorted(x_pos) == [-256, 256]:
        for drone in agent.drones:
            if round(drone.location.x) == agent.side() * -256:
                drone.push(KickOff())
                drone.action = Action.Going
            elif round(drone.location.x) == agent.side() * 256:
                drone.push(Shadow())
                drone.action = Action.Shadowing
    elif -2048 in x_pos or 2048 in x_pos:
        for drone in agent.drones:
            if round(abs(drone.location.x)) == 2048:
                drone.push(KickOff())
                drone.action = Action.Going
            else:
                drone.push(Shadow())
                drone.action = Action.Shadowing
    elif -256 in x_pos or 256 in x_pos:
        for drone in agent.drones:
            if round(abs(drone.location.x)) == 256:
                drone.push(KickOff())
                drone.action = Action.Going
            else:
                drone.push(Shadow())
                drone.action = Action.Shadowing


def setup_3s_kickoff(agent: MyHivemind):
    x_pos = [round(drone.location.x) for drone in agent.drones]
    x_pos.extend([round(friend.location.x) for friend in agent.friends])
    if sorted(x_pos) in [[-2048, -256, 2048], [-2048, 0, 2048], [-2048, 256, 2048]]:
        for drone in agent.drones:
            if round(drone.location.x) == agent.side() * -2048:
                drone.push(KickOff())
                drone.action = Action.Going
            elif round(drone.location.x) == agent.side() * 2048:
                target = agent.friend_goal.location + 2 * (agent.ball.location - agent.friend_goal.location) / 3
                drone.push(Goto(target))
                drone.action = Action.Cheating
            else:
                drone.push(GotoBoost(closest_boost(agent, drone.location)))
                drone.action = Action.Boost
    elif sorted(x_pos) == [-256, 0, 256]:
        for drone in agent.drones:
            if round(drone.location.x) == agent.side() * -256:
                drone.push(KickOff())
                drone.action = Action.Going
            elif round(drone.location.x) == agent.side() * 256:
                target = agent.friend_goal.location + 2 * (agent.ball.location - agent.friend_goal.location) / 3
                drone.push(Goto(target))
                drone.action = Action.Cheating
            else:
                drone.push(GotoBoost(closest_boost(agent, drone.location)))
                drone.action = Action.Boost
    elif -2048 in x_pos or 2048 in x_pos:
        for drone in agent.drones:
            if round(abs(drone.location.x)) == 2048:
                drone.push(KickOff())
                drone.action = Action.Going
            elif round(drone.location.x) == agent.side() * -256:
                target = agent.friend_goal.location + 2 * (agent.ball.location - agent.friend_goal.location) / 3
                drone.push(Goto(target))
                drone.action = Action.Cheating
            elif round(drone.location.x) == 0:
                drone.push(GotoBoost(closest_boost(agent, drone.location)))
                drone.action = Action.Boost
            else:
                if 0 in x_pos:
                    target = agent.friend_goal.location + 2 * (agent.ball.location - agent.friend_goal.location) / 3
                    drone.push(Goto(target))
                    drone.action = Action.Cheating
                else:
                    drone.push(GotoBoost(closest_boost(agent, drone.location)))
                    drone.action = Action.Boost


def setup_other_kickoff(agent: MyHivemind):
    x_pos = [round(drone.location.x) for drone in agent.drones]
    x_pos.extend([round(friend.location.x) for friend in agent.friends])
    for drone in agent.drones:
        if round(drone.location.x) == -2048:
            drone.push(KickOff())
            drone.action = Action.Going
        elif round(drone.location.x) == 2048:
            if -2048 in x_pos:
                drone.push(Shadow())
                drone.action = Action.Shadowing
            else:
                drone.push(KickOff())
                drone.action = Action.Going
        else:
            drone.push(Shadow())
            drone.action = Action.Shadowing
