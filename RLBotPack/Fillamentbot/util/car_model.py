from util.vec import Vec3
from util.orientation import Orientation

class Car:
    #This is to keep track of physics and attributes of each car
    __slots__ = [
        'location',
        'velocity',
        'rotation',
        'angular_velocity',
        'orientation',
        'yaw_velocity',
        'pitch_velocity',
        'roll_velocity',
        'grounded',
        'supersonic',
        'team',
        'vec_to_ball',
        'boost',
        'last_unstable',
        'stable',
        'on_wall',
        'assumed_maneuver',
        'index'
    ]

    #create the car
    def __init__(self, index: int, packet):
        self.index=index
        self.last_unstable=packet.game_info.seconds_elapsed
        self.stable=False
        self.update(packet)

    #updates the info
    def update(self, packet):
        self.location = Vec3(packet.game_cars[self.index].physics.location)
        self.velocity = Vec3(packet.game_cars[self.index].physics.velocity)
        self.rotation = packet.game_cars[self.index].physics.rotation
        self.angular_velocity = Vec3(packet.game_cars[self.index].physics.angular_velocity)
        self.orientation = Orientation(self.rotation)
        self.yaw_velocity = self.orientation.up.dot(self.angular_velocity)
        self.pitch_velocity = self.orientation.right.dot(self.angular_velocity)
        self.roll_velocity = self.orientation.forward.dot(self.angular_velocity)
        self.grounded = packet.game_cars[self.index].has_wheel_contact
        self.supersonic = packet.game_cars[self.index].is_super_sonic
        self.team = packet.game_cars[self.index].team
        self.vec_to_ball = Vec3(packet.game_ball.physics.location) - self.location
        self.boost = packet.game_cars[self.index].boost

        #deal with instability of velocity-facing deficiet or jumping
        if self.velocity.length() != 0:
            if self.velocity.ang_to(self.orientation.forward)>0.2 or not self.grounded:
                self.last_unstable=packet.game_info.seconds_elapsed
                self.stable = False
            elif packet.game_info.seconds_elapsed - self.last_unstable > 0.2:
                self.stable = True

        #logic for on_wall
        self.on_wall = self.grounded and self.orientation.up.z<0.1

        #logic for guessing what they are doing, out of BALL, ROTATE, SUPPORT
        self.assumed_maneuver = None
        if -2< self.velocity.flat().signed_ang_to(self.vec_to_ball) <-0.3 and self.yaw_velocity <0 or 0.3< self.velocity.flat().signed_ang_to(self.vec_to_ball) <2 and self.yaw_velocity >0 or -0.3<self.velocity.flat().signed_ang_to(self.vec_to_ball)<0.3:
            self.assumed_maneuver = "BALL"
        if self.location.y > packet.game_ball.physics.location.y+100 and self.team==0 or self.location.y < packet.game_ball.physics.location.y-100 and self.team==1 :
            self.assumed_maneuver = "OFFSIDE"
        if self.velocity.length()!=0:
            if self.velocity.normalized().y <-0.8 and self.team ==0 or self.velocity.normalized().y >0.8 and self.team ==1:
                self.assumed_maneuver = "ROTATE"
        if self.assumed_maneuver is None:
            self.assumed_maneuver = "SUPPORT"
            
    def unstable_for(self,packet,time):
        self.last_unstable=packet.game_info.seconds_elapsed+time
        self.stable = False


class Ball:
    __slots__ = [
        'velocity',
        'rotation',
        'location',
        'angular_velocity'
    ]

    def __init__(self,packet):
        self.update(packet)

    def update(self,packet):
        self.velocity = Vec3(packet.game_ball.physics.velocity)
        self.rotation = packet.game_ball.physics.rotation
        self.location = Vec3(packet.game_ball.physics.location)
        self.angular_velocity = Vec3(packet.game_ball.physics.angular_velocity)
