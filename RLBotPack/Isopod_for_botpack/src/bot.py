from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3
import math
import copy
import numpy

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

        ##################################################
        ########## Top
        ##################################################

        sequence = "None"
        sequencestarttime = 0


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
        ########## Define Variables
        ##################################################

        # time = packet.game_info.seconds_elapsed - sequencestarttime

        # Gather some information about our car and the ball
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)
        ball_velocity = Vec3(packet.game_ball.physics.velocity)

        # By default we will chase the ball, but target_location can be changed later
        target_location = ball_location

        # 1 for Orange, -1 for Blue
        myteam = ((packet.game_cars[self.index].team) - 0.5) * 2

        # Location of our own goal
        mygoal = Vec3(0, (5150 * myteam), 0)

        # To check Vertical degrees to the ball, use Vdegtotarget
        distheight = (target_location.z) - (my_car.physics.location.z + 75)
        flatdist = math.sqrt(((my_car.physics.location.x - target_location.x) ** 2) + (
                    (my_car.physics.location.y - target_location.y) ** 2))

        # This is inaccurate, but its basically close enough and idk how to fix it lol
        Vdegtotarget = (math.degrees(math.atan2(distheight, flatdist)))

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
        ball_in_future = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + ((car_location.dist(ball_location) - 100) / 1500) + ((ball_location.z - 95) / 5500))

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
        ########## Check for Intercept
        ##################################################

        ballgoingtowardsme = False
        for x in range(50):
            ball_towards_me = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + ((x+10) / 20))
            if ball_towards_me is not None:
                if car_location.dist(ball_towards_me.physics.location) < 300 and ball_towards_me.physics.location.z < 120 and ball_velocity.length() > 1400:
                    ballgoingtowardsme = True


        ##################################################
        ########## Ball targeting adjustment
        ##################################################

        # Adjust our target location to line up for a shot
        if ball_location.z < 400 and ball_location.y * myteam < 1000:
            distancescaling = clamp(car_location.dist(ball_location), 100, 1800) / 2.85
            # if car_location.dist(ballpredict) > 1200:
            #     distancescaling = 800
            # else:
            #     distancescaling = 127
            # lineupvector works just like our old lineups, but we dont use this directly anymore
            lineupvector = ((ballpredict - Vec3(0, 5120 * -myteam, 7)) * 1.1) + Vec3(0, 5120 * -myteam, 7)
            directionadjust = (lineupvector - ballpredict)
            length = math.sqrt(directionadjust.x * directionadjust.x + directionadjust.y * directionadjust.y + directionadjust.z * directionadjust.z)
            directionadjust.x /= length
            directionadjust.x *= 0.95
            directionadjust.y /= length
            directionadjust.y *= 1.065
            directionadjust.z /= length
            # directionadjust is our normalized direction vector
            ballpredict += directionadjust * distancescaling
        else:
            ballpredict.y += myteam * 80
        clamp(ballpredict.y, -5000, 5000)
        clamp(ballpredict.x, -4030, 4030)


        ##################################################
        ########## Check if ball is going in
        ##################################################

        ball_going_in = False
        for x in range(40):
            ball_towards_goal = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + (x / 10))
            if ball_towards_goal is not None:
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


        # To check if we are the closes car, use:
        # closestcar == self.index
        # To check if we are the closest car out of our allies, use:
        # closestally == self.index
        # To check if our team is the closest to the ball, use:
        # closestteam == 1


        ##################################################
        ########## More Variables
        ##################################################

        if abs(car_location.y + myteam * (-5500)) > abs(ballpredict.y + myteam * (-5500)) and abs(car_location.y + myteam * (-5500)) > abs(ball_location.y + myteam * (-5500)):
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
        degreesF = (math.degrees(math.atan2(((5150 * myteam) - my_car.physics.location.y)*myteam, 0 - my_car.physics.location.x)))
        HdegtoGoal = degreesE + degreesF
        if HdegtoGoal > 180:
            HdegtoGoal = HdegtoGoal - 360
        if HdegtoGoal < -180:
            HdegtoGoal = HdegtoGoal + 360

        # To check horizontal degrees to the enemy goal relative to where we are facing, use HdegtoEnemyGoal
        degreesG = (math.degrees(my_car.physics.rotation.yaw) * -myteam)
        degreesH = (math.degrees(math.atan2(((-5150 * myteam) - my_car.physics.location.y)*myteam, 0 - my_car.physics.location.x)))
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

        owngoaling = abs(HdegtoBall - HdegtoGoal) < 20 and car_location.dist(ball_location) < 1000


        ##################################################
        ########## Aerial Control Variables
        ##################################################

        RotVelZ = my_car.physics.angular_velocity.z
        RotVelX = my_car.physics.angular_velocity.x
        RotVelY = my_car.physics.angular_velocity.y


        ##################################################
        ########## Strategy
        ##################################################

        # This is where we decide what action we are going to do
        # Each condition is checked in order from top to bottom, even if the previous one is fulfilled
        # This means that actions near the bottom of the list have the highest priority
        # With that in mind, lets set our first decision to be something basic that might be overwritten
        decision = "Ballchase"

        # If we have an ally, and they are closest to the ball, and we are not closest to the ball, we will play defense
        if len(allylist) > 1 and closestteam == 1 and closestcar != self.index and ballpredict.y * myteam > 900 and car_location.dist(ballpredict) > 1500:
            decision = "Defend"

        # If we have an ally onside and close to the ball, and on the enemy half of the field, or the ball is in a far corner, we will play center
        if closestteam == 1 and ball_location.y * myteam < 0 and closestally != self.index and car_location.dist(ball_location) > 1750:
            decision = "Center"
        if numalliesonside < 1 and ball_location.y * -myteam > 4950 and abs(ball_location.x) > 850:
            decision = "Center"

        # If an ally has posession and we are on our own side of the field, play goalie
        if closestteam == 1 and ball_location.y * myteam > 0 and closestally != self.index and numalliesonside > 0 and car_location.dist(ball_location) > 1750:
            decision = "OwnGoal"

        # Bump an enemy if they are close and we are offside
        if len(enemylist) > 0:
            degtocar = degtotarget(my_car.physics.location, (math.degrees(my_car.physics.rotation.yaw) * -myteam),
                                   myteam, Vec3(packet.game_cars[closestenemytome].physics.location))
        else:
            degtocar = 0
        if len(enemylist) > 0:
            if offside is True and cardisttome < 1600 and my_car.boost > 40 and car_velocity.length() > 1000 and abs(
                    degtocar) < 45:
                decision = "Bump"

        # Check if we can detect the ball to avoid errors. Then check if the ball is lined up with the goal and we are facing the ball, then go for the ball
        if ball_in_future is not None and abs(HdegtoBall - HdegtoEnemyGoal) < 17 and (ballpredict.y * myteam) < 0:
            decision = "TakeShot"

        # Jump or aerial towards the ball
        jumpdistance = 1000 + clamp(my_car.boost*75, 0, 2000)
        if flatdist > 10 and abs(HdegtoBall) < 1 and 250 < car_location.dist(ball_location) < jumpdistance and ballpredict.z > 120 and car_location.z < 90 and car_velocity.z > -10:
            # ball at a low angle
            if 12 < Vdegtotarget < 23:
                if 1000 < car_velocity.length() < 1500:
                    decision = "JumpShot"
            # Ball at a medium angle
            if 15 < Vdegtotarget < 34:
                if 500 < car_velocity.length() < 1100:
                    decision = "JumpShot"
            # Ball at a high angle
            if 25 < Vdegtotarget < 70 and my_car.boost > 25:
                if 100 < car_velocity.length() < 550:
                    decision = "JumpShot"
        if 10 < Vdegtotarget < 60 and car_location.dist(ball_location) < 500 and ballpredict.z > 120 and car_location.z < 90 and car_velocity.z > -10:
            decision = "JumpShot"

        if offside is False and car_location.dist(ball_location) < 3400 and my_car.physics.location.z > 70 and my_car.physics.location.z < target_location.z and abs(Hdegtotarget) < 10:
            decision = "Aerial"

        # If we are on the wrong side of the ball, return to our own goal
        if offside:
            decision = "OwnGoal"

        # Clear the ball out of our corner
        if ballpredict.y * myteam > 4400 and abs(ballpredict.x) > 1100 and ballpredict.z < 2000:
            decision = "Ballchase"

        # # Hit the ball if it is going past us
        # if ballgoingtowardsme is True and offside is False:
        #     decision = "Intercept"

        # Make an emergency save if the ball is going in
        if ball_in_future is not None and ball_going_in is True and owngoaling is False and target_location.z < 200 and ball_location.y * myteam > 1000:
            decision = "EmergencySave"

        # Challenge the ball if the enemy has posession
        if len(enemylist) > 0:
            if ball_in_future is not None and enemydist < 600 and offside and owngoaling is False and ball_location.y * myteam > 1000:
                decision = "EmergencySave"

        # Defend goal if we arent closest on kickoff
            if ball_location.x == 0 and ball_location.y == 0 and closestally != self.index:
                decision = "OwnGoal"

        # Go for kickoff if the ball is centered
        if ball_location.x == 0 and ball_location.y == 0 and car_velocity.length() > 400 and closestally == self.index:
            decision = "Kickoff"

        # if packet.num_cars > 1:
        #     for x in range(packet.num_cars):
        #         if x != self.index:
        #             if car_location.dist(Vec3(packet.game_cars[x].physics.location)) < 240:
        #                 if car_velocity.length() < 100 and car_location.dist(target_location) > 200:
        #                     decision = "HalfFlip"


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
            # if car_location.dist(ball_location) < 250:
            #     target_location = ball_location
            #     target_location.y += myteam * 75

            # if abs(Hdegtotarget) < 10 and ballpredict.z < 260 and 200 < car_location.dist(ballpredict) < 630 and car_velocity.length() > 1200 and ball_velocity.length() < 1000 and abs(car_velocity.z) < 1:
            #     self.active_sequence = Sequence([
            #         ControlStep(duration=0.07, controls=SimpleControllerState(throttle=1, boost=False, jump=False)),
            #         ControlStep(duration=0.09, controls=SimpleControllerState(jump=True)),
            #         ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
            #         ControlStep(duration=0.13, controls=SimpleControllerState(jump=True, pitch=-1, yaw=clamp(HdegtoBall/22,-1,1))),
            #         # ControlStep(duration=0.13, controls=SimpleControllerState(jump=True, pitch=-1)),
            #         ControlStep(duration=0.70, controls=SimpleControllerState(throttle=1)),
            #     ])
            # if abs(Hdegtotarget) < 2 and abs(HdegtoBall) < 8 and car_velocity.length() > 1400 and ballpredict.z < 140:
            #     controls.boost = True

        # This will put us half way between the ball and our own goal
        if decision == "Defend":
            sequencestarttime = packet.game_info.seconds_elapsed
            target_location = Vec3(ballpredict.x / 2, myteam * 2000 + (ballpredict.y / 2), 0)

        if decision == "OwnGoal":
            if car_location.x > 0:
                target_location = Vec3(1100, myteam * 4850, 0)
                if owngoaling:
                    target_location = Vec3(2100, myteam * 4850, 0)
            else:
                target_location = Vec3(-1100, myteam * 4850, 0)
                if owngoaling:
                    target_location = Vec3(-2100, myteam * 4850, 0)
            if ball_going_in is True:
                controls.boost = True

        if decision == "TakeShot":
            target_location = ballpredict
            if car_velocity.length() > 900 and abs(HdegtoBall) < 9:
                controls.boost = True
        #     if abs(Hdegtotarget) < 10 and ballpredict.z < 260 and 200 < car_location.dist(ballpredict) < 630 and car_velocity.length() > 1200 and ball_velocity.length() < 1300 and abs(car_velocity.z) < 1:
        #         self.active_sequence = Sequence([
        #             ControlStep(duration=0.07, controls=SimpleControllerState(throttle=1, boost=False, jump=False)),
        #             ControlStep(duration=0.09, controls=SimpleControllerState(jump=True)),
        #             ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
        #             ControlStep(duration=0.13, controls=SimpleControllerState(jump=True, pitch=-1, yaw=clamp(HdegtoBall/22,-1,1))),
        #             ControlStep(duration=0.70, controls=SimpleControllerState(throttle=1)),
        #         ])

        if decision == "Bump":
            if len(enemylist) > 0:
                target_location = Vec3(packet.game_cars[closestenemytome].physics.location)
                controls.boost = True

        if decision == "Center":
            if ball_in_future is not None:
                target_location = Vec3(ball_in_future.physics.location)
                target_location.y += 1700 * myteam
                target_location.x *= 0.65
                target_location.z = 3

        if decision == "JumpShot":
            controls.jump = True

        if decision == "Aerial":
            controls.boost = True

        if decision == "EmergencySave":
            if ball_in_future is not None:
                target_location = ballpredict
            else:
                target_location = ball_location
            if abs(Hdegtotarget) < 15:
                controls.boost = True
            if abs(Hdegtotarget) > 120:
                target_location = Vec3(ball_location)
            if 10 < Vdegtotarget < 45 and abs(Hdegtotarget) < 3:
                controls.jump = True
                controls.boost = True

        if decision == "Kickoff":
            controls.boost = True
            target_location.y += myteam * 80
            if car_location.dist(ball_location) < 1100:
                self.active_sequence = Sequence([
                    ControlStep(duration=0.08, controls=SimpleControllerState(jump=True)),
                    ControlStep(duration=0.03, controls=SimpleControllerState(jump=False)),
                    ControlStep(duration=0.70, controls=SimpleControllerState(jump=True, pitch=-1)),
                    ControlStep(duration=0.20, controls=SimpleControllerState()),
                ])

        # if decision == "Intercept":
        #     target_location = ball_location
        #     if target_location.z > 110 and car_location.dist(ball_location) < 450:
        #         controls.jump = True

        # if decision == "HalfFlip":
        #     self.active_sequence = Sequence([
        #         ControlStep(duration=0.08, controls=SimpleControllerState(jump=True)),
        #         ControlStep(duration=0.03, controls=SimpleControllerState(jump=False)),
        #         ControlStep(duration=0.10, controls=SimpleControllerState(jump=True, pitch=1)),
        #         ControlStep(duration=0.50, controls=SimpleControllerState()),
        #     ])

        # If you added code for another decision, this is where you would write the if statement and execution
        # Remember when you use 1 = and when you use 2!

        ##################################################
        ########## More Variables
        ##################################################

        # Determine what the horizontal angle is to our target
        degreesC = (math.degrees(my_car.physics.rotation.yaw) * -myteam)
        degreesB = (math.degrees(math.atan2((target_location.y - my_car.physics.location.y) * myteam,
                                            target_location.x - my_car.physics.location.x)))
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
        controls.throttle = 1.0

        # Stop driving forwards if the ball is at a high angle above us
        # if Vdegtotarget > 40 and abs(Hdegtotarget) < 40 and 2200 > car_location.dist(ballpredict) > 800:
        #     if decision == "Ballchase" or decision == "TakeShot":
        #         controls.throttle = -0.33
        #         controls.boost = False
        #         controls.steer = -steer_toward_target(my_car, target_location)

        # Slow down if ball is above and near us
        if abs(Hdegtotarget) < 60 and car_location.dist(ballpredict) < 2500 and ball_velocity.z > -500:
            if decision == "Ballchase" or decision == "TakeShot":
                controls.throttle = clamp(1 - (Vdegtotarget-11)/65, -1, 1)

        # Keep our car level
        controls.roll = clamp((my_car.physics.rotation.roll / -1),-1,1)

        # Aim our car at the ball in mid air
        # controls.yaw = clamp(((((HdegtoBall * 1.5) * myteam) + (RotVelZ * -1.5)) / 20), -1, 1)
        # controls.yaw = clamp((Hdegtotarget * myteam / 75), -1, 1)
        controls.yaw = clamp((Hdegtotarget * myteam / 20 + (RotVelZ * -0.6)), -1, 1)

        # Point up or down at the ball when in air
        controls.pitch = clamp((((math.radians((VdegtoBall * 1.045) + 29.5)) - my_car.physics.rotation.pitch) * 1.5), -1, 1)

        # Level ourselves if we are falling
        if my_car.physics.velocity.z < -400:
            controls.pitch = clamp(((my_car.physics.rotation.pitch) / -2), -1, 1)

        # Dont flip when jumping
        if controls.jump == True:
            controls.pitch = clamp(controls.pitch, -0.1, 0.1)
            controls.yaw = clamp(controls.yaw, -0.1, 0.1)
            controls.roll = clamp(controls.roll, -0.1, 0.1)

        # Use handbrake to turn faster if going for the ball
        controls.handbrake = False

        if abs(Hdegtotarget) > 30 and car_location.dist(target_location) < 600 and car_velocity.length() > 700 and my_car.physics.location.z < 150 and decision == "Ballchase" and offside is True:
            controls.handbrake = True

        if abs(Hdegtotarget) > 55 and car_velocity.length() > 700 and my_car.physics.location.z < 150 and decision == "Ballchase":
            controls.handbrake = True

        # Jump off if we are high on a wall and above the ball and not pointing our car up
        # if my_car.physics.location.z > ball_location.z and my_car.physics.location.z > 2000 and pointup is False:
        #     if abs(my_car.physics.location.y) > 5095:
        #         controls.jump = True
        #     if abs(my_car.physics.location.x) > 4075:
        #         controls.jump = True
        # if my_car.physics.location.z > ball_location.z and my_car.physics.location.z > 1500:
        #     if abs(my_car.physics.location.y) > 5095:
        #         controls.jump = True
        #     if abs(my_car.physics.location.x) > 4075:
        #         controls.jump = True

        # Get down if we are on a wall
        if abs(my_car.physics.location.y) > 5030 or abs(my_car.physics.location.x) > 4006:
            # if my_car.physics.location.z > 400:
            #     target_location.z = 11
            if my_car.physics.location.z > 700 or 30 < Vdegtotarget < 40:
                controls.jump = True

        # Flip into the ball?
        if abs(Hdegtotarget) < 40 and 100 < car_location.z < 1200 and abs(car_location.z - ball_location.z) < 100 and car_location.dist(ball_location) < 390 and car_velocity.length() > 700 and ball_velocity.length() < 2400:
            if abs(car_location.x) < 4000 and abs(car_location.y) < 5000:
                self.active_sequence = Sequence([
                    ControlStep(duration=0.05, controls=SimpleControllerState(jump=False, pitch=1)),
                    ControlStep(duration=0.13, controls=SimpleControllerState(jump=True, pitch=-1, yaw=clamp(HdegtoBall/27,-1,1))),
                    ControlStep(duration=0.40, controls=SimpleControllerState(throttle=1)),
                ])


        ##################################################
        ########## Rendering
        ##################################################

        # Lets draw some things on the screen to see what our bot is thinking, such as where its going and where the ball is going

        if myteam == 1 and ball_in_future is not None:
            self.renderer.draw_line_3d(car_location, target_location, self.renderer.orange())
            self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.orange(), centered=True)
            self.renderer.draw_string_3d(car_location, 1, 1, f'{decision}', self.renderer.white())

        if myteam == -1 and ball_in_future is not None:
            self.renderer.draw_line_3d(car_location, target_location, self.renderer.cyan())
            self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
            self.renderer.draw_string_3d(car_location, 1, 1, f'{decision}', self.renderer.white())


        return controls

        return self.active_sequence.tick(packet)
