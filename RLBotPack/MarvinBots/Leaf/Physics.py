from util import *


r, gc = 0.0306, -650            # air resistance, gravity constant
e2, e1, a = .6, .714, .4        # bounce & min friction factor, spIn inertia thingy
R = 93                          # ball radius
wx, wy, wz = 4100, 5120, 2052   # wall locations
gx, gz = 1792, 640              # goal dimensions
cR, cR2, cR3 = 520, 260, 190    # ramp radii
dR = 8060                       # diamond "radius"

# circle/ramp locations
cx, cy, cz = wx - cR, wy - cR, wz - cR
cx2, cz2 = wx - cR2, cR2
cy3, cz3 = wy - cR3, cR3

gravity = np.array([0, 0, gc])


class ColState():
    def __init__(self, hasCollided=False, Location=np.zeros(3), Rotation=np.zeros(3)):
        self.hasCollided = bool(hasCollided)
        self.Location = a3(Location)
        self.Rotation = a3(Rotation)


def local_space(tL, oL, oR):  # used with the collision surfaces
    L = tL - oL
    L[0], L[1] = rotate2D(L[0], L[1], -oR[0] * PI / 180)
    L[1], L[2] = rotate2D(L[1], L[2], -oR[1] * PI / 180)
    L[0], L[2] = rotate2D(L[0], L[2], -oR[2] * PI / 180)
    return L


def global_space(L, oL, oR):
    tL = np.zeros(3)
    tL[0], tL[2] = rotate2D(L[0], L[2], oR[2] * PI / 180)
    tL[1], tL[2] = rotate2D(L[1], tL[2], oR[1] * PI / 180)
    tL[0], tL[1] = rotate2D(tL[0], tL[1], oR[0] * PI / 180)
    return tL + oL


def CollisionFree(L):
    if 242 < L[2] < 1833:
        if abs(L[0]) < 3278:
            if abs(L[1]) < 4722:
                if (abs(L[0]) + abs(L[1])) / 7424 <= 1:
                    return True
    return False


def Collision_Model(L, R=R):

    x, y, z = a3(L)
    Cl = ColState()

    # Top Ramp X-axis
    if abs(x) > wx - cR and z > cz and (abs(x) - cx)**2 + (z - cz)**2 > (cR - R)**2:
        a = math.atan2(z - cz, abs(x) - cx)
        Cl.hasCollided = True
        Cl.Location[0] = (cR * math.cos(a) + cx) * sign(x)
        Cl.Location[1] = y
        Cl.Location[2] = cR * math.sin(a) + cz
        Cl.Rotation = np.array([0, 0, (90 + a / PI * 180) * sign(x)])
        return Cl

    # Top Ramp Y-axis
    if abs(y) > cy and z > cz and (abs(y) - cy)**2 + (z - cz)**2 > (cR - R)**2:
        a = math.atan2(z - cz, abs(y) - cy)
        Cl.hasCollided = True
        Cl.Location[0] = x
        Cl.Location[1] = (cR * math.cos(a) + cy) * sign(y)
        Cl.Location[2] = cR * math.sin(a) + cz
        Cl.Rotation = np.array([0, (90 + a / PI * 180) * sign(y), 0])
        return Cl

    # Bottom Ramp X-axis
    if abs(x) > cx2 and z < cz2 and (abs(x) - cx2)**2 + (z - cz2)**2 > (cR2 - R)**2:
        a = math.atan2(z - cz2, abs(x) - cx2)
        Cl.hasCollided = True
        Cl.Location[0] = (cR2 * math.cos(a) + cx2) * sign(x)
        Cl.Location[1] = y
        Cl.Location[2] = cR2 * math.sin(a) + cz2
        Cl.Rotation = np.array([0, 0, (90 + a / PI * 180) * sign(x)])
        return Cl

    # Bottom Ramp Y-axis
    if abs(y) > cy3 and z < cz3 and abs(x) > gx / 2 - R / 2 and (abs(y) - cy3)**2 + (z - cz3)**2 > (cR3 - R)**2:
        a = math.atan2(z - cz3, abs(y) - cy3)
        Cl.hasCollided = True
        Cl.Location[0] = x
        Cl.Location[1] = (cR3 * math.cos(a) + cy3) * sign(y)
        Cl.Location[2] = cR3 * math.sin(a) + cz3
        Cl.Rotation = np.array([0, (90 + a / PI * 180) * sign(y), 0])
        return Cl

    # 45° Top Ramp
    if abs(x) + abs(y) + R >= dR - cR and z > cz and (abs(x) + abs(y) - (dR - cR * SQ2))**2 + (z - cz2)**2 > (cR - R)**2:
        a = math.atan2(z - cz, abs(abs(x) + abs(y) - (dR - cR * SQ2)))
        Cl.hasCollided = True
        Cl.Rotation = np.array([-45 * sign(x) * sign(y), (90 + a / PI * 180) * sign(y), 0])
        oL = np.array([(dR - cR * SQ2) * sign(x), 0, cz])  # circle origin
        sL = local_space(L, oL, Cl.Rotation)
        sL[2] = - cR
        Cl.Location = global_space(sL, oL, Cl.Rotation)
        return Cl

    # 45° Bottom Ramp
    if abs(x) + abs(y) + R >= dR - cR2 and z < cz2 and (abs(x) + abs(y) - (dR - cR2 * SQ2))**2 + (z - cz2)**2 > (cR2 - R)**2:
        a = math.atan2(z - cz2, abs(abs(x) + abs(y) - (dR - cR2 * SQ2)))
        Cl.hasCollided = True
        Cl.Rotation = np.array([-45 * sign(x) * sign(y), (90 + a / PI * 180) * sign(y), 0])
        oL = np.array([(dR - cR2 * SQ2) * sign(x), 0, cR2])  # circle origin
        sL = local_space(L, oL, Cl.Rotation)
        sL[2] = - cR2
        Cl.Location = global_space(sL, oL, Cl.Rotation)
        return Cl

    # Flat 45° Corner
    if abs(x) + abs(y) + R >= dR:
        Cl.hasCollided = True
        Cl.Rotation = np.array([-45 * sign(x) * sign(y), 90 * sign(y), 0])
        dL = np.array([dR * sign(x), 0, 0])  # a point in the surface of the diamond
        sL = local_space(L, dL, Cl.Rotation)
        sL[2] = 0  # projection
        Cl.Location = global_space(sL, dL, Cl.Rotation)
        return Cl

    # Floor
    if z < R:
        Cl.hasCollided = True
        Cl.Location = np.array([x, y, 0])
        Cl.Rotation = np.zeros(3)
        return Cl

    # Flat Wall X-axis
    if abs(x) > wx - R:
        Cl.hasCollided = True
        Cl.Location = np.array([wx * sign(x), y, z])
        Cl.Rotation = np.array([0, 0, 90 * sign(x)])
        return Cl

    # Flat Wall Y-axis
    if abs(y) > wy - R and (abs(x) > gx / 2 - R / 2 or z > gz - R / 2):
        Cl.hasCollided = True
        Cl.Location = np.array([x, wy * sign(y), z])
        Cl.Rotation = np.array([0, 90 * sign(y), 0])
        return Cl

    # Ceiling
    if z > wz - R:
        Cl.hasCollided = True
        Cl.Location = np.array([x, y, wz])
        Cl.Rotation = np.array([0, 0, 180])
        return Cl

    # no collision
    Cl.hasCollided = False
    Cl.Location = np.zeros(3)
    Cl.Rotation = np.zeros(3)
    return Cl


def simple_step(L0, V0, dt, g=gravity):

    Acc = g - 0.0202 * V0
    nV = V0 + Acc * dt
    nL = L0 + V0 * dt + 0.5 * Acc * dt ** 2

    return nL, nV


def time_solve_z(z, zv, terminal_z, g=gravity[2]):  # 1 dimensional solve for simple step location

    a = z * 0.0202 - 0.5 * g
    b = -zv
    c = -z + terminal_z

    return quadratic_pos(a, b, c)


def quadratic_pos(a, b, c):
    s, s1, s2 = -1, -1, -1
    if a != 0 and b * b - 4 * a * c >= 0:
        s1 = (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)
        s2 = (-b - math.sqrt(b * b - 4 * a * c)) / (2 * a)
        if s1 > 0 and s2 > 0:
            s = min(s1, s2)
        else:
            s = max(s1, s2)
    return s


def VN(V0, N, ept=1 / 120, g=gravity):
    return V0 * (1 - r * ept)**N + (g / r) * (1 - (1 - r * ept)**N)


def SVN(V0, N, ept=1 / 120, g=gravity):
    return (V0 - g / r) * (1 - (1 - r * ept)**N) * (1 / (r * ept) - 1) + (g / r) * N


def LN(L0, V0, N, ept=1 / 120, g=gravity):
    return L0 + 0.5 * (V0 + 2 * SVN(V0, N - 1, ept, g) + VN(V0, N, ept, g)) * ept


def LN2(L0, V0, N, VN, ept=1 / 120, g=gravity):
    return L0 + 0.5 * (V0 + 2 * SVN(V0, N - 1, ept, g) + VN) * ept


def approx_step(L0, V0, dt, ept=1 / 120, g=gravity):
    N = dt / ept
    nV = VN(V0, N, ept, g)
    return LN2(L0, V0, N, nV, ept, g), nV


def stepBall(L0, V0, AV0, dt, g=gravity):

    Acc = g - r * V0
    nV = V0 + Acc * dt
    nL = L0 + V0 * dt + .5 * Acc * dt**2
    nAV = AV0

    if not CollisionFree(nL):

        Cl = Collision_Model(nL)

        if Cl.hasCollided:

            # transorforming stuff to local space
            lV = local_space(V0, 0, Cl.Rotation)
            lAV = local_space(AV0, 0, Cl.Rotation)
            lL = local_space(L0, Cl.Location, Cl.Rotation)

            if abs(lV[2]) > 1:
                # small step towards contact point
                lG = local_space(g, 0, Cl.Rotation)
                cTime = Range(time_solve_z(lL[2], lV[2], R, lG[2]), dt)
                lL, lV = simple_step(lL, lV, cTime, lG)
                dt -= cTime

            lL[2] = R  # should be above surface

            s = a2(lV) + np.array([-lAV[1] * R, lAV[0] * R])

            p = min(2 * abs(lV[2]) / (dist2d(s) + 1e-9), 1) * 0.285

            # applying bounce friction and spin
            lV[0] -= s[0] * p
            lV[1] -= s[1] * p

            # perpendicular bounce
            lV[2] = abs(lV[2]) * e2

            # Angular velocity
            lAV[0] = -lV[1] / R
            lAV[1] = lV[0] / R

            # transorforming stuff back to global/world space
            nV = global_space(lV, 0, Cl.Rotation)
            nAV = global_space(lAV, 0, Cl.Rotation)
            nL = global_space(lL, Cl.Location, Cl.Rotation)

            # continue step for what's left
            Acc = g - r * nV
            nV = nV + Acc * dt
            nL = nL + nV * dt + 0.5 * Acc * dt ** 2

    # limiting ang vel
    total_av = dist3d(nAV)
    if total_av > 6:
        nAV *= 6 / total_av

    # limiting vel
    total_v = dist3d(nV)
    if total_v > 6000:
        nV *= 6000 / total_v

    return nL, nV, nAV


def stepCar(L0, V0, dt, throttle=0):

    Acc = - r * V0
    nV = V0 + Acc * dt
    nL = L0 + V0 * dt + .5 * Acc * dt**2

    return nL, nV


def predict_sim(L0, V0, aV0, dt, ept=1 / 120):

    cL0, cV0, caV0 = L0, V0, aV0

    pt = []
    for i in range(int(dt / ept)):
        cL0, cV0, caV0 = stepBall(cL0, cV0, caV0, ept)
        pt.append([cL0, cV0, caV0])

    # if dt%ept>0:
    cL0, cV0, caV0 = stepBall(cL0, cV0, caV0, dt % ept)
    pt.append([cL0, cV0, caV0])

    return pt
