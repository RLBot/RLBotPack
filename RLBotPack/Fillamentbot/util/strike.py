from rlbot.agents.base_agent import SimpleControllerState

from util.car_model import Car, Ball
from util.vec import Vec3
from util.sequence import Sequence, ControlStep
from util.mechanics import *
from util.ball_prediction_analysis import find_slice_at_time, find_slices_around_time
from util.dynamics import *

from enum import Enum
import math

#shot enum
class strike_types(Enum):
    simple_linear = 0
    linear_jump = 1
    linear_dblj = 2

#stores the info required to make the strike
class Strike:
    def __init__(self, strike_type:int, slice_location:'Vec3', slice_time:float, ideal_shot:'Vec3'):
        self.strike_type=strike_type
        self.slice_location=slice_location
        self.slice_time=slice_time
        self.ideal_shot=ideal_shot
        self.possible=True

    def rem_time(self,packet):
        return self.slice_time - packet.game_info.seconds_elapsed

#returns a list of possible strikes
def find_strikes(packet, ball_prediction, car:Car, ideal_shot, defence=False):

    strikes = []   
    target_slice = None
    found_one = False
    slice_t=0.01
    while int(slice_t*60)<ball_prediction.num_slices:
        target_slice = ball_prediction.slices[int(slice_t*60)]
        if target_slice is not None:
            slice_location = Vec3(target_slice.physics.location)
            vec_to_target = slice_location - car.location + ideal_shot.rescale(-70) if not defence else slice_location - car.location
            vec_to_target = vec_to_target.rescale(vec_to_target.length()-70)
            ang_to_turn = vec_to_target.flat().ang_to(car.orientation.forward.flat())
            time_to_turn = ang_to_turn/20.3
            req_vel = (vec_to_target.length()-70) / max((slice_t - time_to_turn),0.001)
            required_arc_length = turn_radius(abs(req_vel))*ang_to_turn
            arc_time = ang_to_turn/3.5
            max_dist = max_d_in_t_boost(slice_t, car.velocity.length(),car.boost)
            accel_time = acceleration_time(car.velocity.length(), req_vel, car.boost)

            

            if slice_location.z < 140 and accel_time is not None:
                #ground hit
                can_make_dist = max_dist > vec_to_target.length()
                arc_within_time = arc_time < slice_t
                fast_reaction = slice_t < 0.2 and ang_to_turn < 1
                if can_make_dist and arc_within_time or fast_reaction:
                    strikes.append(Strike(strike_types.simple_linear, slice_location, (slice_t+packet.game_info.seconds_elapsed),ideal_shot))
                    found_one = True

            elif slice_location.z < 230 and accel_time is not None:
                #single jump hit
                jump_t = single_jump_time(slice_location.z-17)
                can_make_dist = max_dist > vec_to_target.length()
                arc_within_time = arc_time < slice_t-jump_t
                fast_reaction = slice_t < 0.2+jump_t and ang_to_turn < 0.8 and abs(vec_to_target.flat().length()-car.velocity.length()*(slice_t-jump_t)) < 250
                gets_to_speed_before_jump = accel_time < slice_t - jump_t
                if can_make_dist and arc_within_time and gets_to_speed_before_jump or fast_reaction:
                    strikes.append(Strike(strike_types.linear_jump, slice_location, (slice_t+packet.game_info.seconds_elapsed),ideal_shot))
                    found_one = True

            elif slice_location.z < 495 and accel_time is not None:
                #double jump hit
                jump_t = double_jump_time(slice_location.z-17)
                can_make_dist = max_dist > vec_to_target.length()
                arc_within_time = arc_time < slice_t-jump_t
                fast_reaction = slice_t < 0.2+jump_t and ang_to_turn < 0.6 and abs(vec_to_target.flat().length()-car.velocity.length()*(slice_t-jump_t)) < 200
                gets_to_speed_before_jump = accel_time < slice_t - jump_t
                if can_make_dist and arc_within_time and gets_to_speed_before_jump or fast_reaction:
                    strikes.append(Strike(strike_types.linear_dblj, slice_location, (slice_t+packet.game_info.seconds_elapsed),ideal_shot))
                    found_one = True
                    
                    
        #next slice when ball has moved 30uu/200uu
        slice_t+=30/Vec3(target_slice.physics.velocity).length() if not found_one else 200/Vec3(target_slice.physics.velocity).length()

        
    return strikes

"""---------------------------------------------------------------------------------------------------------------------------------------------------"""
def execute_strike(packet,car,strike,foes,defence=False):
    #will always return sequence=None, SimpleControllerState, location of slice, time to slice

    #get values to use
    vec_to_slice = strike.slice_location - car.location
    ang_to_slice = car.orientation.forward.signed_ang_to(vec_to_slice)
    time_to_slice = strike.rem_time(packet)
    ball_location = Vec3(packet.game_ball.physics.location)
    vec_to_ball = ball_location - car.location
    ang_to_ball = car.orientation.forward.signed_ang_to(vec_to_ball-car.orientation.forward.rescale(50))
    controls = SimpleControllerState()

    closest_foe = min(foe.vec_to_ball.length() for foe in foes)
    vec_to_target = strike.slice_location - car.location + strike.ideal_shot.rescale(-70) if not defence else strike.slice_location - car.location
    vec_to_target = vec_to_target.rescale(vec_to_target.length()-70)
    ang_to_target = car.orientation.forward.signed_ang_to(vec_to_target)


    if strike.strike_type == strike_types.simple_linear:
        #---------------------------------------- simple_linear ----------------------------------------------------
        req_vel = (vec_to_slice.flat().length()-70) / time_to_slice

        #try out the new targeting
        if not defence:
            side_of_shot = math.copysign(1,strike.ideal_shot.cross(Vec3(0,0,1)).dot(vec_to_slice))
            car_to_offset_perp = vec_to_slice.cross(Vec3(0,0,side_of_shot))

            adjustment = vec_to_slice.flat().ang_to(strike.ideal_shot) * min(max(strike.rem_time(packet), 0.25), 2) * 500
            vec_to_target = strike.slice_location - car.location + car_to_offset_perp.rescale(adjustment) if not defence else strike.slice_location - car.location
            vec_to_target = vec_to_target.rescale(vec_to_target.length()-70)
            ang_to_target = car.orientation.forward.signed_ang_to(vec_to_target)

        #flip into ball on strike, but allow push/carry plays if not immediately challenged
        if time_to_slice <0.15 and vec_to_slice.length()<350:
            if -0.5<ang_to_slice<0.5 and car.stable and (arc_height(packet.game_ball.physics.velocity.z,packet.game_ball.physics.location.z) >130 or closest_foe<500):
                return begin_front_flip(packet)[0], begin_front_flip(packet)[1], strike.slice_location, strike.rem_time(packet)
                #consider height of ball for side flips

            elif -1<ang_to_slice<-0.5 and car.stable:
                return begin_dleft_flip(packet)[0], begin_dleft_flip(packet)[1], strike.slice_location, strike.rem_time(packet)

            elif 0.5<ang_to_slice<1 and car.stable:
                return begin_dright_flip(packet)[0], begin_dright_flip(packet)[1], strike.slice_location, strike.rem_time(packet)

            elif -2.3<ang_to_slice<-1 and car.stable and ball_location.z<120:
                return begin_left_flip(packet)[0], begin_left_flip(packet)[1], strike.slice_location, strike.rem_time(packet)

            elif 1<ang_to_slice<2.3 and car.stable and ball_location.z<120:
                return begin_right_flip(packet)[0], begin_right_flip(packet)[1], strike.slice_location, strike.rem_time(packet) 

        

        #get around ball a little if a while until shot
        if strike.rem_time(packet) >1 and vec_to_slice.length()>400:
            vec_to_target = vec_to_target - strike.ideal_shot.rescale(100*strike.rem_time(packet))
            ang_to_target = car.orientation.forward.signed_ang_to(vec_to_target)
       

        #turn toward target
        if ang_to_target<-0.05:
            controls.steer = -1
        elif ang_to_target > 0.05:
            controls.steer = 1
        #set throttle and boost to maintain speed:
        vel_diff = req_vel - car.velocity.length()
        throttle = (vel_diff**2)*math.copysign(1,vel_diff)/1000
        controls.throttle = 1 if req_vel > 1350 and throttle>0 else max(-1,min(throttle,1))
        controls.boost = True if vel_diff > 150 and car.velocity.length() < 2200 and controls.throttle == 1 and not defence else False
        return None, controls, strike.slice_location, strike.rem_time(packet) 

    elif strike.strike_type == strike_types.linear_jump:
        #---------------------------------------- linear_jump ----------------------------------------------------
        req_vel = (vec_to_slice.flat().length()-70) / time_to_slice
        #do the jump when time
        if time_to_slice <single_jump_time(strike.slice_location.z-17) and car.grounded and car.velocity.flat().ang_to(vec_to_target.flat()) <0.3 and abs(car.velocity.flat().length()*single_jump_time(strike.slice_location.z-17)-vec_to_target.length())<200:
            return long_jump(packet,min(single_jump_time(strike.slice_location.z-17),0.2))[0], long_jump(packet,min(single_jump_time(strike.slice_location.z-17),0.2))[1], strike.slice_location, strike.rem_time(packet)

        #flip in air if needed
        if not car.grounded and time_to_slice <single_jump_time(strike.slice_location.z-17) and abs(vec_to_ball.z)<100:
            if -0.5<ang_to_ball<0.5:
                return begin_front_flip(packet)[0], begin_front_flip(packet)[1], strike.slice_location, strike.rem_time(packet)                

            elif -1<ang_to_ball<-0.5:
                return begin_dleft_flip(packet)[0], begin_dleft_flip(packet)[1], strike.slice_location, strike.rem_time(packet)

            elif 0.5<ang_to_ball<1:
                return begin_dright_flip(packet)[0], begin_dright_flip(packet)[1], strike.slice_location, strike.rem_time(packet)

            elif -2.3<ang_to_ball<-1:
                return begin_left_flip(packet)[0], begin_left_flip(packet)[1], strike.slice_location, strike.rem_time(packet)

            elif 1<ang_to_ball<2.3:
                return begin_right_flip(packet)[0], begin_right_flip(packet)[1], strike.slice_location, strike.rem_time(packet) 

        #try out the new targeting
        if not defence and strike.rem_time(packet) > 0.5 + single_jump_time(strike.slice_location.z-17):
            side_of_shot = math.copysign(1,strike.ideal_shot.cross(Vec3(0,0,1)).dot(vec_to_slice))
            car_to_offset_perp = vec_to_slice.cross(Vec3(0,0,side_of_shot))

            adjustment = vec_to_slice.flat().ang_to(strike.ideal_shot) * min(max(strike.rem_time(packet), 0.25), 2) * 500
            vec_to_target = strike.slice_location - car.location + car_to_offset_perp.rescale(adjustment) if not defence else strike.slice_location - car.location
            vec_to_target = vec_to_target.rescale(vec_to_target.length()-70)
            ang_to_target = car.orientation.forward.signed_ang_to(vec_to_target)

        #turn toward target
        if ang_to_target<-0.05:
            controls.steer = -1
        elif ang_to_target > 0.05:
            controls.steer = 1
        #set throttle and boost to maintain speed:
        vel_diff = req_vel - car.velocity.length()
        throttle = (vel_diff**2)*math.copysign(1,vel_diff)/1000
        controls.throttle = 1 if req_vel > 1350 and throttle>0 else max(-1,min(throttle,1))
        controls.boost = True if vel_diff > 150 and car.velocity.length() < 2200 and controls.throttle == 1 and not defence else False
        return None, controls, strike.slice_location, strike.rem_time(packet)

    elif strike.strike_type == strike_types.linear_dblj:
        #---------------------------------------- linear_dblj ----------------------------------------------------
        req_vel = (vec_to_slice.flat().length()-70) / time_to_slice
        if time_to_slice <double_jump_time(strike.slice_location.z-17) and car.velocity.flat().ang_to(vec_to_target.flat()) <0.2 and abs(car.velocity.flat().length()*double_jump_time(strike.slice_location.z-17)-vec_to_target.length())<200:
            return doublejump(packet)[0], doublejump(packet)[1], strike.slice_location, strike.rem_time(packet)
        #turn toward target
        if ang_to_target<-0.05:
            controls.steer = -1
        elif ang_to_target > 0.05:
            controls.steer = 1
        #set throttle and boost to maintain speed:
        vel_diff = req_vel - car.velocity.length()
        throttle = (vel_diff**2)*math.copysign(1,vel_diff)/1000
        controls.throttle = 1 if req_vel > 1350 and throttle>0 else max(-1,min(throttle,1))
        controls.boost = True if vel_diff > 150 and car.velocity.length() < 2200 and controls.throttle == 1 and not defence else False
        return None, controls, strike.slice_location, strike.rem_time(packet)


    

"""-------------------------------------------------------------------------------------------"""
def check_strike(packet,ball_prediction,strike):
    strike_location = strike.slice_location
    strike_time = strike.slice_time
    new_slices = find_slices_around_time(ball_prediction,strike_time,2)
    if new_slices is None or strike_time - packet.game_info.seconds_elapsed<0:
        return False
    else:
        if all(Vec3(new_slice.physics.location).dist(strike_location) > 15 for new_slice in new_slices):
            #checks if None of the new frames are within 15uu of the target
            return False
            
        else:
            return True

"""------------------------------------------------------------------------------------------"""

