import threading
import time
from datetime import datetime
import sys
from collections import deque

class CircularBufferWrapper(object):
    """docstring for CircularBufferWrapper"""
    def __init__(self, float_buffer):
        super(CircularBufferWrapper, self).__init__()
        self.float_buffer  = float_buffer
        self.buffer_length = len(self.float_buffer)
        self._wrapped_buffer = deque()
        self.shutdown = False
        self.ready = False

        self.t = threading.Thread(target=self.append_new_floats)
        self.t.start()

    def append_new_floats(self):
        while not self.ready:
            pass

        index = 0
        try:
            while not self.shutdown:
                if index >= self.buffer_length:
                    index = 0
                self._wrapped_buffer.append(self.float_buffer[index])
                index += 1
                
        finally:
            self._kill()

    def begin(self):
        self.ready = True

    def close(self):
        self.shutdown = True

    def _kill(self):
        sys.exit(0)

    def __iter__(self):
        return(self)

    def __next__(self):
        try:
            return(self._wrapped_buffer.popleft())
        except IndexError:
            raise StopIteration('No floats in buffer')

    
class AsyncDAQDataHandler(object):
    """docstring for AsyncDAQDataHandler"""
    def __init__(self, float_buffers,
                       buffer_length, 
                       ai_devices_dict,
                       role_write_order,
                       file_length_sec,
                       channel_count, 
                       data_dir,
                       sample_rate,
                       scan_options,
                       v_ranges,
                       input_modes,
                       flags,
                       role='MULTI'):
        super(AsyncDAQDataHandler, self).__init__()
        self.role = role
        self.buffer_length = buffer_length

        try:
            assert set(role_write_order) == set(ai_devices_dict.keys())
        except AssertionError:
            raise ValueError('Role write order MUST match ai_devices keys')
        else:
            self.role_write_order = role_write_order

        self.float_buffers   = {role:float_buffer for role, float_buffer in float_buffers.items()}
        self.ai_device = {role:ai_device for role, ai_device in ai_devices_dict.items()}
        self.status = {role:None for role in ai_devices_dict.keys()}
        self.transfer_status = {role:None for role in ai_devices_dict.keys()}
        self.current_index = {role:0 for role in ai_devices_dict.keys()}
        self.previous_index = 0 # shared by all ai_devices

        self.channel_count    = channel_count
        self.channels_per_daq = self.channel_count/len(self.role_write_order)
        self.data_dir         = data_dir
        self.sample_rate      = sample_rate
        self.file_length_sec  = file_length_sec
        # samples_per_file PER CHANNEL 
        # .. total samples per file (across all channels) = samples_per_file * channel_count
        self.samples_per_file = sample_rate * file_length_sec

        self.scan_options = {role:scan_option for role, scan_option in scan_options.items()}
        self.v_ranges = {role:v_range for role, v_range in v_ranges.items()}
        self.input_modes = {role:input_mode for role, input_mode in input_modes.items()}
        self.flags = {role:_flags for role, _flags in flags.items()}
        self._init_log_file()

        self.shutdown = False
        self.ready    = False
        self.start_time = None
        self.log_filename = '{}/{}_log.log'.format(self.data_dir, self.role)
        #
        #   Create thread for logging
        #
        self.t = threading.Thread(target=self.do_write, name=self.role)
        self.t.start()

    def _init_buffers(self):
        self.buffer_wrappers = {}
        for role in self.role_write_order:
            self.buffer_wrappers[role] = CircularBufferWrapper(float_buffer=self.float_buffers[role])

    def _init_log_file(self):
        output =  '\n--------------------------------------------\n'
        output += '*** NEW SESSION {}\n'.format(datetime.now())
        for role, (sopts, vrange, imode, _flags) in zip(self.ai_device.keys(),
                                                        self.scan_options.values(),
                                                        self.v_ranges.values(),
                                                        self.input_modes.values(),
                                                        self.flags.values())
            output += '--------------------------------------------\n'
            output += '\t Channels on {} device: {}\n'.format(role, self.channels_per_daq)
            output += '\t*** Device Configuration\n'
            output += '\t Sample Rate (Hz): {}\n'.format(self.sample_rate)
            output += '\t Scan Options:     {}\n'.format(sopts)
            output += '\t Voltage Range:    {}\n'.format(vrange)
            output += '\t Input Mode:       {}\n'.format(imode.name)
            output += '\t Flags:            {}\n\n'.format(_flags.name)

        with open(self.log_filename, 'a') as l: 
            l.write(output)

    def _set_start_time(self, start_time_epoch):
        self.start_time = start_time_epoch

    def begin(self, start_time_epoch):
        self._set_start_time(start_time_epoch)
        # let buffer_wrappers know it should start
        for role in self.role_write_order:
            self.buffer_wrappers[role_write_order].begin()
        self.ready = True

    def stop(self):
        # let buffer_wrappers know to shutdown
        for role in self.role_write_order:
            self.buffer_wrappers[role_write_order].close()
        self.shutdown = True

    def _kill(self):
        # kills thread that called _kill
        # .. should only be called within class
        sys.exit(0)

    def write_to_log(self, output):
        with open(self.log_filename, 'a') as l:
            l.write(output)

    def get_filename(self, update_start=True):
        filename = '{}/{:.6f}.txt'.format(self.data_dir, self.start_time)

        if update_start:
            # update start_time so it's correct for next write
            self._set_start_time(self.start_time + self.file_length_sec)

        return(filename)

    def do_write(self):
        start=time.time()
        try:
            # to stop this writing thread from outside 
            # .. call async_inst.stop()
            # .. clean up is handled in finally clause
            while not self.shutdown:
                if time.time() - start >= self.file_length_sec:
                    start=time.time()
                    if self.ready:
                        self.run()
        except Exception as e:
            self.write_to_log('\n![{}] Caught exception: {}\n repr({})\n'.format(datetime.now(), e, repr(e)))
        else:
            self.write_to_log('\n[{}] No exception thrown! sentinel value, shutdown={}\n'.format(datetime.now(), shutdown))
        finally:
            self.write_to_log('[{}] Broke out of do_write loop.\n'.format(datetime.now()))
            self._kill()

    def run(self):
        # get filename with timestamp and update start_time for next file
        filename = self.get_filename(update_start=True)
        #
        #   Append values to channel data
        #
        channel_data = [] # list of columns
        for role in self.role_write_order:
            samples_all_channels = []
            samples = [] # should have len == self.samples_per_file after loop
            # get ALL samples we need from ai_device
            for i in range(1:self.samples_per_file+1):
                samples_all_channels.append(next(self.buffer_wrappers[role]))
                if i % self.channels_per_daq == 0:
                    samples.append(samples_all_channels)
                    samples_all_channels = []

            # now save to channel_data
            # take each row of samples and break into columns
            for i in range(self.channels_per_daq):
                column = [row[i] for row in samples]
                channel_data.append(column)

        write_start=time.time()
        # START WRITING DATA FILE
        with open(filename, 'w') as f:
            for row in rows:
                # write all channel data as csv row
                f.write(row)
        # STOP WRITING DATA FILE
        write_stop=time.time()

        output =  '------------------------------------\n'
        output += 'Data dump to:   {}\n'.format(filename)
        output += 'Write Duration: {} (seconds)\n'.format((write_stop - write_start))
        self.write_to_log(output)

        return(write_stop - write_start)
