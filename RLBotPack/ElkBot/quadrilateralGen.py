import pprint

points = []
xs = []
ys = []

for i in range(2):
    xs.append(int(input("Enter an x value: ")))

for i in range(2):
    ys.append(int(input("Enter an y value: ")))

points.append([xs[0], ys[0]])
points.append([xs[1], ys[0]])
points.append([xs[1], ys[1]])
points.append([xs[0], ys[1]])
pprint.pprint(points, indent=4, compact=False)