import json
import re
from datetime import datetime
import numpy as np

class AISDataPacket(object):
    """docstring for AISDataPacket"""
    def __init__(self, json_obj):
        super(AISDataPacket, self).__init__()
        self._json = json_obj
        # create a few convenient attributes
        self.order_received = self._json['order_received']
        self.ship_id = self._json['mmsi']
        # thanks libais for everything BUT the fact that you
        # .. chose to name lat/lon -> y/x...................
        # .... was it really that much harder?
        self.latitude = self._json['y'] if 'y' in self._json else None
        self.longitude = self._json['x'] if 'x' in self._json else None
        # UTC seconds NOT a full timestamp
        self.utc_seconds = self._json['timestamp'] if 'timestamp' in self._json else None
        self.true_heading = self._json['true_heading'] if 'true_heading' in self._json else None

    def same_ship(self, compare_packet):
        if self.ship_id == compare_packet.ship_id:
            return(True)
        return(False)

class AISLogParser(object):
    """docstring for AISLogParser"""
    def __init__(self, log_file):
        super(AISLogParser, self).__init__()
        self.log_file = log_file
        self._data_set = None

    @property
    def data_set(self):
        return(self._data_set)

    def parse(self, required_fields, start=None, end=None):
        data = self._get_all()
        packets = self._create_data_packets(data)
        # TODO: log AIS with a timestamp.....
        self._data_set = {
            '_packets': []
        }
        for field in required_fields:
            self._data_set[field] = []

        for packet in packets:
            self._data_set['_packets'].append(packet)
            # now get required field data
            for field in required_fields:
                if field == 'transmission':
                    self._data_set[field].append({'id': packet.ship_id,
                                                  'order_received': packet.order_received,
                                                  'true_heading': packet.true_heading,
                                                  'latitude': packet.latitude,
                                                  'longitude': packet.longitude,
                                                  'utc_seconds': packet.utc_seconds})

        if len(self._data_set['_packets']) <= 0:
            raise RuntimeError('No AIS data in the provided window!')

        return(self._data_set, start)

    def _create_data_packets(self, data):
        # now iterate through and create GPSDataPacket objs for each row
        packets = []
        for json_obj in data:
            packets.append(AISDataPacket(json_obj=json_obj))
        return(packets)

    def _get_all(self):
        data = []
        with open(self.log_file) as f:
            all_data = json.loads(f.read())
            
        for i in range(len(all_data)):
            data.append(all_data[i])

        return(data)


class AISPlotter(object):
    """docstring for AISPlotter"""
    def __init__(self, data_set):
        super(AISPlotter, self).__init__()
        if data_set == None:
            raise ValueError('Null dataset provided! (Has the log file been parsed?)')
        else:
            self.data_set = data_set

    def plot(self, ax):
        # print('printing dataset... ', end='')
        # print(self.data_set['transmission'])
        ships = {}
        for packet in self.data_set['transmission']:
            if packet['id'] not in ships:
                ships[packet['id']] = [
                    (packet['order_received'], packet['latitude'], packet['longitude'])
                    ]
            else:
                ships[packet['id']].append(
                        (packet['order_received'], packet['latitude'], packet['longitude'])
                    )

        # look through each ship's messages
        for ship_id, transmissions in ships.items():
            # print(ship_id, transmissions)
            x = sorted(transmissions, key = lambda x: x[0]) # latitude
            y = sorted(transmissions, key = lambda x: x[0]) # longitude
            z = range(len(transmissions))
            ax.scatter(x, y, cmap='inferno', label='vessel MMSI: {}'.format(ship_id))
            # ax.scatter(x, y, c=z, cmap='inferno', label='vessel MMSI: {}'.format(ship_id))

        # label axes
        ax.set_xlabel('Latitude')
        ax.set_ylabel('Longitude')
        legend = ax.legend(loc='upper left')
        for legend_handle in legend.legendHandles:
            legend_handle._legmarker.set_markersize(9)
        return(ax, False)
        

