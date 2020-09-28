import pynmea2
import re
from datetime import datetime
import csv
import matplotlib.pyplot as plt
import numpy as np
import math
import matplotlib.dates as mdate
import time
import pytz

#                             $EULV,x_yaw,0.0000,y_pitch,0.0000,z_roll,0.0000
euler_pattern = re.compile("^\$EULV,x_yaw,([0-9.-]+),y_pitch,([0-9.-]+),z_roll,([0-9.-]+)$")
#                             $QUAT,w,0.0000,x,0.0000,y,0.0000,z,0.0000
quatu_pattern = re.compile("^\$QUAT,w,([0-9.-]+),x,([0-9.-]+),y,([0-9.-]+),z,([0-9.-]+)$")

class IMUDataPacket(object):
    """docstring for IMUDataPacket"""
    def __init__(self, raw, time):
        super(IMUDataPacket, self).__init__()
        self.raw = raw
        self.dt  = time

        if euler_pattern.match(self.raw):
            match = euler_pattern.match(self.raw)
            self._type = 'EULER'
            x, y, z = match.groups()
            self._set_euler_angles(float(x), float(y), float(z))
        elif quatu_pattern.match(self.raw):
            match = quatu_pattern.match(self.raw)
            self._type = 'QUATERNION'
            w, x, y, z = match.groups()
            self._set_rpy_quat(float(w), float(x), float(y), float(z))
        else:
            raise ValueError('The raw data does not match the EULER or QUATERNION pattern!\n{}'.format(self.raw))

    @property
    def header(self):
        return(['timestamp','type','roll','pitch','yaw','w','x','y','z','raw'])

    @property
    def as_row(self):
        return([self.dt,
                self._type,
                self.roll,
                self.pitch,
                self.yaw,
                self.w,
                self.x,
                self.y,
                self.z,
                self.raw])

    def _set_euler_angles(self, x, y, z):
        self.w = None # quat has w component
        self.x = x
        self.y = y
        self.z = z 
        # get roll/pitch/yaw from euler angles
        self.roll  = math.degrees(x)
        self.pitch = math.degrees(y)
        self.yaw   = math.degrees(z)

    def _set_rpy_quat(self, w, x, y, z):
        self.w = w
        self.x = x
        self.y = y
        self.z = z 
        # get roll/pitch/yaw from quaturnion
        self.roll  = math.atan2(2.0*(x*y + w*z), w*w + x*x - y*y - z*z)
        self.pitch = math.asin(-2.0*(x*z - w*y))
        self.yaw   = math.atan2(2.0*(y*z + w*x), w*w - x*x - y*y + z*z)


class IMULogParser(object):
    """docstring for IMULogParser"""
    def __init__(self, log_file, use_euler=True):
        super(IMULogParser, self).__init__()
        self.log_file = log_file
        self._data_set = None
        self.preferred_type = 'EULER' if use_euler else 'QUATERNION'

    @property
    def data_set(self):
        return(self._data_set)

    def parse(self, required_fields, start=0, end=9000000000.0):
        # grab everything first
        parsed_data = self._get_in_window(start, end)
        packets = self._create_data_packets(parsed_data)
        # TODO: only create data packets for times we care about
        # sort through and add only the packets to data_set that fall in window
        self._data_set = {
            '_packets': []
        }
        for field in required_fields:
            self._data_set[field] = []

        for packet in packets:
            if packet.dt.timestamp() >= start and\
               packet.dt.timestamp() <= end:
                if packet._type == self.preferred_type:
                    self._data_set['_packets'].append(packet)
                    # now get required field data
                    for field in required_fields:
                        if field == 'timestamp':
                            # hack since datetime obj is called dt not timestamp
                            self._data_set[field].append(packet.dt)
                        else:
                            self._data_set[field].append(getattr(packet, field))

        if len(self._data_set['_packets']) <= 0:
            raise RuntimeError('No IMU data in the provided window!')

        return(self._data_set, packets[0].dt)

    def _create_data_packets(self, parsed_data):
        # now iterate through and create IMUDataPacket objs for each row
        packets = []
        for dt, raw in zip(parsed_data['timestamp'], parsed_data['raw']):
            try:
                dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                try:
                    dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    # malformed datetime string
                    # TODO: report bad rows
                    continue
            # print('---------------------------------------------------')
            # print('{} Timezone: {}'.format(dt, dt.tzinfo))
            # # set correct timezone
            # dt = dt.replace(tzinfo=pytz.timezone('US/Eastern'))
            # print('{} Timezone: {}'.format(dt, dt.tzinfo))
            packets.append(IMUDataPacket(raw=raw, time=dt))
        return(packets)

    def _get_in_window(self, start, end):
        with open(self.log_file, mode='r') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            for i, row in enumerate(csv_reader):
                if i == 0:
                    # first line is header or keys
                    # .. set keys and starting val for empty list
                    parsed_data = dict((key, []) for key in row)
                    continue
                for col_name, col_val in row.items():
                    # check if time is within bounds
                    if col_name == 'timestamp':
                        try:
                            dt = datetime.strptime(col_val, '%Y-%m-%d %H:%M:%S.%f')
                        except ValueError:
                            try:
                                dt = datetime.strptime(col_val, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                # malformed datetime string
                                # TODO: report bad rows
                                break

                    if dt.timestamp() >= start and\
                       dt.timestamp() <= end:
                        # all data is stored as a string initially for simplicity
                        parsed_data[col_name].append(col_val)
        return(parsed_data)

    def _get_all(self):
        with open(self.log_file, mode='r') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            for i, row in enumerate(csv_reader):
                if i == 0:
                    # first line is header or keys
                    # .. set keys and starting val for empty list
                    parsed_data = dict((key, []) for key in row)
                    continue
                for col_name, col_val in row.items():
                    # all data is stored as a string initially for simplicity
                    parsed_data[col_name].append(col_val)
        return(parsed_data)
        

class IMUPlotter(object):
    """docstring for IMUPlotter"""
    def __init__(self, data_set):
        super(IMUPlotter, self).__init__()
        if data_set == None:
            raise ValueError('Null dataset provided! (Has the log file been parsed?)')
        else:
            self.data_set = data_set

    def plot(self, ax):
        # time_ax, data, xlabel, ylabel, date_formatter = self.get_axes()
        time_ax, data, xlabel, ylabel = self.get_axes()
        for d in data:
            ax.plot_date(time_ax, d[0], d[1], label=d[2], markersize=1.5)

        # ax.xaxis.set_major_formatter(date_formatter)
        # label axes
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.legend(markerscale=6)
        # return(ax, True)
        return(ax, False)

    def get_axes(self):
        data = []
        data.append((self.data_set['roll'], 'b,', 'Roll'))
        # data.append(([p.x for p in self.data_set['_packets']], 'b', 'Roll - Degrees'))
        data.append((self.data_set['pitch'], 'g,', 'Pitch'))
        # data.append(([p.y for p in self.data_set['_packets']], 'g', 'Pitch - Degrees'))
        data.append((self.data_set['yaw'], 'r,', 'Yaw'))
        # data.append(([p.z for p in self.data_set['_packets']], 'r', 'Yaw - Degrees'))
        # Convert to the correct format for matplotlib.
        # mdate.epoch2num converts epoch timestamps to the right format for matplotlib
        # time_ax = mdate.epoch2num([t.timestamp() for t in self.data_set['timestamp']])
        # time_ax = np.linspace(0.0, len(self.data_set['timestamp']), len(self.data_set['timestamp']))
        # Choose your xtick format string
        # date_fmt = '%Y-%m-%d %H:%M:%S'
        # date_fmt = '%H:%M:%S'
        # Use a DateFormatter to set the data to the correct format.
        # date_formatter = mdate.DateFormatter(date_fmt)
        xlabel = 'Time'
        ylabel = 'Angle (degrees)'      
        return(self.data_set['timestamp'], data, xlabel, ylabel)#, date_formatter)