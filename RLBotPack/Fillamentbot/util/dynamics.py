import math

def max_d_in_t_boostless(time:float,initial_velocity:float,cap_vel:float=1400) -> float:
    #calculates the distance that the car will travel in a time, on the ground, holding full throttle and no boost.
    braking_dist = 0
    if initial_velocity<0:
        braking_time =  initial_velocity/-3500
        braking_dist = 1750*braking_time**2 + initial_velocity*braking_time
        time -= braking_time
        if time <0:
            return braking_dist
        initial_velocity = 0

    if initial_velocity>cap_vel:
        return initial_velocity * time
    else:
        if time < math.log((1600-initial_velocity)/(1600-cap_vel)):
            return 1600*time - (1600-initial_velocity)*(1-math.e**(-time)) + braking_dist
        else:
            return 1400*time + (1600-cap_vel)*math.log((1600-initial_velocity)/(1600-cap_vel)) - (1600-initial_velocity)*(1-(1600-cap_vel)/(1600-initial_velocity)) + braking_dist

def max_d_in_t_boost(time:float,initial_velocity:float,boost:int,cap_vel:float=1400):
    #returns the max distance, including boost. Extention of the boostless calculation
    if boost/33.3 < time:
        return initial_velocity*time + .5*992*time**2 if (2300-initial_velocity)/992>time else initial_velocity*(2300-initial_velocity)/992 + .5*992*((2300-initial_velocity)/992)**2+2300*(time-(2300-initial_velocity)/992)
    else:
        return initial_velocity*(boost/33.3) + .5*992*(boost/33.3)**2 + max_d_in_t_boostless(time-boost/33.3,initial_velocity+992*boost/33.3) if (2300-initial_velocity)/992>boost/33.3 else initial_velocity*((2300-initial_velocity)/992) + .5*992*((2300-initial_velocity)/992)**2 + max_d_in_t_boostless(time-(2300-initial_velocity)/992,initial_velocity+992*(2300-initial_velocity)/992)

def max_v_in_t_boostless(time:float,initial_velocity:float) -> float:
    #calculates max speed that the car will reach in a time, on the ground, holding full throttle and no boost.
    if initial_velocity<0:
        braking_time =  initial_velocity/-3500
        time -= braking_time
        if time < 0:
            return time*-3500 + initial_velocity
        initial_velocity = 0

    elif initial_velocity>1400:
        return initial_velocity
    else:
        if time < math.log((1600-initial_velocity)/200):
            return 1600 - (1600-initial_velocity)*math.e**(-time)
        else:
            return 1400

def max_v_in_t_boost(time:float,initial_velocity:float,boost:int,cap_vel:float=1400):
    if boost/33.3 > time:
        return min(initial_velocity + 992*time,2300)
    else:
        return max_v_in_t_boostless(time-boost/33.3,min(initial_velocity + 992*boost/33.3,2300))

def acceleration_time(initial_velocity:float, target_velocity:float, boost:int):
    #returns how long it will take to accelerate to a velocity
    if target_velocity > 1400 and boost==0:
        return None
    if target_velocity <= initial_velocity:
        return (initial_velocity-target_velocity)/3500
    else:
        if (target_velocity-initial_velocity)<992*boost/33.3:
            return (target_velocity-initial_velocity)/992
        else:
            if target_velocity >1400:
                return None
            else:
                return boost/33.3 + math.log((1600-(initial_velocity+992*boost/33.3))/(1600-target_velocity))

def find_speed_cap_boostless(time:float, initial_velocity:float, target_distance:float,precision:float=20) -> float:
    #finds the speed to cap an approach at to cover a distance
    cap = 700
    found_dist=0
    if initial_velocity <= cap:
        found_dist=max_d_in_t_boostless(time,initial_velocity,cap)
    else:
        #grown from considering braking time in motion integration
        found_dist = initial_velocity*time - 1750*time**2 if time < (initial_velocity-cap)/3500 else cap*(time-(initial_velocity-cap)/3500) + (initial_velocity**2-initial_velocity*cap)/3500 - 1750*(initial_velocity-cap)**2/3500**2
    i=1
    while abs(found_dist-target_dist)>precision:
        i+=1
        cap += math.copysign(700/i,found_dist-target_distance)
        if initial_velocity <= cap:
            found_dist=max_d_in_t_boostless(time,initial_velocity,cap)
        else:
            found_dist = initial_velocity*time - 1750*time**2 if time < (initial_velocity-cap)/3500 else cap*(time-(initial_velocity-cap)/3500) + (initial_velocity**2-initial_velocity*cap)/3500 - 1750*(initial_velocity-cap)**2/3500**2
    
    return cap

def arc_height(velocity, height):
    #returns the max height of the ball's current arc
    return velocity**2 / 1300 + height

def single_jump_time(change_in_height):
    #returns how long it takes to reach a height in a single jump
    s = change_in_height
    if s<74:
        return (-288+math.sqrt(288**2-4*404*-s))/808
    else:
        return 0.2 + (-450+math.sqrt(450**2-4*-325*(74-s)))/-650

def double_jump_time(change_in_height):
    #returns how long it takes to reach a height in a double jump
    s = change_in_height
    if s<74:
        return (-288+math.sqrt(288**2-4*404*-s))/808
    else:
        return 0.2 + (-742+math.sqrt(742**2-4*-325*(74-s)))/-650

def turn_radius(v):
    #returns the radius of a turn at max steer, given velocity
    if v == 0:
        return 0
    return 1.0 / curvature(v)

# v is the magnitude of the velocity in the car's forward direction
def curvature(v):
    if 0.0 <= v < 500.0:
        return 0.006900 - 5.84e-6 * v
    if 500.0 <= v < 1000.0:
        return 0.005610 - 3.26e-6 * v
    if 1000.0 <= v < 1500.0:
        return 0.004300 - 1.95e-6 * v
    if 1500.0 <= v < 1750.0:
        return 0.003025 - 1.1e-6 * v
    if 1750.0 <= v:
        return 0.001800 - 4e-7 * v

    return 0.0