# Some physics done by Marvin. Thank you! :D
# Not perfect but will do for now.

import math, numpy as np


# Indecies into the output tuples of predict_b.
BALL_STATE_POS = 0
BALL_STATE_VEL = 1
BALL_STATE_ANGULAR_VEL = 2
BALL_STATE_TIME = 3


def rotate2D(x,y,ang):
    x2 = x*math.cos(ang) - y*math.sin(ang)
    y2 = y*math.cos(ang) + x*math.sin(ang)
    return x2,y2

def local_space(tL,oL,oR):
    L = a3(tL)-a3(oL)
    oR = a3(oR)*math.pi/180
    y, z = rotate2D(L[1],L[2],-oR[0])
    x, z = rotate2D(L[0],z,-oR[1])
    return x,y,z

def global_space(L,oL,oR):
    oR = a3(oR)*math.pi/180
    tL = a3([0,0,0])
    tL[0], tL[2] = rotate2D(L[0],L[2],oR[1])
    tL[1], tL[2] = rotate2D(L[1],tL[2],oR[0])
    tL = a3(tL)+a3(oL)
    return tL

def CollisionFree(L) :
    ''' Returns whether the ball at location L could collide with the arena.'''
    b = False
    if 242<L[2]<1833:
        if abs(L[0])<3278:
            if abs(L[1])<4722:
                if (abs(L[0])+abs(L[1]))/7424 <= 1:
                    b = True
    return b

def Collision_R(L):
    R = 93
    x,y,z = L
    wx,wy,wz = 8200, 10280, 2050    # field dimensions
    gx,gz = 1792, 640               # goal dimensions
    cR, cR2, cR3 = 520, 260, 190
    cx,cy,cz = wx/2-cR, wy/2-cR, wz-cR
    cx2,cz2 = wx/2-cR2, cR2
    cy3,cz3 = wy/2-cR3, cR3

    # Top Ramp X-axis
    if abs(x)>wx/2-cR and z>cz and (abs(x) - cx)**2 + (z - cz)**2 > (cR-R)**2:
        a = math.atan2(z-cz,abs(x)-cx)/math.pi*180
        return True, [0,(90+a)*sign(x)]

    # Top Ramp Y-axis
    if abs(y)>cy and z>cz and (abs(y) - cy)**2 + (z - cz)**2 > (cR-R)**2:
        a = math.atan2(z-cz,abs(y)-cy)/math.pi*180
        return True, [(90+a)*sign(y),0]

    # Bottom Ramp X-axis
    elif abs(x)>cx2 and z<cz2 and (abs(x) - cx2)**2 + (z - cz2)**2 > (cR2-R)**2:
        a = math.atan2(z-cz2,abs(x)-cx2)/math.pi*180
        return True, [0,(90+a)*sign(x)]

    # Bottom Ramp Y-axis
    elif abs(y)>cy3 and z<cz3 and abs(x)>gx/2-R/2 and (abs(y) - cy3)**2 + (z - cz2)**2 > (cR3-R)**2:
        a = math.atan2(z-cz2,abs(y)-cy3)/math.pi*180
        return True, [(90+a)*sign(y),0]

    # Flat 45° Corner
    elif (abs(x)+abs(y)+R)/8060 >= 1:
        return True, [90*sign(y),45*sign(x)]

    # Floor
    elif z<R:
        return True, [0,0]

    # Flat Wall X-axis
    elif abs(x)>wx/2-R:
        return True, [0,90*sign(x)]

    # Flat Wall Y-axis
    elif abs(y)>wy/2-R and (abs(x)>gx/2-R/2 or z>gz-R/2):
        return True, [90*sign(y),0]

    # Ceiling
    elif z>wz-R:
        return True, [0,180]

    else:
        return False, [0,0]


def predict_b(L0,V0,aV0,dt):
    '''
        returns the a BallPath for the given ball (L0, V0, aV0) and duration (dt)
        A BallPath is an array of (Location, Vel, angularVel, elapsedTime) tuples
    '''
    ept = 1/60
    cL0,cV0,caV0,at = L0,V0,aV0,dt

    r, gc = 0.030455, -650
    e2,e1,a = .6,.714,.4
    R = 92.
    g = a3([0,0,gc])


    def rolling_model(L0, V0, aV0, dt):
        '''
            Note: this is a hack.
            returns None if the rolling model is not applicable.
            returns the new (location, velocity, angular_velocity) tuple
        '''
        if L0[-1] > R * 1.2: return None
        if abs(V0[-1]) > 2000: return None
        if abs(np.linalg.norm(aV0)*R - np.linalg.norm(V0)) > 30: return None
        nL = L0 + V0*dt*1.0
        nV = a3([V0[0], V0[1], 0])
        return (nL, V0, aV0)

    def LVt(L0,V0,aV0,dt):
        roll_predict = rolling_model(L0, V0, aV0, dt)
        if roll_predict is not None:
            return roll_predict

        A = g -r*V0
        nV = V0 + A*dt
        nL = L0 + V0*dt + .5*A*dt**2


        total_v = d3(nV) # limiting ball speed
        if total_v > 6000:
            nV[0],nV[1],nV[2] = 6*nV[0]/total_v, 6*nV[1]/total_v, 6*nV[2]/total_v

        naV = aV0

        if not CollisionFree(nL):
            Cl = Collision_R(nL)
            if Cl[0] == True:

                xv,yv,zv = local_space(V0,[0,0,0],Cl[1])
                xav,yav,zav = local_space(aV0,[0,0,0],Cl[1]) # transorforming velocities to local space

                ang = abs(math.atan2(zv,math.sqrt(xv**2+yv**2)))/math.pi*180

                e = (e1-1)/(29)*ang +1
                if e<e1: e=e1
                if zv>-10: e=.85

                xv,yv,zv = (xv+yav*R*a)*e, (yv-xav*R*a)*e, abs(zv)*e2
                xav,yav = -yv/R, xv/R

                total_v = math.sqrt(xv**2+yv**2+zv**2) # limiting ball speed
                if total_v > 6000:
                    xv,yv,zv = 6*xv/total_v, 6*yv/total_v, 6*zv/total_v

                total_av = math.sqrt(xav**2+yav**2+zav**2) # limiting ball spin
                if total_av > 6:
                    xav,yav,zav = 6*xav/total_av, 6*yav/total_av, 6*zav/total_av


                nV = global_space([xv,yv,zv],[0,0,0],Cl[1])
                naV = global_space([xav,yav,zav],[0,0,0],Cl[1])

                nL = L0 + V0*dt*.5
                nL = nL + nV*dt*.5

        return nL,nV,naV

    pt=[]
    for i in range(int(dt/ept)):
        cL0,cV0,caV0 = LVt(cL0,cV0,caV0,ept)
        pt.append([cL0,cV0,caV0,i*ept])

    cL0,cV0,caV0 = LVt(cL0,cV0,caV0,i*ept)
    pt.append([cL0,cV0,caV0,dt])

    return pt



def a3(V):
    a=np.zeros(3)
    try: a[0]=V[0]
    except:
        try: a[0]=V.X
        except: a[0]=V.Pitch
    try: a[1]=V[1]
    except:
        try: a[1]=V.Y
        except: a[1]=V.Yaw
    try: a[2]=V[2]
    except:
        try: a[2]=V.Z
        except:
            try :a[2]=V.Roll
            except : pass
    return a

def d3(A,B=[0,0,0]):
    A,B = a3(A),a3(B)
    return math.sqrt((A[0]-B[0])**2+(A[1]-B[1])**2+(A[2]-B[2])**2)

def sign(x):
    if x>0: return 1
    else: return -1

def Range180(value,pi):
    value = value - abs(value)//(2*pi) * (2*pi) * math.copysign(1,value)
    value = value - int(abs(value)>pi) * (2*pi) * math.copysign(1,value)
    return value
