import pyqtgraph as pg
from pyqtgraph.Qt import QtGui

import quicktracer
from quicktracer import trace
from .vector_math import *
from .tangents import TangetPath, get_tangent_paths, get_length_of_tangent_path, get_length_of_arc_0, get_length_of_arc_1, get_length_of_straight
import numpy as np

FIELD_BOUNDS = 6000


class TangentVisualizer(quicktracer.Display):
    def __init__(self):
        super().__init__()
        self.turn_circle_scatter = pg.ScatterPlotItem(pxMode=False)
        self.speed_arrows = pg.ScatterPlotItem(pxMode=False)
        self.wedge_curve_0 = pg.PlotDataItem()
        self.wedge_curve_1 = pg.PlotDataItem()
        self.tangent_curve = pg.PlotDataItem(symbol='o')
        self.path = None  #TangentPath

    @classmethod
    def accepts_value(cls, value):
        return len(value) == len(TangetPath._fields)

    def add_value(self, message):
        serialized = message[quicktracer.VALUE]
        serialized = [ np.array(x) if isinstance(x, list) else x for x in serialized ]
        self.path = TangetPath(*serialized)

    def init_view_box(self, view_box):
        view_box.invertX(True)  # make the coordinate system the same as the RocketLeague ground, viewed from above
        view_box.showGrid(x=True,y=True)
        view_box.setAspectLocked()
        view_box.setXRange(-FIELD_BOUNDS, FIELD_BOUNDS)
        view_box.setYRange(-FIELD_BOUNDS, FIELD_BOUNDS)
        view_box.addItem(self.turn_circle_scatter)
        view_box.addItem(self.wedge_curve_0)
        view_box.addItem(self.wedge_curve_1)
        view_box.addItem(self.tangent_curve)
        view_box.addItem(self.speed_arrows)

    def render(self):
        path = self.path
        if path is None:
            return
        points = [
            path.pos_0,
            path.turn_center_0,
            path.tangent_0,
            path.tangent_1,
            path.turn_center_1,
            path.pos_1,
        ]
        set_wedge_data(self.wedge_curve_0, path.pos_0, path.turn_center_0, path.tangent_0, path.clockwise_0)
        set_wedge_data(self.wedge_curve_1, path.tangent_1, path.turn_center_1, path.pos_1, path.clockwise_1)
        radius_0 = dist(path.turn_center_0, path.tangent_0)
        radius_1 = dist(path.turn_center_1, path.tangent_1)
        circles = [
            (path.turn_center_0, radius_0),
            (path.turn_center_1, radius_1),
        ]
        spots = []
        for center, radius in circles:
            spots.append({'pos': center, 'size': 2*radius, 'pen': {'color': 'w', 'width': 1}, 'brush': '#3333FF20',})
        self.turn_circle_scatter.setData(spots)

        from_pos_0 = clockwise90degrees(path.pos_0 - path.turn_center_0)
        if not path.clockwise_0:
            from_pos_0 = -from_pos_0
        angle_0 = tau/4 + vec2angle(from_pos_0)

        from_pos_1 = clockwise90degrees(path.pos_1 - path.turn_center_1)
        if not path.clockwise_1:
            from_pos_1 = -from_pos_1
        angle_1 = tau/4 + vec2angle(from_pos_1)

        # arrow_path = pg.functions.makeArrowPath(headLen=0.5, tailLen=0.25, tailWidth=0.1)
        # arrow_path.rotate(angle)
        rot_0 = clockwise_matrix(angle_0)
        arrow_path_0 = QtGui.QPainterPath()
        arrow_path_0.moveTo(*rot_0.dot(-0.5*Vec2( 0.0,  0.0)))
        arrow_path_0.lineTo(*rot_0.dot(-0.5*Vec2(-0.2, -1.0)))
        arrow_path_0.lineTo(*rot_0.dot(-0.5*Vec2( 0.2, -1.0)))
        arrow_path_0.lineTo(*rot_0.dot(-0.5*Vec2( 0.0,  0.0)))

        rot_1 = clockwise_matrix(angle_1)
        arrow_path_1 = QtGui.QPainterPath()
        arrow_path_1.moveTo(*rot_1.dot(-0.5*Vec2( 0.0,  1.0)))
        arrow_path_1.lineTo(*rot_1.dot(-0.5*Vec2(-0.2,  0.0)))
        arrow_path_1.lineTo(*rot_1.dot(-0.5*Vec2( 0.2,  0.0)))
        arrow_path_1.lineTo(*rot_1.dot(-0.5*Vec2( 0.0,  1.0)))

        speed_arrow_data = [
            {
                'pos': path.pos_0,
                'size': 3*mag(from_pos_0),
                'brush': '#4444FF70',
                'symbol': arrow_path_0,
            },
            {
                'pos': path.pos_1,
                'size': 3*mag(from_pos_1),
                'brush': '#4444FF70',
                'symbol': arrow_path_1,
            },
        ]
        self.speed_arrows.setData(speed_arrow_data)

        # part_0 = get_length_of_arc_0(path)
        # part_1 = get_length_of_straight(path)
        # part_2 = get_length_of_arc_1(path)
        # trace(part_0,    view_box='path section lengths')
        # trace(part_0 + part_1,    view_box='path section lengths')
        # trace(part_0 + part_1 + part_2, view_box='path section lengths')

        set_data_points(self.tangent_curve, points)

    def set_view_box(self, view_box):
        self.view_box = view_box
        self.init_view_box(self.view_box)

def set_data_points(view_box_data_item, points):
    view_box_data_item.setData(
        [p[0] for p in points],
        [p[1] for p in points],
    )


def set_wedge_data(wedge_curve, outer_0, center, outer_1, clockwise):
    # finish_angle = clockwise_angle_abc(outer_0, center, outer_1)
    # if not clockwise:
    #     finish_angle *= -1
    # max_angle = positive_angle(finish_angle)
    max_angle = directional_angle(outer_0, center, outer_1, clockwise)
    points = [
        outer_0,
        center,
    ]
    step_angle = tau / 31
    rotate = clockwise_matrix(step_angle if clockwise else -step_angle)
    spoke = outer_0 - center
    for i in np.arange(step_angle, max_angle, step_angle):
        spoke = rotate.dot(spoke)
        points.append(center + spoke)
        points.append(center)
    set_data_points(wedge_curve, points)
    wedge_curve.setPen(pg.mkPen(color='#FFFFFF20'))




def main():

    from pyqtgraph.Qt import QtGui, QtCore


    app = QtGui.QApplication([])
    win = pg.GraphicsWindow(title="Tangents!")
    win.resize(800,800)

    pg.setConfigOptions(antialias=True)

    vel_curve_0 = pg.PlotDataItem()
    vel_curve_1 = pg.PlotDataItem()

    view_box = win.addPlot()
    visualizer = TangentVisualizer()
    visualizer.set_view_box(view_box)

    def update(control_points):
        center_0, vel_0, center_1, vel_1 = control_points
        set_data_points(vel_curve_0, [center_0, vel_0])
        set_data_points(vel_curve_1, [center_1, vel_1])
        vel_0 = vel_0 - center_0
        vel_1 = vel_1 - center_1

        right_0 = normalize(clockwise90degrees(vel_0))
        right_1 = normalize(clockwise90degrees(vel_1))

        radius_0 = 0.5 * mag(vel_0)
        radius_1 = 0.5 * mag(vel_1)

        turn_point_r_0 = center_0 + radius_0 * right_0
        turn_point_l_0 = center_0 - radius_0 * right_0
        turn_point_r_1 = center_1 + radius_1 * right_1
        turn_point_l_1 = center_1 - radius_1 * right_1

        turn_point_0 = turn_point_r_0
        turn_point_1 = turn_point_r_1
        tangent_paths = get_tangent_paths(center_0, radius_0, right_0, center_1, radius_1, right_1)
        if not len(tangent_paths):
            return
        tangent_paths.sort(key=get_length_of_tangent_path)
        path = tangent_paths[0]
        visualizer.add_value({quicktracer.VALUE: path})
        visualizer.render_with_init(win)


    class DraggableNodes(pg.GraphItem):
        def __init__(self):
            self.dragPoint = None
            self.dragOffset = None
            pg.GraphItem.__init__(self)

        def setData(self, **kwds):
            self.text = kwds.pop('text', [])
            self.data = kwds
            if 'pos' in self.data:
                self.data['pos'] = np.array(self.data['pos'])
                npts = self.data['pos'].shape[0]
                self.data['data'] = np.empty(npts, dtype=[('index', int)])
                self.data['data']['index'] = np.arange(npts)
            self.updateGraph()

        def updateGraph(self):
            pg.GraphItem.setData(self, **self.data)
            if 'pos' not in self.data:
                return
            control_points = self.data['pos']
            update(control_points)


        def mouseDragEvent(self, ev):
            if ev.button() != QtCore.Qt.LeftButton:
                ev.ignore()
                return

            if ev.isStart():
                # We are already one step into the drag.
                # Find the point(s) at the mouse cursor when the button was first
                # pressed:
                pos = ev.buttonDownPos()
                pts = self.scatter.pointsAt(pos)
                if len(pts) == 0:
                    ev.ignore()
                    return
                self.dragPoint = pts[0]
                index = pts[0].data()[0]
                self.dragOffset = self.data['pos'][index] - pos
            elif ev.isFinish():
                self.dragPoint = None
                return
            else:
                if self.dragPoint is None:
                    ev.ignore()
                    return

            index = self.dragPoint.data()[0]

            # When dragging the centers, drag the vel with it.
            if index%2 == 0:  # car/target
                vel = self.data['pos'][index+1] - self.data['pos'][index]
                self.data['pos'][index] = ev.pos() + self.dragOffset
                self.data['pos'][index+1] = self.data['pos'][index] + vel
            else:
                self.data['pos'][index] = ev.pos() + self.dragOffset

            self.updateGraph()
            ev.accept()



    center_0 = Vec2(1, 2)
    center_1 = Vec2(7, 5.5)
    control_points = [
        center_0,
        center_0 + 1.5 * Vec2(0,1),
        center_1,
        center_1 + 2 * Vec2(0,1)
    ]
    control_points = [1000 * x for x in control_points]
    draggables = DraggableNodes()
    draggables.setData(pos=control_points, symbol='o', size=30, symbolBrush=pg.mkBrush('#FFFFFF40'))


    visualizer.render_with_init(win)
    view_box.addItem(vel_curve_0)
    view_box.addItem(vel_curve_1)
    view_box.addItem(draggables)


    update(control_points)

    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()

if __name__ == '__main__':
    main()
