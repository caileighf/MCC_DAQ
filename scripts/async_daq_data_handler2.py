import threading
import time
from datetime import datetime
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
                       flags):
        super(AsyncDAQDataHandler, self).__init__()
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

        self.shutdown = False
        self.ready    = False
        with open(self.log_filename, 'a') as l: 
            l.write('\n*** NEW SESSION! {}\n'.format(datetime.now()))
            l.write(' Channels on {} device: {}\n'.format(self.role, self.channel_count))
            l.write('*** Device Configuration\n')
            l.write(' Sample Rate (Hz): {}\n'.format(sample_rate))
            l.write(' Scan Options:     {}\n'.format(scan_options))
            l.write(' Voltage Range:    {}\n'.format(v_range.name))
            l.write(' Input Mode:       {}\n'.format(input_mode.name))
            l.write(' Flags:            {}\n\n'.format(flags.name))

        #
        #   Create thread for logging
        #
        self.t = threading.Thread(target=self.do_write, name=self.role)
        self.t.start()

    def do_write(self, start_time=None):
        # global shutdown
        # global ready
        start=time.time()
        try:
            # while not shutdown:
            while not self.shutdown:
                if time.time() - start >= 1:
                    start=time.time()
                    # if ready:
                    if self.ready:
                        self.run()
        except Exception as e:
            # import ipdb; ipdb.set_trace() # BREAKPOINT
            with open(self.log_filename, 'a') as l: 
                l.write('\n![{}] Caught exception: {}\n repr({}) \n'.format(datetime.now(), e, repr(e)))
                l.write('!')
        else:
            with open(self.log_filename, 'a') as l: 
                l.write('\n[{}] No exception thrown! sentinel value, shutdown={}\n'.format(datetime.now(), shutdown))
        finally:
            with open(self.log_filename, 'a') as l: 
                l.write('[{}] Broke out of do_write loop. \n'.format(datetime.now()))

    def run(self):
        # Get the status of the background operation
        self.status, self.transfer_status = self.ai_device.get_scan_status()
        self.current_index = self.transfer_status.current_index
        if self.current_index == -1:
            # nothing has been written to the buffer yet!
            with open(self.log_filename, 'a') as l: l.write('\nEMPTY BUFFER...\n')
            return(0.0)

        write_start = time.time()
        file_name = '{}/{:.6f}.txt'.format(self.data_dir, write_start)
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

        return(write_stop - write_start)
