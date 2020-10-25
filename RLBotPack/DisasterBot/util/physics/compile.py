import setuptools
from numba.pycc import CC

from numba import jit, typeof
import numpy as np

from util.physics.drive_1d_distance import state_at_distance
from util.physics.drive_1d_time import state_at_time
from util.physics.drive_1d_velocity import state_at_velocity


def state_vectorize(function):
    def vectorized_function(arg1, arg2, arg3):
        output = np.empty((3, len(arg1)), dtype=np.float64)
        for i in range(len(arg1)):
            output[:, i] = function(arg1[i], arg2[i], arg3[i])
        return output

    return jit(nopython=True, fastmath=True)(vectorized_function)


out_type = typeof(np.empty((3, 9), dtype=np.float64))
arg_type = typeof(np.empty((9,), dtype=np.float64))


if __name__ == "__main__":
    cc = CC("drive_1d_distance")

    cc.export("state_at_distance", "UniTuple(f8, 3)(f8, f8, f8)")(state_at_distance)
    cc.export("state_at_distance_vectorized", out_type(arg_type, arg_type, arg_type))(
        state_vectorize(state_at_distance)
    )
    cc.compile()

    cc = CC("drive_1d_time")
    cc.export("state_at_time", "UniTuple(f8, 3)(f8, f8, f8)")(state_at_time)
    cc.export("state_at_time_vectorized", out_type(arg_type, arg_type, arg_type))(state_vectorize(state_at_time))
    cc.compile()

    cc = CC("drive_1d_velocity")
    cc.export("state_at_velocity", "UniTuple(f8, 3)(f8, f8, f8)")(state_at_velocity)
    cc.export("state_at_velocity_vectorized", out_type(arg_type, arg_type, arg_type))(
        state_vectorize(state_at_velocity)
    )
    cc.compile()
