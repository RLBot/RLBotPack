from __future__ import annotations

from utils import *

import math
from copy import copy
from typing import TYPE_CHECKING

from objects import *

gravity: Vector3 = Vector3(0, 0, -650)

# Aerial constants
max_speed: float = 2300
boost_accel: float = 1060
throttle_accel: float = 200 / 3
boost_per_second: float = 30

# Jump constants
jump_speed: float = 291.667
jump_acc = 1458.3333
jump_min_duration = 0.025
jump_max_duration = 0.2

#This file holds all of the mechanical tasks, called "routines", that the bot can do

class ball_chase():
    #Drives towards the ball at max speed without boost
    def run(agent):
        relative_target = agent.ball.location - agent.me.location
        local_target = agent.me.local(relative_target)
        defaultPD(agent, local_target)
        defaultThrottle(agent, 2300)

class goto_friendly_goal():
    #Drives towards friendly goal. If touching or over goal line stops moving and faces enemy goal
    def run(agent):
        if side(agent.team) == -1:
            if agent.me.location.y > -5000:
                relative = Vector3(0,5120*side(agent.team),0) - agent.me.location
                defaultPD(agent,agent.me.local(relative))
                angles = defaultPD(agent, agent.me.local(relative))
                if agent.me.location.y > -4900:
                    defaultThrottle(agent,2300)
            else:
                relative = agent.foe_goal.location - agent.me.location
                defaultPD(agent,agent.me.local(relative))
                angles = defaultPD(agent, agent.me.local(relative))
        else:
            if agent.me.location.y < 5000:
                relative = Vector3(0,5120*side(agent.team),0) - agent.me.location
                defaultPD(agent,agent.me.local(relative))
                angles = defaultPD(agent, agent.me.local(relative))
                if agent.me.location.y < 4900:
                    defaultThrottle(agent,2300)
            else:
                relative = agent.foe_goal.location - agent.me.location
                defaultPD(agent,agent.me.local(relative))
                angles = defaultPD(agent, agent.me.local(relative))
            
        if abs(angles[1]) > 2.88 and abs(angles[1]) < 3.4:
            agent.push(half_flip())


class get_nearest_big_boost():
    def run(agent):
        large_boosts = [boost for boost in agent.boosts if boost.large and boost.active]
        if len(large_boosts) > 0:
            closest = large_boosts[0]
            closest_distance = (large_boosts[0].location - agent.me.location).magnitude()
    
            for item in large_boosts:
                item_distance = (item.location - agent.me.location).magnitude()
                if item_distance < closest_distance:
                    closest = item
                    closest_distance = item_distance
            
            #Calls goto_boost routine with input closest active and large boost
            agent.push(goto_boost(closest))

class get_nearest_small_boost():
    def run(agent):
        small_boosts = [boost for boost in agent.boosts if not(boost.large) and boost.active]
        if len(small_boosts) > 0:
            closest = small_boosts[0]
            closest_distance = (small_boosts[0].location - agent.me.location).magnitude()
    
            for item in small_boosts:
                item_distance = (item.location - agent.me.location).magnitude()
                if item_distance < closest_distance:
                    closest = item
                    closest_distance = item_distance
            
            agent.push(goto_boost(closest))

class wavedash_recovery():
    #Lands the right way up and wavedashes while landing, doesn't work if out of jumps
    #Currently can't land facing a target, normal recovery can
    def __init__(self):
        self.step = 0
    def run(self,agent):
        if agent.me.velocity.flatten().magnitude() > 100:
            target = agent.me.velocity.flatten().normalize()*100 + Vector3(0,0,50)
        else:
            target = agent.me.orientation.forward.flatten()*100 + Vector3(0,0,50)
        local_target=agent.me.local(target)
        defaultPD(agent,local_target)
        self.step += 1
        if self.step > 8:
            if (agent.me.location + (agent.me.velocity * 0.2)).z < 5:
                agent.controller.jump = True
                agent.controller.pitch = -1
                agent.controller.yaw = agent.controller.roll = 0
                agent.pop()
            elif not agent.me.airborne:
                agent.pop()

class demo_enemy_closest_ball():
    def run(agent):
        if agent.me.boost < 10:
            agent.push(get_nearest_big_boost)
        else:  
            try:
                if len(agent.foes) > 0:
                    enemies = agent.foes
                    closest = enemies[0]
                    closest_distance = (enemies[0].location - agent.ball.location).magnitude()
                    x = 0
                    y = 0
                    for item in enemies:
                        item_distance = (item.location - agent.ball.location).magnitude()
                        if item_distance < closest_distance:
                            closest = item
                            closest_distance = item_distance
                            y = x
                        x =+ 1
                        
                    local_target = agent.me.local(agent.foes[y].location - agent.me.location)
                    defaultPD(agent, local_target)
                    defaultThrottle(agent, 2300)
                    distance_remaining = local_target.flatten().magnitude()
                
                if distance_remaining < 2000 or agent.me.boost > 50 and distance_remaining < 5000:
                    agent.controller.boost = True
                else:
                    agent.controller.boost = False
            except:
                print('There are no enemies to demo :(')
            

class half_flip():
    def __init__(self):
        #the time the jump began
        self.time = -1
        #keeps track of the frames the jump button has been released
        self.counter = 0
    def run(self,agent):
        if self.time == -1:
            elapsed = 0
            self.time = agent.time
        else:
            elapsed = agent.time - self.time
        if elapsed < 0.15:
            agent.controller.jump = True
        elif elapsed >=0.15 and self.counter < 1:
            agent.controller.jump = False
            self.counter += 1
        elif elapsed < 0.6:
            agent.controller.jump = True
            agent.controller.pitch = 1
        elif elapsed < 1.4:
            #Rotates and lands
            agent.controller.pitch = -1 
            agent.controller.roll = 1
            agent.controller.yaw = 1
        elif not agent.me.airborne:
            #Stops routine when landed
            agent.pop()

class go_centre():
    #Makes bot go inbetween centre of goal and ball
    #Useful when bot has nothing to do but wants to be in a good position to defend or attack
    def run(agent):
        relative_target = Vector3(agent.ball.location.x / 2, (agent.ball.location.y + 5120 * side(agent.team)) / 2,50) - agent.me.location
        local_target = agent.me.local(relative_target)
        if relative_target.magnitude() > 350:
            defaultPD(agent, local_target)
            defaultThrottle(agent, 2300)
            angles = defaultPD(agent, agent.me.local(relative_target))
            if abs(angles[1]) > 1:
                agent.controller.handbrake = True
                agent.controller.boost = False
        else:
        #If close to target, stop moving and face towards ball
            defaultThrottle(agent, 0)
            relative_target = agent.ball.location - agent.me.location 
            angles = defaultPD(agent, agent.me.local(relative_target))
            if abs(angles[1]) > 2.88 and abs(angles[1]) < 3.4:
                agent.push(half_flip())
        #Line between car and desired location        
        agent.line(Vector3(agent.ball.location.x / 2, (agent.ball.location.y + 5120 * side(agent.team)) / 2,50), agent.me.location, [255,0,255])

class Aerial():
    def __init__(self, ball_location: Vector3, intercept_time: float, on_ground: bool, target: Vector3 = None):
        super().__init__()
        self.ball_location = ball_location
        self.intercept_time = intercept_time
        self.target = target
        self.jumping = on_ground
        self.time = -1
        self.jump_time = -1
        self.counter = 0

    def run(self,agent: CarObject):
        if self.time == -1:
            elapsed = 0
            self.time = agent.time
        else:
            elapsed = agent.time - self.time
        T = self.intercept_time - agent.time
        xf = agent.me.location + agent.me.velocity * T + 0.5 * gravity * T ** 2
        vf = agent.me.velocity + gravity * T
        if self.jumping:
            if self.jump_time == -1:
                jump_elapsed = 0
                self.jump_time = agent.time
            else:
                jump_elapsed = agent.time - self.jump_time
            tau = jump_max_duration - jump_elapsed
            if jump_elapsed == 0:
                vf += agent.me.up * jump_speed
                xf += agent.me.up * jump_speed * T
            
            vf += agent.me.up * jump_acc * tau
            xf += agent.me.up * jump_acc * tau * (T - 0.5 * tau)

            vf += agent.me.up * jump_speed
            xf += agent.me.up * jump_speed * (T - tau)

            if jump_elapsed < jump_max_duration:
                agent.controller.jump = True
            elif elapsed >= jump_max_duration and self.counter < 3:
                agent.controller.jump = False
                self.counter += 1
            elif elapsed < 0.3:
                agent.controller.jump = True
            else:
                self.jumping = jump_elapsed <= 0.3
        else:
            agent.controller.jump = 0

        delta_x = self.ball_location - xf
        direction = delta_x.normalize()
        if delta_x.magnitude() > 50:
            defaultPD(agent, agent.me.local(delta_x))
        else:
            if self.target is not None:
                defaultPD(agent, agent.me.local(self.target))
            else:
                defaultPD(agent,agent.ne.local(self.ball_location - agent.me.location))
        
        if jump_max_duration <= elapsed < 0.3 and self.counter == 3:
            agent.controller.roll = 0
            agent.controller.pitch = 0
            agent.controller.yaw = 0
            agent.controller.steer = 0
        
        if agent.me.forward.angle3D(direction) < 0.3:
            if delta_x.magnitude() > 50:
                agent.controller.boost = 1
                defaultThrottle(agent, 0)
            else:
                agent.controller.boost = 0
                defaultThrottle(agent, cap(0.5 * throttle.accel * T ** 2,0,1))
            
        else:
            agent.controller.boost = 0
            defaultThrottle(agent, 0)

        if T <= 0 or not shot_valid(agent, self, threshold = 150):
            agent.pop()
            agent.push(recovery(agent.ball.location))

    def is_viable(self, agent: CarObject, time: float):
        T = self.intercept_time - time
        xf = agent.me.location + agent.me.velocity * T + 0.5 * gravity * T ** 2
        vf = agent.me.velocity + gravity * T
        if not agent.me.airborne:
            vf += agent.me.up * (2 * jump_speed + jump_acc * jump_max_duration)
            xf += agent.me.up * (jump_speed * (2 * T - jump_max_duration) + jump_acc * (T * jump_max_duration - 0.5 * jump_max_duration ** 2))
        
        delta_x = self.ball_location - xf
        f = delta_x.normalize()
        phi = f.angle3D(agent.me.forward)
        turn_time = 0.7 * (2 * math.sqrt(phi / 9))

        tau1 = turn_time * cap(1 - 0.3 / phi, 0, 1)
        required_acc = (2 * delta_x.magnitude()) / ((T - tau1) ** 2)
        ratio = required_acc / boost_accel
        tau2 = T - (T - tau1) * math.sqrt(1 - cap(ratio, 0, 1))
        velocity_estimate = vf + boost_accel * (tau2 - tau1) * f
        boos_estimate = (tau2 - tau1) * 30
        enough_boost = boos_estimate < 0.95 * agent.me.boost
        enough_time = abs(ratio) < 0.9
        return velocity_estimate.magnitude() < 0.9 * max_speed and enough_boost and enough_time


class aerial_shot():
    #Very similar to jump_shot(), but instead designed to hit targets above 300uu
    #***This routine is a WIP*** It does not currently hit the ball very hard, nor does it like to be accurate above 600uu or so
    def __init__(self, ball_location, intercept_time, shot_vector, ratio):
        self.ball_location = ball_location
        self.intercept_time = intercept_time
        #The direction we intend to hit the ball in
        self.shot_vector = shot_vector
        #The point we hit the ball at
        self.intercept = self.ball_location - (self.shot_vector * 110)
        #dictates when (how late) we jump, much later than in jump_shot because we can take advantage of a double jump
        self.jump_threshold = 600
        #what time we began our jump at
        self.jump_time = 0
        #If we need a second jump we have to let go of the jump button for 3 frames, this counts how many frames we have let go for
        self.counter = 0
    def run(self,agent):
        raw_time_remaining = self.intercept_time - agent.time
        #Capping raw_time_remaining above 0 to prevent division problems
        time_remaining = cap(raw_time_remaining,0.01,10.0)

        car_to_ball = self.ball_location - agent.me.location
        #whether we are to the left or right of the shot vector
        side_of_shot = sign(self.shot_vector.cross((0,0,1)).dot(car_to_ball))

        car_to_intercept = self.intercept - agent.me.location
        car_to_intercept_perp = car_to_intercept.cross((0,0,side_of_shot)) #perpendicular
        distance_remaining = car_to_intercept.flatten().magnitude()

        speed_required = distance_remaining / time_remaining
        #When still on the ground we pretend gravity doesn't exist, for better or worse
        acceleration_required = backsolve(self.intercept,agent.me,time_remaining, 0 if self.jump_time == 0 else 325)
        local_acceleration_required = agent.me.local(acceleration_required)

        #The adjustment causes the car to circle around the dodge point in an effort to line up with the shot vector
        #The adjustment slowly decreases to 0 as the bot nears the time to jump
        adjustment = car_to_intercept.angle(self.shot_vector) * distance_remaining / 1.57 #size of adjustment
        adjustment *= (cap(self.jump_threshold-(acceleration_required[2]),0.0,self.jump_threshold) / self.jump_threshold) #factoring in how close to jump we are
        #we don't adjust the final target if we are already jumping
        final_target = self.intercept + ((car_to_intercept_perp.normalize() * adjustment) if self.jump_time == 0 else 0)

        #Some extra adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1]) > 5150: final_target[0] = cap(final_target[0],-750,750)
        
        local_final_target = agent.me.local(final_target - agent.me.location)

        #drawing debug lines to show the dodge point and final target (which differs due to the adjustment)
        agent.line(agent.me.location,self.intercept)
        agent.line(self.intercept-Vector3(0,0,100), self.intercept+Vector3(0,0,100),[255,0,0])
        agent.line(final_target-Vector3(0,0,100),final_target+Vector3(0,0,100),[0,255,0])

        angles = defaultPD(agent,local_final_target)
        if self.jump_time == 0:
            defaultThrottle(agent, speed_required)
            agent.controller.boost = False if agent.me.airborne or (abs(angles[1]) > 0.3 and car_to_ball.magnitude() < 1000) else agent.controller.boost
            agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake
            if acceleration_required[2] > self.jump_threshold:
                #Switch into the jump when the upward acceleration required reaches our threshold, hopefully we have aligned already...
                self.jump_time = agent.time
        else:
            time_since_jump = agent.time - self.jump_time

            #While airborne we boost if we're within 30 degrees of our local acceleration requirement
            if agent.me.airborne and local_acceleration_required.magnitude() * time_remaining > 100:
                    angles = defaultPD(agent, local_acceleration_required)
                    if abs(angles[0]) + abs(angles[1]) < 0.5:
                        agent.controller.boost = True
            if self.counter == 0 and (time_since_jump <= 0.2 and local_acceleration_required[2] > 0):
                #hold the jump button up to 0.2 seconds to get the most acceleration from the first jump
                agent.controller.jump = True
            elif time_since_jump > 0.2 and self.counter < 3:
                #Release the jump button for 3 ticks
                agent.controller.jump = False
                self.counter += 1
            elif local_acceleration_required[2] > 300 and self.counter == 3:
                #the acceleration from the second jump is instant, so we only do it for 1 frame
                agent.controller.jump = True
                agent.controller.pitch = 0
                agent.controller.yaw = 0
                agent.controller.roll = 0
                self.counter += 1

        if raw_time_remaining < -0.25 or not shot_valid(agent,self):
            agent.pop()
            agent.push(recovery())

class flip():
    #Flip takes a vector in local coordinates and flips/dodges in that direction
    #cancel causes the flip to cancel halfway through, which can be used to half-flip
    def __init__(self,vector,cancel = False):
        self.vector = vector.normalize()
        self.pitch = abs(self.vector[0])* -sign(self.vector[0])
        self.yaw = abs(self.vector[1]) * sign(self.vector[1])
        self.cancel = cancel
        #the time the jump began
        self.time = -1
        #keeps track of the frames the jump button has been released
        self.counter = 0
    def run(self,agent):
        if self.time == -1:
            elapsed = 0
            self.time = agent.time
        else:
            elapsed = agent.time - self.time
        if elapsed < 0.15:
            agent.controller.jump = True
        elif elapsed >=0.15 and self.counter < 3:
            agent.controller.jump = False
            self.counter += 1
        elif elapsed < 0.3 or (not self.cancel and elapsed < 0.9):
            agent.controller.jump = True
            agent.controller.pitch = self.pitch
            agent.controller.yaw = self.yaw
        else:
            agent.pop()
            agent.push(recovery())
            
class goto():
    #Drives towards a designated (stationary) target
    #Optional vector controls where the car should be pointing upon reaching the target
    #TODO - slow down if target is inside our turn radius
    def __init__(self, target, vector=None, direction = 1):
        self.target = target
        self.vector = vector
        self.direction = direction
    def run(self,agent):
        car_to_target = self.target - agent.me.location
        distance_remaining = car_to_target.flatten().magnitude()

        agent.line(self.target - Vector3(0,0,500),self.target + Vector3(0,0,500),[255,0,255])
        
        if self.vector != None:
            #See comments for adjustment in jump_shot or aerial for explanation
            side_of_vector = sign(self.vector.cross((0,0,1)).dot(car_to_target))
            car_to_target_perp = car_to_target.cross((0,0,side_of_vector)).normalize()
            adjustment = car_to_target.angle(self.vector) * distance_remaining / 3.14
            final_target = self.target + (car_to_target_perp * adjustment)
        else:
            final_target = self.target

        #Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1]) > 5150: final_target[0] = cap(final_target[0],-750,750)

        local_target = agent.me.local(final_target - agent.me.location)
        
        angles = defaultPD(agent, local_target, self.direction)
        defaultThrottle(agent, 2300, self.direction)
        
        agent.controller.boost = False
        agent.controller.handbrake = True if abs(angles[1]) > 2 else agent.controller.handbrake

        velocity = 1+agent.me.velocity.magnitude()
        if distance_remaining < 350:
            agent.pop()
        elif abs(angles[1]) < 0.05 and velocity > 600 and velocity < 2150 and distance_remaining / velocity > 2.0:
            agent.push(flip(local_target))
        elif abs(angles[1]) > 2.8 and velocity < 200:
            agent.push(flip(local_target,True))
        elif agent.me.airborne:
            agent.push(recovery(self.target))

class goto_boost():
    #very similar to goto() but designed for grabbing boost
    #if a target is provided the bot will try to be facing the target as it passes over the boost
    def __init__(self,boost,target=None):
        self.boost = boost
        self.target = target
    def run(self,agent):
        car_to_boost = self.boost.location - agent.me.location
        distance_remaining = car_to_boost.flatten().magnitude()

        agent.line(self.boost.location - Vector3(0,0,500),self.boost.location + Vector3(0,0,500),[0,255,255])

        if self.target != None:
            vector = (self.target - self.boost.location).normalize()
            side_of_vector = sign(vector.cross((0,0,1)).dot(car_to_boost))
            car_to_boost_perp = car_to_boost.cross((0,0,side_of_vector)).normalize()
            adjustment = car_to_boost.angle(vector) * distance_remaining / 3.14
            final_target = self.boost.location + (car_to_boost_perp * adjustment)
            car_to_target = (self.target - agent.me.location).magnitude()
        else:
            adjustment = 9999
            car_to_target = 0
            final_target = self.boost.location.copy()
        
        #Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1]) > 5150: final_target[0] = cap(final_target[0],-750,750)

        local_target = agent.me.local(final_target - agent.me.location)
        
        angles = defaultPD(agent, local_target)
        defaultThrottle(agent, 2300)        
        agent.controller.boost = self.boost.large if abs(angles[1]) < 0.3 else False
        if abs(angles[1]) > 2.88 and abs(angles[1]) < 3.4:
            agent.push(half_flip())
        if abs(angles[1]) > 1:
            agent.controller.handbrake = True
            agent.controller.boost = False
        else:
            agent.controller.handbrake = False
            agent.controller.boost = True
        velocity = 1+agent.me.velocity.magnitude()
        if self.boost.active == False or agent.me.boost >= 99.0 or distance_remaining < 350:
            agent.clear()
        elif agent.me.airborne:
            agent.push(recovery(self.target))
        elif abs(angles[1]) < 0.05 and velocity > 600 and velocity < 2150 and (distance_remaining / velocity > 2.0 or (adjustment < 90 and car_to_target/velocity > 2.0)):
            agent.push(flip(local_target))  
      
               
class jump_shot():
    #Hits a target point at a target time towards a target direction
    #Target must be no higher than 300uu unless you're feeling lucky
    #TODO - speed
    def __init__(self, ball_location, intercept_time, shot_vector, ratio, direction=1, speed=2300):
        self.ball_location = ball_location
        self.intercept_time = intercept_time
        #The direction we intend to hit the ball in
        self.shot_vector = shot_vector
        #The point we dodge at
        #173 is the 93uu ball radius + a bit more to account for the car's hitbox
        self.dodge_point = self.ball_location - (self.shot_vector * 173)
        #Ratio is how aligned the car is. Low ratios (<0.5) aren't likely to be hit properly 
        self.ratio = ratio
        #whether the car should attempt this backwards
        self.direction = direction
        #Intercept speed not implemented
        self.speed_desired = speed
        #controls how soon car will jump based on acceleration required. max 584
        #bigger = later, which allows more time to align with shot vector
        #smaller = sooner
        self.jump_threshold = 400
        #Flags for what part of the routine we are in
        self.jumping = False
        self.dodging = False
        self.counter = 0
    def run(self,agent):
        raw_time_remaining = self.intercept_time - agent.time
        #Capping raw_time_remaining above 0 to prevent division problems
        time_remaining = cap(raw_time_remaining,0.001,10.0)
        car_to_ball = self.ball_location - agent.me.location
        #whether we are to the left or right of the shot vector
        side_of_shot = sign(self.shot_vector.cross((0,0,1)).dot(car_to_ball))
        
        car_to_dodge_point = self.dodge_point - agent.me.location
        car_to_dodge_perp = car_to_dodge_point.cross((0,0,side_of_shot)) #perpendicular
        distance_remaining = car_to_dodge_point.magnitude()

        speed_required = distance_remaining / time_remaining
        acceleration_required = backsolve(self.dodge_point,agent.me,time_remaining,0 if not self.jumping else 650)
        local_acceleration_required = agent.me.local(acceleration_required)

        #The adjustment causes the car to circle around the dodge point in an effort to line up with the shot vector
        #The adjustment slowly decreases to 0 as the bot nears the time to jump
        adjustment = car_to_dodge_point.angle(self.shot_vector) * distance_remaining / 2.0 #size of adjustment
        adjustment *= (cap(self.jump_threshold-(acceleration_required[2]),0.0,self.jump_threshold) / self.jump_threshold) #factoring in how close to jump we are
        #we don't adjust the final target if we are already jumping
        final_target = self.dodge_point + ((car_to_dodge_perp.normalize() * adjustment) if not self.jumping else 0) + Vector3(0,0,50)
        #Ensuring our target isn't too close to the sides of the field, where our car would get messed up by the radius of the curves
        
        #Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1]) > 5150: final_target[0] = cap(final_target[0],-750,750)

        local_final_target = agent.me.local(final_target - agent.me.location)

        #drawing debug lines to show the dodge point and final target (which differs due to the adjustment)
        agent.line(agent.me.location,self.dodge_point)
        agent.line(self.dodge_point-Vector3(0,0,100), self.dodge_point+Vector3(0,0,100),[255,0,0])
        agent.line(final_target-Vector3(0,0,100),final_target+Vector3(0,0,100),[0,255,0])

        #Calling our drive utils to get us going towards the final target
        angles = defaultPD(agent,local_final_target,self.direction)
        defaultThrottle(agent, speed_required,self.direction)

        agent.line(agent.me.location, agent.me.location + (self.shot_vector*200), [255,255,255])

        agent.controller.boost = False if agent.me.airborne or (abs(angles[1]) > 0.3 and car_to_ball.magnitude() < 1000) else agent.controller.boost
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 and self.direction == 1 else agent.controller.handbrake

        if not self.jumping:
            if raw_time_remaining <= 0.0 or (speed_required - 2300) * time_remaining > 45 or not shot_valid(agent,self):
                #If we're out of time or not fast enough to be within 45 units of target at the intercept time, we pop
                agent.pop()
                if agent.me.airborne:
                    agent.push(wavedash_recovery())
            elif local_acceleration_required[2] > self.jump_threshold and local_acceleration_required[2] > local_acceleration_required.flatten().magnitude():
                #Switch into the jump when the upward acceleration required reaches our threshold, and our lateral acceleration is negligible
                self.jumping = True 
        else:
            if (raw_time_remaining > 0.2 and not shot_valid(agent,self,150)) or raw_time_remaining <= -0.9 or (not agent.me.airborne and self.counter > 0):
                agent.pop()
                agent.push(recovery())
            elif self.counter == 0 and local_acceleration_required[2] > 0.0 and raw_time_remaining > 0.083:
                #Initial jump to get airborne + we hold the jump button for extra power as required
                agent.controller.jump = True
            elif self.counter < 3:
                #make sure we aren't jumping for at least 3 frames
                agent.controller.jump = False
                self.counter += 1
            elif raw_time_remaining <= 0.1 and raw_time_remaining > -0.9:
                #dodge in the direction of the shot_vector
                agent.controller.jump = True
                if not self.dodging:
                    vector = agent.me.local(self.shot_vector)
                    self.p = abs(vector[0]) * -sign(vector[0])
                    self.y = abs(vector[1]) * sign(vector[1])
                    self.dodging = True
                #simulating a deadzone so that the dodge is more natural
                agent.controller.pitch = self.p if abs(self.p) > 0.2 else 0 
                agent.controller.yaw = self.y if abs(self.y) > 0.3 else 0

class kickoff():
    def __init__(self,kickoff_position):
        #the time the jump began
        self.time = -1
        self.counter = 0
        self.kickoff = kickoff_position
    def run(self,agent):
        if agent.kickoff_flag == False:
            agent.pop()
        else:
            if self.time == -1:
                elapsed = 0
                self.time = agent.time
            else:
                elapsed = agent.time - self.time
            
            if self.kickoff == 'diagonal_right' or self.kickoff == 'diagonal_left':
                #Fast diagonal kickoff
                defaultThrottle(agent,2300)
                agent.controller.boost = True
                #For the first 0.4 seconds drives slightly to the more towards enemy side than spawn position while boosting
                # Then faces towards ball
                if elapsed > 0.4:
                    relative_target = agent.ball.location - agent.me.location
                else:
                    if self.kickoff == 'diagonal_right':
                        relative_target = agent.ball.location + Vector3(600*side(agent.team),0,0) - agent.me.location
                    else:
                        relative_target = agent.ball.location - Vector3(600*side(agent.team),0,0) - agent.me.location
                local_target = agent.me.local(relative_target)
                defaultPD(agent,local_target)
                
                if elapsed > 0.35 and elapsed < 0.4:
                    agent.controller.jump = True
                elif elapsed > 0.4 and self.counter < 3:
                    agent.controller.jump = False
                    self.counter += 1
                elif elapsed > 0.4 and self.counter < 4:
                    agent.controller.jump = True
                    agent.controller.pitch = -1
                    #Faces central 
                    if self.kickoff == 'diagonal_right':
                        agent.controller.yaw = -0.5
                    else:
                        agent.controller.yaw = 0.5                 
                    self.counter += 1
                elif self.counter == 4:
                    agent.controller.jump = False
                    self.counter += 1
                elif self.counter > 4:
                    #Once landed flips into the ball
                    if not agent.me.airborne:
                        agent.push(flip(agent.me.local(agent.ball.location - agent.me.location)))
                    else:
                        if self.kickoff == 'diagonal_right':
                            agent.controller.yaw = 1
                        else:
                            agent.controller.yaw = -1  

            elif self.kickoff == 'back_right' or self.kickoff == 'back_left':
                #Fast off_centre kickoff
                defaultThrottle(agent,2300)
                agent.controller.boost = True
                if elapsed < 0.65:
                    relative_target = agent.boosts[7 if side(agent.team) == -1 else 26].location - agent.me.location
                    local_target = agent.me.local(relative_target)
                    defaultPD(agent,local_target)
                if elapsed > 0.65 and elapsed < 0.7:
                    agent.controller.jump = True
                elif elapsed > 0.65 and self.counter < 3:
                    agent.controller.jump = False
                    self.counter += 1
                elif elapsed > 0.65 and self.counter < 4:
                    agent.controller.jump = True
                    agent.controller.pitch = -1
                    #Faces central 
                    if self.kickoff == 'back_left':
                        agent.controller.yaw = -1
                    else:
                        agent.controller.yaw = 1                 
                    self.counter += 1
                elif self.counter == 4:
                    agent.controller.jump = False
                    self.counter += 1
                elif self.counter > 4:
                    #Once landed flips into the ball
                    if not agent.me.airborne:
                        agent.push(flip(agent.me.local(agent.ball.location - agent.me.location)))
                    else:
                        if self.kickoff == 'back_right':
                            agent.controller.yaw = 0.85
                        else:
                            agent.controller.yaw = -0.85
            
            elif self.kickoff == 'back_centre':
                #Fast back_centre kickoff
                defaultThrottle(agent,2300)
                if self.counter < 5:
                    agent.controller.boost = True
                if elapsed < 0.45:
                    relative_target = agent.ball.location - agent.me.location
                    local_target = agent.me.local(relative_target)
                    defaultPD(agent,local_target)
                elif elapsed < 1:
                    relative_target = agent.boosts[31 if side(agent.team) == -1 else 2].location - agent.me.location
                    local_target = agent.me.local(relative_target)
                    defaultPD(agent,local_target)
                elif elapsed > 1 and elapsed < 1.05:
                    agent.controller.jump = True
                elif elapsed > 1 and self.counter < 3:
                    agent.controller.jump = False
                    self.counter += 1
                elif elapsed > 1 and self.counter < 4:
                    agent.controller.jump = True
                    agent.controller.pitch = -1
                    #Faces central 
                    agent.controller.yaw = -1               
                    self.counter += 1
                elif self.counter == 4:
                    agent.controller.jump = False
                    self.counter += 1
                elif self.counter > 4:
                    #Once landed flips into the ball
                    if agent.me.airborne:
                        agent.controller.boost = False
                        agent.controller.yaw = 0
                    else:
                        agent.push(flip(agent.me.local(agent.ball.location - agent.me.location)))                    

            else:
                #kickoff for non-football gamemodes (heatseaker, dropshot etc) - just drives towards ball and flips
                target = agent.ball.location + Vector3(0,200*side(agent.team),0)
                local_target = agent.me.local(target - agent.me.location)
                defaultPD(agent, local_target)
                defaultThrottle(agent, 2300)
                agent.controller.boost = True
                if local_target.magnitude() < 800:
                    agent.pop()
                    #flip towards opponent goal
                    agent.push(flip(agent.me.local(agent.foe_goal.location - agent.me.location)))
          

class recovery():
    #Point towards our velocity vector and land upright, unless we aren't moving very fast
    #A vector can be provided to control where the car points when it lands
    def __init__(self,target=None):
        self.target = target
    def run(self, agent):
        if self.target != None:
            local_target = agent.me.local((self.target-agent.me.location).flatten())
        else:
            local_target = agent.me.local(agent.me.velocity.flatten())

        defaultPD(agent,local_target)
        agent.controller.throttle = 1
        if not agent.me.airborne:
            agent.pop()

class short_shot():
    #This routine drives towards the ball and attempts to hit it towards a given target
    #It does not require ball prediction and kinda guesses at where the ball will be on its own
    def __init__(self,target):
        self.target = target
    def run(self,agent):
        car_to_ball,distance = (agent.ball.location - agent.me.location).normalize(True)
        ball_to_target = (self.target - agent.ball.location).normalize()

        relative_velocity = car_to_ball.dot(agent.me.velocity-agent.ball.velocity)
        if relative_velocity != 0.0:
            eta = cap(distance / cap(relative_velocity,400,2300),0.0, 1.5)
        else:
            eta = 1.5

        #If we are approaching the ball from the wrong side the car will try to only hit the very edge of the ball
        left_vector = car_to_ball.cross((0,0,1))
        right_vector = car_to_ball.cross((0,0,-1))
        target_vector = -ball_to_target.clamp(left_vector, right_vector)
        final_target = agent.ball.location + (target_vector*(distance/2))

        #Some adjustment to the final target to ensure we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1]) > 5150: final_target[0] = cap(final_target[0],-750,750)
        
        agent.line(final_target-Vector3(0,0,100),final_target+Vector3(0,0,100),[255,255,255])
        angles = defaultPD(agent, agent.me.local(final_target-agent.me.location))
        defaultThrottle(agent, 2300 if distance > 1600 else 2300-cap(1600*abs(angles[1]),0,2050))
        agent.controller.boost = False if agent.me.airborne or (abs(angles[1]) > 0.3 and distance < 1000) else agent.controller.boost
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake

        if abs(angles[1]) < 0.05 and (eta < 0.45 or distance < 150):
            agent.pop()
            agent.push(flip(agent.me.local(car_to_ball)))