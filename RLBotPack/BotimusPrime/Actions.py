import math, time
from Utils import *
from Unreal import Vector3

def dodge(self, target=None):

    # first jump
    if self.on_ground and not self.dodging:
        if target is None:
            roll = 0
            pitch = 1
        else:
            a = math.radians(angle_to(self, target))
            roll = math.sin(a)
            pitch = math.cos(a)

            # if too fast, barrel roll
            if abs(math.degrees(a)) > 30 and self.speed > 1500:
                pitch = 0
                roll = sign(roll)

            # if roll too small, just dodge forward
            if roll < 0.05:
                roll = 0

        self.dodge_pitch = -pitch
        self.dodge_roll = roll
        self.dodging = True
        self.output.jump = True
        self.next_dodge_time = time.time() + 0.1

    # second jump
    elif time.time() > self.next_dodge_time:
        self.output.jump = True
        self.output.pitch = self.dodge_pitch
        self.output.roll = self.dodge_roll
        if self.on_ground or self.location.z > 500 or time.time() > self.next_dodge_time + 1:
            self.dodging = False
            #Recovery kicks in

def halfflip(self):
    # Step 1: Jump
    if not self.halfflipping and self.on_ground:
        self.halfflipping = True
        self.output.jump = True
        self.flip_start_time = time.time()

    # Step 4: Recovery kicks in
    elif time.time() > self.flip_start_time + 1.0:
        self.halfflipping = False
        
    # Step 3: Cancel dodge and start rolling
    elif time.time() > self.flip_start_time + 0.6:
        self.output.pitch = -1
        self.output.roll = 1
        if self.on_ground:
            self.halfflipping = False
    
    # Step 2: Dodge forward
    elif time.time() > self.flip_start_time + 0.3:
        self.output.jump = True
        self.output.pitch = 1



def arrive_with_angle(self, target_location, direction_vector):

    #this function sometimes doesnt work as intended
    #for a better solution, try Dom's:
    # https://github.com/DomNomNom/RocketBot/blob/master/tangents.py


    spd = max(self.speed, 100)

    tr = turn_radius(self.speed)

    target = Vector3()
    direction_vector.z = 0

    hp = target_location + direction_vector * 200

    p1 = hp + Vector3(direction_vector.y, -direction_vector.x, 0) * tr
    p2 = hp + Vector3(-direction_vector.y, direction_vector.x, 0) * tr

    dist1 = distance(self, p1)
    dist2 = distance(self, p2)

    if dist1 <= tr or dist2 <= tr:
        return target_location

    mr1 = math.sqrt(dist1 ** 2 - tr ** 2)
    mr2 = math.sqrt(dist2 ** 2 - tr ** 2)

    try:
        tgp1 = intersect_two_circles(
            p1.x, p1.y, tr, self.location.x, self.location.y, mr1
        )[1]
        tgp2 = intersect_two_circles(
            p2.x, p2.y, tr, self.location.x, self.location.y, mr2
        )[0]
    except:
        return target_location

    tgp1 = Vector3(tgp1[0], tgp1[1], 0)
    tgp2 = Vector3(tgp2[0], tgp2[1], 0)

    b1 = distance(self, tgp1) < distance(self, tgp2)

    if not inside_arena(tgp1) and not inside_arena(tgp2):
        return target_location
    if not inside_arena(tgp1):
        b1 = False
    if not inside_arena(tgp2):
        b1 = True

    tg = tgp1 if b1 else tgp2
    p = p1 if b1 else p2

    target = tg + direction(self, tg) * 100

    return target