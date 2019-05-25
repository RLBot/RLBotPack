import datetime
import json
import ctypes
from io import BytesIO
import base64
import glob
import os

import game_data_struct
import bot_input_struct

from ctype_utils import struct_equal

# hack the ctypes.Structure class to include printing the fields
class Struct(ctypes.Structure):
    def __repr__(self):
        '''Print the fields'''
        res = []
        for field in self._fields_:
            res.append('%s=%s' % (field[0], repr(getattr(self, field[0]))))
        return self.__class__.__name__ + '(' + ','.join(res) + ')'
    @classmethod
    def from_param(cls, obj):
        '''Magically construct from a tuple'''
        if isinstance(obj, cls):
            return obj
        if isinstance(obj, tuple):
            return cls(*obj)
        raise TypeError


class HistoryItem(Struct):
    _fields_ = [
        ('time', ctypes.c_float),
        ('game_tick_packet', game_data_struct.GameTickPacket),
        ('output_vector', bot_input_struct.PlayerInput),
    ]

    # https://stackoverflow.com/questions/7021841/get-the-binary-representation-of-a-ctypes-structure-in-python
    def encode(self):
        fakefile = BytesIO()
        fakefile.write(self)
        return base64.b64encode(fakefile.getvalue())
    @classmethod
    def decode(cls, line):
        fakefile = BytesIO(my_encoded_c_struct)
        history_item = HistoryItem()
        fakefile.readinto(history_item)
        return history_item

class History(object):
    def __init__(self):
        self.items = []
        self.start_time = -float('Inf')
        self.end_time = float('Inf')

    def append(self, item):
        self.items.append(item)

    # Slices the items non-destructively
    # Bounds are inclusive start, exclusive end
    def set_time_bounds(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time

    # time -> output_vector
    # Always includes first and last time
    def get_action_dict(self):
        # TODO cache + invalidation
        time_filtered = [
            item for item in self.items
            if self.start_time <= item.time < self.end_time
        ]
        change_filtered = [
            item for i, item in enumerate(time_filtered)
            if (
                i == 0 or
                i == len(time_filtered) - 1 or
                not struct_equal(item.output_vector, time_filtered[i-1].output_vector)
            )
        ]
        # print ('action size: {} -> {} -> {}'.format(
        #     len(self.items),
        #     len(time_filtered),
        #     len(change_filtered),
        # ))
        return { item.time: item.output_vector for item in change_filtered }

    def get_closest_game_tick_packet(self, time):
        # TODO: optimize with bisect
        time_dist, i, game_tick_packet = min((abs(time-item.time), i, item.game_tick_packet) for i,item in enumerate(self.items))
        return game_tick_packet




    def save(self):
        file_name = datetime.datetime.now().isoformat().replace(':', '-')
        base_path = os.path.dirname(__file__)
        descriptor_file_path = os.path.realpath(os.path.join(base_path, 'histories/descriptors/{}.json'.format(file_name)))
        items_file_name = 'histories/history_items/{}.bin'.format(file_name)
        with open(descriptor_file_path, 'w') as f:
            descriptor = {
                'start_time': self.start_time,
                'end_time': self.end_time,
                'items_file_name': items_file_name,
            }
            json.dump(descriptor, f, indent=2)
        with open(os.path.join(base_path, items_file_name), 'wb') as f:
            for item in self.items:
                f.write(item)

    def load(self, descriptor_file_path=None):
        base_path = os.path.dirname(__file__)

        # Load the most recent, if descriptor is not given.
        if descriptor_file_path is None:
            descriptor_paths = glob.glob(os.path.join(base_path, 'histories/descriptors/*')) # * means all if need specific format then *.csv
            if not descriptor_paths:
                return
            descriptor_file_path = max(descriptor_paths, key=os.path.getmtime)

        with open(descriptor_file_path) as f:
            descriptor = json.load(f)
            self.start_time = descriptor['start_time']
            self.end_time = descriptor['end_time']
            items_file_name = descriptor['items_file_name']

        with open(os.path.realpath(os.path.join(base_path, items_file_name)), 'rb') as f:
            self.items = []
            while True:
                item = HistoryItem()
                bytes_read = f.readinto(item)
                if not bytes_read:
                    break
                self.items.append(item)

