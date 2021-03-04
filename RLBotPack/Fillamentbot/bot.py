#stuff on aerials: https://samuelpmish.github.io/notes/RocketLeague/aerial_control/, https://youtu.be/SmIuaXpSgBQ
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState, BoostState

from util.ball_prediction_analysis import find_slice_at_time, find_slices_around_time
from util.boost_pad_tracker import BoostPadTracker
from util.sequence import Sequence, ControlStep
from util.orientation import Orientation, relative_location
from util.vec import Vec3
from util.car_model import Car, Ball
from util.strike import find_strikes, execute_strike, check_strike, Strike, strike_types
from util.mechanics import *

import math
from random import randint


class MyBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()
        self.controls = SimpleControllerState()
        self.bot_car = None
        self.ball = None
        self.allies=[]
        self.foes=[]
        self.ball_prediction = None
        self.posts=((Vec3(893,-5120,0),Vec3(-893,-5120,0)),(Vec3(893,5120,0),Vec3(-893,5120,0)))
        self.back_corners=((Vec3(3672,-4096,0),Vec3(-3672,-4096,0)),(Vec3(3672,4096,0),Vec3(-3672,4096,0)))
        self.collision_posts=((Vec3(843,-5070,0),Vec3(-843,-5070,0)),(Vec3(843,5070,0),Vec3(-843,5070,0)))
        self.goal_corners=((Vec3(-893,-6000,0),Vec3(893,-5120,642.775)),(Vec3(-893,5120,0),Vec3(893,6000,642.775)))
        self.boxes=((Vec3(-1600,-6000,0),Vec3(1600,-4120,2044)),(Vec3(-1600,4120,0),Vec3(1600,6000,2044))) 

        self.defending = False
        self.rotating = False
        self.supporting = 0
        self.clearing = False
        self.shooting = False
        self.air_recovery = False
        self.current_strike = None

    def initialize_agent(self):
        # Set up information about the boost pads now that the game is active and the info is available
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        

        """ Keep our boost pad info updated with which pads are currently active"""
        self.boost_pad_tracker.update_boost_status(packet)

        
        """Update cars and ball"""
        #ball
        if self.ball is None:
            self.ball = Ball(packet)
        else:
            self.ball.update(packet)

        self.ball_prediction = self.get_ball_prediction_struct()
        #draw 3 sec of path
        self.renderer.draw_polyline_3d([Vec3(ball_slice.physics.location) for ball_slice in self.ball_prediction.slices[:180:5]],self.renderer.yellow())

        #self
        if self.bot_car is None:
            self.bot_car = Car(self.index,packet)
        elif self.bot_car.index != self.index:
            self.bot_car = Car(self.index,packet)
        else:
            self.bot_car.update(packet)

        #check if number of players has changed, and reset allies and foes if it has
        if len(self.allies)+len(self.foes)+1!=len(packet.game_cars):
            self.allies,self.foes = [],[]

        #allies
        if len(self.allies)==0:
            for index in range(packet.num_cars):
                if packet.game_cars[index].team==self.bot_car.team and index!=self.bot_car.index:
                    self.allies.append(Car(index,packet))
        else:
            for car in self.allies:
                car.update(packet)
        

        #foes
        if len(self.foes)==0:
            for index in range(packet.num_cars):
                if packet.game_cars[index].team!=self.bot_car.team:
                    self.foes.append(Car(index,packet))
        else:
            for car in self.foes:
                car.update(packet)

        """Continue and active sequences"""
        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls
        self.controls = SimpleControllerState()


        
        """put cars in positions (for testing) (set air recovery atm)
        if self.bot_car.grounded and self.bot_car.team==0:
            car_state0= CarState(boost_amount=45, physics=Physics(velocity=Vector3(x=randint(-1000,1000),y=randint(-1000,1000),z=randint(-1000,1000)),location=Vector3(x=0,y=-2608,z=1000),rotation=Rotator(randint(-300,300)/100,randint(-300,300)/100,randint(-300,300)/100),angular_velocity=Vector3(randint(-300,300)/100,randint(-300,300)/100,randint(-300,300)/100)))
            car_state1= CarState(boost_amount=45, physics=Physics(velocity=Vector3(x=randint(-1000,1000),y=randint(-1000,1000),z=randint(-1000,1000)),location=Vector3(x=0,y=2608,z=1000),rotation=Rotator(randint(-300,300)/100,randint(-300,300)/100,randint(-300,300)/100),angular_velocity=Vector3(randint(-300,300)/100,randint(-300,300)/100,randint(-300,300)/100)))
            if self.bot_car.index!=self.bot_car.team:
                car_state0,car_state1=car_state1,car_state0
            ball_state= BallState(Physics(velocity=Vector3(x=0,y=0,z=0),location=Vector3(x=0,y=0,z=92.75),rotation=Rotator(0,0,0),angular_velocity=Vector3(0,0,0)))

            self.set_game_state(GameState(ball=ball_state,cars={0:car_state0,1:car_state1}))
        """
        
        """draw in info for blocking testing
        self.renderer.draw_string_2d(20,20,3,3, f"z: {self.bot_car.location.z}", self.renderer.white())

        if self.bot_car.stable:
            return self.long_jump(packet)
        else:
            return SimpleControllerState()
        """

        """kickoff        NOTE: the diagonal flips need to be more sideways than forward when updating for the diagonal and long"""
        if self.ball.location.flat().length()<1 and self.ball.velocity.flat().length()<1 and packet.game_info.is_kickoff_pause:
            ally_on_short = False
            for ally in self.allies:
                if Vec3(-2048,-2560,0).dist(ally.location)<50 or Vec3(-2048,2560,0).dist(ally.location)<50 or Vec3(2048,-2560,0).dist(ally.location)<50 or Vec3(2048,2560,0).dist(ally.location)<50:
                    ally_on_short = True
            if self.bot_car.location.flat().dist(Vec3(-2048,-2560,0))<50 or self.bot_car.location.flat().dist(Vec3(2048,2560,0))<50:
                self.active_sequence, first_frame = right_diagonal(packet)
                return first_frame
            elif self.bot_car.location.flat().dist(Vec3(2048,-2560,0))<50 or self.bot_car.location.flat().dist(Vec3(-2048,2560,0))<50:
                self.active_sequence, first_frame = left_diagonal(packet)
                return first_frame
            elif (self.bot_car.location.flat().dist(Vec3(-256,-3840))<50 or self.bot_car.location.flat().dist(Vec3(256,3840,0))<50) and not ally_on_short:
                self.active_sequence, first_frame = long_right(packet)
                return first_frame
            elif (self.bot_car.location.flat().dist(Vec3(256,-3840,0))<50 or self.bot_car.location.flat().dist(Vec3(-256,3840,0))<50) and not ally_on_short:
                self.active_sequence, first_frame = long_left(packet)
                return first_frame
            elif (self.bot_car.location.flat().dist(Vec3(0,-4608,0))<50 or self.bot_car.location.flat().dist(Vec3(0,4608,0))<50) and len(self.allies)==0:
                self.active_sequence, first_frame = back_kick(packet)
                return first_frame
            else:
               self.active_sequence, first_frame = kickoff_idle(packet)
               return first_frame

       
        """defend check"""
        if self.ball.velocity.flat().length()!=0:
            post0_ang = self.posts[self.bot_car.team][0].__sub__(self.ball.location).flat().ang_to(Vec3(1,0,0))
            ball_vel_ang = self.ball.velocity.flat().ang_to(Vec3(1,0,0))
            post1_ang = self.posts[self.bot_car.team][1].__sub__(self.ball.location).flat().ang_to(Vec3(1,0,0))
            between_posts = post0_ang < ball_vel_ang < post1_ang
            moving_at_posts = self.ball.velocity.y<0 and self.ball.location.y<4000 if self.bot_car.team==0 else self.ball.velocity.y>0 and self.ball.location.y>-4000
        
            self.defending = True if between_posts and moving_at_posts else False
        
        """rotate check"""
        if self.rotating:
            #check for reasons to stop
            far_enough_behind_ball = self.bot_car.location.y-self.ball.location.y<-4000 if self.bot_car.team==0 else self.bot_car.location.y-self.ball.location.y>4000
            about_to_hit_backwall =  self.bot_car.location.y <-4100 if self.bot_car.team==0 else self.bot_car.location.y >4100
            dunk_on_box = self.ball.location.within(self.boxes[(self.bot_car.team+1)%2][0],self.boxes[(self.bot_car.team+1)%2][1]) and min([foe.vec_to_ball.length() for foe in self.foes])>1000 and len(self.allies)==0
            
            self.rotating = not( far_enough_behind_ball or about_to_hit_backwall or dunk_on_box )
        else:
            #check for reasons to start
            wrong_side_of_ball_and_not_deep = self.bot_car.location.y-self.ball.location.y>0 and self.bot_car.location.y >-4000 if self.bot_car.team==0 else self.bot_car.location.y-self.ball.location.y<0 and self.bot_car.location.y <4000
            
            vec_to_goal = Vec3(0, 5200*(self.bot_car.team*2-1),0) - self.bot_car.location
            ball_to_goal = Vec3(0, 5200*(self.bot_car.team*2-1),0) - self.ball.location
            unproductive_to_keep_chasing = vec_to_goal.length() < ball_to_goal.length()

            self.rotating = wrong_side_of_ball_and_not_deep

        """support check"""
        self.supporting=0
        try:
            if self.bot_car.orientation.forward.ang_to(self.bot_car.vec_to_ball)<1.5 and (self.bot_car.team ==0 and self.bot_car.velocity.normalized().y>-0.7 or self.bot_car.team ==1 and self.bot_car.velocity.normalized().y<0.7):
                #self in a position to look to go
                for ally in self.allies:
                    if ally.orientation.forward.ang_to(ally.vec_to_ball)<1.5 and (ally.team ==0 and ally.velocity.normalized().y>-0.7 or ally.team ==1 and ally.velocity.normalized().y<0.7) and (ally.assumed_maneuver =="BALL" or ally.assumed_maneuver =="SUPPORT"):
                        if ally.vec_to_ball.length() < self.bot_car.vec_to_ball.length():
                            self.supporting += 1
            else:
                #self in a position to look to go, allowing an extra 500 for bots that are facing ball
                for ally in self.allies:
                    if ally.orientation.forward.ang_to(ally.vec_to_ball)<1.5 and (ally.team ==0 and ally.velocity.normalized().y>-0.7 or ally.team ==1 and ally.velocity.normalized().y<0.7) and (ally.assumed_maneuver =="BALL" or ally.assumed_maneuver =="SUPPORT"):
                        if ally.vec_to_ball.length() < self.bot_car.vec_to_ball.length():
                            self.supporting += 1
                    else:
                        if ally.vec_to_ball.length() < self.bot_car.vec_to_ball.length()+500:
                            self.supporting += 1

        except:
            stub="don't want to manually catch div 0"

        if self.ball.location.within(self.boxes[0][0],self.boxes[0][1]) or self.ball.location.within(self.boxes[1][0],self.boxes[1][1]):
            #box panic and dunk, both in one
            self.supporting = max(0,self.supporting-1)

        #draw in boxes
        for xy in [(-1600,4140),(-1600,-4140),(1600,4140),(1600,-4140)]:
                self.renderer.draw_line_3d(Vec3(xy[0],xy[1],0), Vec3(xy[0],xy[1],2000), self.renderer.red())

        """clear check"""
        in_half = self.ball.location.y < -2000 if self.bot_car.team==0 else self.ball.location.y > 2000
        self.clearing = in_half

        """shoot check"""
        self.shooting=True

        """air recovery check"""
        if self.current_strike is None:
            self.air_recovery = not self.bot_car.grounded and self.bot_car.location.z>100
        else:
            self.air_recovery = not self.bot_car.grounded and self.current_strike.strike_type != "will add the aerial strike code later" and self.bot_car.location.z>100

        """if ball threatening net but not on target overide"""
        if self.supporting ==0 and self.ball.location.y*math.copysign(1,self.bot_car.team*2-1)>3000:
            self.defending = True

        """defending, but third override"""
        if self.supporting==2 and self.defending:
            self.defending==False

        
        #dribble code is just linear target code with no offset and a little bit of turning
        
        if self.air_recovery:
            self.perform_air_recovery(packet)
            self.renderer.draw_string_3d(self.bot_car.location, 1, 1, f'AIR RECOVERY', self.renderer.white())
        elif self.defending:
            self.defend(packet)
            self.renderer.draw_string_3d(self.bot_car.location, 1, 1, f'DEFENDING', self.renderer.white())
        elif self.rotating:
            self.rotate(packet)
            self.renderer.draw_string_3d(self.bot_car.location, 1, 1, f'ROTATING', self.renderer.white())
        elif self.supporting>0:
            self.support(packet,self.supporting)
            self.renderer.draw_string_3d(self.bot_car.location, 1, 1, f'SUPPORTING', self.renderer.white())
        elif self.clearing:
            self.clear(packet)
            self.renderer.draw_string_3d(self.bot_car.location, 1, 1, f'CLEARING', self.renderer.white())
        elif self.shooting:
            self.shoot(packet)
            self.renderer.draw_string_3d(self.bot_car.location, 1, 1, f'SHOOTING', self.renderer.white())
            

        
        return self.controls


    """tools"""
    

    def steer_toward(self,car: Car, target:Vec3):
        #always call after throttle set
        angle = car.orientation.forward.signed_ang_to(target-car.location)
        if angle<-1.7 and car.grounded and car.vec_to_ball.flat().length()>500:
            self.controls.steer = -1
            if car.velocity.length()>1200:
                self.controls.throttle*=-1
            self.controls.handbrake=True
        elif angle<-0.1 and car.grounded:
            self.controls.steer = -1
            self.controls.handbrake=False
        elif angle>1.7 and car.grounded and car.vec_to_ball.flat().length()>500:
            self.controls.steer = 1
            if car.velocity.length()>1200:
                self.controls.throttle*=-1
            self.controls.handbrake=True
        elif angle>0.1 and car.grounded:
            self.controls.steer = 1
            self.controls.handbrake=False
        else:
            self.controls.steer = 0
            self.controls.handbrake=False

    def point_in_field(self,vec):
        if abs(vec.x)>4096:
            vec = vec * (4096/abs(vec.x))
        if abs(vec.y)>5120:
            vec = vec * (5120/abs(vec.y))
        if abs(vec.z)>2044:
            vec = vec * (2044/abs(vec.z))
        return vec
    
            



    

    """Routines"""
    def shoot(self,packet):
        
        #get vector of ball to the back of other net
        ideal_shot = Vec3(0,6000,0) - self.ball.location.flat() if self.bot_car.team==0 else Vec3(0,-6000,0) - self.ball.location.flat()
        
               
        #continue any strike after checking it
        if self.current_strike is not None:
            if check_strike(packet, self.ball_prediction, self.current_strike):
                self.active_sequence, strike_controls, strike_location, strike_time = execute_strike(packet,self.bot_car,self.current_strike,self.foes)
                self.controls = strike_controls
                self.renderer.draw_rect_3d(strike_location, 8, 8, True, self.renderer.red(), centered=True)
                self.renderer.draw_line_3d(self.bot_car.location, strike_location, self.renderer.white())
                self.renderer.draw_string_2d(20,20,3,3,f"throttle: {self.controls.throttle}",self.renderer.white())
                return
            else:
                self.current_strike = None

        
        #try to find  strikes
        if self.ball.velocity.length()!=0 and self.current_strike is None and self.bot_car.stable:
            strikes = find_strikes(packet, self.ball_prediction, self.bot_car, ideal_shot)
            for strike in strikes:
                if strike.strike_type==strike_types.simple_linear:
                    #linear
                    if (Vec3(0,6000*(1-self.bot_car.team*2),0) - strike.slice_location).ang_to(self.bot_car.orientation.forward) < 2:
                        #if linear strike is not a massive angle from the goal
                        if self.current_strike is not None:
                            self.current_strike = strike if strike.slice_time<self.current_strike.slice_time else self.current_strike
                        else:
                            self.current_strike = strike
                elif strike.strike_type==strike_types.linear_jump:
                    #long jump
                    if (Vec3(0,6000*(1-self.bot_car.team*2-1),0) - strike.slice_location).ang_to(self.bot_car.orientation.forward) < 2:
                        #if linear strike is not a massive angle from the goal
                        if self.current_strike is not None:
                            self.current_strike = strike if strike.slice_time<self.current_strike.slice_time else self.current_strike
                        else:
                            self.current_strike = strike
                elif strike.strike_type==strike_types.linear_dblj:
                    #double jump
                    if (Vec3(0,6000*(1-self.bot_car.team*2-1),0) - strike.slice_location).ang_to(self.bot_car.orientation.forward) < 2:
                        #if linear strike is not a massive angle from the goal
                        if self.current_strike is not None:
                            self.current_strike = strike if strike.slice_time<self.current_strike.slice_time else self.current_strike
                        else:
                            self.current_strike = strike

            #execute straight away if one was chosen
            if self.current_strike is not None:
                self.active_sequence, strike_controls, strike_location, strike_time = execute_strike(packet,self.bot_car,self.current_strike,self.foes)
                self.controls = strike_controls
                self.renderer.draw_rect_3d(strike_location, 8, 8, True, self.renderer.red(), centered=True)
                self.renderer.draw_line_3d(self.bot_car.location, strike_location, self.renderer.white())
                self.renderer.draw_string_2d(20,20,3,3,f"throttle: {self.controls.throttle}",self.renderer.white())
                return

        #position to get a shot on the ball

        future_location, future_velocity = Vec3(self.ball.location), Vec3(self.ball.velocity)

        future_slice = find_slice_at_time(self.ball_prediction,packet.game_info.seconds_elapsed + 2)
        if future_slice is not None:
            future_location = Vec3(future_slice.physics.location)
            future_velocity = Vec3(future_slice.physics.velocity)
            self.renderer.draw_line_3d(self.ball.location, future_location, self.renderer.cyan())

        target_location = self.point_in_field(future_location.flat()+ideal_shot.rescale(-500))
        self.controls.throttle = 1.0
        self.steer_toward(self.bot_car, target_location)
        self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
        self.renderer.draw_line_3d(self.bot_car.location, target_location, self.renderer.white())
        return

        ##################################################################################################


        
        

    def clear(self,packet):

        #get vector of ball from the cone of own net
        ideal_shot = self.ball.location.flat() - Vec3(0,-8000,0) if self.bot_car.team==0 else self.ball.location.flat() - Vec3(0,8000,0)
        
        #find a future position based off the distance from the ball, using the current location as a backup
        future_location = self.ball.location
        future_velocity = self.ball.velocity


        #continue any strike after checking it
        if self.current_strike is not None and self.bot_car.stable:
            if check_strike(packet, self.ball_prediction, self.current_strike):
                self.active_sequence, strike_controls, strike_location, strike_time = execute_strike(packet,self.bot_car,self.current_strike,self.foes)
                self.controls = strike_controls

                #drive out of goal > priority
                in_goal = self.bot_car.location.within(self.goal_corners[self.bot_car.team][0],self.goal_corners[self.bot_car.team][1])
                post0_ang = self.collision_posts[self.bot_car.team][0].__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
                std_ang_to_target = self.current_strike.slice_location.__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
                post1_ang = self.collision_posts[self.bot_car.team][1].__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
                between_posts = post0_ang < std_ang_to_target < post1_ang
                if not between_posts and in_goal:
                    target_location = Vec3(0,(2*self.team-1)*5000,0)
                    self.controls.throttle = 1
                    self.steer_toward(self.bot_car, target_location)
                    self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
                    self.renderer.draw_line_3d(self.bot_car.location, target_location, self.renderer.white())
                    return

                
                self.renderer.draw_rect_3d(strike_location, 8, 8, True, self.renderer.red(), centered=True)
                self.renderer.draw_line_3d(self.bot_car.location, strike_location, self.renderer.white())
                self.renderer.draw_string_2d(20,20,3,3,f"throttle: {self.controls.throttle}",self.renderer.white())
                return
            else:
                self.current_strike = None

       

        #try to find  strikes
        if self.ball.velocity.length()!=0 and self.current_strike is None:
            strikes = find_strikes(packet,self.ball_prediction,self.bot_car,ideal_shot)
            for strike in strikes:
                if strike.strike_type==strike_types.simple_linear:
                    #linear
                    if (strike.slice_location - Vec3(0,5500*(self.bot_car.team*2-1),0)).ang_to(self.bot_car.orientation.forward) < 2.2:
                        #if linear strike is not a massive angle from the goal
                        if self.current_strike is not None:
                            self.current_strike = strike if strike.slice_time<self.current_strike.slice_time else self.current_strike
                        else:
                            self.current_strike = strike
                elif strike.strike_type==strike_types.linear_jump:
                    #long jump
                    if (strike.slice_location - Vec3(0,5500*(self.bot_car.team*2-1),0)).ang_to(self.bot_car.orientation.forward) < 2:
                        #if linear strike is not a massive angle from the goal
                        if self.current_strike is not None:
                            self.current_strike = strike if strike.slice_time<self.current_strike.slice_time else self.current_strike
                        else:
                            self.current_strike = strike
                elif strike.strike_type==strike_types.linear_dblj:
                    #double jump
                    if (strike.slice_location - Vec3(0,5500*(self.bot_car.team*2-1),0)).ang_to(self.bot_car.orientation.forward) < 2:
                        #if linear strike is not a massive angle from the goal
                        if self.current_strike is not None:
                            self.current_strike = strike if strike.slice_time<self.current_strike.slice_time else self.current_strike
                        else:
                            self.current_strike = strike

            #execute straight away if one was chosen:

                
            #execute
            if self.current_strike is not None:
                #drive out of goal > priority
                in_goal = self.bot_car.location.within(self.goal_corners[self.bot_car.team][0],self.goal_corners[self.bot_car.team][1])
                post0_ang = self.collision_posts[self.bot_car.team][0].__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
                std_ang_to_target = self.current_strike.slice_location.__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
                post1_ang = self.collision_posts[self.bot_car.team][1].__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
                between_posts = post0_ang < std_ang_to_target < post1_ang
                if not between_posts and in_goal:
                    target_location = Vec3(0,(2*self.team-1)*5000,0)
                    self.controls.throttle = 1
                    self.steer_toward(self.bot_car, target_location)
                    self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
                    self.renderer.draw_line_3d(self.bot_car.location, target_location, self.renderer.white())
                    return
                    
                #execute
                self.active_sequence, strike_controls, strike_location, strike_time = execute_strike(packet,self.bot_car,self.current_strike,self.foes)
                self.controls = strike_controls
                    
                self.renderer.draw_rect_3d(strike_location, 8, 8, True, self.renderer.red(), centered=True)
                self.renderer.draw_line_3d(self.bot_car.location, strike_location, self.renderer.white())
                self.renderer.draw_string_2d(20,20,3,3,f"throttle: {self.controls.throttle}",self.renderer.white())
                return

                            
        #position for a better shot
        future_location, future_velocity = Vec3(self.ball.location), Vec3(self.ball.velocity)

        future_slice = find_slice_at_time(self.ball_prediction,packet.game_info.seconds_elapsed + 2)
        if future_slice is not None:
            future_location = Vec3(future_slice.physics.location)
            future_velocity = Vec3(future_slice.physics.velocity)
            self.renderer.draw_line_3d(self.ball.location, future_location, self.renderer.cyan())

        target_location = self.point_in_field(future_location.flat()+ideal_shot.rescale(-500))


        #drive out of goal > priority
        in_goal = self.bot_car.location.within(self.goal_corners[self.bot_car.team][0],self.goal_corners[self.bot_car.team][1])
        post0_ang = self.collision_posts[self.bot_car.team][0].__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
        std_ang_to_target = target_location.__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
        post1_ang = self.collision_posts[self.bot_car.team][1].__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
        between_posts = post0_ang < std_ang_to_target < post1_ang
        if not between_posts and in_goal:
            target_location = Vec3(0,(2*self.team-1)*5000,0)
            self.controls.throttle = 1
            self.steer_toward(self.bot_car, target_location)
            self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
            self.renderer.draw_line_3d(self.bot_car.location, target_location, self.renderer.white())
            return
        self.controls.throttle = 1.0
        self.steer_toward(self.bot_car, target_location)
        self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
        self.renderer.draw_line_3d(self.bot_car.location, target_location, self.renderer.white())
        return

    
        
    def rotate(self,packet):

        #continue any strike after checking it
        if self.current_strike is not None:
            if check_strike(packet,self.ball_prediction,self.current_strike) and abs(self.current_strike.slice_location.y) > abs(self.bot_car.location.y):
                self.active_sequence, strike_controls, strike_location, strike_time = execute_strike(packet,self.bot_car,self.current_strike,self.foes)
                self.controls = strike_controls
                self.renderer.draw_rect_3d(strike_location, 8, 8, True, self.renderer.red(), centered=True)
                self.renderer.draw_line_3d(self.bot_car.location, strike_location, self.renderer.white())
                self.renderer.draw_string_2d(20,20,3,3,f"throttle: {self.controls.throttle}",self.renderer.white())
                return
            else:
                self.current_strike = None


        #aim at the post opposite where the ball is
        target_location = self.posts[self.bot_car.team][0] if self.ball.location.x < 0 else self.posts[self.bot_car.team][1]
        #wavedash to rotate quicker
        if self.bot_car.location.dist(target_location) > 3000 and self.bot_car.stable and self.bot_car.orientation.forward.ang_to(target_location-self.bot_car.location)<0.3 and 500<self.bot_car.velocity.length()<1600:
            self.active_sequence, self.controls = wavedash(packet)
            return

        #add something to avoid collisions later
        if self.bot_car.location.point_in_path(target_location - self.bot_car.location,self.ball.location):
            target_location = self.ball.location + Vec3(0,math.copysign(150,target_location.x),0)
        for ally in self.allies:
            if self.bot_car.location.point_in_path(target_location - self.bot_car.location,ally.location):
                target_location = ally.location + Vec3(0,math.copysign(150,target_location.x),0)
                


        #drive toward target
        self.controls.throttle = 1.0
        self.steer_toward(self.bot_car,target_location)
        self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
        self.renderer.draw_line_3d(self.bot_car.location, target_location, self.renderer.white())
        return
    #############################################################################################################################

    def defend(self,packet):
        #get the vector of the ball to where it will hit the goal (
        ball_to_goal = self.ball.velocity.flat()
        if ball_to_goal.length()!=0:
            ball_to_goal = ball_to_goal.rescale(((5120-abs(self.ball.location.y))/abs(ball_to_goal.y)))
        #target 2/3 way between ball and goal
        target_location = self.ball.location + ball_to_goal/1.5

        #get vector of ball from the cone of own net
        ideal_shot = self.ball.location.flat() - Vec3(0,-8000,0) if self.bot_car.team==0 else self.ball.location.flat() - Vec3(0,8000,0)
        #ideal shot is to corner if on other side of ball
        going_to_overtake_ball = (self.bot_car.location-Vec3(0,6000*(2*self.bot_car.team-1),0)).scalar_proj(self.ball.location-Vec3(0,6000*(2*self.bot_car.team-1),0))+100 > Vec3(0,6000*(2*self.bot_car.team-1),0).dist(self.ball.location)
        if going_to_overtake_ball:
            ideal_shot = Vec3(math.copysign(4096,(ball_to_goal+self.ball.location).x),(self.team*2-1)*5120,0) - self.ball.location
        

        
        
        #continue any strike after checking it
        if self.current_strike is not None:
            if check_strike(packet,self.ball_prediction,self.current_strike):
                
                #otherwise, continue on strike
                self.active_sequence, strike_controls, strike_location, strike_time = execute_strike(packet,self.bot_car,self.current_strike,self.foes,defence=True)
                self.controls = strike_controls
                self.renderer.draw_rect_3d(strike_location, 8, 8, True, self.renderer.red(), centered=True)
                self.renderer.draw_line_3d(self.bot_car.location, strike_location, self.renderer.white())
                self.renderer.draw_string_2d(20,20,3,3,f"throttle: {self.controls.throttle}",self.renderer.white())

                #drive out of goal > priority
                in_goal = self.bot_car.location.within(self.goal_corners[self.bot_car.team][0],self.goal_corners[self.bot_car.team][1])
                post0_ang = self.collision_posts[self.bot_car.team][0].__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
                std_ang_to_target = strike_location.__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
                post1_ang = self.collision_posts[self.bot_car.team][1].__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
                between_posts = post0_ang < std_ang_to_target < post1_ang
                if not between_posts and in_goal:
                    target_location = Vec3(0,(2*self.team-1)*5000,0)
                    self.controls.throttle = 1
                    self.steer_toward(self.bot_car, target_location)
                    self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
                    self.renderer.draw_line_3d(self.bot_car.location, target_location, self.renderer.white())
                    return

                return
            else:
                self.current_strike = None

       

        #try to find  strikes
        if self.ball.velocity.length()!=0 and self.current_strike is None and self.bot_car.stable:
            strikes = find_strikes(packet,self.ball_prediction,self.bot_car,ideal_shot,defence=True)
            for strike in strikes:
                if strike.strike_type==strike_types.simple_linear:
                    #linear, will check if line to strike location goes into net
                    post0_ang = self.posts[self.bot_car.team][0].__sub__(self.ball.location).flat().ang_to(Vec3(1,0,0))
                    car_slice_ang = (strike.slice_location - self.bot_car.location).flat().ang_to(Vec3(1,0,0))
                    post1_ang = self.posts[self.bot_car.team][1].__sub__(self.ball.location).flat().ang_to(Vec3(1,0,0))
                    between_posts = post0_ang < car_slice_ang < post1_ang
                    if abs(self.bot_car.location.y)>abs(self.ball.location.y):
                        #clear if on correct side
                        if self.current_strike is not None:
                            self.current_strike = strike if strike.slice_time<self.current_strike.slice_time else self.current_strike
                        else:
                            self.current_strike = strike
                    elif all(abs(ally.location.y-(1-ally.team*2)*6000) < abs(self.bot_car.location.y-(1-ally.team*2)*6000) or abs(ally.location.x)>2500 for ally in self.allies) and not between_posts:
                        #clear to corner
                        if self.current_strike is not None:
                            self.current_strike = strike if strike.slice_time<self.current_strike.slice_time else self.current_strike
                        else:
                            self.current_strike = strike
                elif strike.strike_type==strike_types.linear_jump or strike.strike_type==strike_types.linear_dblj:                    
                    #linear, will check if line to strike location goes into net
                    post0_ang = self.posts[self.bot_car.team][0].__sub__(self.ball.location).flat().ang_to(Vec3(1,0,0))
                    car_slice_ang = (strike.slice_location - self.bot_car.location).flat().ang_to(Vec3(1,0,0))
                    post1_ang = self.posts[self.bot_car.team][1].__sub__(self.ball.location).flat().ang_to(Vec3(1,0,0))
                    between_posts = post0_ang < car_slice_ang < post1_ang
                    if abs(self.bot_car.location.y)>abs(self.ball.location.y):
                        #clear if on correct side
                        if self.current_strike is not None:
                            self.current_strike = strike if strike.slice_time<self.current_strike.slice_time else self.current_strike
                        else:
                            self.current_strike = strike
                    elif all(abs(ally.location.y-(1-ally.team*2)*6000) < abs(self.bot_car.location.y-(1-ally.team*2)*6000) or abs(ally.location.x)>2500 for ally in self.allies) and not between_posts:
                        #clear to corner
                        if self.current_strike is not None:
                            self.current_strike = strike if strike.slice_time<self.current_strike.slice_time else self.current_strike
                        else:
                            self.current_strike = strike

            #execute straight away
            if self.current_strike is not None:
                self.active_sequence, strike_controls, strike_location, strike_time = execute_strike(packet,self.bot_car,self.current_strike,self.foes,defence=True)
                self.controls = strike_controls
                self.renderer.draw_rect_3d(strike_location, 8, 8, True, self.renderer.red(), centered=True)
                self.renderer.draw_line_3d(self.bot_car.location, strike_location, self.renderer.white())
                self.renderer.draw_string_2d(20,20,3,3,f"throttle: {self.controls.throttle}",self.renderer.white())

                #drive out of goal > priority
                in_goal = self.bot_car.location.within(self.goal_corners[self.bot_car.team][0],self.goal_corners[self.bot_car.team][1])
                post0_ang = self.collision_posts[self.bot_car.team][0].__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
                std_ang_to_target = strike_location.__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
                post1_ang = self.collision_posts[self.bot_car.team][1].__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
                between_posts = post0_ang < std_ang_to_target < post1_ang
                if not between_posts and in_goal:
                    target_location = Vec3(0,(2*self.team-1)*5000,0)
                    self.controls.throttle = 1
                    self.steer_toward(self.bot_car, target_location)
                    self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
                    self.renderer.draw_line_3d(self.bot_car.location, target_location, self.renderer.white())
                    return

                return
        """
        keep the rest for now, esp for defence
        """
        #changed to if car is further from goal than ball
        if Vec3(0,6000*(2*self.bot_car.team-1),0).dist(self.bot_car.location) > Vec3(0,6000*(2*self.bot_car.team-1),0).dist(self.ball.location)-100:
            offset = self.bot_car.vec_to_ball.flat().cross(Vec3(0,0,1)).normalized()
            if offset.y>0 and self.ball.velocity.y <0 or offset.y<0 and self.ball.velocity.y >0:
                offset = -offset
            target_location = target_location + 150*offset
            self.controls.throttle=1.0
            self.steer_toward(self.bot_car, target_location)
            self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
            self.renderer.draw_line_3d(self.bot_car.location, target_location, self.renderer.white())
            return
        

        #Drive to the point, using atan to slow when close to the point (judged by d/v)
        est_time = -1
        try:
            est_time = self.bot_car.location.dist(target_location) / self.bot_car.velocity.flat().scalar_proj((target_location - self.bot_car.location).flat())
        except:
            stub="catch div 0"
        self.controls.throttle = (2*math.atan(est_time)/math.pi)*1.2-0.2 if est_time>0 else 1
        self.steer_toward(self.bot_car, target_location)
        self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
        self.renderer.draw_line_3d(self.bot_car.location, target_location, self.renderer.white())
        return

    def support(self, packet, position:int):

        #continue any strike after checking it
        if self.current_strike is not None:
            if check_strike(packet,self.ball_prediction,self.current_strike) and self.current_strike.slice_time-packet.game_info.seconds_elapsed < 1.5:
                self.active_sequence, strike_controls, strike_location, strike_time = execute_strike(packet,self.bot_car,self.current_strike,self.foes)
                self.controls = strike_controls
                self.renderer.draw_rect_3d(strike_location, 8, 8, True, self.renderer.red(), centered=True)
                self.renderer.draw_line_3d(self.bot_car.location, strike_location, self.renderer.white())
                self.renderer.draw_string_2d(20,20,3,3,f"throttle: {self.controls.throttle}",self.renderer.white())
                return
            else:
                self.current_strike = None
        
        target_location = Vec3(0,0,0)
        if position==1:        
            target_location = self.ball.location.flat() + Vec3(-self.ball.location.x/2,(self.bot_car.team*2-1)*3000,0)

        else:
            target_location = self.ball.location.flat() + (Vec3(0,(self.bot_car.team*2-1)*6500,0) - self.ball.location.flat()).rescale(6000)

        target_location = self.point_in_field(target_location)

        #second man in net on defence, or if would drive up wall
        if self.ball.location.y *(2*self.bot_car.team-1)>0 and self.ball.velocity.y *(2*self.bot_car.team-1)>0 or abs(target_location.y)>4600:
            target_location = Vec3(0,5200*(2*self.bot_car.team-1),0)
            #if it needs to drive around posts, do it
            in_goal = self.bot_car.location.within(self.goal_corners[self.bot_car.team][0],self.goal_corners[self.bot_car.team][1])
            post0_ang = self.collision_posts[self.bot_car.team][0].__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
            std_ang_to_target = target_location.__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
            facing_ang = self.bot_car.orientation.forward.ang_to(Vec3(1,0,1))
            post1_ang = self.collision_posts[self.bot_car.team][1].__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
            travel_between_posts = post0_ang < std_ang_to_target < post1_ang
            facing_between_posts = post0_ang < facing_ang < post1_ang
            if not in_goal and not travel_between_posts:
                target_location = Vec3(0,5000*(2*self.bot_car.team-1),0)
            for ally in self.allies:
                if ally.location.within(self.goal_corners[self.bot_car.team][0],self.goal_corners[self.bot_car.team][1]):
                    target_location = Vec3(-1*math.copysign(950,self.ball.location.x),4900,0)

            self.controls.throttle = min(self.bot_car.location.dist(target_location)**2/1000**2,1)
            if in_goal and self.bot_car.orientation.forward.y*(1-2*self.bot_car.team) >0.7 and abs(self.bot_car.location.y) <5220:
                self.controls.throttle = 0 if self.bot_car.velocity.length() <20 else -1*math.copysign(1,self.bot_car.velocity.dot(self.bot_car.orientation.forward))
            self.steer_toward(self.bot_car, target_location)
            self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
            self.renderer.draw_line_3d(self.bot_car.location, target_location, self.renderer.white())
            return

        #exit goal if needed
        ##try:
        in_goal = self.bot_car.location.within(self.goal_corners[self.bot_car.team][0],self.goal_corners[self.bot_car.team][1])
        post0_ang = self.collision_posts[self.bot_car.team][0].__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
        std_ang_to_target = target_location.__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
        post1_ang = self.collision_posts[self.bot_car.team][1].__sub__(self.bot_car.location).flat().ang_to(Vec3(1,0,0))
        between_posts = post0_ang < std_ang_to_target < post1_ang
        if not between_posts and in_goal:
            target_location = Vec3(0,(2*self.team-1)*5000,0)
            self.controls.throttle = min(self.bot_car.location.dist(target_location)**2/800**2+0.1,1)
            self.steer_toward(self.bot_car, target_location)
            self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
            self.renderer.draw_line_3d(self.bot_car.location, target_location, self.renderer.white())
            return
        ##except:
            ##stub="catch div 0 errors"

        self.controls.throttle = min(self.bot_car.location.dist(target_location)**2/1000**2,1)
        self.steer_toward(self.bot_car, target_location)
        self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
        self.renderer.draw_line_3d(self.bot_car.location, target_location, self.renderer.white())
        return

    def perform_air_recovery(self, packet):
        try:
            self.controls.steer = self.bot_car.orientation.right.dot(self.bot_car.velocity.flat().normalized())
            self.controls.pitch = self.bot_car.orientation.up.dot(self.bot_car.velocity.flat().normalized())
            self.controls.roll = self.bot_car.orientation.right.dot(Vec3(0,0,1))
        except:
            stub="I'm too lazy to catch div 0 properly"
        return
