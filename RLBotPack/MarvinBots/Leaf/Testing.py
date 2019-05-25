import time
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from util import *
from PhysicsLib import *
# from Physics import predict_sim


def graph_path(s):

    s.boost = 0
    if s.counter < 9:
        s.boost = s.counter % 2  # move to start

    if s.counter == 9:  # init state
        s.gt = []  # ground truth
        s.init_time = s.time
        s.init_state = s.ball
        s.gt.append([s.bL, s.bV, s.baV])
        print("Initial State:", s.gt[0])

    if s.counter > 9:
        s.gt.append([s.bL, s.bV, s.baV])  # record real ball path

    if s.counter > 509:  # generate predicion and graph results

        tbefore = time.time()

        dt = s.time - s.init_time
        pr = predict_sim(*s.gt[0], dt)  # generate prediction

        print("Generated prediction in {} seconds.".format(time.time() - tbefore))

        fig = plt.figure()
        ax = fig.gca(projection='3d')

        g = 0  # 0 to graph location, 1 for velocity, 2 for angular velocity

        if g == 0:
            ax.set_xlim3d(-4500, 4500)
            ax.set_ylim3d(-5500, 5500)
            ax.set_zlim3d(-100, 2500)

        ax.plot([i[g][0] for i in s.gt], [i[g][1] for i in s.gt], [i[g][2] for i in s.gt], label="Ground Truth")
        ax.plot([i[g][0] for i in pr], [i[g][1] for i in pr], [i[g][2] for i in pr], label="Predicted")

        print("Final state..\n GroundTruth: {}\n Prediction : {}".format(pr[-1][g], s.gt[-1][g]))
        print("Final Error =", dist3d(pr[-1][g], s.gt[-1][g]))

        plt.legend()
        plt.show()
        plt.pause(300)


def graph_Carpath(s):

    s.boost = 0
    if s.counter < 9:
        s.boost = s.counter % 2  # move to start

    if s.counter == 9:  # init state
        s.gt = []  # ground truth
        s.init_time = s.time
        s.init_state = s.player
        s.gt.append([s.pL, s.pV])
        print("Initial State:", s.gt[0])

    if s.counter > 9:
        s.gt.append([s.pL, s.pV])  # record real ball path

    if s.counter > 509:  # generate predicion and graph results

        tbefore = time.time()

        dt = s.time - s.init_time
        pr = predict_CarSim(*s.gt[0], dt)  # generate prediction

        print("Generated prediction in {} seconds.".format(time.time() - tbefore))

        fig = plt.figure()
        ax = fig.gca(projection='3d')

        g = 0  # 0 to graph location, 1 for velocity

        if g == 0:
            ax.set_xlim3d(-5500, 5500)
            ax.set_ylim3d(-5500, 5500)
            ax.set_zlim3d(-100, 2500)

        ax.plot([i[g][0] for i in s.gt], [i[g][1] for i in s.gt], [i[g][2] for i in s.gt], label="Ground Truth")
        ax.plot([i[g][0] for i in pr], [i[g][1] for i in pr], [i[g][2] for i in pr], label="Predicted")

        print("Final state..\n GroundTruth: {}\n Prediction : {}".format(pr[-1][g], s.gt[-1][g]))
        print("Final Error =", dist3d(pr[-1][g], s.gt[-1][g]))

        plt.legend()
        plt.show()
        plt.pause(300)


FILENAME = "output.txt"


def record_data(s):

    data_format = "vy\tlast_vy\tlast_vz"

    if s.counter < 9:
        s.boost = s.counter % 2  # move to start

    if s.counter == 9:
        s.start_time = s.time
        print("starting")
        # print_and_append(data_format)
        s.last_printed = data_format

    if s.counter > 9:
        data = str(s.bV[1]) + "\t" + str(s.lbV[1]) + "\t" + str(s.lbV[2])
        if data != s.last_printed and sign(s.bV[2]) != sign(s.lbV[2]):
            print_and_append(data)
            print("e :", s.bV[1] / s.lbV[1])
            s.last_printed = data

    if s.counter > 209:
        # print_and_append("\n")
        print("done")
        time.sleep(300)

    s.lbV = s.bV


def print_and_append(string):
    string = string.replace(".", ",")  # for excel floats
    print(string)
    with open(FILENAME, "a") as f:
        f.write(string + "\n")


def boost_rate(s):

    s.boost = 1

    if s.counter == 1:
        s.ipB = s.pB
        s.itime = s.time

    if s.counter > 1 and s.dtime != 0:
        print((s.pyv - s.lpyv) / s.dtime)  # boost acc rate

    s.lpyv = s.pyv
