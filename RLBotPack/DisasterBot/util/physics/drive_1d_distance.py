from numba import jit, f8, guvectorize
from numba.types import UniTuple

from util.physics.drive_1d_solutions import (
    State,
    VelocityNegative,
    Velocity0To1400Boost,
    Velocity0To1400,
    Velocity1400To2300,
    BOOST_CONSUMPTION_RATE,
)


def wrap_state_at_distance_step(cls):
    """Advances the state to the soonest phase end."""

    cls_max_speed = cls.max_speed
    cls_distance_traveled = cls.distance_traveled
    cls_velocity_reached = cls.velocity_reached
    cls_time_reach_velocity = cls.time_reach_velocity
    cls_time_travel_distance = cls.time_travel_distance

    if cls.use_boost:

        def time_travel_distance_state_step(state: State) -> State:
            if cls_max_speed <= state.vel or state.dist == 0.0 or state.boost <= 0:
                return state

            time_0_boost = state.boost / BOOST_CONSUMPTION_RATE
            time_vel = cls_time_reach_velocity(cls_max_speed, state.vel)

            if time_0_boost <= time_vel:
                dist_0_boost = cls_distance_traveled(time_0_boost, state.vel)
                if state.dist >= dist_0_boost:
                    time = state.time + time_0_boost
                    vel = cls_velocity_reached(time_0_boost, state.vel)
                    dist = state.dist - dist_0_boost
                    return State(dist, vel, 0.0, time)
            else:
                dist_vel = cls_distance_traveled(time_vel, state.vel)
                if state.dist >= dist_vel:
                    time = state.time + time_vel
                    dist = state.dist - dist_vel
                    boost = state.boost - time_vel * BOOST_CONSUMPTION_RATE
                    return State(dist, cls_max_speed, boost, time)

            delta_time = cls_time_travel_distance(state.dist, state.vel)
            time = state.time + delta_time
            vel = cls_velocity_reached(delta_time, state.vel)
            boost = state.boost - delta_time * BOOST_CONSUMPTION_RATE

            return State(0.0, vel, boost, time)

    else:

        def time_travel_distance_state_step(state: State) -> State:
            if cls_max_speed <= state.vel or state.dist == 0.0:
                return state

            time_vel = cls_time_reach_velocity(cls_max_speed, state.vel)
            dist_vel = cls_distance_traveled(time_vel, state.vel)

            if state.dist <= dist_vel:
                delta_time = cls_time_travel_distance(state.dist, state.vel)
                time = state.time + delta_time
                vel = cls_velocity_reached(delta_time, state.vel)
                return State(0.0, vel, state.boost, time)
            else:
                time = state.time + time_vel
                vel = cls_max_speed
                dist = state.dist - dist_vel
                return State(dist, vel, state.boost, time)

    return jit(time_travel_distance_state_step, nopython=True, fastmath=True)


state_distance_step_range_negative = wrap_state_at_distance_step(VelocityNegative)
state_distance_step_range_0_1400_boost = wrap_state_at_distance_step(Velocity0To1400Boost)
state_distance_step_range_0_1400 = wrap_state_at_distance_step(Velocity0To1400)
state_distance_step_range_1400_2300 = wrap_state_at_distance_step(Velocity1400To2300)


@jit(UniTuple(f8, 3)(f8, f8, f8), nopython=True, fastmath=True, cache=True)
def state_at_distance(distance: float, initial_velocity: float, boost_amount: float) -> (float, float, float):
    """Returns the state reached (time, vel, boost)
    after driving forward and using boost and reaching a certain distance."""

    if distance == 0:
        return 0.0, initial_velocity, boost_amount

    state = State(distance, initial_velocity, boost_amount, 0.0)

    state = state_distance_step_range_negative(state)
    state = state_distance_step_range_0_1400_boost(state)
    state = state_distance_step_range_0_1400(state)
    state = state_distance_step_range_1400_2300(state)

    return state.time + state.dist / max(state.vel, 1e-9), state.vel, state.boost


@guvectorize(["(f8[:], f8[:], f8[:], f8[:], f8[:], f8[:])"], "(n), (n), (n) -> (n), (n), (n)", nopython=True)
def state_at_distance_vectorized(distance, initial_velocity, boost_amount, out_time, out_vel, out_boost) -> None:
    """Returns the states reached (time[], vel[], boost[])
    after driving forward and using boost and reaching a certain distance."""
    for i in range(len(distance)):
        out_time[i], out_vel[i], out_boost[i] = state_at_distance(distance[i], initial_velocity[i], boost_amount[i])


def main():

    from timeit import timeit
    import numpy as np

    initial_velocity = np.linspace(-2300, 2300, 360)
    desired_dist = np.linspace(0, 6000, 360)
    boost_amount = np.linspace(0, 100, 360)

    def test_function():
        return state_at_distance_vectorized(desired_dist, initial_velocity, boost_amount)

    print(test_function())

    fps = 120
    n_times = 10000
    time_taken = timeit(test_function, number=n_times)
    percentage = time_taken * fps / n_times * 100

    print(f"Took {time_taken} seconds to run {n_times} times.")
    print(f"That's {percentage:.5f} % of our time budget.")


if __name__ == "__main__":
    main()
