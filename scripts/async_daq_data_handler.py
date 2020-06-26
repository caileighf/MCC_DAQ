import threading
import time
from datetime import datetime

class AsyncDAQDataHandler(threading.Thread):
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
                       flags):
        threading.Thread.__init__(self)
        self.float_buffer    = float_buffer
        self.buffer_length   = len(self.float_buffer)
        self.role            = role
        self.ai_device       = ai_device
        self.channel_count   = channel_count
        self.data_dir        = data_dir
        self.status          = None
        self.transfer_status = None
        self.current_index   = 0
        self.previous_index  = 0
        self.log_filename    = '{}/{}_log.log'.format(self.data_dir, self.role)
        with open(self.log_filename, 'a') as l: 
            l.write('\n*** NEW SESSION! {}\n'.format(datetime.now()))
            l.write(' Channels on {} device: {}\n'.format(self.role, self.channel_count))
            l.write('*** Device Configuration\n')
            l.write(' Sample Rate (Hz): {}\n'.format(sample_rate))
            l.write(' Scan Options:     {}\n'.format(scan_options))
            l.write(' Voltage Range:    {}\n'.format(v_range.name))
            l.write(' Input Mode:       {}\n'.format(input_mode.name))
            l.write(' Flags:            {}\n\n'.format(flags.name))

    def do_write(self, start_time):
        self.run(start=start_time)

    def run(self, start):
        # Get the status of the background operation
        self.status, self.transfer_status = self.ai_device.get_scan_status()
        self.current_index = self.transfer_status.current_index
        if self.current_index == -1:
            # nothing has been written to the buffer yet!
            with open(self.log_filename, 'a') as l: l.write('\nEMPTY BUFFER...\n')
            return

        write_start = time.time()
        file_name = '{}/{:.6f}.txt'.format(self.data_dir, start)
        with open(file_name, 'w') as f:
            i=1
            # check if buffer has wrapped
            if self.previous_index > self.current_index:
                # start at self.previous_index and read to the end of buffer
                for val in self.float_buffer[self.previous_index:self.buffer_length]:
                    f.write('{}'.format(val))
                    if i%self.channel_count == 0 and i!=0:
                        f.write('\n')
                    else:
                        f.write(',')
                    i+=1
                # now reset self.previous_index to 0
                # ..so we start reading from the beginning of the buffer
                # ..in the next loop
                self.previous_index=0

            # Read from the self.previous_index to the current_index
            # .. set self.previous_index to current_index
            for val in self.float_buffer[self.previous_index:self.current_index]:
                f.write('{}'.format(val))
                if i%self.channel_count == 0 and i!=0:
                    f.write('\n')
                else:
                    f.write(',')
                i+=1
            self.previous_index=self.current_index
        write_stop = time.time()
        with open(self.log_filename, 'a') as l: 
            l.write('------------------------------------\n')
            l.write('Data dump to:   {}\n'.format(file_name))
            l.write('Write Duration: {} (seconds)\n'.format((write_stop - write_start)))
