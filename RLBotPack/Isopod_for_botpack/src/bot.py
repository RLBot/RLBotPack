from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState
from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3
import math
import copy
import numpy
import random

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

def normalize2d(x, y):
    vectorlength = math.sqrt(x*x + y*y)
    newx = x / vectorlength
    newy = y / vectorlength
    return newx, newy

def normalize3d(x, y, z):
    length = math.sqrt(x*x + y*y + z*z)
    newx = x / length
    newy = y / length
    newz = z / length
    return (newx, newy, newz)

class MyBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()

        self.sequence = "None"
        self.starttime = 0

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

        # This is made from Zing Utils Bot v0.4
        # You may contact me @ zimg on discord or join my server @ https://discord.gg/YkXV6wQ
        # Join the RLBot official discord @ https://discord.gg/zbaAKPt
        # View the RLBot website @ http://rlbot.org/
        # View the RLBot wiki @ https://github.com/RLBot/RLBot/wiki
        # Within the wiki, here are 2 useful links:
        # Gametick packet, input and output data https://github.com/RLBot/RLBotPythonExample/wiki/Input-and-Output-Data
        # Useful game values https://github.com/RLBot/RLBot/wiki/Useful-Game-Values

        ##################################################
        ########## Define Variables
        ##################################################

        # Gather some information about our car and the ball
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)
        ball_velocity = Vec3(packet.game_ball.physics.velocity)

        time = packet.game_info.seconds_elapsed - self.starttime

        # By default we will chase the ball, but target_location can be changed later
        target_location = ball_location

        # 1 for Orange, -1 for Blue
        myteam = ((packet.game_cars[self.index].team) - 0.5) * 2

        # High Y value * myteam means close to our side
        # Negative Y Value * myteam means close to enemy side

        # Location of our own goal
        mygoal = Vec3(0, (5230 * myteam), 0)

        # To check horizontal degrees to our own goal relative to where we are facing, use Hdegtogoal
        degreesE = (math.degrees(my_car.physics.rotation.yaw) * -myteam)
        degreesF = (math.degrees(math.atan2((-5150 - my_car.physics.location.y) * -myteam, 0 - my_car.physics.location.x)))
        Hdegtogoal = degreesE + degreesF
        if Hdegtogoal > 180:
            Hdegtogoal = Hdegtogoal - 360
        if Hdegtogoal < -180:
            Hdegtogoal = Hdegtogoal + 360

        # To check horizontal degrees to the enemy goal relative to where we are facing, use Hdegtoenemygoal
        degreesG = (math.degrees(my_car.physics.rotation.yaw) * -myteam)
        degreesH = (math.degrees(math.atan2((5150 - my_car.physics.location.y) * myteam, 0 - my_car.physics.location.x)))
        Hdegtoenemygoal = degreesG + degreesH
        if Hdegtoenemygoal > 180:
            Hdegtoenemygoal = Hdegtoenemygoal - 360
        if Hdegtoenemygoal < -180:
            Hdegtoenemygoal = Hdegtoenemygoal + 360

        # pointup == True if our car is roughly pointing upwards
        pointup = my_car.physics.rotation.pitch > 0.25

        # wejusthit == 1 if we just hit the ball
        if packet.game_ball.latest_touch.player_index == self.index and packet.game_info.seconds_elapsed - packet.game_ball.latest_touch.time_seconds < 0.8:
            wejusthit = 1
        else:
            wejusthit = 0

        ##################################################
        ########## Ball Prediction Processing
        ##################################################

        # ball, let's try to lead it a little bit
        ball_prediction = self.get_ball_prediction_struct()  # This can predict bounces, etc

        ballpredictcount = (car_location.dist(ball_location) - 110) / (1410 + (ball_location.z-100)/2.1 + ball_velocity.length()/6.5)

        ball_in_future = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + ballpredictcount)
        if ball_in_future is not None:
            shortballpredictcalc = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + ballpredictcount/2)
            shortballpredict = Vec3(shortballpredictcalc.physics.location)
        else:
            shortballpredict = ball_location

        # ball_in_future might be None if we don't have an adequate ball prediction right now, like during
        # replays, so check it to avoid errors.
        if ball_in_future is not None:
            target_location = Vec3(ball_in_future.physics.location)
            choosetarget = "BallPredict"

        if ball_in_future is not None:
            ballpredict = Vec3(ball_in_future.physics.location)
        else:
            ballpredict = ball_location

        # When you want to target the ball, use:
        # target_location = ballpredict


        ##################################################
        ########## Ball targeting adjustment
        ##################################################

        # Adjust our target location to line up for a shot
        if ball_location.z < 150 and abs(ball_velocity.z) < 150 and ball_location.y * myteam < 1000:
            distancescaling = clamp(car_location.dist(ball_location) - 90, 280, 2300) / 3.0
            # modify the last 3 numbers in the above formula to change the min, max, and scaling of our lineup adjustments
        else:
            distancescaling = 80
            # shortballpredict.y += myteam * 75
        # lineupvector works just like our old lineups, but we dont use this directly anymore
        lineupvector = ((ballpredict - Vec3(0, 5120 * -myteam, 7)) * 1.1) + Vec3(0, 5120 * -myteam, 7)
        directionadjust = (lineupvector - ballpredict)
        length = math.sqrt(
            directionadjust.x * directionadjust.x + directionadjust.y * directionadjust.y + directionadjust.z * directionadjust.z)
        directionadjust.x /= length
        directionadjust.y /= length
        directionadjust.z /= length
        # directionadjust is our normalized direction vector
        ballpredict += directionadjust * distancescaling
        shortballpredict += directionadjust * distancescaling

        target_location = ballpredict


        ##################################################
        ########## Check if ball is going in
        ##################################################


        ball_going_in = False
        for x in range(32):
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

        myteamsize = len(allylist)

        for x in range(packet.num_cars):
            if packet.game_cars[x].team == packet.game_cars[self.index].team:
                allylist.append(x)
            else:
                enemylist.append(x)

        closestcar = 0
        closestdist = Vec3(packet.game_cars[closestcar].physics.location).dist(ballpredict)
        for x in range(packet.num_cars):
            if (Vec3(packet.game_cars[x].physics.location).dist(ballpredict)) < (Vec3(packet.game_cars[closestcar].physics.location).dist(ballpredict)):
                closestcar = x
                closestdist = (Vec3(packet.game_cars[x].physics.location).dist(ballpredict))

        if packet.game_cars[closestcar].team != packet.game_cars[self.index].team:
            closestteam = 0
        else:
            closestteam = 1

        closestally = allylist[0]

        allydist = Vec3(packet.game_cars[allylist[0]].physics.location).dist(ballpredict)

        for x in allylist:
            if (Vec3(packet.game_cars[x].physics.location).dist(ballpredict)) < (Vec3(packet.game_cars[closestally].physics.location).dist(ballpredict)):
                closestally = x
                allydist = (Vec3(packet.game_cars[x].physics.location).dist(ballpredict))

        closestallydist = ballpredict.dist(packet.game_cars[closestally].physics.location)

        if len(enemylist) > 0:
            closestenemy = enemylist[0]
            enemydist = Vec3(packet.game_cars[enemylist[0]].physics.location).dist(ballpredict)

        for x in enemylist:
            if (Vec3(packet.game_cars[x].physics.location).dist(ballpredict)) < (Vec3(packet.game_cars[closestenemy].physics.location).dist(ballpredict)):
                closestenemy = x
                enemydist = (Vec3(packet.game_cars[x].physics.location).dist(ballpredict))

        # Calculate who the closest enemy is to us, and how far

        if len(enemylist) > 0:
            closestenemytome = enemylist[0]
            for x in enemylist:
                if (Vec3(packet.game_cars[x].physics.location).dist(my_car.physics.location)) <= (
                Vec3(packet.game_cars[closestenemytome].physics.location).dist(my_car.physics.location)):
                    closestenemytome = x
                    cardisttome = (Vec3(packet.game_cars[x].physics.location).dist(my_car.physics.location))

        # Calculate which allies are onside/offside
        numalliesonside = 0
        for x in allylist:
            if packet.game_cars[x].physics.location.y + myteam * -5500 < ball_location.y + myteam * -5500 and x != self.index:
                numalliesonside += 1

        # calculate our position on our team. 1st, 2nd, 3rd
        myposition = 1
        for x in allylist:
            if x != self.index:
                if packet.game_cars[x].physics.location.y * -myteam > my_car.physics.location.y * -myteam:
                    myposition += 1

        # calculate our position on our team. 1st, 2nd, 3rd
        myonsideposition = 1
        for x in allylist:
            if x != self.index:
                if my_car.physics.location.y * -myteam < packet.game_cars[x].physics.location.y * -myteam < ball_location.y * -myteam:
                    myonsideposition += 1

        # Calculate allies behind me and onside
        alliesinfrontofme = 0
        for x in allylist:
            if x != self.index:
                if packet.game_cars[x].physics.location.y * myteam < my_car.physics.location.y * myteam and packet.game_cars[x].physics.location.y * myteam > ball_location.y * myteam:
                    alliesinfrontofme += 1

        # Calculate allies infront of me and onside
        alliesbehindme = 0
        for x in allylist:
            if x != self.index:
                if packet.game_cars[x].physics.location.y * myteam > my_car.physics.location.y * myteam and packet.game_cars[x].physics.location.y * myteam > ball_location.y * myteam:
                    alliesbehindme += 1

        # To check if we are the closes car, use:
        # closestcar == self.index
        # To check if we are the closest car out of our allies, use:
        # closestally == self.index
        # To check if our team is the closest to the ball, use:
        # closestteam == 1


        ##################################################
        ########## More Variables
        ##################################################

        # if abs(car_location.y + myteam * (-5500)) > abs(ballpredict.y + myteam * (-5500)) and abs(car_location.y + myteam * (-5500)) > abs(ball_location.y + myteam * (-5500)):
        # if abs(car_location.y + myteam * (-5500)) > abs(ball_location.y + myteam * (-5500)):
        if car_location.y * -myteam > ball_location.y * -myteam:
            offside = True
        else:
            offside = False

        # To check horizontal degrees to the ball relative to where we are facing, use HdegtoBall
        degreesC = (math.degrees(my_car.physics.rotation.yaw) * -myteam)
        degreesB = (math.degrees(math.atan2((ballpredict.y - my_car.physics.location.y)*myteam,ballpredict.x - my_car.physics.location.x)))
        HdegtoBall = degreesC + degreesB
        if HdegtoBall > 180:
            HdegtoBall = HdegtoBall - 360
        if HdegtoBall < -180:
            HdegtoBall = HdegtoBall + 360

        # To check horizontal degrees to our own goal relative to where we are facing, use HdegtoGoal
        degreesE = (math.degrees(my_car.physics.rotation.yaw) * -myteam)
        degreesF = (math.degrees(math.atan2((5150 - my_car.physics.location.y),0 - my_car.physics.location.x)))
        HdegtoGoal = degreesE + degreesF
        if HdegtoGoal > 180:
            HdegtoGoal = HdegtoGoal - 360
        if HdegtoGoal < -180:
            HdegtoGoal = HdegtoGoal + 360

        # To check horizontal degrees to the enemy goal relative to where we are facing, use HdegtoEnemyGoal
        degreesG = (math.degrees(my_car.physics.rotation.yaw) * -myteam)
        degreesH = (math.degrees(math.atan2((-5150 - my_car.physics.location.y),0 - my_car.physics.location.x)))
        HdegtoEnemyGoal = degreesG + degreesH
        if HdegtoEnemyGoal > 180:
            HdegtoEnemyGoal = HdegtoEnemyGoal - 360
        if HdegtoEnemyGoal < -180:
            HdegtoEnemyGoal = HdegtoEnemyGoal + 360

        # Specifically the distance in height between us and the ball
        distheight = (ballpredict.z) - (my_car.physics.location.z + 75)
        # Specifically the distance ignoring height between us and the ball
        flatdist = math.sqrt(((my_car.physics.location.x - ballpredict.x) ** 2) + ((my_car.physics.location.y - target_location.y) ** 2))

        # The vertical degrees to the ball
        VdegtoBall = (math.degrees(math.atan2(distheight, flatdist)))

        # The speed at which our car is rotating. These represent an axis that we are rotating around moreso than a direction that we are rotating
        RotVelX = my_car.physics.angular_velocity.x
        RotVelY = my_car.physics.angular_velocity.y
        RotVelZ = my_car.physics.angular_velocity.z

        # Determine what the horizontal angle is to the our current target, which is the ball right here. we will redo this below just incase our target changes
        degreesC = (math.degrees(my_car.physics.rotation.yaw) * -myteam)
        degreesB = (math.degrees(math.atan2((target_location.y - my_car.physics.location.y) * myteam, target_location.x - my_car.physics.location.x)))
        Hdegtotarget = degreesC + degreesB
        if Hdegtotarget > 180:
            Hdegtotarget = Hdegtotarget - 360
        if Hdegtotarget < -180:
            Hdegtotarget = Hdegtotarget + 360

        owngoaling = abs(HdegtoBall - HdegtoGoal) < 17 and car_location.dist(ball_location) < 1500

        jumpdistance = 400 + clamp(my_car.boost, 0, 40) * 60
        targetangle = (-27 / 1400) * clamp((car_velocity.length()), 0, 1400) + 40
        angledforjump = (targetangle - 8) < VdegtoBall < (targetangle + 8)

        mechanics = "None"

        ##################################################
        ########## Strategy
        ##################################################

        # This is where we decide what action we are going to do
        # Each condition is checked in order from top to bottom, even if the previous one is fulfilled
        # This means that actions near the bottom of the list have the highest priority
        # With that in mind, lets set our first decision to be something basic that might be overwritten

        # Chase the ball
        decision = "Ballchase"

        # Return to our goal if we are offside
        if offside:
            decision = "ToGoal"

        # Stay behind if we are second man
        if alliesinfrontofme == 1 and car_location.dist(ball_location) > 1000 and -3500 < ball_location.y < 3500:
            decision = "Center"

        # Check if the ball is lined up with the goal and we are facing the ball, then go for the ball
        if ball_in_future is not None and abs(HdegtoBall - HdegtoEnemyGoal) < 17 and (ballpredict.y * myteam) < 1 and ballpredict.z < 150 and abs(ball_velocity.z) < 100 and offside is False:
            decision = "TakeShot"

        # Play goalie if we are third man
        if alliesinfrontofme == 2 and car_location.dist(ball_location) > 1000 and -4000 < ball_location.y * myteam < 4000:
            decision = "ToGoal"

        # Stay behind if the ball is high up
        if ball_location.z > 2500 or ballpredict.z > 2500:
            decision = "Center"

        # Stay behind if ally has possesion
        if closestallydist < 300 and closestally == closestcar and closestally is not self.index and ball_going_in is False:
            decision = "Center"

        # Jump or aerial towards the ball
        if offside is False and angledforjump and abs(Hdegtotarget) < 3 and car_location.z < 100 and flatdist > 50 and car_velocity.z > -50 and 145 < ball_location.z < 2000 and 200 < car_location.dist(ball_location) < jumpdistance and RotVelZ < 0.06:
            if car_velocity.length() > 1000 or ball_velocity.length() < 1000:
                decision = "JumpShot"

        if offside is False and my_car.physics.location.z > 50 and my_car.physics.location.z < ballpredict.z and abs(Hdegtotarget) < 10 and car_location.dist(ball_location) < jumpdistance:
            decision = "Aerial"

        # Clear the ball out of our corner
        if ballpredict.y * myteam > 4400 and abs(ballpredict.x) > 1100 and ballpredict.z < 2000:
            decision = "Ballchase"

        # Challenge the ball if the enemy has posession
        if len(enemylist) > 0:
            if closestcar in enemylist or enemydist < 1100:
                if ball_in_future is not None and offside and owngoaling is False:
                    decision = "EmergencySave"

        # Go for a save if the ball is going in
        if ball_going_in is True and owngoaling is False and target_location.z < 200:
            decision = "EmergencySave"

        # Go for kickoff if the ball is at 0,0
        if ball_location.x == 0 and ball_location.y == 0 and car_velocity.length() > 200 and closestally == self.index:
            decision = "Kickoff"





        ##################################################
        ########## Define and set up Controls
        ##################################################

        # Define our controller and set up some default controls so that our stuff works properly
        controls = SimpleControllerState()
        controls.handbrake = False
        controls.jump = False
        controls.boost = False


        ##################################################
        ########## Action
        ##################################################

        # This is where our bot does actions based on our decision
        # These will be led with if statements. Check if our decision is something, then do some actions

        if decision == "Ballchase":
            if ball_in_future is not None:
                target_location = ballpredict
            else:
                target_location = ball_location
            mechanics = "DriveTo"
            if ball_location.y * myteam < 4500 and flatdist < 1300 and car_location.z < 70:
                if target_location.z > 200 or abs(ball_velocity.z) > 400:
                    mechanics = "DriveToAndStop"

        if decision == "ToGoal":
            target_location = mygoal
            mechanics = "DriveToAndStop"

        if decision == "Center":
            target_location.y = (ballpredict.y + mygoal.y) / 2
            target_location.x = (ballpredict.x) / 2
            target_location.z = 31
            mechanics = "DriveToAndStop"

        if decision == "Goalie":
            target_location = mygoal
            if owngoaling:
                if car_location.x > 0:
                    target_location = Vec3(1300, myteam * 4750, 0)
                else:
                    target_location = Vec3(-1300, myteam * 4750, 0)
            mechanics = "DriveToAndStop"

        if decision == "TakeShot":
            if ball_in_future is not None:
                target_location = shortballpredict
            else:
                target_location = ball_location
            mechanics = "BoostTo"

        if decision == "JumpShot":
            # target_location = shortballpredict
            mechanics = "Jump"

        if decision == "Aerial":
            # target_location = shortballpredict
            mechanics = "Aerial"

        if decision == "EmergencySave":
            if ball_in_future is not None:
                target_location = shortballpredict
            else:
                target_location = ball_location
            target_location.y += 55 * myteam
            mechanics = "BoostTo"
            if ballpredict.z > 170 and car_location.dist(ballpredict) < 1400:
                if car_location.z < 100 and car_velocity.z > -100:
                    mechanics = "Jump"
                else:
                    mechanics = "Aerial"

        if decision == "Kickoff":
            target_location.x = 0
            target_location.y = myteam * 94
            target_location.z = 24
            mechanics = "BoostTo"
            if 1300 < car_velocity.length() < 1500:
                self.active_sequence = Sequence([
                    ControlStep(duration=0.10, controls=SimpleControllerState(jump=True, boost=True)),
                    ControlStep(duration=0.03, controls=SimpleControllerState(jump=False, boost=True)),
                    ControlStep(duration=0.70, controls=SimpleControllerState(jump=True, pitch=-1)),
                    ControlStep(duration=0.20, controls=SimpleControllerState()),
                ])

        ##################################################
        ########## More Variables
        ##################################################

        # TESTING
        # target_location = Vec3(0, 0, 0)
        # mechanics = "DriveToAndStop"

        # Determine what the horizontal angle is to the our current target
        degreesC = (math.degrees(my_car.physics.rotation.yaw) * -myteam)
        degreesB = (math.degrees(math.atan2((target_location.y - my_car.physics.location.y) * myteam, target_location.x - my_car.physics.location.x)))
        Hdegtotarget = degreesC + degreesB
        if Hdegtotarget > 180:
            Hdegtotarget = Hdegtotarget - 360
        if Hdegtotarget < -180:
            Hdegtotarget = Hdegtotarget + 360


        ##################################################
        ########## Mechanics
        ##################################################

        if mechanics == "DriveTo":
            controls.throttle = 1.0
            if target_location.y > 5200:
                target_location.y = 5200
            if target_location.y < -5200:
                target_location.y = -5200

        if mechanics == "DriveToAndStop":
            # target_location.y += myteam * 70
            if car_location.dist(target_location) < 500:
                controls.throttle = clamp((car_location.dist(target_location) + 200 - car_velocity.length() / 1.0) / 2500, -1, 1)
            else:
                controls.throttle = 1
            if car_location.dist(target_location) < 80:
                controls.throttle = 0
            if target_location.y > 5200:
                target_location.y = 5200
            if target_location.y < -5200:
                target_location.y = -5200

        if mechanics == "BoostTo":
            controls.throttle = 1.0
            if abs(Hdegtotarget) < 10 and car_velocity.length() > 800:
                controls.boost = True
            if target_location.y > 5200:
                target_location.y = 5200
            if target_location.y < -5200:
                target_location.y = -5200
            if car_location.dist(ballpredict) < 470 and abs(Hdegtotarget) < 6 and ball_velocity.length() < 1300 and car_velocity.length() > 1300:
                controls.jump = True

        if mechanics == "Jump":
            controls.throttle = 1.0
            controls.jump = True

        if mechanics == "Aerial":
            controls.throttle = 1.0
            controls.boost = True

        if mechanics == "None":
            controls.throttle = 0.0


        ##################################################
        ########## More Variables
        ##################################################

        # Determine what the horizontal angle is to our target
        degreesC = (math.degrees(my_car.physics.rotation.yaw) * -myteam)
        degreesB = (math.degrees(math.atan2((target_location.y - my_car.physics.location.y) * myteam, target_location.x - my_car.physics.location.x)))
        Hdegtotarget = degreesC + degreesB
        if Hdegtotarget > 180:
            Hdegtotarget = Hdegtotarget - 360
        if Hdegtotarget < -180:
            Hdegtotarget = Hdegtotarget + 360


        ##################################################
        ########## Basic Controls
        ##################################################

        # These things are always running, regardless of our decision.

        # Steer and throttle towards our target
        controls.steer = steer_toward_target(my_car, target_location)

        # Keep our car level
        controls.roll = clamp((my_car.physics.rotation.roll / -1),-1,1)

        # Aim our car at the ball in mid air
        # controls.yaw = clamp(((((HdegtoBall * 1.5) * myteam) + (RotVelZ * -1.5)) / 20), -1, 1)
        controls.yaw = clamp((Hdegtotarget * myteam / 45), -1, 1)

        # Point up or down at the ball when in air
        controls.pitch = clamp((((math.radians((VdegtoBall * 1.8) + 23)) - my_car.physics.rotation.pitch) * 1.5), -1, 1)

        # Level ourselves if we are falling
        if my_car.physics.velocity.z < -400:
            controls.pitch = clamp(((my_car.physics.rotation.pitch) / -2), -1, 1)

        # Dont flip when jumping
        if controls.jump == True:
            controls.pitch = clamp(controls.pitch, -0.4, 0.4)
            controls.yaw = clamp(controls.yaw, -0.4, 0.4)
            controls.roll = clamp(controls.roll, -0.4, 0.4)

        # Use handbrake to turn faster if going for the ball
        controls.handbrake = False

        if abs(Hdegtotarget) > 35 and 120 < car_location.dist(target_location) < 600 and car_velocity.length() > 200 and my_car.physics.location.z < 150 and decision == "Ballchase" and offside is True:
            controls.handbrake = True

        if abs(Hdegtotarget) > 55 and car_location.dist(target_location) > 600 and car_velocity.length() > 200 and my_car.physics.location.z < 150 and decision == "Ballchase":
            controls.handbrake = True

        # Flip into the ball?
        if offside == False and abs(Hdegtotarget) < 40 and 70 < car_location.z < 350 and abs(car_location.z - ball_location.z) < 40 and car_location.dist(ball_location) < 390 and car_velocity.length() > 700 and ball_velocity.length() < 2400:
            if abs(car_location.x) < 4000 and abs(car_location.y) < 5000:
                self.active_sequence = Sequence([
                    ControlStep(duration=0.05, controls=SimpleControllerState(jump=False, pitch=1)),
                    ControlStep(duration=0.13, controls=SimpleControllerState(jump=True, pitch=-1, yaw=clamp(HdegtoBall * myteam / 38, -1, 1))),
                    ControlStep(duration=0.40, controls=SimpleControllerState(throttle=1)),
                ])

        # Get down if we are on a wall
        if abs(my_car.physics.location.y) > 5030 or abs(my_car.physics.location.x) > 4006:
            if VdegtoBall < 40 and car_location.dist(ballpredict) < 250:
                controls.jump = True
            if my_car.physics.location.z > ballpredict.z + 200:
                controls.jump = True
            if my_car.physics.location.z > 700 and car_location.dist(target_location) > 1600:
                target_location = car_location
                target_location.z = 4


        ##################################################
        ########## State Setting
        ##################################################

        # Vertical and Horizontal Aerial control training
        # if abs(ball_location.y) > 3800 or abs(ball_location.x) > 3800:
        #     randomboost = random.randint(20, 100)
        #     randomX = random.randint(-2000, 2000)
        #     randomR = random.randint(-3, 3)
        #     car_state = CarState(Physics(location=Vector3(randomX, 2000 * myteam, 42), velocity=Vector3(0, 0, 0)), boost_amount=randomboost)
        #     randomX = random.randint(-3500, 3500)
        #     randomZ = random.randint(1000, 1000)
        #     ball_state = BallState(Physics(location=Vector3(randomX, -1000*myteam, randomZ), velocity=Vector3(-randomX/2.5, 0, randomZ/7), angular_velocity=Vector3(0, 1, 0)))
        #     game_state = GameState(ball=ball_state, cars={self.index: car_state})
        #     self.set_game_state(game_state)

        # Test DriveToAndStop
        # if abs(car_location.x) < 100 and abs(car_location.y) < 100 and car_velocity.length() < 25:
        #     randomX = random.randint(-3000, 3000)
        #     randomY = random.randint(-4000, 4000)
        #     car_state = CarState(Physics(location=Vector3(randomX, randomY, 42)))
        #     game_state = GameState(cars={self.index: car_state})
        #     self.set_game_state(game_state)


        ##################################################
        ########## Rendering
        ##################################################

        # Lets draw some things on the screen to see what our bot is thinking, such as where its going and where the ball is going

        if myteam == 1 and ball_in_future is not None:
            self.renderer.draw_line_3d(car_location, target_location, self.renderer.orange())
            self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.orange(), centered=True)

        if myteam == -1 and ball_in_future is not None:
            self.renderer.draw_line_3d(car_location, target_location, self.renderer.cyan())
            self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)

        self.renderer.draw_string_3d(car_location, 1, 1, f'{decision}\n{mechanics}', self.renderer.white())


        return controls

        return self.active_sequence.tick(packet)
