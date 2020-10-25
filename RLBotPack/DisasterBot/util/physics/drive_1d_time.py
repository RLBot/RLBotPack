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


def wrap_state_at_time_step(cls):
    """Advances the state to the soonest phase end."""

    cls_max_speed = cls.max_speed
    cls_distance_traveled = cls.distance_traveled
    cls_velocity_reached = cls.velocity_reached
    cls_time_reach_velocity = cls.time_reach_velocity

    if cls.use_boost:

        def distance_state_step(state: State) -> State:
            if cls_max_speed <= state.vel or state.time == 0.0 or state.boost <= 0:
                return state

            time_0_boost = state.boost / BOOST_CONSUMPTION_RATE
            time_vel = cls_time_reach_velocity(cls_max_speed, state.vel)

            if state.time <= time_0_boost and state.time <= time_vel:
                dist = state.dist + cls_distance_traveled(state.time, state.vel)
                vel = cls_velocity_reached(state.time, state.vel)
                boost = state.boost - state.time * BOOST_CONSUMPTION_RATE
                return State(dist, vel, boost, 0.0)

            if time_0_boost < time_vel:
                delta_time = time_0_boost
                vel = cls_velocity_reached(time_0_boost, state.vel)
                boost = 0.0
            else:
                delta_time = time_vel
                vel = cls_max_speed
                boost = state.boost - delta_time * BOOST_CONSUMPTION_RATE

            dist = state.dist + cls_distance_traveled(delta_time, state.vel)
            time = state.time - delta_time

            return State(dist, vel, boost, time)

    else:

        def distance_state_step(state: State) -> State:
            if cls_max_speed <= state.vel or state.time == 0.0:
                return state

            time_vel = cls_time_reach_velocity(cls_max_speed, state.vel)

            if state.time <= time_vel:
                dist = state.dist + cls_distance_traveled(state.time, state.vel)
                vel = cls_velocity_reached(state.time, state.vel)
                return State(dist, vel, state.boost, 0.0)

            dist = state.dist + cls_distance_traveled(time_vel, state.vel)
            time = state.time - time_vel

            return State(dist, cls_max_speed, state.boost, time)

    return jit(distance_state_step, nopython=True, fastmath=True)


state_time_range_negative = wrap_state_at_time_step(VelocityNegative)
state_time_range_0_1400_boost = wrap_state_at_time_step(Velocity0To1400Boost)
state_time_range_0_1400 = wrap_state_at_time_step(Velocity0To1400)
state_time_range_1400_2300 = wrap_state_at_time_step(Velocity1400To2300)


@jit(UniTuple(f8, 3)(f8, f8, f8), nopython=True, fastmath=True, cache=True)
def state_at_time(time: float, initial_velocity: float, boost_amount: float) -> (float, float, float):
    """Returns the state reached (dist, vel, boost)
    after driving forward and using boost and reaching a certain time."""
    if time == 0.0:
        return 0.0, initial_velocity, boost_amount

    state = State(0.0, initial_velocity, boost_amount, time)

    state = state_time_range_negative(state)
    state = state_time_range_0_1400_boost(state)
    state = state_time_range_0_1400(state)
    state = state_time_range_1400_2300(state)

    return state.dist + state.time * state.vel, state.vel, state.boost


@guvectorize(["(f8[:], f8[:], f8[:], f8[:], f8[:], f8[:])"], "(n), (n), (n) -> (n), (n), (n)", nopython=True)
def state_at_time_vectorized(time, initial_velocity, boost_amount, out_dist, out_vel, out_boost) -> None:
    """Returns the states reached (dist[], vel[], boost[]) after driving forward and using boost."""
    for i in range(len(time)):
        out_dist[i], out_vel[i], out_boost[i] = state_at_time(time[i], initial_velocity[i], boost_amount[i])


def main():

    from timeit import timeit
    import numpy as np

    time = np.linspace(0, 6, 360)
    initial_velocity = np.linspace(-2300, 2300, 360)
    boost_amount = np.linspace(0, 100, 360)

    def test_function():
        return state_at_time_vectorized(time, initial_velocity, boost_amount)[0]

    print(test_function())

    fps = 120
    n_times = 10000
    time_taken = timeit(test_function, number=n_times)
    percentage = time_taken * fps / n_times * 100

    print(f"Took {time_taken} seconds to run {n_times} times.")
    print(f"That's {percentage:.5f} % of our time budget.")


if __name__ == "__main__":
    main()
