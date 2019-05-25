import ctypes
import os

from util import a3

CAR_FRICTION = 0

MAX_BALL_STATES = 999


class Vector3(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float),
                ("y", ctypes.c_float),
                ("z", ctypes.c_float)]


class BallState(ctypes.Structure):
    _fields_ = [("Location", Vector3),
                ("Velocity", Vector3),
                ("AngularVelocity", Vector3)]


class BallPath(ctypes.Structure):
    _fields_ = [("ballstates", BallState * MAX_BALL_STATES),
                ("numstates", ctypes.c_int)]


class CarState(ctypes.Structure):
    _fields_ = [("Location", Vector3),
                ("Velocity", Vector3)]


class InterceptState(ctypes.Structure):
    _fields_ = [("Ball", BallState),
                ("Car", CarState),
                ("dt", ctypes.c_float)]


# import dll
directory = os.path.dirname(os.path.realpath(__file__))
dllpath = os.path.join(directory, "PhysicsLibrary.dll")
PhyLib = ctypes.CDLL(dllpath)

# test function
# PhyLib.connect()

# input & output types
PhyLib.predictPath.argtypes = [BallState, ctypes.c_float, ctypes.c_float, ctypes.c_float]
PhyLib.predictPath.restype = BallPath

PhyLib.ballStep.argtypes = [BallState, ctypes.c_float, ctypes.c_float]
PhyLib.ballStep.restype = BallState

PhyLib.carStep.argtypes = [CarState, ctypes.c_float, ctypes.c_float, ctypes.c_float]
PhyLib.carStep.restype = CarState

PhyLib.intercept.argtypes = [BallState, CarState, ctypes.c_float, ctypes.c_float, ctypes.c_float]
PhyLib.intercept.restype = InterceptState


def ar(V):
    return [V.x, V.y, V.z]


def state_bar(st):  # nested array from struct
    return [ar(st.Location), ar(st.Velocity), ar(st.AngularVelocity)]


def state_ba3(st):  # nested numpy array
    return [a3(st.Location), a3(st.Velocity), a3(st.AngularVelocity)]


def state_ca3(st):  # nested numpy array
    return [a3(st.Location), a3(st.Velocity)]


def predictPath(L0, V0, AV0, dt, tps, g):  # tuples or numpy arrays for the arguments
    init_state = BallState(Vector3(*L0), Vector3(*V0), Vector3(*AV0))
    return PhyLib.predictPath(init_state, dt, tps, g)  # returns BallPath struct


def predictPath2(ball, dt, tps, g):  # you can use gameball from gametickpacket as an argument.
    init_state = BallState(Vector3(*ar(ball.Location)), Vector3(*ar(ball.Velocity)), Vector3(*ar(ball.AngularVelocity)))
    return PhyLib.predictPath(init_state, dt, tps, g)


def intercept(gameball, gamecar, dt, tps, g, cf=CAR_FRICTION):
    ball = BallState(Vector3(*ar(gameball.Location)), Vector3(*ar(gameball.Velocity)),
                     Vector3(*ar(gameball.AngularVelocity)))
    car = CarState(Vector3(*ar(gamecar.Location)), Vector3(*ar(gamecar.Velocity)))
    return PhyLib.intercept(ball, car, dt, tps, g, cf)   # returns InterceptState


def intercept2(bL, bV, bAV, pL, pV, dt, tps, g, cf=CAR_FRICTION):
    ball = BallState(Vector3(*bL), Vector3(*bV), Vector3(*bAV))
    car = CarState(Vector3(*pL), Vector3(*pV))
    return PhyLib.intercept(ball, car, dt, tps, g, cf)


def predict_sim(L0, V0, AV0, dt, ept, g):

    init_state = BallState(Vector3(*L0), Vector3(*V0), Vector3(*AV0))

    Path = PhyLib.predictPath(init_state, dt, 1 / ept, g)

    pt = []  # constructing and appending to a nested array, can be a bit slow.
    for i in range(Path.numstates):
        pt.append([*state_ba3(Path.ballstates[i]), (i + 1) * ept])

    return pt


def predict_BallSim(L0, V0, AV0, dt, ept, g):

    st = BallState(Vector3(*L0), Vector3(*V0), Vector3(*AV0))

    pt = []
    for i in range(int(dt / ept)):
        st = PhyLib.ballStep(st, ept, g)  # calling the step function
        pt.append(state_ba3(st))

    # if dt%ept>0:
    st = PhyLib.ballStep(st, dt % ept, g)
    pt.append(state_ba3(st))

    return pt


def predict_CarSim(L0, V0, dt, ept, g, cf=CAR_FRICTION):

    st = CarState(Vector3(*L0), Vector3(*V0))

    pt = []
    for i in range(int(dt / ept)):
        st = PhyLib.carStep(st, ept, g, cf)  # calling the step function
        pt.append([a3(st.Location), a3(st.Velocity)])

    # if dt%ept>0:
    st = PhyLib.carStep(st, dt % ept, g, cf)
    pt.append([a3(st.Location), a3(st.Velocity)])

    return pt


def predict_CarLoc(L0, V0, dt, ept, g, cf=CAR_FRICTION):

    st = CarState(Vector3(*L0), Vector3(*V0))

    for i in range(int(dt / ept)):
        st = PhyLib.carStep(st, ept, g, cf)  # calling the step function

    # if dt%ept>0:
    st = PhyLib.carStep(st, dt % ept, g, cf)

    return a3(st.Location)


def ballStep(L0, V0, AV0, dt, g):
    return state_ba3(PhyLib.ballStep(BallState(Vector3(*L0), Vector3(*V0), Vector3(*AV0)), dt, g))


def CarStep(L0, V0, dt, g, cf=CAR_FRICTION):
    return state_ca3(PhyLib.carStep(CarState(Vector3(*L0), Vector3(*V0)), dt, g, cf))
