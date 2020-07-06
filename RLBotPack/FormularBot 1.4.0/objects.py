import math
import rlbot.utils.structures.game_data_struct as game_data_struct
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState

#This file holds all of the objects used in gosling utils
#Includes custom vector and matrix objects

class GoslingAgent(BaseAgent):
    #This is the main object of Gosling Utils. It holds/updates information about the game and runs routines
    #All utils rely on information being structured and accessed the same way as configured in this class
    def initialize_agent(self):
        #A list of cars for both teammates and opponents
        self.friends = []
        self.foes = []
        #This holds the carobject for our agent
        self.me = car_object(self.index)
        
        self.ball = ball_object()
        self.game = game_object()
        #A list of boosts
        self.boosts = []
        #goals
        self.friend_goal = goal_object(self.team)
        self.foe_goal = goal_object(not self.team)
        #A list that acts as the routines stack
        self.stack = []
        #Game time
        self.time = 0.0
        #Whether or not GoslingAgent has run its get_ready() function
        self.ready = False
        #the controller that is returned to the framework after every tick
        self.controller = SimpleControllerState()
        #a flag that tells us when kickoff is happening
        self.kickoff_flag = False
        
    def get_ready(self,packet):
        #Preps all of the objects that will be updated during play
        field_info = self.get_field_info()
        for i in range(field_info.num_boosts):
            boost = field_info.boost_pads[i]
            self.boosts.append(boost_object(i,boost.location,boost.is_full_boost))
        self.refresh_player_lists(packet)
        self.ball.update(packet)
        self.ready = True
    def refresh_player_lists(self,packet):
        #makes new freind/foe lists
        #Useful to keep separate from get_ready because humans can join/leave a match
        self.friends = [car_object(i,packet) for i in range(packet.num_cars) if packet.game_cars[i].team == self.team and i != self.index]
        self.foes = [car_object(i,packet) for i in range(packet.num_cars) if packet.game_cars[i].team != self.team]
    def push(self,routine):
        #Shorthand for adding a routine to the stack
        self.stack.append(routine)
    def pop(self):
        #Shorthand for removing a routine from the stack, returns the routine
        return self.stack.pop()
    def line(self,start,end,color=None):
        color = color if color != None else [255,255,255]
        self.renderer.draw_line_3d(start,end,self.renderer.create_color(255,*color))
    def debug_stack(self):
        #Draws the stack on the screen
        white = self.renderer.white()
        for i in range(len(self.stack)-1,-1,-1):
            text = self.stack[i].__class__.__name__
            self.renderer.draw_string_2d(10,50+(50*(len(self.stack)-i)),3,3,text,white)  
    def clear(self):
        #Shorthand for clearing the stack of all routines
        self.stack = []
    def preprocess(self,packet):
        #Calling the update functions for all of the objects
        if packet.num_cars != len(self.friends)+len(self.foes)+1: self.refresh_player_lists(packet)
        for car in self.friends: car.update(packet)
        for car in self.foes: car.update(packet)
        for pad in self.boosts: pad.update(packet)
        self.ball.update(packet)
        self.me.update(packet)
        self.game.update(packet)
        self.time = packet.game_info.seconds_elapsed
        #When a new kickoff begins we empty the stack
        if self.kickoff_flag == False and packet.game_info.is_round_active and packet.game_info.is_kickoff_pause:
            self.stack = []
        #Tells us when to go for kickoff
        self.kickoff_flag = packet.game_info.is_round_active and packet.game_info.is_kickoff_pause
        self.kickoff_finished = packet.game_info.is_round_active and not packet.game_info.is_kickoff_pause
    def get_output(self,packet):
        #Reset controller
        self.controller.__init__()
        #Get ready, then preprocess
        if not self.ready:
            self.get_ready(packet)
        self.preprocess(packet)
        
        self.renderer.begin_rendering()
        #Run our strategy code
        self.run()
        #run the routine on the end of the stack
        if len(self.stack) > 0:
            self.stack[-1].run(self)
        self.renderer.end_rendering()
        #send our updated controller back to rlbot
        return self.controller
    def run(self):
        #override this with your strategy code
        pass

class car_object:
    #The carObject, and kin, convert the gametickpacket in something a little friendlier to use,
    #and are updated by GoslingAgent as the game runs
    def __init__(self, index, packet = None):
        self.location = Vector3(0,0,0)
        self.orientation = Matrix3(0,0,0)
        self.velocity = Vector3(0,0,0)
        self.angular_velocity = [0,0,0]
        self.demolished = False
        self.airborne = False
        self.supersonic = False
        self.jumped = False
        self.doublejumped = False
        self.boost = 0
        self.index = index
        if packet != None:
            self.update(packet)
    def local(self,value):
        #Shorthand for self.orientation.dot(value)
        return self.orientation.dot(value)
    def update(self, packet):
        car = packet.game_cars[self.index]
        self.location.data = [car.physics.location.x, car.physics.location.y, car.physics.location.z]
        self.velocity.data = [car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z]
        self.orientation = Matrix3(car.physics.rotation.pitch, car.physics.rotation.yaw, car.physics.rotation.roll)
        self.angular_velocity = self.orientation.dot([car.physics.angular_velocity.x, car.physics.angular_velocity.y, car.physics.angular_velocity.z]).data
        self.demolished = car.is_demolished
        self.airborne = not car.has_wheel_contact
        self.supersonic = car.is_super_sonic
        self.jumped = car.jumped
        self.doublejumped = car.double_jumped
        self.boost = car.boost
    @property
    def forward(self):
        #A vector pointing forwards relative to the cars orientation. Its magnitude is 1
        return self.orientation.forward
    @property
    def left(self):
        #A vector pointing left relative to the cars orientation. Its magnitude is 1
        return self.orientation.left
    @property
    def up(self):
        #A vector pointing up relative to the cars orientation. Its magnitude is 1
        return self.orientation.up

class ball_object:
    def __init__(self):
        self.location = Vector3(0,0,0)
        self.velocity = Vector3(0,0,0)
        self.latest_touched_time = 0
        self.latest_touched_team = 0
    def update(self,packet):
        ball = packet.game_ball
        self.location.data = [ball.physics.location.x, ball.physics.location.y, ball.physics.location.z]
        self.velocity.data = [ball.physics.velocity.x, ball.physics.velocity.y, ball.physics.velocity.z]
        self.latest_touched_time = ball.latest_touch.time_seconds
        self.latest_touched_team = ball.latest_touch.team

class boost_object:
    def __init__(self,index,location,large):
        self.index = index
        self.location = Vector3(location.x,location.y,location.z)
        self.active = True
        self.large = large
    def update(self,packet):
        self.active = packet.game_boosts[self.index].is_active

class goal_object:
    #This is a simple object that creates/holds goalpost locations for a given team (for soccer on standard maps only)
    def __init__(self,team):
        team = 1 if team == 1 else -1
        self.location = Vector3(0, team * 5100, 320) #center of goal line
        #Posts are closer to x=750, but this allows the bot to be a little more accurate
        self.left_post = Vector3(team * 850, team * 5100, 320)
        self.right_post = Vector3(-team * 850, team * 5100, 320)

class game_object:
    #This object holds information about the current match
    def __init__(self):
        self.time = 0
        self.time_remaining = 0
        self.overtime = False
        self.round_active = False
        self.kickoff = False
        self.match_ended = False
    def update(self,packet):
        game = packet.game_info
        self.time = game.seconds_elapsed
        self.time_remaining = game.game_time_remaining
        self.overtime = game.is_overtime
        self.round_active = game.is_round_active
        self.kickoff = game.is_kickoff_pause
        self.match_ended = game.is_match_ended
        
class Matrix3:
    #The Matrix3's sole purpose is to convert roll, pitch, and yaw data from the gametickpaket into an orientation matrix
    #An orientation matrix contains 3 Vector3's
    #Matrix3[0] is the "forward" direction of a given car
    #Matrix3[1] is the "left" direction of a given car
    #Matrix3[2] is the "up" direction of a given car
    #If you have a distance between the car and some object, ie ball.location - car.location,
    #you can convert that to local coordinates by dotting it with this matrix
    #ie: local_ball_location = Matrix3.dot(ball.location - car.location)
    def __init__(self,pitch,yaw,roll): 
        CP = math.cos(pitch)
        SP = math.sin(pitch)
        CY = math.cos(yaw)
        SY = math.sin(yaw)
        CR = math.cos(roll)
        SR = math.sin(roll)
        #List of 3 vectors, each descriping the direction of an axis: Forward, Left, and Up
        self.data = [
            Vector3(CP*CY, CP*SY, SP),
            Vector3(CY*SP*SR-CR*SY,SY*SP*SR+CR*CY, -CP*SR),
            Vector3(-CR*CY*SP-SR*SY, -CR*SY*SP+SR*CY, CP*CR)]
        self.forward, self.left, self.up = self.data
    def __getitem__(self,key):
        return self.data[key]
    def dot(self,vector):
        return Vector3(self.forward.dot(vector),self.left.dot(vector),self.up.dot(vector))

class Vector3:
    #This is the backbone of Gosling Utils. The Vector3 makes it easy to store positions, velocities, etc and perform vector math
    #A Vector3 can be created with:
    # - Anything that has a __getitem__ (lists, tuples, Vector3's, etc)
    # - 3 numbers
    # - A gametickpacket vector
    def __init__(self, *args):
        if hasattr(args[0],"__getitem__"):
            self.data = list(args[0])
        elif isinstance(args[0], game_data_struct.Vector3):
            self.data = [args[0].x, args[0].y, args[0].z]
        elif isinstance(args[0],game_data_struct.Rotator):
            self.data = [args[0].pitch, args[0].yaw, args[0].roll]
        elif len(args) == 3:
            self.data = list(args)
        else:
            raise TypeError("Vector3 unable to accept %s"%(args))
    #Property functions allow you to use `Vector3.x` vs `Vector3[0]`
    @property
    def x(self):
        return self.data[0]
    @x.setter
    def x(self,value):
        self.data[0] = value
    @property
    def y(self):
        return self.data[1]
    @y.setter
    def y(self,value):
        self.data[1] = value
    @property
    def z(self):
        return self.data[2]
    @z.setter
    def z(self,value):
        self.data[2] = value
    def __getitem__(self,key):
        #To access a single value in a Vector3, treat it like a list
        # ie: to get the first (x) value use: Vector3[0]
        #The same works for setting values
        return self.data[key]
    def __setitem__(self,key,value):
        self.data[key] = value
    def __str__(self):
        #Vector3's can be printed to console
        return str(self.data)
    __repr__ = __str__
    def __eq__(self,value):
        #Vector3's can be compared with:
        # - Another Vector3, in which case True will be returned if they have the same values
        # - A list, in which case True will be returned if they have the same values
        # - A single value, in which case True will be returned if the Vector's length matches the value
        if isinstance(value,Vector3):
            return self.data == value.data
        elif isinstance(value,list):
            return self.data == value
        else:
            return self.magnitude() == value
    #Vector3's support most operators (+-*/)
    #If using an operator with another Vector3, each dimension will be independent
    #ie x+x, y+y, z+z
    #If using an operator with only a value, each dimension will be affected by that value
    #ie x+v, y+v, z+v
    def __add__(self,value):
        if isinstance(value,Vector3):
            return Vector3(self[0]+value[0], self[1]+value[1], self[2]+value[2])
        return Vector3(self[0]+value, self[1]+value, self[2]+value)
    __radd__ = __add__
    def __sub__(self,value):
        if isinstance(value,Vector3):
            return Vector3(self[0]-value[0],self[1]-value[1],self[2]-value[2])
        return Vector3(self[0]-value,self[1]-value,self[2]-value)
    __rsub__ = __sub__
    def __neg__(self):
        return Vector3(-self[0],-self[1],-self[2])
    def __mul__(self,value):
        if isinstance(value,Vector3):
            return Vector3(self[0]*value[0], self[1]*value[1], self[2]*value[2])            
        return Vector3(self[0]*value, self[1]*value, self[2]*value)
    __rmul__ = __mul__
    def __truediv__(self,value):
        if isinstance(value,Vector3):
            return Vector3(self[0]/value[0], self[1]/value[1], self[2]/value[2])
        return Vector3(self[0]/value, self[1]/value, self[2]/value)
    def __rtruediv__(self,value):
        if isinstance(value,Vector3):
            return Vector3(value[0]/self[0],value[1]/self[1],value[2]/self[2])
        raise TypeError("unsupported rtruediv operands")
    def magnitude(self):
        #Magnitude() returns the length of the vector
        return math.sqrt((self[0]*self[0]) + (self[1] * self[1]) + (self[2]* self[2]))
    def normalize(self,return_magnitude=False):
        #Normalize() returns a Vector3 that shares the same direction but has a length of 1.0
        #Normalize(True) can also be used if you'd like the length of this Vector3 (used for optimization)
        magnitude = self.magnitude()
        if magnitude != 0:
            if return_magnitude:
                return Vector3(self[0]/magnitude, self[1]/magnitude, self[2]/magnitude),magnitude
            return Vector3(self[0]/magnitude, self[1]/magnitude, self[2]/magnitude)
        if return_magnitude:
            return Vector3(0,0,0),0
        return Vector3(0,0,0)
    #Linear algebra functions
    def dot(self,value):
        return self[0]*value[0] + self[1]*value[1] + self[2]*value[2]
    def cross(self,value):
        return Vector3((self[1]*value[2]) - (self[2]*value[1]),(self[2]*value[0]) - (self[0]*value[2]),(self[0]*value[1]) - (self[1]*value[0]))
    def flatten(self):
        #Sets Z (Vector3[2]) to 0
        return Vector3(self[0],self[1],0)
    def render(self):
        #Returns a list with the x and y values, to be used with pygame
        return [self[0],self[1]]
    def copy(self):
        #Returns a copy of this Vector3
        return Vector3(self.data[:])
    def angle(self,value):
        #Returns the angle between this Vector3 and another Vector3
        return math.acos(round(self.flatten().normalize().dot(value.flatten().normalize()),4))
    def angle3D(self,value):
        #Returns the angle between this Vector3 and another Vector3
        return math.acos(round(self.normalize().dot(value.flatten().normalize()),4))
    def rotate(self,angle):
        #Rotates this Vector3 by the given angle in radians
        #Note that this is only 2D, in the x and y axis
        return Vector3((math.cos(angle)*self[0]) - (math.sin(angle)*self[1]),(math.sin(angle)*self[0]) + (math.cos(angle)*self[1]),self[2])
    def clamp(self,start,end):
        #Similar to integer clamping, Vector3's clamp() forces the Vector3's direction between a start and end Vector3
        #Such that Start < Vector3 < End in terms of clockwise rotation
        #Note that this is only 2D, in the x and y axis
        s = self.normalize()
        right = s.dot(end.cross((0,0,-1))) < 0
        left = s.dot(start.cross((0,0,-1))) > 0
        if (right and left) if end.dot(start.cross((0,0,-1))) > 0 else (right or left):
            return self
        if start.dot(s) < end.dot(s):
            return end
        return start
