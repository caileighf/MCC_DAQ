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
        self.ready = True

    def stop(self):
        self.shutdown = True

    def _kill(self):
        # kills thread that called _kill
        # .. should only be called within class
        sys.exit(0)

    def write_to_log(self, output):
        with open(self.log_filename, 'a') as l:
            l.write(output)

    def get_filename(self, samples_to_read, update_start=True):
        filename = '{}/{:.6f}.txt'.format(self.data_dir, self.start_time)
        # update start_time so it's correct for next write
        file_length_sec_ACTUAL = None

        if samples_to_read < self.samples_per_file:
            # if some of the ai_devices haven't written as far
            # .. file_length_sec > file_length_sec_ACTUAL
            file_length_sec_ACTUAL = (samples_to_read * self.file_length_sec) / self.samples_per_file
            start_time_epoch = self.start_time + file_length_sec_ACTUAL
        elif samples_to_read == self.samples_per_file:
            file_length_sec_ACTUAL = self.start_time + self.file_length_sec

        if file_length_sec_ACTUAL != None:
            self._set_start_time(start_time_epoch=self.start_time + file_length_sec_ACTUAL)
        else:
            output =  'Samples to read is greater than the samples per file per channel!\n'
            output += 'Samples to read: {}\n'.format(samples_to_read)
            self.write_to_log(output)
            return(None)
        return(filename)

    def do_write(self):
        start=time.time()
        self.delta_t = 0.0
        try:
            # to stop this writing thread from outside 
            # .. call async_inst.stop()
            # .. clean up is handled in finally clause
            while not self.shutdown:
                if time.time() - start >= self.file_length_sec:
                    start=time.time()
                    if self.ready:
                        self.delta_t = self.run()
        except Exception as e:
            self.write_to_log('\n![{}] Caught exception: {}\n repr({})\n'.format(datetime.now(), e, repr(e)))
        else:
            self.write_to_log('\n[{}] No exception thrown! sentinel value, shutdown={}\n'.format(datetime.now(), shutdown))
        finally:
            self.write_to_log('[{}] Broke out of do_write loop.\n'.format(datetime.now()))
            self._kill()

    def get_valid_index(self, index):
        if index >= self.buffer_length:
            return(index - self.buffer_length)
        return(index)

    def get_max_valid_index(self, indices):
        # this method name seems misleading but it's not
        # get_max_valid_index() finds the index closest to (or equal to)
        # .. the IDEAL index given a shared previous_index
        # that means the max valid index will not read from one of..
        # .. the float buffers and find that there is no data yet

        #  You could have an index == 2 'win' to and index == 999
        #  because the buffers are circular
        temp = []
        for current_index in indices:
            if self.previous_index > current_index:
                # this index wrapped around
                temp.append(((current_index + self.buffer_length), current_index))
            else:
                temp.append((current_index, current_index))

        # use first val in tuple t[0] to decide min
        # use second val in tuple t[1] for actual min_index (circular buffer)
        min_index = min(temp, key=lambda t: t[0])[1]
        return(min_index)

    def get_bounds_of_next_read(self, current_index, set_previous_index=True):
        # stop index MAX/IDEAL
        ideal_stop_index = self.get_valid_index(self.previous_index + self.samples_per_file) 
        # stop index ACTUAL -- OK/INCLUSIVE for all ai_devices (could be < or > ideal_stop_index)
        max_stop_index = self.get_max_valid_index(indices=list(current_index.values()))

        # start index ACTUAL
        start_index = self.previous_index 
        # stop index ACTUAL (will be <= ideal_stop_index)
        stop_index = None
        # samples available to read ACTUAL 
        # if samples_avail_to_read >= self.samples_per_file  --> stop index = ideal_stop_index
        #                                                        && samples_to_read = self.samples_per_file
        # else samples_avail_to_read < self.samples_per_file --> stop_index = max_stop_index
        #                                                        && samples_to_read = less than self.samples_per_file
        samples_avail_to_read = None
        samples_to_read = None

        # get # available samples and handle possible buffer wrap for max_stop_index
        if max_stop_index < start_index:
            samples_avail_to_read = max_stop_index + (self.buffer_length - start_index)
        elif max_stop_index > start_index:
            samples_avail_to_read = max_stop_index - start_index

        if samples_avail_to_read < self.samples_per_file:
            # if samples available is less than the self.samples_per_file
            stop_index = max_stop_index
            samples_to_read = samples_avail_to_read
        else:
            # if samples available is greater or equal to the self.samples_per_file
            stop_index = ideal_stop_index
            samples_to_read = self.samples_per_file

        # if requested set new previous index
        if set_previous_index:
            self.previous_index = ideal_stop_index

        return((start_index, stop_index, samples_to_read))

    def run(self):
        # Get the status of the background operation
        # .. for each role in role write order
        # .. save to local_current_index before assigning to class attr
        # .. in case one of the buffers is empty, we don't update class attrs!
        local_current_index = {role:None for role in self.role_write_order}
        for role in self.role_write_order:
            self.status[role], self.transfer_status[role] = self.ai_devices[role].get_scan_status()
            if self.transfer_status[role].current_index != -1:
                # set current index
                local_current_index[role] = self.transfer_status[role].current_index
            else:
                # nothing has been written to the buffer yet!
                # .. and we have not over written self.current_index vals
                self.write_to_log('\nEMPTY {} BUFFER...\n'.format(role))
                return(0.0)

        # get the COMMON start_index, stop_index, and samples to read
        # .. self.samples_per_file OR less
        start_index, stop_index, samples_to_read = self.get_bounds_of_next_read(local_current_index)

        # now assign local_current_index to class attrs
        for role in self.role_write_order:
            self.current_index[role] = local_current_index[role]

        # get filename with timestamp and update start_time for next file
        filename = self.get_filename(samples_to_read=samples_to_read, update_start=True)

        #
        #   Write data file
        #
        row = ''
        channel = 0
        # check if buffer has wrapped -- grab start of row that is the remainder of the buffer
        if start_index > stop_index:
            # from start_index, read to the end of buffer
            for role in self.role_write_order:
                channel_device_index = 0
                for val in self.float_buffers[role][start_index:self.buffer_length]:
                    row += '{}'.format(val)
                    if channel_device_index >= self.channels_per_daq:
                        break # go to next role if any
                    else:
                        row += ','
                    channel += 1
                    channel_device_index += 1

                if channel >= self.channel_count:
                    row += '\n'
                    break
            start_index = 0

        # from start_index, read to stop_index
        for role in self.role_write_order:
            for val in self.float_buffers[role][start_index:stop_index]:
                row += '{}'.format(val)
                if channel >= self.channel_count:
                    row += '\n'
                else:
                    row += ','
                channel += 1

        write_start=time.time()
        # START WRITING DATA FILE
        with open(filename, 'w') as f:
            # write all channel data as csv row
            f.write(row)
        # STOP WRITING DATA FILE
        write_stop=time.time()

        output =  '------------------------------------\n'
        output += 'Data dump to:   {}\n'.format(filename)
        output += 'Write Duration: {} (seconds)\n'.format((write_stop - write_start))
        self.write_to_log(output)

        return(write_stop - write_start)
