from tools import  *
from utils import *
from routines import *
from agent import *
from custom_routines import *


#This file is for strategy

class ExampleBot(VirxERLU):
    def initialize_agent(self):
        super().initialize_agent()
        self.state = None
        self.do_debug = True
        self.RTG_flip_time = 0
    def run(self):
        num_foes = len(self.foes)
        my_goal_to_ball, my_ball_distance = (self.ball.location-self.friend_goal.location).normalize(True)
        goal_to_me = self.me.location-self.friend_goal.location
        my_distance = my_goal_to_ball.dot(goal_to_me)

        foe_goal_to_ball, foe_ball_distance = (self.ball.location-self.friend_goal.location).normalize(True)

        foe_onside = False

        for foe in self.foes:
            foe_goal_to_foe = self.foes[0].location-self.friend_goal.location
            foe_distance = foe_goal_to_ball.dot(foe_goal_to_foe)
            if foe_distance - 200 < foe_ball_distance:
                foe_onside = True

        me_onside = my_distance - 200 < my_ball_distance
        close = (self.me.location - self.ball.location).magnitude() < 2000
        have_boost = self.me.boost > 20

        # -1: defensive third, 0: middle third,  1: offensive third
        if -1706 < self.ball.location.y < 1706:
            ball_third = 0 
        elif (self.team and self.ball.location.y > 1706) or (not self.team and self.ball.location.y < -1706):
            ball_third = -1
        else: 
            ball_third = 1

        return_to_goal = False

        need_to_save = False

        bump_opponent = False

        struct = self.get_ball_prediction_struct()
        for pred_slice in struct.slices:
            if side(self.team) * pred_slice.physics.location.y > 5200:
                need_to_save = True
                break

        for pred_slice in struct.slices:
            if side(self.team) * pred_slice.physics.location.y < -5200:
                bump_opponent = True
                break
            

        

        if len(self.stack) < 1 or (self.state == 'getting boost' and len(self.stack) == 1):
            if self.state == 'getting boost' and len(self.stack) == 1:
                self.pop()
            self.state = None
            if self.kickoff_flag:
                my_kickoff = True
                if abs(self.me.location.x) == 2048:
                    self.print(f'speedflipping!')
                    self.push(speed_flip_kickoff())
                    self.state = 'speedflip kickoff'
                else:
                    for friend in self.friends:
                        if (friend.location - self.ball.location).magnitude() < (self.me.location - self.ball.location).magnitude():
                            my_kickoff = False
                    if my_kickoff:
                        self.push(generic_kickoff())
                        self.state = 'my kickoff'
                    else:
                        boosts = [boost for boost in self.boosts if boost.large and boost.active]
                        if len(boosts) > 0:
                            closest = boosts[0]
                            for boost in boosts:
                                if (boost.location - self.me.location).magnitude() < (closest.location - self.me.location).magnitude():
                                    closest = boost
                            self.push(goto_boost(closest))
                            self.state = 'kickoff (getting boost)'
            elif need_to_save:
                left_field = Vector(4200*(-side(self.team)), self.ball.location.y + 2000*(-side(self.team)), 0)
                right_field = Vector(4200*(side(self.team)), self.ball.location.y + 2000*(-side(self.team)), 0)
                self.state = 'need to save'
                team = 1 if self.team == 1 else -1
                targets = {'my_goal': (Vector(-team * 850, team * 5100, 320), Vector(team * 850, team * 5100, 320)), 'goal': (self.foe_goal.left_post, self.foe_goal.right_post), 'upfield': (left_field, right_field)}
                shots = self.find_hits(targets)
                if shots['goal'] is not None:
                    self.push(shots['goal'])
                    self.state = 'shooting (NTS)'
                elif shots['upfield'] is not None:
                    self.push(shots['upfield'])
                    self.state= 'upfield (NTS)'
                elif shots['my_goal'] is not None:
                    self.push(shots['my_goal'])
                    self.state = 'not my goal (NTS)'
                else:
                    return_to_goal = True
                    self.state = 'need to save (RTG)'
            elif (close and me_onside) or (not foe_onside and me_onside):
                left_field = Vector(4200*(-side(self.team)), self.ball.location.y + 2000*(-side(self.team)), 0)
                right_field = Vector(4200*(side(self.team)), self.ball.location.y + 2000*(-side(self.team)), 0)
                targets = {'goal': (self.foe_goal.left_post, self.foe_goal.right_post), 'upfield': (left_field, right_field)}
                shots = self.find_hits(targets)
                if shots['goal'] is not None:
                    self.push(shots['goal'])
                    self.state = 'shooting'
                elif shots['upfield'] is not None:
                    self.push(shots['upfield'])
                    self.state= 'upfield'
                else:
                    return_to_goal = True
                    self.state = 'no shot/upfield (RTG)'
            elif not me_onside and not have_boost and ball_third != -1 and not foe_onside: 
                boosts = [boost for boost in self.boosts if boost.large and boost.active]
                if len(boosts) > 0:
                    closest = boosts[0]
                    for boost in boosts:
                        if (boost.location - self.me.location).magnitude() < (closest.location - self.me.location).magnitude():
                            closest = boost
                    if (self.me.location - closest.location).magnitude() < 2000:
                        self.push(goto_boost(closest))
                        self.state = 'getting boost'
                    else:
                        state = 'no close boost'
                        return_to_goal = True
                else:
                    return_to_goal = True
                    self.state = 'no boost (RTG)'
            elif not me_onside and foe_onside:
                self.state = 'get onside (RTGw/B)'
                return_to_goal = True
                self.controller.boost = True
            else:
                return_to_goal = True
                self.state = 'RTG'
            
            if return_to_goal and ((self.me.location.y - self.ball.location.y) * side(self.team) > 1000) and (self.me.location-self.ball.location).magnitude() > 500:
                self.state = 'HIT DA BALL'
                relative_target = self.ball.location - self.me.location
                angles, vel = defaultDrive(self, 1400, self.me.local(relative_target))
                self.controller.boost = False if abs(angles[1]) > 0.5 or self.me.airborne else self.controller.boost
                self.controller.handbrake = True if abs(angles[1]) > 2.8 else False
            else:
                if not (side(self.team) * self.me.location.y > 5120):
                    relative_target = self.friend_goal.location - self.me.location
                    angles, vel = defaultDrive(self, 2300, self.me.local(relative_target))
                    if angles[1] < 0.75 and relative_target.magnitude() > 750 and 500 < self.me.velocity.magnitude() < 1000 and self.time - self.RTG_flip_time > 2:
                        self.push(flip(self.me.local(relative_target)))
                        self.RTG_flip_time = self.time
                    else:
                        self.controller.boost = False if abs(angles[1]) > 0.5 or self.me.airborne else self.controller.boost
                        self.controller.handbrake = True if abs(angles[1]) > 2.8 else False
                else:
                    self.state += ' (In goal)'

        if self.do_debug:
            #this overdoes the rendering, needs fixing
            # self.renderer.draw_polyline_3d([pred_slice.physics.location for pred_slice in struct.slices], self.renderer.cyan())
            for stackitem in self.stack:
                if hasattr(stackitem, 'ball_location'):
                    self.draw_cube_wireframe(stackitem.ball_location, self.renderer.pink())
            self.line(self.friend_goal.location, self.ball.location, (255,255, 255))
            my_point = self.friend_goal.location + (my_goal_to_ball * my_distance)
            self.line(my_point - Vector(0,0,100),  my_point + Vector(0,0,100), (0,255,0))
            car_to_ball = 'working!'
            self.renderer.draw_string_2d(10, 30*(self.index + 10), 2, 2, (str(ball_third) + ' ' + str(return_to_goal) + ' ' + str(need_to_save) + ' ' + str(self.state) + ' ' + str(car_to_ball)), self.renderer.white())

    def draw_cube_wireframe(self, center, color, size=75):
        points = []
        for offset in [Vector(size/2, size/2, size/2), Vector(size/2, size/2, -size/2), Vector(size/2, -size/2, size/2), Vector(size/2, -size/2, -size/2), Vector(-size/2, size/2, size/2), Vector(-size/2, size/2, -size/2), Vector(-size/2, -size/2, size/2), Vector(-size/2, -size/2, -size/2)]:
            try:
                points.append(center + offset)
            except TypeError:
                pass
        for point in points:
            for other_point in points:
                if point == other_point:
                    continue
                if abs((point-other_point).magnitude()) == size:
                    self.renderer.draw_line_3d(point, other_point, color)
    
    def find_hits(self, targets, test_for_ground_shot=True):
        output = {}
        for name, target in targets.items():
            shot = find_shot(self, target)
            if shot is not None and test_for_ground_shot:
                ball_pos_at_time = self.get_ball_prediction_struct().slices[round((shot.intercept_time - self.time) * 60) - 1].physics.location
                ball_vec_at_time = Vector(ball_pos_at_time.x, ball_pos_at_time.y, ball_pos_at_time.z)
                if shot.__class__.__name__ == 'ground_shot' and ((ball_vec_at_time - self.me.location).magnitude()/(shot.intercept_time-self.time)) < 500:
                    shot = find_shot(self, target, can_ground=False)
                    self.print('bad ground shot!')
            output[name] = shot
        return output
        
            