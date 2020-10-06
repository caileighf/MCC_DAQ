import threading
import time
from datetime import datetime
import os
import sys
        
shutdown = False
ready = False

class AsyncDAQDataHandler(object):
    """docstring for AsyncDAQDataHandler"""
    def __init__(self, float_buffer, 
                       role, 
                       ai_device, 
                       channel_count, 
                       data_dir,
                       sample_rate,
                       scan_options,
                       v_range,
                       input_mode,
                       flags,
                       file_length,
                       trigger_type=None):
        super(AsyncDAQDataHandler, self).__init__()
        self.float_buffer    = float_buffer
        self.buffer_length   = len(self.float_buffer)
        self.role            = role
        self.ai_device       = ai_device
        self.channel_count   = channel_count
        self.data_dir        = data_dir
        self.sample_rate     = sample_rate
        self.file_length     = file_length
        self.file_length_rows = int(self.sample_rate) * int(self.file_length)
        self.status          = None
        self.transfer_status = None
        self.start_time      = None
        self.current_index   = 0
        self.rows_written    = 0
        self.log_filename    = '{}/{}_log.log'.format(self.data_dir, self.role)
        self.is_triggered_mode = trigger_type != None

        self.shutdown = False
        self.ready    = False

        output  = ('\n*** NEW SESSION! {}\n'.format(datetime.now()))
        output += (' Channels on {} device: {}\n'.format(self.role, self.channel_count))
        output += ('*** Device Configuration\n')
        output += (' Sample Rate (Hz): {}\n'.format(sample_rate))
        output += (' Scan Options:     {}\n'.format(scan_options))
        output += (' Voltage Range:    {}\n'.format(v_range.name))
        output += (' Input Mode:       {}\n'.format(input_mode.name))
        output += (' Flags:            {}\n\n'.format(flags.name))
        if self.is_triggered_mode:
            output += (' Trigger Type:     {}\n\n'.format(trigger_type))
        self.write_to_log(output)
        #
        #   Create thread for logging
        #
        self.t = threading.Thread(target=self.do_write, name=self.role)
        self.t.start()

    def reset(self):
        self.status          = None
        self.transfer_status = None
        self.start_time      = None
        self.current_index   = 0

    def trigger(self, start_time):
        self.reset()
        self.start_time = start_time
        self.ready = True
        while self.ready:
            pass
        return(True)

    def stop(self):
        self.shutdown = True

    def _kill(self):
        sys.exit()

    def write_to_log(self, output, prefix_tstamp=False):
        with open(self.log_filename, 'a') as l:
            if prefix_tstamp:
                l.write('[{}]: {}'.format(datetime.now(), output))
            else:
                l.write(output)

    def do_write(self):
        start=time.time()
        try:
            # while not shutdown:
            while not self.shutdown:
                if time.time() - start >= 1:
                    start=time.time()
                    # if ready:
                    if self.ready:
                        if self.is_triggered_mode:
                            self.write_to_log('[{}]: Triggered!\n'.format(datetime.now()))
                        self.run()
                        if self.is_triggered_mode:
                            self.ready = False
        except Exception as e:
            import traceback
            output  = ('\n![{}] Caught exception: {}\n repr({}) \n'.format(datetime.now(), e, repr(e)))
            output += ('\n![{}] traceback: {}\n'.format(datetime.now(), traceback.format_exc()))
        else:
            self.write_to_log('\n[{}] No exception thrown! sentinel value, shutdown={}\n'.format(datetime.now(), shutdown))
        finally:
            self.write_to_log('[{}] Broke out of do_write loop. \n'.format(datetime.now()))
            self._kill()

    def run(self):
        # Get the status of the background operation
        self.status, self.transfer_status = self.ai_device.get_scan_status()
        self.current_index = self.transfer_status.current_index
        self.write_to_log('Status:        {}\n'.format(self.status), prefix_tstamp=True)
        self.write_to_log('Current Index: {}\n'.format(self.transfer_status.current_index), prefix_tstamp=True)
        if self.current_index == -1:
            # nothing has been written to the buffer yet!
            self.write_to_log('\nEMPTY BUFFER...\n')
            return(0.0)
        elif self.current_index % self.channel_count != 0:
            self.write_to_log("This implementation assumes that the circular buffer always receives values"
                             " from all channels at once, which means the current index will be divisible"
                             " the channel count.")
            raise ValueError("This implementation assumes that the circular buffer always receives values"
                             " from all channels at once, which means the current index will be divisible"
                             " the channel count.")

        # filename created with timestamp passed during trigger() call
        file_start_time = float(self.start_time)
        file_name = os.path.join(self.data_dir, '{:.6f}.txt'.format(file_start_time))

        self.write_to_log('reading from index: [0, {}] in float buffer\n'.format(self.file_length_rows * self.channel_count + 1), prefix_tstamp=True)
        self.write_to_log('length of float buffer: {}\n'.format(len(self.float_buffer)), prefix_tstamp=True)
        # grab values from float buffer
        vals = self.float_buffer[:self.file_length_rows * self.channel_count + 1]
        self.write_to_log('Length of vals: {}\n'.format(len(vals)), prefix_tstamp=True)
        # transpose to get row data (float buff writes in 'columns')
        # float_buffer = [channel0_reading1, channel1_reading1, channel0_reading2, channel1_reading2, ..]
        rows_to_write = []
        i = 0
        while (i + self.channel_count) < len(vals) + 1:
            rows_to_write.append(vals[i:i + self.channel_count])
            i += self.channel_count

        self.write_to_log('Length of rows to write: {}\n'.format(len(rows_to_write)), prefix_tstamp=True)

        write_start = time.time()  # For logging/tuning
        with open(file_name, 'w') as f:
            for row in rows_to_write:
                f.write(','.join('{:.12f}'.format(v) for v in row) + '\n')
        write_stop = time.time() 

        output  = ('---------------------\n')
        output += ('Wrote file name:  {}\n'.format(file_name))
        output += ('At epoch seconds: {}\n'.format(time.time()))
        output += ('Buffer length:    {}\n'.format(self.buffer_length))
        output += ('current_index:    {}\n'.format(self.current_index))
        output += ('Rows written:     {}\n'.format(self.rows_written))
        output += ('Rows per file:    {}\n'.format(self.file_length_rows))
        output += ('File length sec:  {}\n'.format(self.file_length))
        output += ('Sample rate Hz:   {}\n'.format(self.sample_rate))
        self.write_to_log(output)

        self.rows_written += self.file_length_rows

        self.write_to_log('------------------------------------\n')
        self.write_to_log('Write Duration: {} (seconds)\n'.format((write_stop - write_start)))

        return(write_stop - write_start)
