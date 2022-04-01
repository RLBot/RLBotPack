from utils import *

#This file holds all of the mechanical tasks, called "routines", that the bot can do

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

class atba():
    #An example routine that just drives towards the ball at max speed
    def run(self, agent):
        relative_target = agent.ball.location - agent.me.location
        local_target = agent.me.local(relative_target)
        defaultPD(agent, local_target)
        defaultThrottle(agent, 2300)


class aerial():

    def __init__(self, ball_location: Vector3, intercept_time: float, on_ground: bool, target: Vector3 = None):
        super().__init__()
        self.ball_location = ball_location
        self.intercept_time = intercept_time
        self.target = target
        self.jumping = on_ground
        self.time = -1
        self.jump_time = -1
        self.counter = 0

    def run(self, agent):
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
                vf += agent.me.orientation.up * jump_speed
                xf += agent.me.orientation.up * jump_speed * T

            vf += agent.me.orientation.up * jump_acc * tau
            xf += agent.me.orientation.up * jump_acc * tau * (T - 0.5 * tau)

            vf += agent.me.orientation.up * jump_speed
            xf += agent.me.orientation.up * jump_speed * (T - tau)

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
                defaultPD(agent, agent.me.local(self.ball_location - agent.me.location))

        if jump_max_duration <= elapsed < 0.3 and self.counter == 3:
            agent.controller.roll = 0
            agent.controller.pitch = 0
            agent.controller.yaw = 0
            agent.controller.steer = 0

        if agent.me.forward.angle3D(direction) < 0.3:
            if delta_x.magnitude() > 50:
                agent.controller.boost = 1
                agent.controller.throttle = 0
            else:
                agent.controller.boost = 0
                agent.controller.throttle = cap(0.5 * throttle_accel * T ** 2, 0, 1)
        else:
            agent.controller.boost = 0
            agent.controller.throttle = 0

        if T <= 0 or not shot_valid(agent, self, threshold=150):
            agent.pop()
            agent.push(recovery())

    def is_viable(self, agent, time: float):
        T = self.intercept_time - time
        xf = agent.me.location + agent.me.velocity * T + 0.5 * gravity * T ** 2
        vf = agent.me.velocity + gravity * T
        if not agent.me.airborne:
            vf += agent.me.orientation.up * (2 * jump_speed + jump_acc * jump_max_duration)
            xf += agent.me.orientation.up * (jump_speed * (2 * T - jump_max_duration) + jump_acc * (
                    T * jump_max_duration - 0.5 * jump_max_duration ** 2))

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

        in_goal = abs(agent.me.location.y) > 5000

        return velocity_estimate.magnitude() < 0.9 * max_speed and enough_boost and enough_time and not in_goal


class aerial_shot():
    #Very similar to jump_shot(), but instead designed to hit targets above 300uu
    #***This routine is a WIP*** It does not currently hit the ball very hard, nor does it like to be accurate above 600uu or so
    def __init__(self, ball_location, intercept_time, shot_vector, ratio):
        self.ball_location = ball_location
        self.intercept_time = intercept_time
        #The direction we intend to hit the ball in
        self.shot_vector = shot_vector
        #The point we hit the ball at
        self.intercept = self.ball_location - (self.shot_vector * 100)
        #dictates when (how late) we jump, much later than in jump_shot because we can take advantage of a double jump
        self.jump_threshold = 750
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
        if abs(agent.me.location[1]) > 5000:
            if abs(final_target[0]) < 800:
                final_target[0] = cap(final_target[0],-800,800)
            else:
                final_target[1] = cap(final_target[1],-5100,5100)
        
        local_final_target = agent.me.local(final_target - agent.me.location)

        #drawing debug lines to show the dodge point and final target (which differs due to the adjustment)
        agent.line(agent.me.location,self.intercept)
        agent.line(self.intercept-Vector3(0,0,100), self.intercept+Vector3(0,0,100),[255,0,0])
        agent.line(final_target-Vector3(0,0,100),final_target+Vector3(0,0,100),[0,255,0])

        angles = defaultPD(agent,local_final_target)
        
        if self.jump_time == 0:
            defaultThrottle(agent, speed_required)
            agent.controller.boost = False if abs(angles[1]) > 0.3 or agent.me.airborne else agent.controller.boost
            agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake
            if local_acceleration_required[2] > self.jump_threshold and local_acceleration_required[2] > local_acceleration_required.flatten().magnitude():
                #Switch into the jump when the upward acceleration required reaches our threshold, hopefully we have aligned already...
                self.jump_time = agent.time
        else:
            time_since_jump = agent.time - self.jump_time

            #While airborne we boost if we're within 30 degrees of our local acceleration requirement
            if agent.me.airborne and local_acceleration_required.magnitude() * time_remaining > 100:
                    if agent.me.boost > 1:
                        angles = defaultPD(agent, local_acceleration_required)
                        if abs(angles[0]) + abs(angles[1]) < 0.5:
                            agent.controller.boost = True
                    else:
                        angles = defaultPD(agent, agent.me.local(self.shot_vector))
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

        if raw_time_remaining < -0.25 or not shot_valid(agent,self) or (agent.rotation_index != 0 and local_acceleration_required[2] < self.jump_threshold / 5 and self.jump_time == 0):
            agent.pop()
            agent.push(recovery())

class flip():
    #Flip takes a vector in local coordinates and flips/dodges in that direction
    #cancel causes the flip to cancel halfway through, which can be used to half-flip
    def __init__(self, vector, cancel=False, boosting=False):
        self.vector = vector.normalize()
        self.pitch = -self.vector[0]
        self.yaw = self.vector[1]
        self.cancel = cancel
        self.boosting = boosting
        #the time the jump began
        self.time = -1
        #keeps track of the frames the jump button has been released
        self.counter = 0
    def run(self, agent):
        if self.time == -1:
            elapsed = 0
            self.time = agent.time
        else:
            elapsed = agent.time - self.time
        if elapsed < 0.1:
            agent.controller.jump = True
        elif elapsed >=0.1 and self.counter < 3:
            agent.controller.jump = False
            self.counter += 1
        elif elapsed < 0.25 or (not self.cancel and elapsed < 0.85):
            agent.controller.jump = True
            agent.controller.pitch = self.pitch
            agent.controller.yaw = self.yaw
        else:
            agent.pop()
            agent.push(recovery(None, self.boosting))
        if self.boosting:
            agent.controller.boost = agent.me.local(agent.me.forward).angle3D(self.vector) < math.pi
            
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
            #See commends for adjustment in jump_shot or aerial for explanation
            side_of_vector = sign(self.vector.cross((0,0,1)).dot(car_to_target))
            car_to_target_perp = car_to_target.cross((0,0,side_of_vector)).normalize()
            adjustment = car_to_target.angle(self.vector) * distance_remaining / 3.14
            final_target = self.target + (car_to_target_perp * adjustment)
        else:
            final_target = self.target

        #Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1]) > 5100: final_target[0] = cap(final_target[0],-750,750)

        local_target = agent.me.local(final_target - agent.me.location)
        
        angles = defaultPD(agent, local_target, self.direction)
        defaultThrottle(agent, 2300, self.direction)
        
        agent.controller.boost = False
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake

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

        agent.line(self.boost.location - Vector3(0,0,500),self.boost.location+ Vector3(0,0,500),[0,255,0])

        if self.target != None:
            vector = (self.target - self.boost.location).normalize()
            side_of_vector = sign(vector.cross((0,0,1)).dot(car_to_boost))
            car_to_boost_perp = car_to_boost.cross((0,0,side_of_vector)).normalize()
            adjustment = car_to_boost.angle(vector) * distance_remaining / 3.5
            final_target = self.boost.location + (car_to_boost_perp * adjustment)
            if on_wall(agent.me.location):
                final_target = final_target.flatten()
            #Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
            if abs(agent.me.location[1]) > 5100:
                final_target[0] = cap(final_target[0], -800, 800)
                final_target[1] = cap(final_target[1], -5000, 5000)

            if abs(final_target[0]) > 4096:
                final_target[0] = (4000 + distance_to_wall(agent.me.location)) * sign(final_target[0])
            if abs(final_target[1]) > 5120:
                final_target[1] = (5000 + distance_to_wall(agent.me.location)) * sign(final_target[1])
            car_to_target = (self.target - agent.me.location).magnitude()
        else:
            adjustment = 9999
            car_to_target = 0
            final_target = self.boost.location

        #Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1]) > 5100: final_target[0] = cap(final_target[0],-750,750)

        local_target = agent.me.local(final_target - agent.me.location)
        
        angles = defaultPD(agent, local_target)
        defaultThrottle(agent, 2300)
        
        agent.controller.boost = self.boost.large if abs(angles[1]) < 0.3 else False
        agent.controller.handbrake = True if abs(angles[1]) > 1.6 else agent.controller.handbrake

        velocity = 1+agent.me.velocity.magnitude()
        if self.boost.active == False or agent.me.boost >= 99.0 or distance_remaining < 350 or agent.rotation_index == 0:
            agent.pop()
        elif agent.me.airborne:
            agent.push(recovery(self.target))
        elif abs(angles[1]) < 0.05 and velocity > 600 and velocity < 2150 and distance_remaining / velocity > 2.5:
            agent.push(flip(local_target))


class goto_pad():
    # very similar to goto() but designed for grabbing boost
    # if a target is provided the bot will try to be facing the target as it passes over the boost
    def __init__(self, boost, target=None):
        self.boost = boost
        self.target = target

    def run(self, agent):
        car_to_boost = self.boost.location - agent.me.location
        distance_remaining = car_to_boost.flatten().magnitude()

        agent.line(self.boost.location - Vector3(0, 0, 500), self.boost.location + Vector3(0, 0, 500), [0, 255, 0])

        if self.target != None:
            vector = (self.target - self.boost.location).normalize()
            side_of_vector = sign(vector.cross((0, 0, 1)).dot(car_to_boost))
            car_to_boost_perp = car_to_boost.cross((0, 0, side_of_vector)).normalize()
            adjustment = car_to_boost.angle(vector) * distance_remaining / 3.14
            final_target = self.boost.location + (car_to_boost_perp * adjustment)
        else:
            final_target = self.boost.location

        # Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1]) > 5100: final_target[0] = cap(final_target[0], -750, 750)

        local_target = agent.me.local(final_target - agent.me.location)

        angles = defaultPD(agent, local_target)
        defaultThrottle(agent, 2300)

        agent.controller.boost = self.boost.large if abs(angles[1]) < 0.3 else False
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake

        if self.boost.active == False or agent.me.boost >= 99.0 or distance_remaining < 800 or distance_remaining > 1200 or agent.rotation_index == 0:
            agent.pop()
        elif agent.me.airborne:
            agent.push(recovery(self.target))

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
        self.dodge_point = self.ball_location - (self.shot_vector * 170)
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
        if abs(agent.me.location[1]) > 5100:
            final_target[0] = cap(final_target[0], -800, 800)
            final_target[1] = cap(final_target[1], -5000, 5000)

        distance_from_goal = (self.ball_location - agent.friend_goal.location).magnitude()

        if distance_from_goal < 6000:
            if abs(final_target[0]) > 4096:
                final_target[0] = (4000 + distance_to_wall(agent.me.location)) * sign(final_target[0])
            if abs(final_target[1]) > 5120:
                final_target[1] = (5000 + distance_to_wall(agent.me.location)) * sign(final_target[1])

        local_final_target = agent.me.local(final_target - agent.me.location)

        #drawing debug lines to show the dodge point and final target (which differs due to the adjustment)
        agent.line(agent.me.location,self.dodge_point)
        agent.line(self.dodge_point-Vector3(0,0,100), self.dodge_point+Vector3(0,0,100),[255,0,0])
        agent.line(final_target-Vector3(0,0,100),final_target+Vector3(0,0,100),[0,255,0])

        #Calling our drive utils to get us going towards the final target
        angles = defaultPD(agent,local_final_target,self.direction)
        defaultThrottle(agent, speed_required,self.direction)

        agent.line(agent.me.location, agent.me.location + (self.shot_vector*200), [255,255,255])

        agent.controller.boost = False if abs(angles[1]) > 0.3 or agent.me.airborne else agent.controller.boost
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 and self.direction == 1 else agent.controller.handbrake

        if not self.jumping:
            if raw_time_remaining <= 0.0 or (speed_required - 2300) * time_remaining > 45 or not shot_valid(agent,self) or (agent.rotation_index != 0 and local_acceleration_required[2] < self.jump_threshold / 5):
                #If we're out of time or not fast enough to be within 45 units of target at the intercept time, we pop
                agent.pop()
                if agent.me.airborne:
                    agent.push(recovery())
            elif local_acceleration_required[2] > self.jump_threshold and local_acceleration_required[2] > local_acceleration_required.flatten().magnitude():
                #Switch into the jump when the upward acceleration required reaches our threshold, and our lateral acceleration is negligible
                self.jumping = True 
        else:
            if (raw_time_remaining > 0.2 and not shot_valid(agent,self,60)) or raw_time_remaining <= -0.9 or (not agent.me.airborne and self.counter > 0):
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


class wall_shot():
    # Hits a target point at a target time towards a target direction
    # Target must be no higher than 300uu unless you're feeling lucky
    # TODO - speed
    def __init__(self, ball_location, intercept_time, shot_vector, ratio, direction=1, speed=2300):
        self.ball_location = ball_location
        self.intercept_time = intercept_time
        # The direction we intend to hit the ball in
        self.shot_vector = shot_vector
        # The point we dodge at
        # 173 is the 93uu ball radius + a bit more to account for the car's hitbox
        self.dodge_point = self.ball_location - (self.shot_vector * 170)
        # Ratio is how aligned the car is. Low ratios (<0.5) aren't likely to be hit properly
        self.ratio = ratio
        # whether the car should attempt this backwards
        self.direction = direction
        # Intercept speed not implemented
        self.speed_desired = speed
        # controls how soon car will jump based on acceleration required. max 584
        # bigger = later, which allows more time to align with shot vector
        # smaller = sooner
        self.jump_threshold = 450
        # Flags for what part of the routine we are in
        self.jumping = False
        self.dodging = False
        self.counter = 0

    def run(self, agent):
        raw_time_remaining = self.intercept_time - agent.time
        # Capping raw_time_remaining above 0 to prevent division problems
        time_remaining = cap(raw_time_remaining, 0.001, 10.0)
        car_to_ball = self.ball_location - agent.me.location
        # whether we are to the left or right of the shot vector
        side_of_shot = sign(self.ball_location[0])

        car_to_dodge_point = self.dodge_point - agent.me.location
        car_to_dodge_perp = car_to_dodge_point.cross((0, 0, side_of_shot))  # perpendicular
        distance_remaining = car_to_dodge_point.magnitude()

        speed_required = distance_remaining / time_remaining
        acceleration_required = backsolve(self.dodge_point, agent.me, time_remaining, 0 if not self.jumping else 650)
        local_acceleration_required = agent.me.local(acceleration_required)

        height_difference = abs(agent.me.location[2] - self.ball_location[2])

        # The adjustment causes the car to circle around the dodge point in an effort to line up with the shot vector
        # The adjustment slowly decreases to 0 as the bot nears the time to jump
        adjustment = distance_remaining * 2 # size of adjustment
        # we don't adjust the final target if we are already jumping
        final_target = self.dodge_point + (
            car_to_dodge_perp.normalize() * adjustment if not self.jumping else 0) + Vector3(0, 0, 50)
        # Ensuring our target isn't too close to the sides of the field, where our car would get messed up by the radius of the curves

        # Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1]) > 5050 and abs(agent.me.location[0]) < 900:
            if abs(final_target[0]) < 750:
                final_target[0] = cap(final_target[0], -700, 700)
            else:
                final_target[1] = cap(final_target[1], -5000, 5000)

        local_final_target = agent.me.local(final_target - agent.me.location)

        # drawing debug lines to show the dodge point and final target (which differs due to the adjustment)
        agent.line(agent.me.location, self.dodge_point)
        agent.line(self.dodge_point - Vector3(0, 0, 100), self.dodge_point + Vector3(0, 0, 100), [255, 0, 0])
        agent.line(final_target - Vector3(0, 0, 100), final_target + Vector3(0, 0, 100), [0, 255, 0])

        # Calling our drive utils to get us going towards the final target
        angles = defaultPD(agent, local_final_target, self.direction)
        defaultThrottle(agent, speed_required, self.direction)

        agent.line(agent.me.location, agent.me.location + (self.shot_vector * 200), [255, 255, 255])

        agent.controller.boost = False if abs(angles[1]) > 0.3 or agent.me.airborne else agent.controller.boost
        agent.controller.handbrake = True if abs(
            angles[1]) > 2.3 and self.direction == 1 else agent.controller.handbrake

        if not self.jumping:
            if raw_time_remaining <= 0.0 or (speed_required - 2300) * time_remaining > 45 or not shot_valid(agent,self) or agent.rotation_index != 0:
                # If we're out of time or not fast enough to be within 45 units of target at the intercept time, we pop
                agent.pop()
                if agent.me.airborne:
                    agent.push(recovery())
            elif local_acceleration_required[2] > self.jump_threshold and local_acceleration_required[2] > local_acceleration_required.flatten().magnitude() and distance_remaining < 800 and height_difference < 500:
                # Switch into the jump when the upward acceleration required reaches our threshold, and our lateral acceleration is negligible
                self.jumping = True
        else:
            if (raw_time_remaining > 0.2 and not shot_valid(agent, self, 60)) or raw_time_remaining <= -0.9 or (
                    not agent.me.airborne and self.counter > 0) or agent.rotation_index != 0:
                agent.pop()
                agent.push(recovery())
            elif self.counter == 0 and local_acceleration_required[2] > 0.0 and raw_time_remaining > 0.083:
                # Initial jump to get airborne + we hold the jump button for extra power as required
                agent.controller.jump = True
                agent.controller.boost = True
            elif self.counter < 3:
                # make sure we aren't jumping for at least 3 frames
                agent.controller.jump = False
                agent.controller.boost = True
                self.counter += 1
            elif raw_time_remaining <= 0.1 and raw_time_remaining > -0.9:
                # dodge in the direction of the shot_vector
                agent.controller.jump = True
                if not self.dodging:
                    vector = agent.me.local(self.shot_vector)
                    self.p = abs(vector[0]) * -sign(vector[0])
                    self.y = abs(vector[1]) * sign(vector[1]) * self.direction
                    self.dodging = True
                # simulating a deadzone so that the dodge is more natural
                agent.controller.pitch = self.p if abs(self.p) > 0.2 else 0
                agent.controller.yaw = self.y if abs(self.y) > 0.3 else 0

class kickoff():
    def __init__(self, x):
        self.time_of_kickoff = -1
        self.corner_kickoff = abs(x) > 1500
        self.straight_kickoff = abs(x) < 100
        self.side = sign(x + 1)
    def run(self, agent):
        if self.time_of_kickoff == -1:
            self.time_of_kickoff = agent.time
        elapsed = agent.time - self.time_of_kickoff

        car_to_ball = agent.ball.location - agent.me.location

        corner_kickoff = abs(agent.me.location.x) > 1500
        straight_kickoff = abs(agent.me.location.x) < 100
        team = -side(agent.team)

        steer = self.side * team if corner_kickoff else -self.side * team
        local_car_to_ball = agent.me.local(car_to_ball)

        speed_flip_vector = Vector3(1/math.sqrt(2), -steer/math.sqrt(2), 0)

        if not agent.kickoff_flag:
            agent.pop()

        if self.corner_kickoff:
            if elapsed < 0.23:
                agent.controller.steer = steer / 4
                defaultThrottle(agent, 2300)
            elif elapsed < 0.3:
                agent.push(flip(speed_flip_vector, True, True))
            elif elapsed < 2:
                agent.push(flip(local_car_to_ball))
        elif self.straight_kickoff:
            if elapsed < 0.4:
                agent.controller.steer = steer / 4
                defaultThrottle(agent, 2300)
            elif elapsed < 0.5:
                agent.push(flip(speed_flip_vector, True, True))
            elif elapsed < 2.2:
                defaultPD(agent, local_car_to_ball)
                defaultThrottle(agent, 2300)
                agent.controller.handbrake = True
            elif elapsed < 3:
                agent.push(flip(local_car_to_ball))
        else:
            if elapsed < 0.3:
                agent.controller.steer = steer / 4
                defaultThrottle(agent, 2300)
            elif elapsed < 0.5:
                agent.push(flip(speed_flip_vector, True, True))
            elif elapsed < 2:
                defaultPD(agent, local_car_to_ball)
                defaultThrottle(agent, 2300)
                agent.controller.handbrake = True
            elif elapsed < 3:
                agent.push(flip(local_car_to_ball))

class recovery():
    #Point towards our velocity vector and land upright, unless we aren't moving very fast
    #A vector can be provided to control where the car points when it lands
    def __init__(self, target=None, boosting=False):
        self.target = target
        self.boosting = boosting
    def run(self, agent):
        if self.target != None:
            local_target = agent.me.local((self.target-agent.me.location).flatten())
        else:
            local_target = agent.me.local(agent.me.velocity.flatten())

        angles = defaultPD(agent, local_target)
        agent.controller.throttle = 1
        agent.controller.boost = self.boosting

        angles_magnitude = angles[0] + angles[1] + angles[2]

        if angles_magnitude < 1 and not agent.me.doublejumped:
            agent.pop()
            #Wavedash recovery!
            agent.push(wavedash())

        if not agent.me.airborne:
            agent.pop()

class wavedash():
    # this routine will wavedash on recovery!
    def __init__(self):
        self.step = 0
    def run(self, agent):
        if agent.me.velocity.flatten().magnitude() > 100:
            target = agent.me.velocity.flatten().normalize()*100 + Vector3(0, 0, 50)
        else:
            target = agent.me.forward.flatten()*100 + Vector3(0, 0, 50)
        local_target = agent.me.local(target)
        defaultPD(agent, local_target)
        if self.step < 6 and not agent.me.airborne:
            self.step += 1
            if self.step < 3:
                agent.controller.jump = True
            else:
                agent.controller.jump = False
        else:
            if agent.me.location.z + agent.me.velocity.z * 0.2 < 5:
                agent.controller.jump = True
                agent.controller.pitch = -1
                agent.controller.yaw = agent.controller.roll = 0
                agent.pop()
            elif not agent.me.airborne or agent.me.doublejumped:
                agent.pop()

class pop_up():
    # Hits a target point at a target time towards a target direction
    # Target must be no higher than 300uu unless you're feeling lucky
    # TODO - speed
    def __init__(self, ball_location, intercept_time, shot_vector, ratio, direction=1, speed=2300):
        self.ball_location = ball_location
        self.intercept_time = intercept_time
        # The direction we intend to hit the ball in
        self.shot_vector = shot_vector
        # Ratio is how aligned the car is. Low ratios (<0.5) aren't likely to be hit properly
        self.ratio = ratio
        # whether the car should attempt this backwards
        self.direction = direction
        # Intercept speed not implemented
        self.speed_desired = speed
        # controls how soon car will jump based on acceleration required. max 584
        # bigger = later, which allows more time to align with shot vector
        # smaller = sooner
        self.jump_threshold = 400
        # Flags for what part of the routine we are in
        self.jumping = False
        self.dodging = False
        self.counter = 0

    def run(self, agent):
        raw_time_remaining = self.intercept_time - agent.time
        # Capping raw_time_remaining above 0 to prevent division problems
        time_remaining = cap(raw_time_remaining, 0.001, 10.0)
        car_to_ball = self.ball_location - agent.me.location
        # whether we are to the left or right of the shot vector
        side_of_shot = sign(self.shot_vector.cross((0, 0, 1)).dot(car_to_ball))

        car_to_point = self.ball_location - agent.me.location
        car_to_perp = car_to_point.cross((0, 0, side_of_shot))  # perpendicular
        distance_remaining = car_to_point.magnitude()

        speed_required = distance_remaining / time_remaining
        acceleration_required = backsolve(self.ball_location, agent.me, time_remaining,
                                          0 if not self.jumping else 650)
        local_acceleration_required = agent.me.local(acceleration_required)

        # The adjustment causes the car to circle around the dodge point in an effort to line up with the shot vector

        added_wall_adjustment = cap(4 - distance_to_wall(agent.me.location) / 500, 0, 4)

        adjustment = car_to_point.angle(self.shot_vector) * distance_remaining / 2.0 + added_wall_adjustment #size of adjustment
        adjustment *= (cap(self.jump_threshold - (acceleration_required[2]), 0.0,
                           self.jump_threshold) / self.jump_threshold)  # factoring in how close to jump we are
        # we don't adjust the final target if we are already jumping
        final_target = self.ball_location + (
            (car_to_perp.normalize() * adjustment) if not self.jumping else 0) + Vector3(0, 0, 50)
        # Ensuring our target isn't too close to the sides of the field, where our car would get messed up by the radius of the curves

        #Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1]) > 5100:
            final_target[0] = cap(final_target[0], -800, 800)
            final_target[1] = cap(final_target[1], -5000, 5000)

        distance_from_goal = (self.ball_location - agent.friend_goal.location).magnitude()

        if distance_from_goal < 6000:
            if abs(final_target[0]) > 4096:
                final_target[0] = (4096 + distance_to_wall(agent.me.location)) * sign(final_target[0])
            if abs(final_target[1]) > 5120:
                final_target[1] = (5120 + distance_to_wall(agent.me.location)) * sign(final_target[1])

        local_final_target = agent.me.local(final_target - agent.me.location)

        # drawing debug lines to show the dodge point and final target (which differs due to the adjustment)
        agent.line(agent.me.location, self.ball_location)
        agent.line(self.ball_location - Vector3(0, 0, 100), self.ball_location + Vector3(0, 0, 100), [255, 0, 0])
        agent.line(final_target - Vector3(0, 0, 100), final_target + Vector3(0, 0, 100), [0, 255, 0])

        # Calling our drive utils to get us going towards the final target
        angles = defaultPD(agent, local_final_target, self.direction)
        defaultThrottle(agent, speed_required, self.direction)

        agent.line(agent.me.location, agent.me.location + (self.shot_vector * 200), [255, 255, 255])

        agent.controller.boost = False if abs(angles[1]) > 0.3 or agent.me.airborne else agent.controller.boost
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 and self.direction == 1 else agent.controller.handbrake

        if raw_time_remaining <= 0.0 or (speed_required - 2300) * time_remaining > 45 or not shot_valid(agent, self) or agent.rotation_index != 0:
            # If we're out of time or not fast enough to be within 45 units of target at the intercept time, we pop
            agent.pop()
            if agent.me.airborne:
                agent.push(recovery())

class short_shot():
    #This routine drives towards the ball and attempts to hit it towards a given target
    #It does not require ball prediction and kinda guesses at where the ball will be on its own
    def __init__(self,target):
        self.target = target
    def run(self,agent):
        car_to_ball,distance = (agent.ball.location - agent.me.location).normalize(True)
        ball_to_target = (self.target - agent.ball.location).normalize()

        ball_to_our_goal = (agent.friend_goal.location - agent.ball.location)

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

        #Some extra adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1]) > 5000:
            if abs(final_target[0]) < 800:
                final_target[0] = cap(final_target[0],-800,800)
            else:
                final_target[1] = cap(final_target[1],-5100,5100)
        
        agent.line(final_target-Vector3(0,0,100),final_target+Vector3(0,0,100),[255,255,255])
        
        angles = defaultPD(agent, agent.me.local(final_target-agent.me.location))
        defaultThrottle(agent, 2300 if distance > 1600 else 2300-cap(1600*abs(angles[1]),0,2050))
        agent.controller.boost = False if agent.me.airborne or abs(angles[1]) > 0.3 else agent.controller.boost
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake

        if abs(angles[1]) < 0.05 and (eta < 0.45 or distance < 150):
            agent.pop()
            agent.push(flip(agent.me.local(car_to_ball)))
        if eta > 1 or ball_to_our_goal.magnitude() < 500 or agent.rotation_index != 0:
            agent.pop()

class save():
    # this routine simply hits the ball away from our goal
    def __init__(self):
        self.eta = 0
    def run(self, agent):
        car_to_ball, distance = (agent.ball.location - agent.me.location).normalize(True)

        ball_to_our_goal = (agent.ball.location - agent.friend_goal.location).normalize()

        relative_velocity = car_to_ball.dot(agent.me.velocity - agent.ball.velocity)
        if relative_velocity != 0.0:
            self.eta = cap(distance / cap(relative_velocity, 400, 2300), 0.0, 1.5)
        else:
            self.eta = 1.5

        # If we are approaching the ball from the wrong side the car will try to only hit the very edge of the ball
        left_vector = car_to_ball.cross((0, 0, 1))
        right_vector = car_to_ball.cross((0, 0, -1))
        target_vector = -ball_to_our_goal.clamp(left_vector, right_vector)
        final_target = agent.ball.location + (target_vector * (distance / 2))

        # Some extra adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1]) > 5000:
            if abs(final_target[0]) < 800:
                final_target[0] = cap(final_target[0],-800,800)
            else:
                final_target[1] = cap(final_target[1],-5100,5100)

        agent.line(final_target - Vector3(0, 0, 100), final_target + Vector3(0, 0, 100), [255, 255, 255])

        angles = defaultPD(agent, agent.me.local(final_target - agent.me.location))
        defaultThrottle(agent, 2300 if distance > 1600 else 2300 - cap(1600 * abs(angles[1]), 0, 2050))
        agent.controller.boost = False if agent.me.airborne or abs(angles[1]) > 0.3 else agent.controller.boost
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake

        if abs(angles[1]) < 0.05 and (self.eta < 0.45 or distance < 150):
            agent.pop()
            agent.push(flip(agent.me.local(car_to_ball)))
        if self.eta > 1 or agent.rotation_index != 0:
            agent.pop()

class demo():
    # this routine simply hits the ball away from our goal
    def __init__(self, target):
        self.target = target
    def run(self, agent):
        distance = (self.target.location - agent.me.location).magnitude()
        car_to_target = self.target.location + self.target.velocity * (distance / 2000) - agent.me.location

        angles = defaultPD(agent, agent.me.local(car_to_target))
        defaultThrottle(agent, 2300 if distance < 500 else 2300 - cap(1600 * abs(angles[1]), 0, 2050))
        agent.controller.boost = False if agent.me.airborne else agent.controller.boost
        agent.controller.handbrake = True if abs(angles[1]) > 2.0 else agent.controller.handbrake

        if self.target.location.z > 100 and distance < 1000 and abs(self.target.location.x) < 4000 and abs(self.target.location.y) < 5000:
            agent.pop()
            agent.controller.jump = True
        elif self.target.demolished or not agent.me.supersonic:
            agent.pop()

class align_in_goal():
    # this routine simply hits the ball away from our goal
    def __init__(self):
        self.backwards = False

    def run(self, agent):
        my_ball_distance = (agent.friend_goal.location - agent.ball.location).magnitude()
        ball_too_close = my_ball_distance < 1500 or (agent.ball.location + agent.ball.velocity - agent.me.location).magnitude() < 2000

        friend_goal_to_ball = (agent.friend_goal.location - agent.ball.location).flatten().normalize()
        ideal_position = (agent.friend_goal.location - friend_goal_to_ball * 700).flatten()
        ideal_position_to_me = ideal_position - agent.me.location
        ideal_distance = ideal_position_to_me.magnitude()

        me_to_goal = (agent.friend_goal.location - agent.me.location).flatten()

        relative_target = agent.ball.location - agent.me.location
        distance = me_to_goal.magnitude()

        ball_distance = (agent.friend_goal.location - agent.ball.location).magnitude()

        agent.line(ideal_position - Vector3(0, 0, 100), ideal_position + Vector3(0, 0, 100), [0, 0, 0])

        if distance < 700 and not self.backwards:
            defaultPD(agent, agent.me.local(relative_target))
            agent.controller.throttle = 1
            self.backwards = False
        else:
            self.backwards = True
        if distance > 400 and self.backwards:
            defaultPD(agent, agent.me.local(me_to_goal), -1)
            agent.controller.throttle = -1
            self.backwards = True

        if self.backwards and distance < 400:
            agent.pop()

        if ideal_distance < 50 or distance > 900 or ball_too_close:
            agent.pop()

class dribble():
    # this routine simply hits the ball away from our goal
    def __init__(self, target):
        self.target = target
        self.jumping = False
        self.step = 0
        self.eta = 0
    def run(self, agent):
        me_to_goal = (agent.me.location - self.target).normalize()
        balance_spot = agent.me.location + me_to_goal * 20

        ball_to_spot = agent.ball.location - balance_spot
        local_ball_offset = agent.me.local(ball_to_spot)
        distance = ball_to_spot.flatten().magnitude()

        ball_speed = agent.ball.velocity.flatten().magnitude()

        defaultPD(agent, local_ball_offset)
        if self.step == 0:
            car_to_ball = (agent.ball.location - agent.me.location).normalize()

            ball_to_our_goal = (agent.ball.location - agent.friend_goal.location).normalize()

            relative_velocity = car_to_ball.dot(agent.me.velocity - agent.ball.velocity)
            if relative_velocity != 0.0:
                self.eta = cap(distance / cap(relative_velocity, 400, 2300), 0.0, 1.5)
            else:
                self.eta = 1.5

            # If we are approaching the ball from the wrong side the car will try to only hit the very edge of the ball
            left_vector = car_to_ball.cross((0, 0, 1))
            right_vector = car_to_ball.cross((0, 0, -1))
            target_vector = -ball_to_our_goal.clamp(left_vector, right_vector)
            final_target = agent.ball.location + (target_vector * (distance / 2))

            # Some extra adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
            if abs(agent.me.location[1]) > 5000:
                if abs(final_target[0]) < 800:
                    final_target[0] = cap(final_target[0], -800, 800)
                else:
                    final_target[1] = cap(final_target[1], -5100, 5100)

            angles = defaultPD(agent, agent.me.local(final_target - agent.me.location))
            defaultThrottle(agent, cap(ball_speed + distance + 800, 0, 2300))
            agent.controller.boost = False if agent.me.airborne or abs(angles[1]) > 0.3 else agent.controller.boost
            agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake
            if agent.ball.location.z > 100 and distance < 500:
                self.step = 1
        if self.step == 1:
            defaultThrottle(agent, 2300)
            if distance < 50 and agent.ball.location.z > 80:
                self.step = 2
            elif agent.ball.location.z < 100:
                agent.pop()
        if self.step > 1:
            agent.controller.steer = cap(local_ball_offset[1] / 50, -1, 1)
            defaultThrottle(agent, cap(local_ball_offset[0] * 2 + ball_speed, 0, 2300))
            if agent.ball.location.z < 50 or distance > 200:
                agent.pop()
        if agent.me.airborne or agent.me.location.z > 500 or agent.rotation_index != 0:
            agent.pop()