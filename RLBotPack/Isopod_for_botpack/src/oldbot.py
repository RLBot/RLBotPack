from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3
import math

def clamp(num, min_value, max_value):
    return max(min(num, max_value), min_value)

def degtotarget(source, sourcedegrees, team, target):
    degreesS = sourcedegrees
    degreesT = (math.degrees(math.atan2((target.y - source.y)*team,target.x - source.x)))
    Hdegtotarget = degreesS + degreesT
    if Hdegtotarget > 180:
        Hdegtotarget = Hdegtotarget - 360
    if Hdegtotarget < -180:
        Hdegtotarget = Hdegtotarget + 360
    return Hdegtotarget

class MyBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()
        self.jumpcount = 0
        self.laststate = 0

    def initialize_agent(self):
        # Set up information about the boost pads now that the game is active and the info is available
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        """
        This function will be called by the framework many times per second. This is where you can
        see the motion of the ball, etc. and return controls to drive your car.
        """

        # Keep our boost pad info updated with which pads are currently active
        self.boost_pad_tracker.update_boost_status(packet)

        # This is good to keep at the beginning of get_output. It will allow you to continue
        # any sequences that you may have started during a previous call to get_output.
        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls



        ##################################################
        ########## Top
        ##################################################

        ##################################################
        ########## Define Variables
        ##################################################

        # Gather some information about our car and the ball
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)
        ball_velocity = Vec3(packet.game_ball.physics.velocity)

        # By default we will chase the ball, but target_location can be changed later
        target_location = ball_location
        choosetarget = "BallPredict"

        # 1 for Orange, -1 for Blue
        myteam = ((packet.game_cars[self.index].team) - 0.5) * 2

        mygoal = Vec3(0, (5200 * myteam), 0)

        # To check horizontal degrees to our own goal relative to where we are facing, use Hdegtogoal
        degreesE = (math.degrees(my_car.physics.rotation.yaw) * -myteam)
        degreesF = (
            math.degrees(math.atan2((-5150 - my_car.physics.location.y) * myteam, 0 - my_car.physics.location.x)))
        Hdegtogoal = degreesE + degreesF
        if Hdegtogoal > 180:
            Hdegtogoal = Hdegtogoal - 360
        if Hdegtogoal < -180:
            Hdegtogoal = Hdegtogoal + 360

        # To check horizontal degrees to the enemy goal relative to where we are facing, use Hdegtoenemygoal
        degreesG = (math.degrees(my_car.physics.rotation.yaw) * -myteam)
        degreesH = (
            math.degrees(math.atan2((5150 - my_car.physics.location.y) * myteam, 0 - my_car.physics.location.x)))
        Hdegtoenemygoal = degreesG + degreesH
        if Hdegtoenemygoal > 180:
            Hdegtoenemygoal = Hdegtoenemygoal - 360
        if Hdegtoenemygoal < -180:
            Hdegtoenemygoal = Hdegtoenemygoal + 360

        distheight = (target_location.z) - (my_car.physics.location.z + 75)
        flatdist = math.sqrt(((my_car.physics.location.x - target_location.x)**2) + ((my_car.physics.location.y - target_location.y)**2))

        #This is inaccurate, but its basically close enough and idk how to fix it lol
        Vdegtotarget = (math.degrees(math.atan2(distheight,flatdist)))

        pointup = my_car.physics.rotation.pitch > 0.25

        if packet.game_ball.latest_touch.player_index == self.index and packet.game_info.seconds_elapsed - packet.game_ball.latest_touch.time_seconds < 0.8:
            wejusthit = 1
        else:
            wejusthit = 0


        ##################################################
        ########## Ball Prediction Processing
        ##################################################


        # ball, let's try to lead it a little bit
        ball_prediction = self.get_ball_prediction_struct()  # This can predict bounces, etc
        ball_in_future = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + ((car_location.dist(ball_location)-100) / 1400) + ((ball_location.z - 95) / 2100))

        # ball_in_future might be None if we don't have an adequate ball prediction right now, like during
        # replays, so check it to avoid errors.
        if ball_in_future is not None:
            target_location = Vec3(ball_in_future.physics.location)
            choosetarget = "BallPredict"

        if ball_in_future is not None:
            ballpredict = Vec3(ball_in_future.physics.location)
        else:
            ballpredict = ball_location


        ##################################################
        ########## Check if ball is going in
        ##################################################


        ball_going_in = False
        for x in range(40):
            ball_towards_goal = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + (x / 8))
            if ball_towards_goal is not None:
                # print(type(ball_towards_goal))
                if myteam == 1:
                    if ball_towards_goal.physics.location.y > 5120:
                        ball_going_in = True
                if myteam == -1:
                    if ball_towards_goal.physics.location.y < -5120:
                        ball_going_in = True



        ##################################################
        ########## Calculate allies and enemies and see whos closest to ball
        ##################################################

        allylist = []
        enemylist = []

        for x in range(packet.num_cars):
            if packet.game_cars[x].team == packet.game_cars[self.index].team:
                allylist.append(x)
            else:
                enemylist.append(x)

        closestcar = 0
        closestdist = Vec3(packet.game_cars[closestcar].physics.location).dist(ball_location)
        for x in range(packet.num_cars):
            if (Vec3(packet.game_cars[x].physics.location).dist(ball_location)) < (Vec3(packet.game_cars[closestcar].physics.location).dist(ball_location)):
                closestcar = x
                closestdist = (Vec3(packet.game_cars[x].physics.location).dist(ball_location))

        if packet.game_cars[closestcar].team != packet.game_cars[self.index].team:
            closestteam = 0
        else:
            closestteam = 1

        closestally = allylist[0]

        allydist = Vec3(packet.game_cars[allylist[0]].physics.location).dist(ball_location)

        for x in allylist:
            if (Vec3(packet.game_cars[x].physics.location).dist(ball_location)) < (Vec3(packet.game_cars[closestally].physics.location).dist(ball_location)):
                closestally = x
                allydist = (Vec3(packet.game_cars[x].physics.location).dist(ball_location))

        closestenemy = enemylist[0]

        enemydist = Vec3(packet.game_cars[enemylist[0]].physics.location).dist(ball_location)

        for x in enemylist:
            if (Vec3(packet.game_cars[x].physics.location).dist(ball_location)) < (Vec3(packet.game_cars[closestenemy].physics.location).dist(ball_location)):
                closestenemy = x
                enemydist = (Vec3(packet.game_cars[x].physics.location).dist(ball_location))


        # Calculate who the closest enemy is to us, and how far

        if len(enemylist) > 0:
            closestenemytome = enemylist[0]
            for x in enemylist:
                if (Vec3(packet.game_cars[x].physics.location).dist(my_car.physics.location)) <= (Vec3(packet.game_cars[closestenemytome].physics.location).dist(my_car.physics.location)):
                    closestenemytome = x
                    cardisttome = (Vec3(packet.game_cars[x].physics.location).dist(my_car.physics.location))


        # Calculate which allies are onside/offside

        numalliesonside = 0
        for x in allylist:
            if packet.game_cars[x].physics.location.y + myteam * -5500 < ball_location.y + myteam * -5500 and x != self.index:
                numalliesonside += 1


        ##################################################
        ########## More Variables
        ##################################################

        if ball_in_future is not None:
        #Deg to ball
            degtoball = degtotarget(my_car.physics.location, (math.degrees(my_car.physics.rotation.yaw) * -myteam), myteam, Vec3(ball_in_future.physics.location))

        #Deg to own goal
            degtoowngoal = degtotarget(my_car.physics.location, (math.degrees(my_car.physics.rotation.yaw) * -myteam), myteam, Vec3(0, (5150 * myteam), 0))

        if ball_in_future is not None:
            lineupA = Vec3(ball_in_future.physics.location) - Vec3(0, (-5250 * myteam), 0)
            lineupB = lineupA * 1.15
            lineupB.x *= 1.1
            lineupC = lineupB + Vec3(0, -5300 * myteam, 0)
            lineupC.z = 20
            lineupD = lineupA * 1.3
            lineupD.x *= 1.2
            lineupE = lineupD + Vec3(0, -5300 * myteam, 0)
            lineupE.z = 20
            lineupclose = car_location.dist(lineupC) < 900 or car_location.dist(lineupE) < 900

        degreesC = (math.degrees(my_car.physics.rotation.yaw) * -myteam)
        degreesB = (math.degrees(math.atan2((target_location.y - my_car.physics.location.y) * myteam, target_location.x - my_car.physics.location.x)))
        Hdegtotarget = degreesC + degreesB
        if Hdegtotarget > 180:
            Hdegtotarget = Hdegtotarget - 360
        if Hdegtotarget < -180:
            Hdegtotarget = Hdegtotarget + 360

        degreesR = (math.degrees(my_car.physics.rotation.yaw) * -myteam)
        degreesS = (math.degrees(math.atan2((ball_location.y - my_car.physics.location.y) * myteam,
                                            ball_location.x - my_car.physics.location.x)))
        Hdegtoball = degreesR + degreesS
        if Hdegtoball > 180:
            Hdegtoball = Hdegtoball - 360
        if Hdegtoball < -180:
            Hdegtoball = Hdegtoball + 360

        # if abs(car_location.y + myteam*(-5500)) < abs(ball_location.y + myteam*(-5500)):
        # offside = False
        if abs(car_location.y + myteam * (-5500)) > abs(ball_location.y + myteam * (-5500)) or ballpredict.z > 2100:
            offside = True
        else:
            offside = False


        ##################################################
        ########## Aerial Control Variables
        ##################################################

        RotVelX = my_car.physics.angular_velocity.x
        RotVelY = my_car.physics.angular_velocity.y
        RotVelZ = my_car.physics.angular_velocity.z


        ##################################################
        ########## Define and set up Controls
        ##################################################

        controls = SimpleControllerState()
        controls.handbrake = False
        controls.jump = False
        controls.boost = False


        ##################################################
        ########## Play Goalie
        ##################################################

        if len(allylist) > 1 and closestteam == 1 and ball_location.y * myteam > 900 and closestally != self.index:
            choosetarget = "Goalie"


        ##################################################
        ########## Play Center
        ##################################################

        if numalliesonside > 1 and closestteam == 1 and ball_location.y * myteam < 0 and closestally != self.index:
            choosetarget = "Center"

        if numalliesonside < 1 and ball_location.y * -myteam > 4950 and abs(ball_location.x) > 850:
            choosetarget = "Center"

        # if ball_location.z > 400 and car_location.dist(ballpredict) > 800:
        #     choosetarget = "Center"


        ##################################################
        ########## Return to defense if on the wrong side of the ball or ball very high
        ##################################################

        if offside:
            choosetarget = "OwnGoal"


        ##################################################
        ########## Go for bump
        ##################################################

        if len(enemylist) > 0:
            degtocar = degtotarget(my_car.physics.location, (math.degrees(my_car.physics.rotation.yaw) * -myteam), myteam, Vec3(packet.game_cars[closestenemytome].physics.location))
        else:
            degtocar = 0

        if len(enemylist) > 0:
            if offside == True and cardisttome < 1100 and my_car.boost > 45 and car_velocity.length() > 1000 and abs(degtocar) < 25:
                choosetarget = "Bump"

        ##################################################
        ########## Line up for a shot
        ##################################################

        if ball_in_future is not None and offside == False and ball_location.z < 1000 and abs(target_location.x) < 1800:
            if car_location.dist(ball_location) > 650 and lineupclose == False and car_location.dist(ball_location) < 3000 and (ball_location.y * myteam) < -800:
                choosetarget = "Lineup"


        ##################################################
        ########## Shot is now lined up
        ##################################################

        if ball_in_future is not None and abs(Hdegtotarget - Hdegtogoal) < 13 and abs(Hdegtotarget) < 10 and offside == False and car_location.dist(ball_location) < 2500 and ball_location.y * -myteam > 100 and target_location.z < 900:
            choosetarget = "BallPredict"


        if ball_in_future is not None and Vec3(0, myteam * -4900, 0).dist(ball_location) < 600 and offside == False:
            choosetarget = "BallPredict"


        ##################################################
        ########## Aerialing
        ##################################################

        # if 200 < ball_location.z < 2000 and car_velocity.length() > 500 and ball_velocity.length() < 2400 and flatdist > 50 and abs(Hdegtotarget) < 2 and car_location.dist(ball_location) < 4000 and my_car.boost > 20:
        #     choosetarget = "JumpShot"
        #
        # if 170 < ball_location.z < 1000 and car_velocity.length() > 500 and ball_velocity.length() < 2400 and flatdist > 50 and abs(Hdegtotarget) < 2 and car_location.dist(ball_location) < 3000:
        #     choosetarget = "JumpShot"
        #
        # if offside == False and car_location.dist(ball_location) < 4000 and car_velocity.length() > 500 and my_car.physics.location.z > 70 and my_car.physics.location.z + 140 < ball_location.z:
        #     choosetarget = "Aerial"

        if 10 < Vdegtotarget < 35 and flatdist > 75 and abs(Hdegtotarget) < 2 and car_location.dist(ball_location) < 4000 and car_velocity.length() > 300:
            choosetarget = "JumpShot"

        if offside == False and car_location.dist(ball_location) < 4000 and my_car.physics.location.z > 110 and my_car.physics.location.z - 100 < target_location.z:
            choosetarget = "Aerial"


        ##################################################
        ########## Clear from our corner
        ##################################################

        if ball_location.y * myteam > 4900 and abs(ball_location.x) > 1000:
            choosetarget = "BallPredict"


        ##################################################
        ########## Emergency Save
        ##################################################

        if ball_in_future is not None and ball_going_in == True and abs(degtoball - degtoowngoal) > 14 and target_location.z < 100:
            choosetarget = "EmergencySave"

        if ball_in_future is not None and enemydist < 500 and offside and abs(degtoball - degtoowngoal) > 20:
            choosetarget = "EmergencySave"


        ##################################################
        ########## Go for kickoff
        ##################################################

        if ball_location.x == 0 and ball_location.y == 0 and car_velocity.length() > 400 and closestally == self.index:
            choosetarget = "Kickoff"

        ##################################################
        ########## Decision Processing
        ##################################################

        if choosetarget == "Goalie":
            target_location = Vec3(0, myteam * 4800, 0)

        if choosetarget == "Center":
            if ball_in_future is not None:
                target_location = Vec3(ball_in_future.physics.location)
                target_location.y += 2100 * myteam
                target_location.x *= 0.85
                target_location.z = 3

        if choosetarget == "Bump":
            if len(enemylist) > 0:
                target_location = Vec3(packet.game_cars[closestenemytome].physics.location)
                controls.boost = True

        if choosetarget == "OwnGoal":
            if my_car.physics.location.x > 0:
                target_location = Vec3(1300, (4700 * myteam), 0)
            else:
                target_location = Vec3(-1300, (4700 * myteam), 0)
            if car_location.dist(target_location) > 1800 and my_car.boost > 30 and abs(Hdegtotarget) < 10:
                controls.boost = True
            # if abs(Hdegtogoal - Hdegtotarget) < 13:
            #     target_location.x *= 2

        if choosetarget == "Lineup":
            target_location = lineupC

        if choosetarget == "BallPredict":
            if ball_in_future is not None:
                target_location = Vec3(ball_in_future.physics.location)
                if abs(Hdegtotarget) < 10 and Vec3(0, myteam * -4900, 0).dist(ball_location) < 600 and offside == False:
                    controls.boost = True
                if abs(Hdegtotarget - Hdegtogoal) < 13 and abs(Hdegtotarget) < 10 and offside == False and car_location.dist(ball_location) < 2500 and ball_location.y * -myteam > 100:
                    controls.boost = True
                # if 330 < car_location.dist(ball_location) < 430 or car_location.dist(ball_location) < 230:
                #     if abs(Hdegtotarget) < 6 and car_velocity.length() > 700 and my_car.physics.location.z < 60 and target_location.z < 240:
                #         self.active_sequence = Sequence([
                #             ControlStep(duration=0.10, controls=SimpleControllerState(jump=True)),
                #             ControlStep(duration=0.04, controls=SimpleControllerState(jump=False)),
                #             ControlStep(duration=0.20, controls=SimpleControllerState(jump=True, steer=steer_toward_target(my_car, target_location), pitch=-1)),
                #             ControlStep(duration=0.60, controls=SimpleControllerState()),
                #         ])
            else:
                target_location = ball_location


        if choosetarget == "JumpShot":
            controls.jump = True

        if choosetarget == "Aerial":
            controls.boost = True
            # return self.aerial(packet, target_location, currenttime)

        if choosetarget == "EmergencySave":
            if ball_in_future is not None:
                target_location = Vec3(ball_in_future.physics.location)
            else:
                target_location = ball_location
            if abs(Hdegtotarget) < 15:
                controls.boost = True
            if abs(Hdegtotarget) > 120:
                target_location = Vec3(ball_location)

        if choosetarget == "Kickoff":
            controls.boost = True
            controls.steer = steer_toward_target(my_car, ball_location)
            if car_location.dist(ball_location) < 1000:
                self.active_sequence = Sequence([
                    ControlStep(duration=0.08, controls=SimpleControllerState(jump=True)),
                    ControlStep(duration=0.03, controls=SimpleControllerState(jump=False)),
                    ControlStep(duration=0.10, controls=SimpleControllerState(jump=True, pitch=-1)),
                    ControlStep(duration=0.50, controls=SimpleControllerState()),
                ])


        ##################################################
        ########## Ball targeting adjustment
        ##################################################

        if choosetarget == "BallPredict" and ball_in_future is not None:
            target_location.y -= -60 * myteam

        if choosetarget == "JumpShot" or "Aerial" and ball_in_future is not None:
            target_location.y -= -30 * myteam

        distanceadjustment = (1500 - clamp(car_location.dist(ballpredict), 0, 1500)) / 1400

        if choosetarget == "BallPredict" and ball_in_future is not None and ball_location.y * myteam < 2000:
            target_location.x = clamp((target_location.x*1.15), target_location.x - (50 * distanceadjustment), target_location.x + (50 * distanceadjustment))

        if choosetarget == "JumpShot" or "Aerial" and ball_in_future is not None and ball_location.y * myteam < 2000:
            target_location.x = clamp((target_location.x * 1.15), target_location.x - (25 * distanceadjustment), target_location.x + (25 * distanceadjustment))

        ##################################################
        ########## Rendering
        ##################################################

        if myteam == 1 and ball_in_future is not None:
            self.renderer.draw_line_3d(car_location, target_location, self.renderer.orange())
            self.renderer.draw_string_3d(car_location, 1, 1, f'{choosetarget}', self.renderer.white())
            self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.orange(), centered=True)
            self.renderer.draw_rect_3d(ballpredict, 8, 8, True, self.renderer.orange(), centered=True)
            self.renderer.draw_line_3d(ball_location, ballpredict, self.renderer.orange())

        if myteam == -1 and ball_in_future is not None:
            self.renderer.draw_line_3d(car_location, target_location, self.renderer.cyan())
            self.renderer.draw_string_3d(car_location, 1, 1, f'{choosetarget}', self.renderer.white())
            self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
            self.renderer.draw_rect_3d(ballpredict, 8, 8, True, self.renderer.cyan(), centered=True)
            self.renderer.draw_line_3d(ball_location, ballpredict, self.renderer.cyan())


        ##################################################
        ########## Basic Controls
        ##################################################

        controls.throttle = 1.0

        if Vdegtotarget > 40 and abs(Hdegtotarget) < 20 and choosetarget == "BallPredict":
            controls.throttle = 0.1
            controls.boost = False

        # if choosetarget == "BallPredict" and flatdist < 140 and 20 > abs(Hdegtoball) > 4 and car_velocity.length() > 1000:
        #     controls.throttle = -1

        controls.steer = steer_toward_target(my_car, target_location)

        # if choosetarget == "BallPredict" and ball_in_future is not None and ball_location.y * myteam < 0 and Hdegtotarget < 30 and car_location.dist(ball_location) < 300 and abs(Hdegtoenemygoal) < 24:
        #     controls.steer = clamp(controls.steer + (Hdegtoenemygoal / 10), -1, 1)

        # if choosetarget == "BallPredict" and car_location.dist(ball_location) < 300 and abs(Hdegtotarget) < 15:
        #     controls.steer = clamp(controls.steer-(Hdegtoenemygoal/450), -1, 1)

        controls.roll = clamp((my_car.physics.rotation.roll / -5),-1,1)

        controls.yaw = clamp(steer_toward_target(my_car, target_location) * 1.2, -1, 1)
        # controls.yaw = clamp((((Hdegtotarget * myteam) + (RotVelZ * -20)) / 25), -1, 1)

        #if controls.jump == True:
            #lastjumptime = packet.game_info.seconds_elapsed

        #if controls.jump == True and packet.game_info.seconds_elapsed - lastjumptime <= 0.5:
            #wejustjumped = 1
        #else:
            #wejustjumped = 0

        controls.pitch = clamp((((math.radians((Vdegtotarget * 1.3) + 12)) - my_car.physics.rotation.pitch) * 1.0), -1, 1)

        if my_car.physics.velocity.z < -200:
            controls.pitch = clamp(((my_car.physics.rotation.pitch) / -2), -1, 1)

        controls.handbrake = False

        if abs(Hdegtotarget) > 38 and car_location.dist(target_location) < 600 and car_velocity.length() > 700 and my_car.physics.location.z < 150 and choosetarget == "BallPredict" and offside == True:
            controls.handbrake = True

        if abs(Hdegtotarget) > 58 and car_velocity.length() > 700 and my_car.physics.location.z < 150 and choosetarget == "BallPredict":
            controls.handbrake = True

        # if choosetarget == "BallPredict" and target_location.z < 100 and car_location.dist(target_location) > 500 and car_location.z < 60 and car_velocity.length() > 1000 and abs(Hdegtotarget) < 2:
        #     self.active_sequence = Sequence([
        #         ControlStep(duration=0.20, controls=SimpleControllerState(throttle=1)),
        #         ControlStep(duration=0.10, controls=SimpleControllerState(jump=True)),
        #         ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
        #         ControlStep(duration=0.10, controls=SimpleControllerState(jump=True, pitch=-1)),
        #         ControlStep(duration=0.90, controls=SimpleControllerState(throttle=1)),
        #     ])


        # if flatdist < 150 and target_location.z > 300:
        #     controls.throttle = 0.225


        # Flip value testing
        # if controls.jump == True:
        #     controls.steer = clamp(controls.steer, -0.4, 0.4)
        #     controls.roll = clamp(controls.roll, -0.4, 0.4)
        #     controls.pitch = clamp(controls.pitch, -0.4, 0.4)
        #     controls.yaw = clamp(controls.yaw, -0.4, 0.4)

        # print(car_location.dist(ball_location))

        if controls.jump == False:
            self.laststate = 0

        if controls.jump == True:
            if self.laststate == 0:
                self.jumpcount += 1
                # print(f"{self.jumpcount} Jumps. Last jump at {packet.game_info.seconds_elapsed}")
            self.laststate = 1


        return controls

    # def Aerial(self, packet, target, time=packet.game_info.seconds_elapsed):
    #     my_car = packet.game_cars[self.index]
    #     if packet.game_info.seconds_elapsed < time + 2.5:
    #         controls.boost = True
    #     else:
    #         pass

    def begin_front_flip(self, packet):
        # Do a front flip. We will be committed to this for a few seconds and the bot will ignore other
        # logic during that time because we are setting the active_sequence.
        self.active_sequence = Sequence([
            ControlStep(duration=0.15, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.12, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.20, controls=SimpleControllerState(jump=True, pitch=-1)),
            ControlStep(duration=0.60, controls=SimpleControllerState()),
        ])


        # Return the controls associated with the beginning of the sequence so we can start right away.
        return self.active_sequence.tick(packet)
