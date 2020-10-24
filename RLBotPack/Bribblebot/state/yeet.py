from rlbot.agents.base_agent import BaseAgent
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.structures.quick_chats import QuickChats

from util.orientation import Orientation
from util.vec import Vec3
import util.const

from state.state import State
import math



class Yeet(State):
    def __init__(self, agent: BaseAgent): 
        super().__init__(agent)
        self.agent.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Custom_Exclamation_Yeet)
        self.startTick = 0
        self.state = 0
        self.lastBallHit = 0
        self.alpha = -1
        self.beta = 1


    def tick(self, packet: GameTickPacket) -> bool:


        if self.state == 3:
            return False


        myCar = packet.game_cars[self.agent.index]
        carDirection = -myCar.physics.rotation.yaw
        carLocation = Vec3(myCar.physics.location)
        ballLocation = Vec3(packet.game_ball.physics.location)
        ballVelocity = Vec3(packet.game_ball.physics.velocity)
        ballToCarAbsoluteLocation = (ballLocation - carLocation)
        ballToCarLocation = ballToCarAbsoluteLocation.rotate_2D(carDirection)
        ballToCarDistance = ballToCarLocation.length()
        ballToCarLocation = ballToCarLocation.flat()
        ballRelativeCarLocation = Vec3(ballToCarLocation.x * .5 / 118.01, ballToCarLocation.y * .5 / 84.2, 0)
        dodgeDirectionMaxOumpf = ballToCarLocation.normalized()
        dodgeDirectionMaxOumpf /= max(abs(dodgeDirectionMaxOumpf.x), abs(dodgeDirectionMaxOumpf.y))

        
        teamDirection = 1 if packet.game_cars[self.agent.index].team == 0 else -1
        dodgeAbsoluteDirectionMaxAim = ballLocation - Vec3(0, 5120 * teamDirection, min(893 - 100 - 50, -ballVelocity.x))
        dodgeDirectionMaxAim = dodgeAbsoluteDirectionMaxAim.flat().rotate_2D(carDirection).normalized()
        dodgeDirectionMaxAim /= max(abs(dodgeDirectionMaxAim.x), abs(dodgeDirectionMaxAim.y))
        #print(f"{round(dodgeDirectionMaxAim.x, 2)}\t{round(dodgeDirectionMaxAim.y, 2)}")

        if self.alpha == -1:
            ballXAtGoal = abs(ballLocation.x + (5120 - ballLocation.y*teamDirection) / max(1, ballVelocity.y) * ballVelocity.x) - (893 - 100 - 50)
            if ballXAtGoal < 0:
                self.alpha = min(1, (ballVelocity.length() - 2 * ballXAtGoal) / 2000)
                #print(f"alpha is {self.alpha}")
            else:
                #print("the shot is shit")
                self.alpha = 0


        if self.startTick == 0:
            self.startTick = self.agent.tick
        ticksElapsed = self.agent.tick - self.startTick
            

        minJumpTick = 7
        maxJumpTick = 80
        newHit = self.lastBallHit != packet.game_ball.latest_touch.time_seconds
        if self.state == 0:
            if ticksElapsed >= minJumpTick and (ticksElapsed >= maxJumpTick or newHit or ballRelativeCarLocation.length() > .75 or ballLocation.z - carLocation.z < 110):
                self.state = 1
            else:
                if ticksElapsed < minJumpTick:
                    self.lastBallHit = packet.game_ball.latest_touch.time_seconds
                self.controller.jump = True
        
        if self.state == 1:
                if self.controller.jump: # set it to false for one input frame
                    self.controller.jump = False
                else:
                    self.state = 2
        if self.state == 2:
                self.state = 3
                if ballRelativeCarLocation.length() < .3:
                    #print("the ball is too close to the center so a whack shot will be too whack")
                    self.alpha = 0
                elif ballToCarDistance > 160:
                    #print("im too far from the ball")
                    self.beta = -1 # this inverts the direction making the dodge towards the ball instead of trying to flick it
                    self.alpha *= max(0, 1 - (160 - ballToCarDistance) / 50)
                    

                self.controller.roll = -(self.beta * dodgeDirectionMaxOumpf.y if self.alpha > 0.5 else dodgeDirectionMaxAim.y)
                self.controller.jump = True

                

        pitch = self.alpha * self.beta * dodgeDirectionMaxOumpf.x + (1 - self.alpha) * dodgeDirectionMaxAim.x
        if abs(pitch) > 0.5:
            pitch = math.copysign(1, pitch)
        else:
            pitch = 0
        self.controller.pitch = pitch
        self.controller.throttle = 1

        #print(f"{ticksElapsed}\t{self.state}\t{newHit}\t{round(ballRelativeCarLocation.length(), 2)}\t{round(ballLocation.z - carLocation.z)}\t{round(ballToCarLocation.length())}\t{round(ballToCarDistance)}")
        return True
