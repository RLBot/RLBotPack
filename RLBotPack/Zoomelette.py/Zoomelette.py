import math

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

class Vector3:
    def __init__(self,a,b,c):
        self.data = [a,b,c]
    def __getitem__(self,key):
        return self.data[key]
    def __str__(self):
        return str(self.data)
    def __add__(self,value):
        return Vector3(self[0]+value[0], self[1]+value[1], self[2]+value[2])
    def __sub__(self,value):
        return Vector3(self[0]-value[0],self[1]-value[1],self[2]-value[2])
    def __mul__(self,value):
        return Vector3(self[0]*value, self[1]*value, self[2]*value)
    __rmul__ = __mul__
    def __div__(self,value):
        return Vector3(self[0]/value, self[1]/value, self[2]/value)
    def magnitude(self):
        return math.sqrt((self[0]*self[0]) + (self[1] * self[1]) + (self[2]* self[2]))
    def normalize(self):
        mag = self.magnitude()
        if mag != 0:
            return Vector3(self[0]/mag, self[1]/mag, self[2]/mag)
        else:
            return Vector3(0,0,0)
    def dot(self,value):
        return self[0]*value[0] + self[1]*value[1] + self[2]*value[2]
    def cross(self,value):
        return Vector3((self[1]*value[2]) - (self[2]*value[1]),(self[2]*value[0]) - (self[0]*value[2]),(self[0]*value[1]) - (self[1]*value[0]))
    def flatten(self):
        return Vector3(self[0],self[1],0)

class carobject:
    def __init__(self):
        self.loc = Vector3(0,0,0)
        self.vel = Vector3(0,0,0)
        self.rot = Vector3(0,0,0)
        self.Rotvel = Vector3(0,0,0)
        self.matrix = Matrix3D(self.rot)
        self.goals = 0
        self.saves = 0
        self.name = ""
        self.jumped = False
        self.doublejumped = False
        self.team = 0
        self.boostAmount = 0
        self.wheelcontact = False
        self.supersonic = False

    def update(self,TempVar):
        self.loc.data = [TempVar.physics.location.x,TempVar.physics.location.y,TempVar.physics.location.z]
        self.vel.data = [TempVar.physics.velocity.x,TempVar.physics.velocity.y,TempVar.physics.velocity.z]
        self.rot.data = [TempVar.physics.rotation.pitch,TempVar.physics.rotation.yaw,TempVar.physics.rotation.roll]
        self.matrix = Matrix3D(self.rot)
        TempRot = Vector3(TempVar.physics.angular_velocity.x,TempVar.physics.angular_velocity.y,TempVar.physics.angular_velocity.z)
        self.Rotvel = self.matrix.dot(TempRot)
        self.goals = TempVar.score_info.goals
        self.saves = TempVar.score_info.saves
        self.name = TempVar.name
        self.jumped = TempVar.jumped
        self.doublejumped = TempVar.double_jumped
        self.team = TempVar.team
        self.boostAmount = TempVar.boost
        self.wheelcontact = TempVar.has_wheel_contact
        self.supersonic = TempVar.is_super_sonic
    
class Matrix3D:
    def __init__(self,r):
        CR = math.cos(r[2])
        SR = math.sin(r[2])
        CP = math.cos(r[0])
        SP = math.sin(r[0])
        CY = math.cos(r[1])
        SY = math.sin(r[1])        
        self.data = [Vector3(CP*CY, CP*SY, SP),Vector3(CY*SP*SR-CR*SY, SY*SP*SR+CR*CY, -CP * SR),Vector3(-CR*CY*SP-SR*SY, -CR*SY*SP+SR*CY, CP*CR)]

    def dot(self,vector):
        return Vector3(self.data[0].dot(vector),self.data[1].dot(vector),self.data[2].dot(vector))

class ballobject:
    def __init__(self):
        self.loc = Vector3(0,0,0)
        self.vel = Vector3(0,0,0)
        self.rot = Vector3(0,0,0)
        self.Rotvel = Vector3(0,0,0)

    def update(self,TempVar):
        self.loc.data = [TempVar.physics.location.x,TempVar.physics.location.y,TempVar.physics.location.z]
        self.vel.data = [TempVar.physics.velocity.x,TempVar.physics.velocity.y,TempVar.physics.velocity.z]
        self.rot.data = [TempVar.physics.rotation.pitch,TempVar.physics.rotation.yaw,TempVar.physics.rotation.roll]
        self.Rotvel.data = [TempVar.physics.angular_velocity.x,TempVar.physics.angular_velocity.y,TempVar.physics.angular_velocity.z]


class Zoomelette(BaseAgent):
    def initialize_agent(self):
        self.controller_state = SimpleControllerState()
        self.car = carobject()
        self.ball = ballobject()

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        self.preprocess(packet)

        self.renderer.begin_rendering()
        self.renderer.draw_line_3d(self.ball.loc, self.ball.loc + ((self.ball.loc - Vector3(0, -5150 * side(self.team),0)).normalize() * ((self.car.loc - self.ball.loc).magnitude() / 2)),self.renderer.black())
        self.renderer.draw_rect_3d(Vector3(0,0,10) + self.ball.loc + ((self.ball.loc - Vector3(0, -5150 * side(self.team),0)).normalize() * ((self.car.loc - self.ball.loc).magnitude() / 2)), 10, 10, True, self.renderer.red())
        self.renderer.draw_line_3d(self.car.loc, self.ball.loc + ((self.ball.loc - Vector3(0, -5150 * side(self.team),0)).normalize() * ((self.car.loc - self.ball.loc).magnitude() / 2)), self.renderer.black())
        self.renderer.end_rendering()

        return self.Brain()

    def preprocess(self, gamepacket):
        self.car.update(gamepacket.game_cars[self.index])
        self.ball.update(gamepacket.game_ball)
    
    def Brain(self):
        if self.ball.loc[1]==0:
            print("KickOff")
            return KickOff(self)
        elif (self.ball.loc-self.car.loc)[1] * side(self.team) > 0:
            print("Recovery")
            return Recovery(self)
        else:
            print("Shooting")
            return Shooting(self)

    
def KickOff(agent):
    target = agent.ball.loc
    speed = 2300
    return Controller_output(agent,target,speed)

def Recovery(agent):
    target = Vector3(0,5150*side(agent.team),0)
    speed = 2300
    return Controller_output(agent,target,speed)

def Shooting(agent):
    target = agent.ball.loc + ((agent.ball.loc - Vector3(0, -5150 * side(agent.team),0)).normalize() * ((agent.car.loc - agent.ball.loc).magnitude() / 2))
    speed = 2300
    return Controller_output(agent,target,speed)

def Controller_output(agent,target,speed):
    Controller = SimpleControllerState()
    LocalTagret = agent.car.matrix.dot(target-agent.car.loc)
    angle_target = math.atan2(LocalTagret[1],LocalTagret[0])
    Controller.steer = steer(angle_target)
    agentSpeed = velocity2D(agent.car)
    Controller.throttle,Controller.boost = throttle(speed,agentSpeed)
    if abs(angle_target) > 2:
        Controller.handbrake = True
    else:
        Controller.handbrake = False
    return Controller

def side(x):
    if x <= 0:
        return -1
    return 1

def cap(x, low, high):
    if x < low:
        return low
    elif x > high:
        return high
    else:
        return x
    
def steer(angle):
    final = ((35 * angle)**3) / 20
    return cap(final,-1,1)

def velocity2D(target_object):
    return math.sqrt(target_object.vel[0]**2 + target_object.vel[1]**2)

def throttle(speed, agent_speed):
    final = ((speed - agent_speed)/100)
    if final > 1:
        boost = True
    else:
        boost = False
    if final > 0 and speed > 1400:
        final = 1
    return cap(final,-1,1),boost


        
