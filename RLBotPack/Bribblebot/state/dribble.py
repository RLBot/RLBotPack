from rlbot.agents.base_agent import BaseAgent
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.orientation import Orientation
from util.vec import Vec3
import util.const

from state.state import State
from state.yeet import Yeet
from state.frontflip import Frontflip
import math

from rlutilities.linear_algebra import vec3, axis_to_rotation, dot, norm, normalize
from rlutilities.mechanics import Drive as RLUDrive


normalSpeed = 1409
boostSpeed = 2299

###################################################################################
#                                                                                 #
# WARNING!!                                                                       #
#                                                                                 #
# THIS BOT WAS JUST MENT TO BE A PID BALL BALANCING BOT TEST.                     #
# IT WAS NEVER MENT TO BECOME ANYTHING WHATSOEVER OR PARTICIPATE IN COMPETITIONS. #
# THIS CODE IS THEREFORE EXTREMELY MESSY AND I DONT INTEND ON MAINTAINING IT.     #
#                                                                                 #
# SERIOUSLY, THE AMOUNT OF TECHNICAL DEBT IS ASTONISHING FOR SUCH A SMALL FILE.   #
#                                                                                 #
# IF YOU INTEND ON PLAYING WITH THIS CODE, GOOD LUCK.                             #
#                                                                                 #
###################################################################################



# TODO for competitions:
# TODO get boost when ball is high in the air
# TODO better flick
# TODO no flick when OT
# TODO fix flick when not on blue team


class Dribble(State):
    def __init__(self, agent: BaseAgent):
        super().__init__(agent)
        self.balanceTime = 0
        self.carToTargetIntegral = Vec3()
        self.steerBiasLimit = 0.5
        self.lastVelocities = [vec3(0, 0, 0)] * 32


    def tick(self, packet: GameTickPacket) -> bool:
        #self.agent.renderer.begin_rendering()

        kickoff = packet.game_info.is_round_active and packet.game_info.is_kickoff_pause

        carAccelerations = []
        for i in range(packet.num_cars):
            car = packet.game_cars[i]
            velocity = vec3(car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z)
            carAccelerations.append((velocity - self.lastVelocities[i]) / self.agent.ticksThisPacket * 120)
            self.lastVelocities[i] = velocity


        # car info
        myCar = packet.game_cars[self.agent.index]
        carLocation = Vec3(myCar.physics.location)
        carVelocity = Vec3(myCar.physics.velocity)
        carSpeed = carVelocity.length()

        # ball info
        realBallLocation = ballLocation = Vec3(packet.game_ball.physics.location)
        ballVelocity = Vec3(packet.game_ball.physics.velocity)
        if ballLocation.z < 100:
            self.balanceTime = 0
            #return False
        action_display = f"Air time: {self.balanceTime}" 
        self.balanceTime += 1

        # unstuck goal hack
        if abs(carLocation.y) > 5100:
            ballLocation.x = 0

        # target ball info
        #targetBallLocation, targetBallVelocity, targetAngle = getTargetBall(self.agent, packet, carLocation)
        
        teamDirection = 1 if packet.game_cars[self.agent.index].team == 0 else -1
        sidewaysDiff = abs(carLocation.x)-893+100
        isInCorner = sidewaysDiff > 0
        if isInCorner:
            sidewaysDiff = max(0, sidewaysDiff + 0.4*(carLocation.y * teamDirection - (5120-100)))
            inTriangleAmount = max(0, min(1, sidewaysDiff / 4500))
            scale = 0.55
        else:
            scale = 2
            inTriangleAmount = 0
        targetBallLocation = Vec3(0, (5120+100 - sidewaysDiff * scale) * teamDirection, 0)




        ## if teammate is closer to the ball, go to defend position.
        ballToCarAbsoluteLocation = (ballLocation - carLocation).flat()
        ballToCarDistance = ballToCarAbsoluteLocation.length()
        futurePositionScoreVector = ballLocation + 1 * ballVelocity - carLocation
        positionScore = Vec3(futurePositionScoreVector.x, futurePositionScoreVector.y * (1 if futurePositionScoreVector.y * (2*self.agent.team-1) < 0 else 3), 0).length()\
                      + Vec3(ballToCarAbsoluteLocation.x, ballToCarAbsoluteLocation.y * (1 if ballToCarAbsoluteLocation.y * (2*self.agent.team-1) < 0 else 3), 0).length()

        beAnnoying = False
        for carIndex in range(packet.num_cars):
            car = packet.game_cars[carIndex]
            if car.team == self.agent.team and carIndex != self.agent.index and not car.is_demolished:
                OtherCarToBall = ballLocation - Vec3(car.physics.location)
                OtherFutureCarToBall = ballLocation + 1 * ballVelocity - Vec3(car.physics.location)
                otherPositionScore = Vec3(OtherCarToBall.x      , OtherCarToBall.y       * (1 if OtherCarToBall.y       * (2*self.agent.team-1) < 0 else 3), 0).length()\
                                   + Vec3(OtherFutureCarToBall.x, OtherFutureCarToBall.y * (1 if OtherFutureCarToBall.y * (2*self.agent.team-1) < 0 else 3), 0).length()

                # print(f"[{self.agent.index} {round(positionScore)}] {carIndex}: {round(otherPositionScore)}!")
                if otherPositionScore + math.copysign(5, carIndex - self.agent.index) < positionScore:

                    # print(f"{self.agent.index} other one is closer!")

                    teamClosestDistance = math.inf
                    enemyClosestDistance = math.inf
                    for carIndex in range(packet.num_cars):
                        car = packet.game_cars[carIndex]
                        distance = (ballLocation - Vec3(car.physics.location)).flat().length()
                        if car.team == self.agent.team:
                            teamClosestDistance = min(teamClosestDistance, distance)
                        else:
                            enemyClosestDistance = min(enemyClosestDistance, distance)
                    teamHasBallControl = teamClosestDistance - 500 < enemyClosestDistance


                    targetScore = math.inf
                    target = None
                    for carIndex in range(packet.num_cars):
                        car = packet.game_cars[carIndex]
                        # print(f"[{self.agent.index} {self.agent.team}] {carIndex} {car.team}")
                        if car.team != self.agent.team:
                            score = (ballLocation - Vec3(car.physics.location)).flat().length() + teamHasBallControl * (Vec3(0, 5120 * (2*car.team-1), 0) - Vec3(car.physics.location)).flat().length()
                            # print(f"[{self.agent.index}] considering car {carIndex}")
                            if score < targetScore:
                                targetScore = score
                                target = car

                    if target != None:

                        beAnnoying = True

                        huntLocation = Vec3(target.physics.location)
                        for _ in range(20):
                            time = min(.6, 900 / max(1, Vec3(target.physics.velocity).length()), (carLocation - huntLocation).length() / max(carSpeed, 1))
                            huntLocation = Vec3(target.physics.location) + time * Vec3(target.physics.velocity)

                        ballLocation = huntLocation
                        ballVelocity = Vec3(0, 0, 0)#Vec3(target.physics.velocity)
                        ballToCarAbsoluteLocation = (ballLocation - carLocation).flat()
                        ballToCarDistance = ballToCarAbsoluteLocation.length()


                    break







        ## if convenient, change ball location to nearby boost pad.
        fieldInfo = self.agent.get_field_info()
        carFutureLocation = carLocation + 0.2 * carVelocity
        ballToFutureCarAbsoluteLocation = (ballLocation - carFutureLocation).flat()
        ballToFutureCarDistance = ballToFutureCarAbsoluteLocation.length()
        goingForBoost = False
        if ballToCarDistance > 250 and myCar.boost < 88:
            convenientBoostPads = []
            costs = []
            for i in range(fieldInfo.num_boosts):
                if not packet.game_boosts[i].is_active:
                    continue
                boostPad = fieldInfo.boost_pads[i]
                boostLocation = Vec3(boostPad.location)

                maxOffset = (208 if boostPad.is_full_boost else 144) - 20
                orth = (boostLocation - carLocation).orthogonalize(ballToCarAbsoluteLocation)
                boostLocation -= orth.normalized() * min(orth.length(), maxOffset)
                
                carToBoostLength = (boostLocation - carFutureLocation).length()
                detourLength = (ballLocation - boostLocation).length() + carToBoostLength
                cost = (detourLength - ballToFutureCarDistance) / (1450 if boostPad.is_full_boost else 250)
                costs.append(cost)
                if cost < ((100 - myCar.boost) / 100) ** 1.5:
                    convenientBoostPads.append((i, carToBoostLength * cost, boostLocation))
                    #self.agent.renderer.draw_line_3d(boostLocation, boostLocation + Vec3(0, 0, 100), self.agent.renderer.pink())
                
            #print(round(min(costs), 1))

            if len(convenientBoostPads) > 0:
                convenientBoostPads.sort(key=lambda b: b[1], reverse=False)
                boostPad = fieldInfo.boost_pads[convenientBoostPads[0][0]]
                boostLocation = convenientBoostPads[0][2]
                #self.agent.renderer.draw_line_3d(boostLocation, boostLocation + Vec3(0, 0, 400), self.agent.renderer.pink())

                ballLocation = boostLocation
                ballVelocity = Vec3(0, 0, 0)
                
                ballToCarAbsoluteLocation = (ballLocation - carLocation).flat()
                ballToCarDistance = ballToCarAbsoluteLocation.length()
                goingForBoost = True
                


        ## time to next bounce
        if not goingForBoost:
            pass






        ## calculate angles
        ballDirection = math.atan2(ballVelocity.y, -ballVelocity.x)
        carDirection = -myCar.physics.rotation.yaw
        carToBallAngle = math.atan2(ballToCarAbsoluteLocation.y, -ballToCarAbsoluteLocation.x) - carDirection
        if abs(carToBallAngle) > math.pi:
            if carToBallAngle > 0:
                carToBallAngle -= 2*math.pi
            else:
                carToBallAngle += 2*math.pi
        ballToTargetAbsoluteLocation = (ballLocation - targetBallLocation).flat()
        carToTargetAngle = math.atan2(ballToTargetAbsoluteLocation.y, -ballToTargetAbsoluteLocation.x) - carDirection
        if abs(carToTargetAngle) > math.pi:
            if carToTargetAngle > 0:
                carToTargetAngle -= 2*math.pi
            else:
                carToTargetAngle += 2*math.pi
        carToTargetAbsoluteLocation = (carLocation - targetBallLocation).flat()

        ## separate into steering and throttle components
        ballToCarLocation = ballToCarAbsoluteLocation.rotate_2D(carDirection)
        ballToTargetLocation = ballToTargetAbsoluteLocation.rotate_2D(carDirection)
        carToTargetLocation = carToTargetAbsoluteLocation.rotate_2D(carDirection)

        ballToCarVelocity = (ballVelocity - carVelocity).flat().rotate_2D(carDirection)
        #carToTargetVelocity = (carVelocity - targetBallVelocity).flat().rotate_2D(carDirection)

        maxSpeed = max(1410, min(2300, 1410 + (2300-1410)/33*myCar.boost))
        carToMaxSpeed = carVelocity.flat().length() - maxSpeed
        desiredSpeed = 1200

        if ballToTargetLocation.y < 500:
            self.carToTargetIntegral += ballToTargetLocation
        else:
            self.carToTargetIntegral = Vec3()


        
        canYeet = myCar.has_wheel_contact \
                and (not goingForBoost) \
                and ballToCarLocation.length() < 275 \
                and ballLocation.z > 100 \
                and ballLocation.z < 275 \
                and packet.game_info.seconds_elapsed - packet.game_ball.latest_touch.time_seconds < 0.1
        teamDirection = 1 if packet.game_cars[self.agent.index].team == 0 else -1
        inCornerDegree = math.atan((max(abs(carLocation.x), 893)-893) / max(5120 - carLocation.y*teamDirection, 1))
        shouldYeet = ((ballLocation + 1 * ballVelocity).flat() * teamDirection - Vec3(0, 5120+100, 0)).length() < 1500 \
                and inCornerDegree < math.pi * 2 / 6 \
                and 4200 - abs(ballLocation.y) < 0.7 * abs(ballVelocity.y)

        #print(f"{canYeet}\t{shouldYeet}\t{round(4200 - abs(ballLocation.y))}\t{round(0.7 * abs(ballVelocity.y))}")
        #action_display = f"{round((ballLocation.flat() - Vec3(0, 5120+100 * teamDirection, 0)).length())}"
        carlocs = []
        if canYeet and shouldYeet:

            inComingCar = False
            for i in range(packet.num_cars):
                if i == self.agent.index:
                    continue
                car = packet.game_cars[i]
                if car.team == myCar.team or car.is_demolished:
                    continue
                #print(round(0.1 + norm(carAccelerations[i]) / RLUDrive.throttle_accel(Vec3(car.physics.velocity).length()), 2))
                for throttle in (0, min(1, 0.1 + norm(carAccelerations[i]) / RLUDrive.throttle_accel(Vec3(car.physics.velocity).length()))):
                    carBoost = car.boost
                    
                    attackerCarLocation = Vec3(car.physics.location)
                    # divide by 120, to go from per second to per frame
                    STEPSIZE = 120
                    gravity = packet.game_info.world_gravity_z / STEPSIZE**2
                    attackerCarVelocity = vec3(car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z) / STEPSIZE
                    attackerCarAngular  = axis_to_rotation(vec3(car.physics.angular_velocity.x, car.physics.angular_velocity.y, car.physics.angular_velocity.z) / STEPSIZE)
                    
                    ballV = ballVelocity / STEPSIZE

                    for j in range(round(STEPSIZE * 0.7)): # simulate 40 ticks forwards
                        attackerCarLocation += Vec3(attackerCarVelocity[0], attackerCarVelocity[1], attackerCarVelocity[2])
                        if car.has_wheel_contact:
                            attackerCarVelocity = dot(attackerCarAngular, attackerCarVelocity)
                        attackerCarVelocity += vec3(0, 0, gravity)
                        if throttle == 0:
                            attackerCarVelocity -= vec3(math.copysign(min(525 / STEPSIZE, abs(attackerCarVelocity[0])), attackerCarVelocity[0]), 0, 0)
                        else:
                            acceleration = (991.667*(carBoost>0) + RLUDrive.throttle_accel(norm(attackerCarVelocity)))
                            attackerCarVelocity += normalize(attackerCarVelocity) * acceleration / STEPSIZE
                        if attackerCarLocation.z < ballLocation.z:
                            attackerCarLocation.z = ballLocation.z
                        carlocs.append(attackerCarLocation)
                        if (attackerCarLocation - ballLocation + j * ballV).flat().length() < 750: # longest car has a diagonal of 157uu
                            inComingCar = True
                            break
                        #print(f"{j}\t{ (attackerCarLocation - ballLocation + j * ballV).flat().length()}")
                    if inComingCar:
                        break

                    carBoost -= 1 / 3 / STEPSIZE
                    


                if inComingCar:

                    self.agent.stateMachine.changeStateMidTick(Yeet)
                    return inComingCar



        if kickoff and (carLocation - realBallLocation).length() < 800 and myCar.has_wheel_contact:
            self.agent.stateMachine.changeStateMidTick(Frontflip)
            return True


        ## STEERING
        steer = 0
        steerBias = 0
        # ball to car proportional
        #print(f"{round(min(15, max(-15, 0.02 * ballToCarLocation.y)), 2)}\t{round(0.003 * ballToCarVelocity.y, 2)}")
        steer += min(15, max(-15, 0.02 * ballToCarLocation.y))
        if not goingForBoost:
            # ball to car derivative
            steer += 0.005 * ballToCarVelocity.y
            #print(f"pos: {round(min(15, max(-15, 0.02 * ballToCarLocation.y)), 2)}\tvel: {round(0.009 * ballToCarVelocity.y,2)}")
            # ball to target proportional
            targetSteer = ballToTargetLocation.y
            #action_display = f"{round(carToTargetLocation.x)}"
            if carToTargetLocation.x > 300:
                targetSteer = math.copysign(100000, targetSteer)
            steerBias += 0.005 * targetSteer
            # ball to target derivative
            #steerBias += 0.002 * carToTargetVelocity.y
            # ball to target integral
            #steerBias += 0.000001 * self.carToTargetIntegral.y
            #print(f"{round(steerBias, 1)}\t{round(0.008 * carToTargetVelocity.y, 1)}")
            
            applySpeedLimit = True
            if kickoff or beAnnoying:
                self.steerBiasLimit = 0
            if abs(carLocation.x) < 930 and abs(carLocation.y) > 5120-550 and ballLocation.z > 500:
                self.steerBiasLimit = 2.5
                applySpeedLimit = False
            if ballLocation.z > 160 or ballToCarLocation.length() > 800:
                self.steerBiasLimit = max(0.5, self.steerBiasLimit - 0.1)
            elif ballLocation.z < 100:
                self.steerBiasLimit = max(0.5, self.steerBiasLimit - 0.1)
            else:
                self.steerBiasLimit = min(2.5, 1 + 1 * max(0, carSpeed - 600) / 1800, self.steerBiasLimit + 0.065)

            if applySpeedLimit and ballToCarLocation.length() < 180:
                self.steerBiasLimit = min(self.steerBiasLimit, 1.3 + (1400 - carVelocity.flat().length()) / 800)

            steer += min(self.steerBiasLimit, max(-self.steerBiasLimit, steerBias))
            action_display = f"SBL {round(self.steerBiasLimit, 1)} SB: {round(min(self.steerBiasLimit, max(-self.steerBiasLimit, steerBias)), 1)}" 
            #action_display = f"{round(ballToTargetLocation.x)}"

        ## THROTTLE
        throttle = 0
        # ball to car proportional
        throttle += 0.07 * ballToCarLocation.x
        # ball to car derivative
        throttle += 0.015 * ballToCarVelocity.x
        

        #print(ballVelocity.length())
        if (ballToCarLocation.length() < 300 and not (abs(ballToCarLocation.y) > 100 and ballVelocity.length() < 500)) and not beAnnoying: # if the ball is too far from the car, use speed to drive car to ball


            throttleBias = 0
            ## NORMAL TARGET BIAS
            #ball to target proportional
            #throttleBias += 0.004 * ballToTargetLocation.x
            # ball to target derivative
            if ballLocation.z > 100:
                #action_display = f"triangle: {round((1 - inTriangleAmount), 1)}\ttargetangle: {round(0.8*math.cos(carToTargetAngle/2), 1)}" 
                carToDesiredSpeed = carVelocity.flat().length() - desiredSpeed * max(0.2, (1 - inTriangleAmount))
                throttleBias += 0.005 * carToDesiredSpeed
            # ball to target integral
            #throttleBias += 0.00001 * self.carToTargetIntegral.x

            ## STEERING HELP BIAS WHEN FAR AWAY
            #targetSteeringSpeed = 400 + 3000 * math.pow(math.cos(carToTargetAngle/2), 16)
            #throttleSteeringBias = max(-1, 3 * (carSpeed - targetSteeringSpeed) / 1400)

        
            # alpha = max(0, min(1, (ballToTargetLocation.length() - 1000) / 3000))

            # throttleBias = throttleSteeringBias * alpha + throttleBias * (1 - alpha)

            throttle += min(2, max(-0.9, throttleBias))
            #action_display = f"TB: {round(throttleBias, 1)}\tT: {round(throttle, 1)}" 
        else:
            throttle = 1-0.8*math.cos(carToBallAngle)

        #print(action_display)

        if goingForBoost:
            throttle = max(throttle, 1)

        ## set controller state
        self.controller.steer = min(1, max(-1, steer))
        self.controller.throttle = min(1, max(-1, throttle))
        if myCar.has_wheel_contact and throttle > 1.7 and carLocation.z < 100 and realBallLocation.z < 500:
            self.controller.boost = carSpeed < 2300 - 991.667/120 * (1 if self.controller.boost else 10)
        else:
            self.controller.boost = False


            ## test if forward dodge is needed
            if abs(steer) < 0.5 and not kickoff and carSpeed > 1400 and carSpeed < 2200 and (myCar.boost == 0 or carSpeed > 2300-20-500):
                
                try:
                    angleCoeff = carVelocity.normalized().dot(ballVelocity.normalized())
                except:
                    angleCoeff = -1

                if angleCoeff > 0.95:

                    dist = (realBallLocation - carLocation).length()
                    vel = (carSpeed + 500 - ballVelocity.length())
                    time = dist / vel
                    ballAfterLocation = realBallLocation + time * ballVelocity
                    isStillInMap = abs(ballAfterLocation.x) < 4096 + 500 and abs(ballAfterLocation.y) < 5120 + 500
                    if time > 1.5:
                        self.agent.stateMachine.changeStateMidTick(Frontflip)
                        return True




        # print(self.ballToTargetIntegral)
        # action_display = f"steer: {round(ballToTargetLocation.y)}"
        # action_display = f"distance: {round(ballToTargetLocation.x)}" 



        # # Find the direction of our car using the Orientation class
        #car_orientation = Orientation(myCar.physics.rotation).forward
        #car_direction = car_orientation.forward


        # steer_correction_radians = find_correction(car_direction, ballToCarLocation)

        # turnProportional = max(-1, min(1, steer_correction_radians * 4))
        # #action_display = f"turn {round(turn, 2)}" 
        # self.controller.steer = turnProportional



        # throttleProportional = 10
        # speed = Vec3.length(myCar.physics.velocity)
        # targetSpeed = min(boostSpeed, Vec3.dist(ballLocation, carLocation) * 5 * math.cos(steer_correction_radians))

        # self.controller.throttle = max(-1, min(1, (targetSpeed - speed) * 1000))
        # self.controller.steer = turnProportional
        # self.controller.boost = speed < targetSpeed if self.controller.boost or (abs(turnProportional) < 1 and targetSpeed > normalSpeed) else (abs(turnProportional) < 1 and speed < targetSpeed - 400)



        
        # targetBallLocation.z = 150
        #draw_debug(self.agent, myCar, packet.game_ball, action_display, targetBallLocation, carlocs)

        return True







# def getTargetBall(agent, packet: GameTickPacket, carLocation: Vec3) -> (Vec3, Vec3, float):
#     # RADIUS = 1200
#     # SPEED = 0.8
#     # VELOCITY = SPEED
#     # try:
#     #     angle = SPEED * packet.game_info.seconds_elapsed 
#     #     return  Vec3(RADIUS * math.sin(angle),
#     #                  RADIUS * math.cos(angle),
#     #                  0), \
#     #             Vec3(RADIUS * math.cos(angle),
#     #                  RADIUS * -math.sin(angle),
#     #                  0) * VELOCITY, \
#     #             angle
#     # except Exception:
#     #     return Vec3()

#     teamDirection = 1 if packet.game_cars[agent.index].team == 0 else -1
#     sidewaysDiff = abs(carLocation.x)-893+100
#     if sidewaysDiff > 0:
#         sidewaysDiff = max(0, sidewaysDiff + 0.4*(carLocation.y * teamDirection - (5120-100)))
#         scale = 0.6
#         print("hi")
#     else:
#         scale = 2
#         print("ho")
#     print("sup")
#     return Vec3(0, (5120+100 - sidewaysDiff * scale) * teamDirection, 0), Vec3(0, 0 * teamDirection, 0), 0











def draw_debug(agent, car, ball, action_display, targetBallLocation, carlocs):
    renderer = agent.renderer
    ballPrediction = agent.get_ball_prediction_struct()
    
    predictionLine = []
    if ballPrediction is not None:
        for i in range(0, ballPrediction.num_slices):
            predictionLine.append(Vec3(ballPrediction.slices[i].physics.location))

    red = agent.renderer.create_color(255, 255, 30, 30)
    if len(carlocs) > 1:
        agent.renderer.draw_polyline_3d(carlocs, red)
    # draw a line from the car to the ball
    renderer.draw_line_3d(car.physics.location, ball.physics.location, renderer.white())
    renderer.draw_line_3d(targetBallLocation, ball.physics.location, renderer.white())
    # print the action that the bot is taking
    renderer.draw_string_3d(car.physics.location, 2, 2, action_display, renderer.white())

    
    draw_point(renderer, targetBallLocation, renderer.yellow())
    renderer.end_rendering()



def draw_point(renderer, location, color):
    for axis in (Vec3(0, 0, 1), Vec3(0, 1, 0), Vec3(1, 0, 0)):
        renderer.draw_line_3d(location + 100 * axis, location - 100 * axis, color)
