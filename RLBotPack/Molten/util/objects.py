import math
import numpy as np
import rlbot.utils.structures.game_data_struct as game_data_struct
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from tmcp import TMCPHandler, TMCPMessage, ActionType, TMCP_VERSION

class MoltenAgent(BaseAgent):
    def initialize_agent(self):
        #A list of cars for both teammates and opponents
        self.friends = []
        self.foes = []
        #This holds the carobject for our agent
        self.me = car_object(self.index)
        
        self.ball = ball_object()
        self.game = game_object()
        #A list of pads
        self.pads = []
        #A list of boosts
        self.boosts = []
        #goals
        self.friend_goal = goal_object(self.team)
        self.foe_goal = goal_object(not self.team)
        #A list that acts as the routines stack
        self.stack = []
        #Game time
        self.time = 0.0
        self.tick = 0
        self.update_time = -500
        self.latest_touched_time = 0
        #Whether or not GoslingAgent has run its get_ready() function
        self.ready = False
        #the controller that is returned to the framework after every tick
        self.controller = SimpleControllerState()
        #a flag that tells us when kickoff is happening
        self.kickoff = False
        #the rotation position of my bot
        self.first_pos = Vector3(0,0,0)
        self.first_moment = None
        self.rotation_index = 0
        self.plan = None
        self.old_plan = None
        self.tmcp_handler = TMCPHandler(self)
    def get_ready(self,packet):
        #Preps all of the objects that will be updated during play
        field_info = self.get_field_info()
        for i in range(field_info.num_boosts):
            boost = field_info.boost_pads[i]
            if boost.is_full_boost:
                self.boosts.append(boost_object(i,boost.location,boost.is_full_boost))
            else:
                self.pads.append(boost_object(i,boost.location,boost.is_full_boost))
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
        self.renderer.draw_line_3d(start.copy(),end.copy(),self.renderer.create_color(255,*color))
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
        for boost in self.boosts: boost.update(packet)
        for pad in self.pads: pad.update(packet)
        self.ball.update(packet)
        self.me.update(packet)
        self.game.update(packet)
        self.time = packet.game_info.seconds_elapsed
        #When a new kickoff begins we empty the stack
        if self.kickoff == False and packet.game_info.is_round_active and packet.game_info.is_kickoff_pause:
            self.stack = []
        #Tells us when to go for kickoff
        self.kickoff = packet.game_info.is_round_active and packet.game_info.is_kickoff_pause
    def get_output(self,packet):
        if self.tick < 25:
            self.tick += 1
        else:
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

            if self.plan != None and (self.old_plan == None or (self.plan != None and self.plan.action_type != self.old_plan.action_type)):
                self.tmcp_handler.send(self.plan)
                self.old_plan = self.plan
            
            self.renderer.end_rendering()
            #send our updated controller back to rlbot
            return self.controller
    def run(self):
        #override this with your strategy code
        pass

class car_object:
    #The carObject, and kin, convert the gametickpacket in something a little friendlier to use,
    #and are updated as the game runs
    def __init__(self, index, packet = None):
        self.location = Vector3(0,0,0)
        self.orientation = Matrix3(0,0,0)
        self.velocity = Vector3(0,0,0)
        self.angular_velocity = [0,0,0]
        self.hitbox = hitbox()
        self.demolished = False
        self.airborne = False
        self.supersonic = False
        self.jumped = False
        self.doublejumped = False
        self.boost = 0
        self.index = index
        self.state = None
        self.team = 0
        self.intercept = 0
        self.eta = 0
        self.ready = True
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
        self.hitbox.update(self.index, packet)
        self.demolished = car.is_demolished
        self.airborne = not car.has_wheel_contact
        self.supersonic = car.is_super_sonic
        self.jumped = car.jumped
        self.team = car.team
        self.doublejumped = car.double_jumped
        self.boost = car.boost
    def debug_next_hit(self, agent):
        agent.line(self.next_hit.location, self.location, [255,255,255])
        agent.line(self.next_hit.location - Vector3(0,0,-100), self.next_hit.location - Vector3(0,0,100), [0,255,255])
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

class hitbox:
    def __init__(self):
        self.location = Vector3.zero
        self.offset = Vector3.zero
        self.half_scale = Vector3.zero
        self.orientation = Matrix3(Vector3.zero,Vector3.zero,Vector3.zero)
    def update(self, index, packet):
        car = packet.game_cars[index]
        self.location = Vector3(car.physics.location.x, car.physics.location.y, car.physics.location.z)
        self.orientation = Matrix3(car.physics.rotation.pitch, car.physics.rotation.yaw, car.physics.rotation.roll)
        self.offset = Vector3(car.hitbox_offset.x, car.hitbox_offset.y, car.hitbox_offset.z)
        self.half_scale = Vector3(car.hitbox.length, car.hitbox.width, car.hitbox.height) / 2
    def get_nearest_point(self, point):
        local_point = self.orientation.dot(point - self.location) + self.offset

        closest_point = Vector3(
            local_point[0] if local_point[0] > -self.half_scale[0] and local_point[0] < self.half_scale[0] else -self.half_scale[0] if local_point[0] < -self.half_scale[0] else self.half_scale[0],
            local_point[1] if local_point[1] > -self.half_scale[1] and local_point[1] < self.half_scale[1] else -self.half_scale[1] if local_point[1] < -self.half_scale[1] else self.half_scale[1],
            local_point[2] if local_point[2] > -self.half_scale[2] and local_point[2] < self.half_scale[2] else -self.half_scale[2] if local_point[2] < -self.half_scale[2] else self.half_scale[2]
        )

        return closest_point.dot(self.orientation) + self.location + self.offset.dot(self.orientation)
    def get_offset(self, vector):
        offset = 500
        local_point = self.orientation.dot(vector * offset) + self.offset

        if local_point[0] < -self.half_scale[0] or local_point[0] > self.half_scale[0]:
            if self.half_scale[0] / (0.001 + abs(vector[0])) + 92.75 < offset:
                offset = self.half_scale[0] / (0.001 + abs(vector[0])) + 92.75
                local_point = self.orientation.dot(vector * offset) + self.offset
        if local_point[1] < -self.half_scale[1] or local_point[1] > self.half_scale[1]:
            if self.half_scale[1] / (0.001 + abs(vector[1])) + 92.75 < offset:
                offset = self.half_scale[1] / (0.001 + abs(vector[1])) + 92.75
                local_point = self.orientation.dot(vector * offset) + self.offset
        if local_point[2] < -self.half_scale[2] or local_point[2] > self.half_scale[2]:
            if self.half_scale[2] / (0.001 + abs(vector[2])) + 92.75 < offset:
                offset = self.half_scale[2] / (0.001 + abs(vector[2])) + 92.75
                local_point = self.orientation.dot(vector * offset) + self.offset

        return self.get_nearest_point(local_point.dot(self.orientation) + self.offset.dot(self.orientation)).magnitude() + 92.75
    def intersect_ball(self, ball_location):
        closest_point = self.get_nearest_point(ball_location)
        return (closest_point - ball_location).magnitude() < 94.41
    def render(self, agent, color):
        orient = self.orientation
        center = self.location + self.offset.dot(orient)
        hs = self.half_scale

        # bottom-right line
        agent.line(center + Vector3(hs[0],hs[1],-hs[2]).dot(orient), center + Vector3(-hs[0],hs[1],-hs[2]).dot(orient), color)
        # top-right line
        agent.line(center + Vector3(hs[0],hs[1],hs[2]).dot(orient), center + Vector3(-hs[0],hs[1],hs[2]).dot(orient), color)
        # bottom-left line
        agent.line(center + Vector3(hs[0],-hs[1],-hs[2]).dot(orient), center + Vector3(-hs[0],-hs[1],-hs[2]).dot(orient), color)
        # top-left line
        agent.line(center + Vector3(hs[0],-hs[1],hs[2]).dot(orient), center + Vector3(-hs[0],-hs[1],hs[2]).dot(orient), color)
        # bottom-front line
        agent.line(center + Vector3(hs[0],-hs[1],-hs[2]).dot(orient), center + Vector3(hs[0],hs[1],-hs[2]).dot(orient), color)
        # top-front line
        agent.line(center + Vector3(hs[0],-hs[1],hs[2]).dot(orient), center + Vector3(hs[0],hs[1],hs[2]).dot(orient), color)
        # bottom-back line
        agent.line(center + Vector3(-hs[0],-hs[1],-hs[2]).dot(orient), center + Vector3(-hs[0],hs[1],-hs[2]).dot(orient), color)
        # top-back line
        agent.line(center + Vector3(-hs[0],-hs[1],hs[2]).dot(orient), center + Vector3(-hs[0],hs[1],hs[2]).dot(orient), color)
        # front-right line
        agent.line(center + Vector3(hs[0],hs[1],hs[2]).dot(orient), center + Vector3(hs[0],hs[1],-hs[2]).dot(orient), color)
        # front-left line
        agent.line(center + Vector3(hs[0],-hs[1],hs[2]).dot(orient), center + Vector3(hs[0],-hs[1],-hs[2]).dot(orient), color)
        # back-right line
        agent.line(center + Vector3(-hs[0],hs[1],hs[2]).dot(orient), center + Vector3(-hs[0],hs[1],-hs[2]).dot(orient), color)
        # back-left line
        agent.line(center + Vector3(-hs[0],-hs[1],hs[2]).dot(orient), center + Vector3(-hs[0],-hs[1],-hs[2]).dot(orient), color)

class ball_moment:
    def __init__(self, location, velocity, time):
        self.location = location
        self.velocity = velocity
        self.time = time

class ball_object:
    def __init__(self):
        self.location = Vector3(0,0,0)
        self.velocity = Vector3(0,0,0)
        self.latest_touched_time = 0
        self.latest_touched_team = 0
        self.radius = 94.41
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
        if isinstance(pitch, float):
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
        else:
            self.data = [
                pitch,
                yaw,
                roll
            ]
            self.forward, self.left, self.up = self.data
    def __getitem__(self,key):
        return self.data[key]
    def dot(self,vector):
        return Vector3(self.forward.dot(vector),self.left.dot(vector),self.up.dot(vector))

class Vector3:
    #The Vector3 makes it easy to store positions, velocities, etc and perform vector math
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
    @property
    def zero(self):
        return Vector3(0, 0, 0)
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
    def __add__(self, value):
        if hasattr(value, "__getitem__"):
            return Vector3(self[0] + value[0], self[1] + value[1], self[2] + value[2])
        return Vector3(self[0] + value, self[1] + value, self[2] + value)
    __radd__ = __add__
    def __sub__(self, value):
        if hasattr(value, "__getitem__"):
            return Vector3(self[0] - value[0], self[1] - value[1], self[2] - value[2])
        return Vector3(self[0] - value, self[1] - value, self[2] - value)
    __rsub__ = __sub__
    def __neg__(self):
        return Vector3(-self[0], -self[1], -self[2])
    def __mul__(self, value):
        if hasattr(value, "__getitem__"):
            return Vector3(self[0] * value[0], self[1] * value[1], self[2] * value[2])
        return Vector3(self[0] * value, self[1] * value, self[2] * value)
    __rmul__ = __mul__
    def __truediv__(self, value):
        if hasattr(value, "__getitem__"):
            return Vector3(self[0] / value[0], self[1] / value[1], self[2] / value[2])
        return Vector3(self[0] / value, self[1] / value, self[2] / value)
    def __rtruediv__(self, value):
        if hasattr(value, "__getitem__"):
            return Vector3(value[0] / self[0], value[1] / self[1], value[2] / self[2])
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
    def distance(self,value):
        #returns the distance between vectors
        return (value - self).magnitude()
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
    def angle3D(self, value) -> float:
        # Returns the angle between this Vector3 and another Vector3
        return math.acos(round(self.normalize().dot(value.normalize()), 4))
    def rotate(self,angle):
        #Rotates this Vector3 by the given angle in radians
        #Note that this is only 2D, in the x and y axis
        return Vector3((math.cos(angle)*self[0]) - (math.sin(angle)*self[1]),(math.sin(angle)*self[0]) + (math.cos(angle)*self[1]),self[2])
    def anglesign(self, value):
        self_angle = math.atan(self.y/(self.x + 0.001)) if self.x >= 0 else math.atan(self.y/(self.x + 0.001)) + math.pi
        value_angle = math.atan(value.y/(value.x + 0.001)) if value.x >= 0 else math.atan(value.y/(value.x + 0.001)) + math.pi
        return value_angle - self_angle
    def flatten_by_vector(self,value):
        return Vector3(self[0]*(1-abs(value[0])), self[1]*(1-abs(value[1])), self[2]*(1-abs(value[2])))
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
    def clamp3D(self, bottom_left, top_right, return_target=False):
        #Similar to integer clamping, Vector3's clamp() forces the Vector3's direction between a start and end Vector3
        #Such that left < Vector3 < right in terms of clockwise rotation
        #Will also limit angle in the vertical direction. Such that top > Vector3 > bottom
        s = self.normalize()
        v1 = self.clamp(bottom_left.normalize(), top_right.normalize()).flatten().normalize().flatten()
        v2 = (top_right - bottom_left).flatten()
        p2 = bottom_left.flatten()
        if (v1.cross(v2).angle3D(p2.cross(v2)) == math.pi or v1.cross(v2).angle3D(p2.cross(v2)) == 0) and v1.cross(v2) != Vector3.zero:
            direction = v1 + Vector3(0, 0, self.z)
            target = direction * (p2.cross(v2).magnitude() / v1.cross(v2).magnitude())
            target.z = target.z if bottom_left.z < target.z < top_right.z else top_right.z if top_right.z < target.z else bottom_left.z

            return target.normalize(), target if return_target else target.normalize()
        else:
            right = s.dot(top_right.normalize().cross((0,0,-1))) < 0
            left = s.dot(bottom_left.normalize().cross((0,0,-1))) > 0
            if bottom_left.normalize().dot(s) < top_right.normalize().dot(s):
                return top_right.normalize(), top_right if return_target else top_right.normalize()
            return bottom_left.normalize(), bottom_left if return_target else bottom_left.normalize()