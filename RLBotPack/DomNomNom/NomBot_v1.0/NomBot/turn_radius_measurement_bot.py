from utils import main, EasyGameState, clamp01, clamp11, sanitize_output_vector, mag
if __name__ == '__main__':
    main()  # blocking

from quicktracer import trace

from controller_input import controller

# Results!
def estimate_turn_radius(car_speed):
    # https://docs.google.com/spreadsheets/d/1Hhg1TJqVUCcKIRmwvO2KHnRZG1z8K4Qn-UnAf5-Pt64/edit?usp=sharing
    return (
        +156
        +0.1         * car_speed
        +0.000069    * car_speed**2
        +0.000000164 * car_speed**3
        -5.62E-11    * car_speed**4
    )

class Agent:
    def __init__(self, name, team, index):
        self.name = name
        self.team = team
        self.index = index
        self.start_time = None
        self.measurements = []

    def get_output_vector(self, game_tick_packet):
        s = EasyGameState(game_tick_packet, self.team, self.index)
        speed = mag(s.car_vel)
        turn_rate = game_tick_packet.gamecars[self.index].AngularVelocity.Z  # rad/s
        turn_radius = speed/max(turn_rate,0.001)

        if self.start_time is None:
            self.start_time = s.time
        time_elapsed = s.time - self.start_time
        desired_speed = 10 + time_elapsed*100

        too_slow = desired_speed > speed
        should_boost = desired_speed > 1000 and too_slow
        pedal = too_slow
        if desired_speed < 500: pedal *= 0.5

        trace(speed)
        # trace(turn_rate)
        trace(turn_radius)
        # trace(desired_speed)
        trace(turn_radius - estimate_turn_radius(speed))

        output_vector = [
            pedal,  # fThrottle
            1,  # fSteer
            0,  # fPitch
            0,  # fYaw
            0,  # fRoll
            0,  # bJump
            should_boost,  # bBoost
            0,  # bHandbrake
        ]

        if not controller.hat_toggle_west:
            if self.measurements:
                print ('TADA:')
                print (repr(self.measurements))
            output_vector = (
                round(controller.fThrottle),
                round(controller.fSteer),
                round(controller.fPitch),
                round(controller.fYaw),
                round(controller.fRoll),
                round(controller.bJump),
                round(controller.bBoost),
                round(controller.bHandbrake),
            )
            self.start_time = None
            self.measurements = []
        else:
            # self.start_time = s.time
            self.measurements.append((desired_speed, turn_radius))

        return sanitize_output_vector(output_vector)
