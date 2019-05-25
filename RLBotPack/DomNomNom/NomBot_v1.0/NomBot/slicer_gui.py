import threading
import numpy as np
import json
import sys
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph.Point import Point
import traceback
from slicer_constants import MIN_X, MAX_X, POS, SET_SPOTS, SET_REGION, PLAYBACK_MARKER, TIME_IN_HISTORY


spots = [{POS: [0, 0]}, {POS: [2, 1]}]
region = None
scatter_plot = None
# playback_marker_scatter = None

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
    sys.stderr.flush()


def update():
    global region
    region.setZValue(10)
    min_x, max_x = region.getRegion()
    print(json.dumps({MIN_X: min_x, MAX_X: max_x}))
    sys.stdout.flush()

def set_spots(spots_json):
    global spots
    spots = spots_json
    scatter_plot.setData(spots)

def set_region(region_json):
    global spots
    global region
    min_x = region_json[MIN_X]
    max_x = region_json[MAX_X]
    if not np.isfinite(min_x): min_x = min(spot[POS][0] for spot in spots)
    if not np.isfinite(max_x): max_x = max(spot[POS][0] for spot in spots)

    region.setRegion([min_x, max_x])

def set_playback_marker(playback_marker_json):
    global playback_marker
    global view_box
    # This shit makes the gui freeze after a while for some reason

    # time_in_history = playback_marker_json[TIME_IN_HISTORY]
    # if time_in_history < -1000:
    #     return
    # min_x, max_x = region.getRegion()
    # time_in_history = min(max_x, max(min_x, time_in_history))
    # playback_spots = [ {POS: (time_in_history, i)} for i in range(7) ]
    # playback_marker_scatter.setData(playback_spots)
    # eprint(time_in_history)
    # playback_marker.setPos((time_in_history,0))
    # eprint (playback_marker_json)

def read_input():
    try:
        while True:
            try:
                line = input()
            except EOFError as e:
                return
            message = json.loads(line)
            if SET_SPOTS in message:
                set_spots(message[SET_SPOTS])
            elif SET_REGION in message:
                set_region(message[SET_REGION])
            elif PLAYBACK_MARKER in message:
                set_playback_marker(message[PLAYBACK_MARKER])
            else:
                eprint('bad message: ', message)
    except Exception as e:
        traceback.print_exc()
        sys.stderr.flush()
        os.exit(-1)


class NonFocusStealingGraphicsWindow(pg.GraphicsWindow):
    def show(self):
        self.setAttribute(98) # Qt::WA_ShowWithoutActivating
        super().show()


def main():
    global region
    global scatter_plot
    global view_box


    # window layout
    app = QtGui.QApplication([])
    win = NonFocusStealingGraphicsWindow(title='Slicer')
    win.setGeometry(0, 660, 600, 380)

    label = pg.LabelItem(justify='right')
    win.addItem(label)
    view_box = win.addPlot(row=1, col=0)

    region = pg.LinearRegionItem()
    region.setZValue(10)
    region.sigRegionChanged.connect(update)
    # Add the LinearRegionItem to the ViewBox, but tell the ViewBox to exclude this
    # item when doing auto-range calculations.
    view_box.addItem(region, ignoreBounds=True)


    # pg.dbg()
    scatter_plot = pg.ScatterPlotItem(size=10, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 255, 120))
    set_spots(spots)
    view_box.addItem(scatter_plot)

    # playback_marker = pg.InfiniteLine(pos=(0,0), angle=30)
    # view_box.addItem(playback_marker)
    # global playback_marker_scatter
    # playback_marker_scatter = pg.ScatterPlotItem(size=10, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 255, 120))
    # view_box.addItem(playback_marker_scatter)

    threading.Thread(target=read_input, daemon=True).start()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()


## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    main()
