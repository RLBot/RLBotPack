from dataclasses import dataclass

from data.lookup_table import LookupTable


class AccelerationLUT(LookupTable):
    def __init__(self, file_name: str):
        super().__init__(file_name)
        self.distances = self.get_column('car_loc_x')
        self.times = self.get_column('time')
        self.speeds = self.get_column('car_vel_x')
        assert self.distances and self.times and self.speeds

        # shift times so that it starts at 0
        t0 = self.times[0]
        for i in range(len(self.times)):
            self.times[i] -= t0

    @dataclass
    class LookupResult:
        speed_reached: float
        time_passed: float = 0.0
        distance_traveled: float = 0.0

        speed_limit_reached: bool = False
        time_limit_reached: bool = False
        distance_limit_reached: bool = False

    def simulate_until_limit(self,
                             initial_speed: float,
                             time_limit: float = None,
                             distance_limit: float = None,
                             speed_limit: float = None) -> LookupResult:

        # at least one limit must be set
        assert time_limit or distance_limit or speed_limit

        # limits must be positive
        if time_limit: assert time_limit > 0
        if speed_limit: assert speed_limit > 0
        if distance_limit: assert distance_limit > 0

        if speed_limit: assert speed_limit > initial_speed

        starting_index = self.find_index(self.speeds, initial_speed)
        # TODO: Interpolate
        initial_time = self.times[starting_index]
        initial_distance = self.distances[starting_index]

        last_index = len(self.times) - 1
        time_limit_index = distance_limit_index = speed_limit_index = last_index

        if time_limit: time_limit_index = self.find_index(self.times, initial_time + time_limit)
        if distance_limit: distance_limit_index = self.find_index(self.distances, initial_distance + distance_limit)
        if speed_limit: speed_limit_index = self.find_index(self.speeds, speed_limit)

        final_index = min(time_limit_index, distance_limit_index, speed_limit_index)  # use the soonest reached limit
        if final_index < starting_index: final_index = starting_index

        # TODO: Interpolate values
        return self.LookupResult(
            speed_reached=self.speeds[final_index],
            time_passed=self.times[final_index] - initial_time,
            distance_traveled=self.distances[final_index] - initial_distance,
            distance_limit_reached=distance_limit and final_index == distance_limit_index < last_index,
            speed_limit_reached=speed_limit and final_index == speed_limit_index < last_index,
            time_limit_reached=time_limit and final_index == time_limit_index < last_index
        )


BOOST = AccelerationLUT('acceleration/boost.csv')
THROTTLE = AccelerationLUT('acceleration/throttle.csv')
