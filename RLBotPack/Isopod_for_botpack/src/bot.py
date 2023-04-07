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

        # 1 for Orange, -1 for Blue
        myteam = ((packet.game_cars[self.index].team) - 0.5) * 2

        # Location of our own goal
        mygoal = Vec3(0, (5150 * myteam), 0)

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
        ball_in_future = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + ((car_location.dist(ball_location) - 100) / 1400) + ((ball_location.z - 95) / 2500))

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
        ########## Check if ball is going in
        ##################################################


        ball_going_in = False
        for x in range(48):
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
        ########## Lineup Processing
        ##################################################

        # lineupclose == True if we are close to a position where we are lined up for a shot
        # lineupC and lineupE are vectors that are lined up with the goal and the ball
        if ball_in_future is not None:
            lineupA = Vec3(ball_in_future.physics.location) - Vec3(0, (-5250 * myteam), 0)
            lineupB = lineupA * 1.15
            lineupB.x *= 1.1
            lineupC = lineupB + Vec3(0, -5250 * myteam, 0)
            lineupC.z = 20
            lineupD = lineupA * 1.3
            lineupD.x *= 1.2
            lineupE = lineupD + Vec3(0, -5250 * myteam, 0)
            lineupE.z = 20
            lineupclose = car_location.dist(lineupC) < 1500 or car_location.dist(lineupE) < 1500

        ##################################################
        ########## More Variables
        ##################################################

        if abs(car_location.y + myteam * (-5500)) > abs(ballpredict.y + myteam * (-5500)) or ballpredict.z > 2100:
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
        degreesF = (math.degrees(math.atan2((-5150 - my_car.physics.location.y)*myteam,0 - my_car.physics.location.x)))
        HdegtoGoal = degreesE + degreesF
        if HdegtoGoal > 180:
            HdegtoGoal = HdegtoGoal - 360
        if HdegtoGoal < -180:
            HdegtoGoal = HdegtoGoal + 360

        # To check horizontal degrees to the enemy goal relative to where we are facing, use HdegtoEnemyGoal
        degreesG = (math.degrees(my_car.physics.rotation.yaw) * -myteam)
        degreesH = (math.degrees(math.atan2((5150 - my_car.physics.location.y)*myteam,0 - my_car.physics.location.x)))
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

        # Bump an enemy if they are close and we are offside
        if len(enemylist) > 0:
            degtocar = degtotarget(my_car.physics.location, (math.degrees(my_car.physics.rotation.yaw) * -myteam), myteam, Vec3(packet.game_cars[closestenemytome].physics.location))
        else:
            degtocar = 0
        if len(enemylist) > 0:
            if offside is True and cardisttome < 1300 and my_car.boost > 45 and car_velocity.length() > 1000 and abs(degtocar) < 35:
                decision = "Bump"

        # Line up for a shot if the ball is on the other side of the field
        if car_location.dist(ballpredict) > 650 and ball_in_future is not None and lineupclose is False and (ballpredict.y * myteam) < 0:
            decision = "Lineup"

        # If we have an ally, and they are closest to the ball, and we are not closest to the ball, we will play defense
        if len(allylist) > 1 and closestteam == 1 and closestcar != self.index and ballpredict.y * myteam > 900 and car_location.dist(ballpredict) > 1500:
            decision = "Defend"

        # If we have an ally onside and close to the ball, and on the enemy half of the field, or the ball is in a far corner, we will play center
        if closestteam == 1 and ball_location.y * myteam < 0 and closestally != self.index:
            decision = "Center"
        if numalliesonside < 1 and ball_location.y * -myteam > 4950 and abs(ball_location.x) > 850:
            decision = "Center"

        # Check if we can detect the ball to avoid errors. Then check if the ball is lined up with the goal and we are facing the ball, then go for the ball
        if ball_in_future is not None and abs(HdegtoBall - HdegtoGoal) < 13 and abs(HdegtoBall) < 10 and (ballpredict.y * myteam) < 0:
            decision = "TakeShot"

        # Jump or aerial towards the ball
        if 10 < Vdegtotarget < 35 and flatdist > 75 and abs(Hdegtotarget) < 2 and car_location.dist(ball_location) < 4000 and car_velocity.length() > 450:
            decision = "JumpShot"

        if offside is False and car_location.dist(ball_location) < 4000 and my_car.physics.location.z > 110 and my_car.physics.location.z < target_location.z:
            decision = "Aerial"

        # If we are on the wrong side of the ball, return to our own goal
        if offside:
            decision = "OwnGoal"

        # Clear the ball out of our corner
        if ball_location.y * myteam > 4900 and abs(ball_location.x) > 1000:
            decision = "Ballchase"

        # Make an emergency save if the ball is going in
        if ball_in_future is not None and ball_going_in is True and abs(
                HdegtoBall - Hdegtogoal) > 14 and target_location.z < 200:
            decision = "EmergencySave"

        # Challenge the ball if the enemy has posession
        if ball_in_future is not None and enemydist < 600 and offside and abs(HdegtoBall - Hdegtogoal) > 20:
            decision = "EmergencySave"

        # Go for kickoff if the ball is centered
        if ball_location.x == 0 and ball_location.y == 0 and car_velocity.length() > 400 and closestally == self.index:
            decision = "Kickoff"


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

        # This will put us half way between the ball and our own goal
        if decision == "Defend":
            target_location = Vec3(ballpredict.x / 2, myteam * 2000 + (ballpredict.y / 2), 0)

        if decision == "OwnGoal":
            if car_location.x > 0:
                target_location = Vec3(1100, myteam * 4850, 0)
            else:
                target_location = Vec3(-1100, myteam * 4850, 0)

        if decision == "Lineup":
            target_location = lineupC

        if decision == "TakeShot":
            target_location = ballpredict
            if car_velocity.length() > 900:
                controls.boost = True

        if decision == "Bump":
            if len(enemylist) > 0:
                target_location = Vec3(packet.game_cars[closestenemytome].physics.location)
                controls.boost = True

        if decision == "Center":
            if ball_in_future is not None:
                target_location = Vec3(ball_in_future.physics.location)
                target_location.y += 2000 * myteam
                target_location.x *= 0.85
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

        if decision == "Kickoff":
            controls.boost = True
            if car_location.dist(ball_location) < 1100:
                self.active_sequence = Sequence([
                    ControlStep(duration=0.08, controls=SimpleControllerState(jump=True)),
                    ControlStep(duration=0.03, controls=SimpleControllerState(jump=False)),
                    ControlStep(duration=0.10, controls=SimpleControllerState(jump=True, pitch=-1)),
                    ControlStep(duration=0.50, controls=SimpleControllerState()),
                ])

        # If you added code for another decision, this is where you would write the if statement and execution
        # Remember when you use 1 = and when you use 2!


        ##################################################
        ########## Ball targeting adjustment
        ##################################################

        distanceadjustment = (1500 - clamp(car_location.dist(ballpredict), 0, 1500)) / 1350

        if decision == "Ballchase" or "TakeShot" or "Kickoff" or "JumpShot":
            if ball_in_future is not None:
                target_location.x = clamp((target_location.x * 1.17), target_location.x - (50 * distanceadjustment), target_location.x + (50 * distanceadjustment))
                target_location.y -= -65 * myteam


        ##################################################
        ########## Basic Controls
        ##################################################

        # These things are always running, regardless of our decision.

        # Steer and throttle towards our target
        controls.steer = steer_toward_target(my_car, target_location)
        controls.throttle = 1.0

        # Stop driving forwards if the ball is at a high angle above us
        if Vdegtotarget > 40 and abs(Hdegtotarget) < 40 and decision == "Ballchase":
            controls.throttle = -0.1
            controls.boost = False

        # Keep our car level
        controls.roll = clamp((my_car.physics.rotation.roll / -1),-1,1)

        # Aim our car at the ball in mid air
        controls.yaw = clamp(((((HdegtoBall * 1.5) * myteam) + (RotVelZ * -1.0)) / 20), -1, 1)

        # Point up or down at the ball when in air
        controls.pitch = clamp((((math.radians((VdegtoBall * 1.3) + 25)) - my_car.physics.rotation.pitch) * 1.3), -1, 1)

        # Level ourselves if we are falling
        if my_car.physics.velocity.z < -50:
            controls.pitch = clamp(((my_car.physics.rotation.pitch) / -2), -1, 1)

        # Flatten out when falling
        if my_car.physics.velocity.z < 0:
            controls.pitch = clamp(((my_car.physics.rotation.pitch) / -2), -1, 1)

        # Use handbrake to turn faster if going for the ball
        controls.handbrake = False

        if abs(Hdegtotarget) > 38 and car_location.dist(
                target_location) < 600 and car_velocity.length() > 700 and my_car.physics.location.z < 150 and decision == "Ballchase" and offside is True:
            controls.handbrake = True

        if abs(Hdegtotarget) > 58 and car_velocity.length() > 700 and my_car.physics.location.z < 150 and decision == "Ballchase":
            controls.handbrake = True

        # Jump off if we are on a wall and above the ball and not pointing our car up
        if my_car.physics.location.z > ballpredict.z and pointup is False:
            if abs(my_car.physics.location.y) > 5095:
                controls.jump = True
            if abs(my_car.physics.location.x) > 4075:
                controls.jump = True


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
