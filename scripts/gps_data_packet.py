import pynmea2
import re
from datetime import datetime
import matplotlib.dates as mdate
import csv

#                           $GPRMC,043606.036,V,,,,,0.00,0.00,300620,,,N*48
gps_pattern = re.compile("^\$GP[A-Z]{3},.+$") # match beginning only

def get_ZDA_fields(msg):
    data = [
        ('gps_time', msg.timestamp),
        ('latitude', None),
        ('longitude', None),
        ('gps_fix_type', None),
        ('satellites_used', None),
        ('speed_over_ground', None),
        ('pdop', None),
        ('hdop', None),
        ('vdop', None),
        ('nmea_type', msg.sentence_type)
    ]
    return(data)

def get_GSV_fields(msg):
    data = [
        ('gps_time', None),
        ('latitude', None),
        ('longitude', None),
        ('gps_fix_type', None),
        ('satellites_used', None),
        ('speed_over_ground', None),
        ('pdop', None),
        ('hdop', None),
        ('vdop', None),
        ('nmea_type', msg.sentence_type)
    ]
    return(data)

def get_GGA_fields(msg):    
    data = [
        ('gps_time', msg.timestamp),
        ('latitude', msg.lat),
        ('longitude', msg.lon),
        ('gps_fix_type', None),
        ('satellites_used', msg.num_sats),
        ('speed_over_ground', None),
        ('pdop', None),
        ('hdop', msg.horizontal_dil),
        ('vdop', None),
        ('nmea_type', msg.sentence_type)
    ]
    return(data)

def get_GSA_fields(msg):
    data = [
        ('gps_time', None),
        ('latitude', None),
        ('longitude', None),
        ('gps_fix_type', msg.mode_fix_type),
        ('satellites_used', None),
        ('speed_over_ground', None),
        ('pdop', msg.pdop),
        ('hdop', msg.hdop),
        ('vdop', msg.vdop),
        ('nmea_type', msg.sentence_type)
    ]
    return(data)

def get_RMC_fields(msg):
    data = [
        ('gps_time', msg.timestamp),
        ('latitude', msg.lat),
        ('longitude', msg.lon),
        ('gps_fix_type', None),
        ('satellites_used', None),
        ('speed_over_ground', msg.spd_over_grnd),
        ('pdop', None),
        ('hdop', None),
        ('vdop', None),
        ('nmea_type', msg.sentence_type)
    ]
    return(data)

sentence_table = {
    'ZDA': get_ZDA_fields,
    # 'GSV': get_GSV_fields, # currently no info for header
    'GGA': get_GGA_fields,
    'GSA': get_GSA_fields,
    'RMC': get_RMC_fields,
}

class GPSDataPacket(object):
    """docstring for GPSDataPacket"""
    def __init__(self, raw, time):
        super(GPSDataPacket, self).__init__()
        self.raw = raw
        self.dt  = time

        if gps_pattern.match(self.raw):
            self.msg  = pynmea2.parse(self.raw)
            try:
                self.data = sentence_table[self.msg.sentence_type](self.msg)
            except KeyError:
                raise ValueError('[{}] NMEA sentences are supported by pynmea2 but are not supported by this csv writer'.format(self.msg.sentence_type))
            # add timestamp from computer
            self.data.insert(0, ('timestamp', self.dt))
        else:
            raise ValueError('The raw data does not match the GPS NMEA sentence pattern!\n{}'.format(self.raw))

    @property
    def header(self):
        return([x[0] for x in self.data])

    @property
    def as_row(self):
        return([x[1] for x in self.data])

class GPSLogParser(object):
    """docstring for GPSLogParser"""
    def __init__(self, log_file):
        super(GPSLogParser, self).__init__()
        self.log_file = log_file
        self._data_set = None

    @property
    def data_set(self):
        return(self._data_set)

    def parse(self, required_fields, start=0, end=9000000000.0):
        # grab everything first
        parsed_data = self._get_all()
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
                self._data_set['_packets'].append(packet)
                # now get required field data
                for field in required_fields:
                    if field == 'timestamp':
                        # hack since datetime obj is called dt not timestamp
                        self._data_set[field].append(packet.dt)
                    else:
                        self._data_set[field].append(getattr(packet, key))

        if len(self._data_set['_packets']) <= 0:
            raise RuntimeError('No GPS data in the provided window!')
            
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
            packets.append(GPSDataPacket(dt=dt, raw=raw))
        return(packets)

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


class GPSPlotter(object):
    """docstring for GPSPlotter"""
    def __init__(self, data_set):
        super(GPSPlotter, self).__init__()
        if data_set == None:
            raise ValueError('Null dataset provided! (Has the log file been parsed?)')
        else:
            self.data_set = data_set

    def plot(self, ax):
        x = self.data_set['latitude']
        y = self.data_set['longitude']
        plt.scatter(x, y, cmap='inferno')

        # label axes
        ax.set_xlabel('Latitude')
        ax.set_ylabel('Longitude')
        return(ax, False)