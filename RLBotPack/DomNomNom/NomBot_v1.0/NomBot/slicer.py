import threading
from subprocess import Popen, PIPE, TimeoutExpired, STARTUPINFO, STARTF_USESHOWWINDOW
import time
import os
import sys
import atexit
import collections
import json

from slicer_constants import MIN_X, MAX_X, POS, SET_SPOTS, SET_REGION, PLAYBACK_MARKER, TIME_IN_HISTORY

class Slicer(object):
    def __init__(self):
        self.min_x = 0
        self.max_x = 1
        self.child_process = None
        self.have_notified_about_child_dying = False
        self.min_max_callback = lambda min, max: None
        self.start_gui_subprocess()

    def set_positions(self, positions):
        '''slicer.set_spots([[0, 0], [2, 1], [3, 1]])'''
        spots = [ {POS: pos} for pos in positions ]
        self.send_message({SET_SPOTS: spots})

    def set_min_max(self, min_x, max_x):
        self.send_message({SET_REGION: {MIN_X:min_x, MAX_X:max_x}})
    def set_playback_marker(self, time_in_history):
        self.send_message({PLAYBACK_MARKER: {TIME_IN_HISTORY: time_in_history}})

    def send_message(self, data):
        line = json.dumps(data) + '\n'
        # print (line)
        message = line.encode('utf-8')
        try:
            self.child_process.stdin.write(message)
            self.child_process.stdin.flush()
        except Exception as e:
            if self.have_notified_about_child_dying: return
            self.have_notified_about_child_dying = True
            raise Exception("=== slicer GUI died ===")

    def register_min_max_callback(self, callback):
        self.min_max_callback = callback

    def process_messages_from_gui(self, stream):
        for line in stream:
            line = line.decode('utf-8')
            json_data = json.loads(line)
            if MIN_X in json_data: self.min_x = json_data[MIN_X]
            if MAX_X in json_data: self.max_x = json_data[MAX_X]
            self.min_max_callback(self.min_x, self.max_x)


    def start_gui_subprocess(self):
        # Create a new process such that QT doesn't complain about not being in the main thread
        quicktracer_dir = os.path.dirname(os.path.realpath(__file__))

        self.child_process = Popen(
            'python slicer_gui.py',
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            cwd=quicktracer_dir,
        )
        atexit.register(lambda: self.child_process.kill())  # behave like a daemon
        self.read_out = threading.Thread(target=self.process_messages_from_gui, args=[self.child_process.stdout], daemon=True)
        self.read_out.start()
        self.read_err = threading.Thread(target=print_stderr, args=[self.child_process.stderr], daemon=True)
        self.read_err.start()

    def close_window(self):
        self.child_process.kill()  # MURDER!

def print_stderr(f):
    for line in f:
        print(line.decode('utf-8').rstrip(), file=sys.stderr)
        sys.stderr.flush()

def main():
    # Demo: Show some dummy data
    positions = [
        [-1, -0.5],
        [0, 0],
        [2, 1],
        [3, 1],
    ]
    xs = [pos[0] for pos in positions]

    def on_min_max_change(min_x, max_x):
        print('heya', min_x, max_x)

    slicer = Slicer()
    slicer.set_positions(positions)
    slicer.set_min_max(min(xs), 0.7*max(xs))
    slicer.register_min_max_callback(on_min_max_change)

    import time
    time.sleep(100)

if __name__ == '__main__':
    main()
