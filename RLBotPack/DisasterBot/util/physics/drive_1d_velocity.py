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


def wrap_state_at_velocity_step(cls):
    """Advances the state to the soonest phase end."""

    cls_max_speed = cls.max_speed
    cls_velocity_reached = cls.velocity_reached
    cls_time_reach_velocity = cls.time_reach_velocity
    cls_distance_traveled = cls.distance_traveled

    if cls.use_boost:

        def time_reach_velocity_step(state: State, desired_vel: float) -> State:
            if cls_max_speed <= state.vel or desired_vel <= state.vel or state.boost <= 0:
                return state

            time_0_boost = state.boost / BOOST_CONSUMPTION_RATE
            time_vel = cls_time_reach_velocity(cls_max_speed, state.vel)
            vel_0_boost = cls_velocity_reached(time_0_boost, state.vel)

            if desired_vel <= vel_0_boost and desired_vel <= cls_max_speed:
                delta_time = cls_time_reach_velocity(desired_vel, state.vel)
                dist = state.dist + cls_distance_traveled(delta_time, state.vel)
                boost = state.boost - delta_time * BOOST_CONSUMPTION_RATE
                time = state.time + delta_time
                return State(dist, desired_vel, boost, time)

            if time_0_boost < time_vel:
                dist = state.dist + cls_distance_traveled(time_0_boost, state.vel)
                velocity = vel_0_boost
                boost = 0
                time = state.time + time_0_boost
            else:
                dist = state.dist + cls_distance_traveled(time_vel, state.vel)
                velocity = cls_max_speed
                boost = state.boost - time_vel * BOOST_CONSUMPTION_RATE
                time = state.time + time_vel

            return State(dist, velocity, boost, time)

    else:

        def time_reach_velocity_step(state: State, desired_vel: float) -> State:
            rel_sign = 1 if state.vel < desired_vel else -1
            if cls_max_speed <= rel_sign * state.vel or desired_vel == state.vel:
                return state

            if rel_sign * desired_vel <= cls_max_speed:
                delta_time = cls_time_reach_velocity(desired_vel * rel_sign, state.vel * rel_sign)
                velocity = desired_vel

            else:
                delta_time = cls_time_reach_velocity(cls_max_speed * rel_sign, state.vel * rel_sign)
                velocity = cls_max_speed * rel_sign

            dist = state.dist + cls_distance_traveled(delta_time, state.vel * rel_sign) * rel_sign
            time = state.time + delta_time

            return State(dist, velocity, state.boost, time)

    return jit(time_reach_velocity_step, nopython=True, fastmath=True)


state_velocity_step_range_negative = wrap_state_at_velocity_step(VelocityNegative)
state_velocity_step_range_0_1400_boost = wrap_state_at_velocity_step(Velocity0To1400Boost)
state_velocity_step_range_0_1400 = wrap_state_at_velocity_step(Velocity0To1400)
state_velocity_step_range_1400_2300 = wrap_state_at_velocity_step(Velocity1400To2300)


@jit(UniTuple(f8, 3)(f8, f8, f8), nopython=True, fastmath=True, cache=True)
def state_at_velocity(desired_velocity: float, initial_velocity: float, boost_amount: float) -> (float, float, float):
    """Returns the time it takes to reach any desired velocity including those that require reversing."""
    state = State(0.0, initial_velocity, boost_amount, 0.0)

    state = state_velocity_step_range_negative(state, desired_velocity)
    state = state_velocity_step_range_0_1400_boost(state, desired_velocity)
    state = state_velocity_step_range_0_1400(state, desired_velocity)
    state = state_velocity_step_range_1400_2300(state, desired_velocity)

    if desired_velocity != state.vel:
        return 10.0, 10000.0, state.boost
    return state.time, state.dist, state.boost


@guvectorize(["(f8[:], f8[:], f8[:], f8[:], f8[:], f8[:])"], "(n), (n), (n) -> (n), (n), (n)", nopython=True)
def state_at_velocity_vectorized(
    desired_velocity, initial_velocity, boost_amount, out_time, out_dist, out_boost
) -> None:
    for i in range(len(desired_velocity)):
        out_time[i], out_dist[i], out_boost[i] = state_at_velocity(
            desired_velocity[i], initial_velocity[i], boost_amount[i]
        )


def main():

    from timeit import timeit
    import numpy as np

    initial_velocity = np.linspace(-2300, 2300, 360)
    desired_vel = -initial_velocity
    boost_amount = np.linspace(0, 100, 360)

    def test_function():
        return state_at_velocity_vectorized(desired_vel, initial_velocity, boost_amount)

    print(test_function())

    fps = 120
    n_times = 10000
    time_taken = timeit(test_function, number=n_times)
    percentage = time_taken * fps / n_times * 100

    print(f"Took {time_taken} seconds to run {n_times} times.")
    print(f"That's {percentage:.5f} % of our time budget.")


if __name__ == "__main__":
    main()
