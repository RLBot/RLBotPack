from util.utils import (Vector, backsolve, cap, defaultPD, defaultThrottle,
                        shot_valid, side, sign)

import math

max_speed = 2300
throttle_accel = 2/3 * 100
boost_per_second = 33 + (1/3)
jump_max_duration = 0.2
jump_speed = 291 + (2/3)
jump_acc = 1458 + (1/3)


class atba():
    def __init__(self, exit_distance=500, exit_flip=True):
        self.exit_distance = exit_distance
        self.exit_flip = exit_flip

    def run(self, agent):
        target = agent.ball.location
        car_to_target = target - agent.me.location
        distance_remaining = car_to_target.flatten().magnitude()

        # Some adjustment to the final target to ensure it's inside the field and we don't try to drive through any goalposts to reach it
        if abs(agent.me.location.y) > 5150:
            target.x = cap(target.x, -750, 750)

        local_target = agent.me.local(target - agent.me.location)

        angles = defaultPD(agent, local_target)
        defaultThrottle(agent, 1400)

        agent.controller.boost = False
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake

        velocity = 1+agent.me.velocity.magnitude()
        if distance_remaining < self.exit_distance:
            agent.pop()
            if self.exit_flip:
                agent.push(flip(local_target))
        elif abs(angles[1]) < 0.05 and velocity > 600 and velocity < 2150 and distance_remaining / velocity > 2.0:
            agent.push(flip(local_target))
        elif abs(angles[1]) > 2.8 and velocity < 200:
            agent.push(flip(local_target, True))
        elif agent.me.airborne:
            agent.push(recovery(target))


class wave_dash():
    # This is a straight-line only version of flip()
    # TODO - Refine jumping
    def __init__(self, boost=False):
        self.step = 0
        self.boost = boost

    def run(self, agent):
        # if agent.me.velocity.flatten().magnitude() > 100:
        #     target = agent.me.velocity.flatten().normalize() * 100 + Vector(z=50)
        # else:
        #     target = agent.me.forward.flatten() * 100 + Vector(z=50)

        # local_target = agent.me.local(target)
        # defaultPD(agent, local_target)

        if self.step <= 5:
            self.step += 1
            agent.controller.pitch = 1
            agent.controller.yaw = agent.controller.role = 0

        if self.step == 0:
            pass
        elif self.step < 3:
            agent.controller.jump = True
        elif self.step < 4:
            agent.controller.jump = False
        else:
            if (agent.me.location + (agent.me.velocity * 0.2)).z < 5:
                agent.controller.jump = True
                agent.controller.pitch = -1
                agent.controller.yaw = agent.controller.role = 0
                agent.pop()
            elif not agent.me.airborne:
                agent.pop()


class Aerial():
    def __init__(self, ball_intercept, intercept_time):
        self.target = ball_intercept
        self.intercept_time = intercept_time
        self.jumping = True
        self.time = -1
        self.jump_time = -1
        self.counter = 0

    def run(self, agent):
        agent.shooting = True

        if self.time is -1:
            elapsed = 0
            self.time = agent.time
            agent.print(f"Enter aerial - Hit ball {round(agent.me.location.dist(self.target) * 1000) / 1000}uu's away in {self.intercept_time - self.time}s")
        else:
            elapsed = agent.time - self.time

        T = self.intercept_time - agent.time
        xf = agent.me.location + agent.me.velocity * T + 0.5 * agent.gravity * T ** 2
        vf = agent.me.velocity + agent.gravity * T
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
                self.jumping = jump_elapsed <= 0.3  # jump_max_duration
        else:
            agent.controller.jump = False

        delta_x = self.target - xf
        direction = delta_x.normalize()

        agent.line(agent.me.location, self.target, agent.renderer.white())
        agent.line(self.target - Vector(z=100), self.target + Vector(z=100), agent.renderer.red())
        agent.line(agent.me.location, direction, agent.renderer.green())
        agent.dbg_2d(f"Delta_x.norm(): {delta_x.norm()}")

        if delta_x.norm() > 50:
            defaultPD(agent, agent.me.local(delta_x))
        else:
            defaultPD(agent, agent.me.local(self.target))

        if jump_max_duration <= elapsed and elapsed < 0.3 and self.counter ** 3:
            agent.controller.roll = agent.controller.pitch = agent.controller.yaw = agent.controller.steer = 0

        if agent.me.forward.angle3D(direction) < 0.3:
            if delta_x.norm() > 50:
                agent.controller.boost = 1
                agent.controller.throttle = 0
            else:
                agent.controller.boost = 0
                agent.controller.throttle = cap(0.5 * throttle_accel * T * T, 0, 1)
        else:
            agent.controller.boost = agent.controller.throttle = 0

        if T <= 0 or not shot_valid(agent, self, target=self.target):
            agent.pop()
            agent.shooting = False
            agent.shot_weight = -1
            agent.shot_time = -1
            agent.push(recovery(agent.friend_goal.location))

    def is_viable(self, agent):
        T = self.intercept_time - agent.time
        xf = agent.me.location + agent.me.velocity * T + 0.5 * agent.gravity * T * T
        vf = agent.me.velocity + agent.gravity * T

        if not agent.me.airborne:
            vf += agent.me.up * (2 * jump_speed + jump_acc * jump_max_duration)
            xf += agent.me.up * (jump_speed * (2 * T - jump_max_duration) + jump_acc * (T * jump_max_duration - 0.5 * jump_max_duration ** 2))

        delta_x = self.target - xf
        f = delta_x.normalize()
        phi = f.angle3D(agent.me.forward)
        turn_time = 0.7 * (2 * math.sqrt(phi / 9))

        tau1 = turn_time * cap(1 - 0.3 / phi, 0, 1)
        required_acc = (2 * delta_x.norm()) / ((T - tau1) * (T - tau1))
        ratio = required_acc / agent.boost_accel
        tau2 = T - (T - tau1) * math.sqrt(1 - cap(ratio, 0, 1))
        velocity_estimate = vf + agent.boost_accel * (tau2 - tau1) * f
        boost_estimate = (tau2 - tau1) * 30
        enough_boost = boost_estimate < 0.95 * agent.me.boost
        enough_time = abs(ratio) < 0.9
        enough_speed = velocity_estimate.normalize(True)[1] < 0.9 * max_speed
        return enough_speed and enough_boost and enough_time


class aerial_shot():
    # Very similar to jump_shot(), but instead designed to hit targets above 300uu
    # ***This routine is a WIP*** It does not currently hit the ball very hard, nor does it like to be accurate above 600uu or so
    def __init__(self, ball_location, intercept_time, shot_vector, ratio):
        self.ball_location = ball_location
        self.intercept_time = intercept_time
        # The direction we intend to hit the ball in
        self.shot_vector = shot_vector
        # The point we hit the ball at
        self.intercept = self.ball_location - (self.shot_vector * 110)
        # dictates when (how late) we jump, much later than in jump_shot because we can take advantage of a double jump
        self.jump_threshold = 600
        # what time we began our jump at
        self.jump_time = 0
        # If we need a second jump we have to let go of the jump button for 3 frames, this counts how many frames we have let go for
        self.counter = 0

    def run(self, agent):
        agent.shooting = True
        raw_time_remaining = self.intercept_time - agent.time
        # Capping raw_time_remaining above 0 to prevent division problems
        time_remaining = cap(raw_time_remaining, 0.001, 10.0)

        car_to_ball = self.ball_location - agent.me.location
        # whether we are to the left or right of the shot vector
        side_of_shot = sign(self.shot_vector.cross(Vector(z=1)).dot(car_to_ball))

        car_to_intercept = self.intercept - agent.me.location
        car_to_intercept_perp = car_to_intercept.cross(Vector(z=side_of_shot))  # perpendicular
        distance_remaining = car_to_intercept.flatten().magnitude()

        speed_required = distance_remaining / time_remaining
        # When still on the ground we pretend agent.gravity doesn't exist, for better or worse
        acceleration_required = backsolve(self.intercept, agent.me, time_remaining, 0 if self.jump_time == 0 else agent.gravity.z)
        local_acceleration_required = agent.me.local(acceleration_required)

        # The adjustment causes the car to circle around the dodge point in an effort to line up with the shot vector
        # The adjustment slowly decreases to 0 as the bot nears the time to jump
        adjustment = car_to_intercept.angle(self.shot_vector) * distance_remaining / 1.57  # size of adjustment
        # factoring in how close to jump we are
        adjustment *= cap(self.jump_threshold - (acceleration_required.z), 0, self.jump_threshold) / self.jump_threshold
        # we don't adjust the final target if we are already jumping
        final_target = self.intercept + ((car_to_intercept_perp.normalize() * adjustment) if self.jump_time == 0 else 0)

        # Some extra adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location.y) > 5150:
            final_target.x = cap(final_target.x, -750, 750)

        local_final_target = agent.me.local(final_target - agent.me.location)

        # drawing debug lines to show the dodge point and final target (which differs due to the adjustment)
        agent.line(agent.me.location, self.intercept, agent.renderer.white())
        agent.line(self.intercept-Vector(z=100), self.intercept+Vector(z=100), agent.renderer.red())
        agent.line(final_target-Vector(z=100), final_target+Vector(z=100), agent.renderer.green())

        angles = defaultPD(agent, local_final_target)

        if self.jump_time == 0:
            defaultThrottle(agent, speed_required)
            agent.controller.boost = False if abs(angles[1]) > 0.3 or agent.me.airborne else agent.controller.boost
            agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake
            if acceleration_required.z > self.jump_threshold:
                # Switch into the jump when the upward acceleration required reaches our threshold, hopefully we have aligned already...
                self.jump_time = agent.time
        else:
            time_since_jump = agent.time - self.jump_time

            # While airborne we boost if we're within 30 degrees of our local acceleration requirement
            if agent.me.airborne and local_acceleration_required.magnitude() * time_remaining > 100:
                angles = defaultPD(agent, local_acceleration_required)
                if abs(angles[0]) + abs(angles[1]) < 0.5:
                    agent.controller.boost = True
            if self.counter == 0 and (time_since_jump <= 0.2 and local_acceleration_required.z > 0):
                # hold the jump button up to 0.2 seconds to get the most acceleration from the first jump
                agent.controller.jump = True
            elif time_since_jump > 0.2 and self.counter < 3:
                # Release the jump button for 3 ticks
                agent.controller.jump = False
                self.counter += 1
            elif local_acceleration_required.z > 300 and self.counter == 3:
                # the acceleration from the second jump is instant, so we only do it for 1 frame
                agent.controller.jump = True
                agent.controller.pitch = 0
                agent.controller.yaw = 0
                agent.controller.roll = 0
                self.counter += 1

        if raw_time_remaining < -0.25 or not shot_valid(agent, self):
            agent.pop()
            agent.shooting = False
            agent.shot_weight = -1
            agent.shot_time = -1
            agent.push(recovery())


class flip():
    # Flip takes a vector in local coordinates and flips/dodges in that direction
    # cancel causes the flip to cancel halfway through, which can be used to half-flip
    def __init__(self, vector, cancel=False):
        self.vector = vector.normalize()
        self.pitch = abs(self.vector.x) * -sign(self.vector.x)
        self.yaw = abs(self.vector.y) * sign(self.vector.y)
        self.cancel = cancel
        # the time the jump began
        self.time = -1
        # keeps track of the frames the jump button has been released
        self.counter = 0

    def run(self, agent):
        if self.time == -1:
            elapsed = 0
            self.time = agent.time
        else:
            elapsed = agent.time - self.time

        if elapsed < 0.15:
            agent.controller.jump = True
        elif elapsed >= 0.15 and self.counter < 3:
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
    # Drives towards a designated (stationary) target
    # Optional vector controls where the car should be pointing upon reaching the target
    # TODO - slow down if target is inside our turn radius
    def __init__(self, target, vector=None, direction=1):
        self.target = target
        self.vector = vector
        self.direction = direction

    def run(self, agent):
        car_to_target = self.target - agent.me.location
        distance_remaining = car_to_target.flatten().magnitude()

        agent.line(self.target - Vector(z=500), self.target + Vector(z=500), [255, 0, 255])

        if self.vector != None:
            # See commends for adjustment in jump_shot or aerial for explanation
            side_of_vector = sign(self.vector.cross(Vector(z=1)).dot(car_to_target))
            car_to_target_perp = car_to_target.cross(Vector(z=side_of_vector)).normalize()
            adjustment = car_to_target.angle(self.vector) * distance_remaining / 3.14
            final_target = self.target + (car_to_target_perp * adjustment)
        else:
            final_target = self.target

        # Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location.y) > 5150:
            final_target.x = cap(final_target.x, -750, 750)

        local_target = agent.me.local(final_target - agent.me.location)

        angles = defaultPD(agent, local_target, self.direction)
        defaultThrottle(agent, 2300, self.direction)

        if agent.me.boost < 30 or (agent.playstyle is agent.playstyles.Defensive and agent.predictions['self_from_goal'] < 5000):
            agent.controller.boost = False
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake

        velocity = 1+agent.me.velocity.magnitude()
        agent.dbg_2d(distance_remaining)
        if distance_remaining < 350:
            agent.pop()
        elif abs(angles[1]) < 0.05 and velocity > 600 and velocity < 2150 and distance_remaining / velocity > 2.0:
            agent.push(flip(local_target))
        elif abs(angles[1]) > 2.8 and velocity < 200:
            agent.push(flip(local_target, True))
        elif agent.me.airborne:
            agent.push(recovery(self.target))


class goto_boost():
    # very similar to goto() but designed for grabbing boost
    # if a target is provided the bot will try to be facing the target as it passes over the boost
    def __init__(self, boost, target=None):
        self.boost = boost
        self.target = target
        self.start_time = None

    def run(self, agent):
        if self.start_time is None:
            self.start_time = agent.time

        car_to_boost = self.boost.location - agent.me.location
        distance_remaining = car_to_boost.flatten().magnitude()

        agent.line(self.boost.location - Vector(z=500), self.boost.location + Vector(z=500), [0, 255, 0])

        if self.target is not None:
            vector = (self.target - self.boost.location).normalize()
            side_of_vector = sign(vector.cross(Vector(z=1)).dot(car_to_boost))
            car_to_boost_perp = car_to_boost.cross(Vector(z=side_of_vector)).normalize()
            adjustment = car_to_boost.angle(vector) * distance_remaining / 3.14
            final_target = self.boost.location + (car_to_boost_perp * adjustment)
            car_to_target = (self.target - agent.me.location).magnitude()
        else:
            adjustment = 9999
            car_to_target = 0
            final_target = self.boost.location

        # Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location.y) > 5150:
            final_target.x = cap(final_target.x, -750, 750)

        local_target = agent.me.local(final_target - agent.me.location)

        angles = defaultPD(agent, local_target)
        defaultThrottle(agent, 2300)

        agent.controller.boost = self.boost.large if abs(angles[1]) < 0.3 else False
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake

        velocity = 1+agent.me.velocity.magnitude()
        if not self.boost.active or agent.me.boost >= 99.0 or distance_remaining < 350:
            agent.pop()
        elif agent.me.airborne:
            agent.push(recovery(self.target))
        elif abs(angles[1]) < 0.05 and velocity > 600 and velocity < 2150 and (distance_remaining / velocity > 2.0 or (adjustment < 90 and car_to_target/velocity > 2.0)):
            agent.push(flip(local_target))
        elif agent.time - self.start_time > 6 and not agent.stack[-1].__class__.__name__ == "flip":
            agent.pop()


class jump_shot():
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
        self.dodge_point = self.ball_location - (self.shot_vector * 173)
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
        agent.shooting = True
        raw_time_remaining = self.intercept_time - agent.time
        # Capping raw_time_remaining above 0 to prevent division problems
        time_remaining = cap(raw_time_remaining, 0.001, 10.0)
        car_to_ball = self.ball_location - agent.me.location
        # whether we are to the left or right of the shot vector
        side_of_shot = sign(self.shot_vector.cross(Vector(z=1)).dot(car_to_ball))

        car_to_dodge_point = self.dodge_point - agent.me.location
        car_to_dodge_perp = car_to_dodge_point.cross(Vector(z=side_of_shot))  # perpendicular
        distance_remaining = car_to_dodge_point.magnitude()

        speed_required = distance_remaining / time_remaining
        acceleration_required = backsolve(self.dodge_point, agent.me, time_remaining, 0 if not self.jumping else agent.gravity.z)
        local_acceleration_required = agent.me.local(acceleration_required)

        # The adjustment causes the car to circle around the dodge point in an effort to line up with the shot vector
        # The adjustment slowly decreases to 0 as the bot nears the time to jump
        adjustment = car_to_dodge_point.angle(self.shot_vector) * distance_remaining / 2.0  # size of adjustment
        # factoring in how close to jump we are
        adjustment *= (cap(self.jump_threshold - (acceleration_required.z), 0, self.jump_threshold) / self.jump_threshold)
        # we don't adjust the final target if we are already jumping
        final_target = self.dodge_point + ((car_to_dodge_perp.normalize() * adjustment) if not self.jumping else 0) + Vector(z=50)
        # Ensuring our target isn't too close to the sides of the field, where our car would get messed up by the radius of the curves

        # Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location.y) > 5150:
            final_target.x = cap(final_target.x, -750, 750)

        local_final_target = agent.me.local(final_target - agent.me.location)

        # drawing debug lines to show the dodge point and final target (which differs due to the adjustment)
        agent.line(agent.me.location, self.dodge_point, agent.renderer.white())
        agent.line(self.dodge_point-Vector(z=100), self.dodge_point+Vector(z=100), agent.renderer.red())
        agent.line(final_target-Vector(z=100), final_target+Vector(z=100), agent.renderer.green())

        # Calling our drive utils to get us going towards the final target
        angles = defaultPD(agent, local_final_target, self.direction)
        defaultThrottle(agent, speed_required, self.direction)

        agent.line(agent.me.location, agent.me.location + (self.shot_vector*200), agent.renderer.white())

        agent.controller.boost = False if abs(angles[1]) > 0.3 or agent.me.airborne else agent.controller.boost
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 and self.direction == 1 else agent.controller.handbrake

        if not self.jumping:
            if raw_time_remaining <= 0 or (speed_required - 2300) * time_remaining > 45 or not shot_valid(agent, self):
                # If we're out of time or not fast enough to be within 45 units of target at the intercept time, we pop
                agent.pop()
                agent.shooting = False
                agent.shot_weight = -1
                agent.shot_time = -1
                if agent.me.airborne:
                    agent.push(recovery())
            elif local_acceleration_required.z > self.jump_threshold and local_acceleration_required.z > local_acceleration_required.flatten().magnitude():
                # Switch into the jump when the upward acceleration required reaches our threshold, and our lateral acceleration is negligible
                self.jumping = True
        else:
            if (raw_time_remaining > 0.2 and not shot_valid(agent, self, 150)) or raw_time_remaining <= -0.9 or (not agent.me.airborne and self.counter > 0):
                agent.pop()
                agent.shooting = False
                agent.shot_weight = -1
                agent.shot_time = -1
                agent.push(recovery())
            elif self.counter == 0 and local_acceleration_required.z > 0 and raw_time_remaining > 0.083:
                # Initial jump to get airborne + we hold the jump button for extra power as required
                agent.controller.jump = True
            elif self.counter < 3:
                # make sure we aren't jumping for at least 3 frames
                agent.controller.jump = False
                self.counter += 1
            elif raw_time_remaining <= 0.1 and raw_time_remaining > -0.9:
                # dodge in the direction of the shot_vector
                agent.controller.jump = True
                if not self.dodging:
                    vector = agent.me.local(self.shot_vector)
                    self.p = abs(vector.x) * -sign(vector.x)
                    self.y = abs(vector.y) * sign(vector.y) * self.direction
                    self.dodging = True
                # simulating a deadzone so that the dodge is more natural
                agent.controller.pitch = self.p if abs(self.p) > 0.2 else 0
                agent.controller.yaw = self.y if abs(self.y) > 0.3 else 0


class generic_kickoff():
    def run(self, agent):
        target = agent.ball.location + Vector(y=200*side(agent.team))
        local_target = agent.me.local(target - agent.me.location)

        defaultPD(agent, local_target)
        agent.controller.throttle = 1
        agent.controller.boost = True

        distance = local_target.magnitude()

        if distance < 650:
            if len(agent.foes) > 0 and agent.predictions['closest_enemy'] > 1000:
                if distance < 100 or distance > 700:
                    agent.pop()
                    agent.kickoff_done = True
            else:
                agent.pop()
                agent.kickoff_done = True
                agent.push(flip(agent.me.local(agent.foe_goal.location - agent.me.location)))


class corner_kickoff():
    def run(self, agent):
        target = agent.ball.location + Vector(y=200*side(agent.team))
        local_target = agent.me.local(target - agent.me.location)

        defaultPD(agent, local_target)
        defaultThrottle(agent, 2300)

        distance = local_target.magnitude()
        agent.controller.throttle = 1
        agent.controller.boost = True

        if distance < 650:
            if len(agent.foes) > 0 and agent.predictions['closest_enemy'] > 1000:
                if distance < 100 or distance > 500:
                    agent.pop()
                    agent.kickoff_done = True

                defaultPD(agent, agent.ball.location - Vector(y=500*side(agent.team)))
            elif distance < 450:
                agent.pop()
                agent.kickoff_done = True
                agent.push(flip(agent.me.local(agent.foe_goal.location)))


class back_kickoff():
    def __init__(self):
        self.wave_dash = False
        self.start_time = None

    def run(self, agent):
        if self.start_time is None:
            self.start_time = agent.time

        if not self.wave_dash:
            time_elapsed = agent.time - self.start_time

            if time_elapsed > 0.75:
                self.wave_dash = True
                agent.push(wave_dash())

        target = agent.ball.location + Vector(y=200*side(agent.team))
        local_target = agent.me.local(target - agent.me.location)

        defaultPD(agent, local_target)
        agent.controller.throttle = 1
        agent.controller.boost = True

        distance = local_target.magnitude()

        if distance < 650:
            if len(agent.foes) > 0 and agent.predictions['closest_enemy'] > 1000:
                if distance < 100 or distance > 700:
                    agent.pop()
                    agent.kickoff_done = True
            else:
                agent.pop()
                agent.kickoff_done = True
                agent.push(flip(agent.me.local(agent.foe_goal.location - agent.me.location)))


class recovery():
    # Point towards our velocity vector and land upright, unless we aren't moving very fast
    # A vector can be provided to control where the car points when it lands
    def __init__(self, target=None):
        self.target = target

    def run(self, agent):
        if self.target is not None:
            local_target = agent.me.local(
                (self.target-agent.me.location).flatten())
        else:
            local_target = agent.me.local(agent.me.velocity.flatten())

        defaultPD(agent, local_target)
        agent.controller.throttle = 1
        if not agent.me.airborne:
            agent.pop()


class short_shot():
    # This routine drives towards the ball and attempts to hit it towards a given target
    # It does not require ball prediction and kinda guesses at where the ball will be on its own
    def __init__(self, target):
        self.target = target
        self.start_time = None

    def run(self, agent):
        agent.shooting = True

        if self.start_time is None:
            self.start_time = agent.time

        car_to_ball, distance = (agent.ball.location - agent.me.location).normalize(True)
        ball_to_target = (self.target - agent.ball.location).normalize()

        relative_velocity = car_to_ball.dot(agent.me.velocity-agent.ball.velocity)
        if relative_velocity != 0:
            eta = cap(distance / cap(relative_velocity, 400, 2300), 0, 1.5)
        else:
            eta = 1.5

        # If we are approaching the ball from the wrong side the car will try to only hit the very edge of the ball
        left_vector = car_to_ball.cross(Vector(z=1))
        right_vector = car_to_ball.cross(Vector(z=-1))
        target_vector = -ball_to_target.clamp(left_vector, right_vector)
        final_target = agent.ball.location + (target_vector*(distance/2))

        # Some adjustment to the final target to ensure we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location.y) > 5150:
            final_target.x = cap(final_target.x, -750, 750)

        agent.line(final_target-Vector(z=100), final_target + Vector(z=100), [255, 255, 255])

        angles = defaultPD(agent, agent.me.local(final_target-agent.me.location))
        defaultThrottle(agent, 2300 if distance > 1600 else 2300-cap(1600*abs(angles[1]), 0, 2050))
        agent.controller.boost = False if agent.me.airborne or abs(angles[1]) > 0.3 else agent.controller.boost
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake

        if abs(angles[1]) < 0.05 and (eta < 0.45 or distance < 150):
            agent.pop()
            agent.shooting = False
            agent.shot_weight = -1
            agent.shot_time = -1
            agent.push(flip(agent.me.local(car_to_ball)))
        elif agent.time - self.start_time > 3:
            agent.pop()
            agent.shooting = False
            agent.shot_weight = -1
            agent.shot_time = -1
