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
                       flags,
                       file_length):
        super(AsyncDAQDataHandler, self).__init__()
        self.float_buffer    = float_buffer
        self.buffer_length   = len(self.float_buffer)
        self.role            = role
        self.ai_device       = ai_device
        self.channel_count   = channel_count
        self.data_dir        = data_dir
        self.sample_rate     = sample_rate
        self.file_length     = file_length
        self.status          = None
        self.transfer_status = None
        self.start_time      = None
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

    def begin(self, start_time):
        self.start_time = start_time
        self.ready = True

    def stop(self):
        self.shutdown = True

    def _kill(self):
        sys.exit()

    def do_write(self):
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
            import traceback
            with open(self.log_filename, 'a') as l: 
                l.write('\n![{}] Caught exception: {}\n repr({}) \n'.format(datetime.now(), e, repr(e)))
                l.write('\n![{}] traceback: {}\n'.format(datetime.now(), traceback.format_exc()))
        else:
            with open(self.log_filename, 'a') as l: 
                l.write('\n[{}] No exception thrown! sentinel value, shutdown={}\n'.format(datetime.now(), shutdown))
        finally:
            with open(self.log_filename, 'a') as l: 
                l.write('[{}] Broke out of do_write loop. \n'.format(datetime.now()))
            self._kill()

    def run(self):
        # Get the status of the background operation
        self.status, self.transfer_status = self.ai_device.get_scan_status()
        self.current_index = self.transfer_status.current_index
        if self.current_index == -1:
            # nothing has been written to the buffer yet!
            with open(self.log_filename, 'a') as l: l.write('\nEMPTY BUFFER...\n')
            return(0.0)
        else:
            with open(self.log_filename, 'a') as l: l.write('current_index = {}\n'.format(self.current_index))


        write_start = time.time()  # For logging/tuning
        file_name = '{}/{:.6f}.txt'.format(self.data_dir, self.start_time)
        rows_written = 0
        row_counter_iter = iter(range(int(self.sample_rate*self.file_length)))
        i=0
        samples_written=0
        with open(file_name, 'w') as f:
            
            try:
                # check if buffer has wrapped
                if self.previous_index > self.current_index:
                    # start at self.previous_index and read to the end of buffer
                    for val in self.float_buffer[self.previous_index:self.buffer_length]:
                        f.write('{}'.format(val))
                        samples_written += 1
                        if i % self.channel_count == 0 and i != 0:
                            rows_written += 1
                            next(row_counter_iter)
                            f.write('\n')
                        else:
                            f.write(',')
                        i += 1
                    # next loop to start at index 0
                    start_index = 0
                else:
                    start_index = self.previous_index

                # Read from the self.previous_index to the current_index
                # .. set self.previous_index to current_index
                for val in self.float_buffer[start_index:self.current_index]:
                    f.write('{}'.format(val))
                    samples_written += 1
                    if i%self.channel_count == 0 and i != 0:
                        rows_written += 1
                        next(row_counter_iter)
                        f.write('\n')
                    else:
                        f.write(',')
                    i += 1
            except StopIteration:
                rows_written = int(self.sample_rate * self.file_length)
                self.previous_index += samples_written
                if self.previous_index >= self.buffer_length:
                    self.previous_index = self.buffer_length - self.previous_index
            else:
                self.previous_index = self.current_index

            # increment time
            self.start_time += float(self.sample_rate / rows_written)

        write_stop = time.time()
        with open(self.log_filename, 'a') as l: 
            l.write('------------------------------------\n')
            l.write('Data dump to:   {}\n'.format(file_name))
            l.write('Write Duration: {} (seconds)\n'.format((write_stop - write_start)))
            l.write('File length:    {} (seconds)\n'.format(self.sample_rate / rows_written))
            l.write('Rows written:   {}\n'.format(rows_written))

        return(write_stop - write_start)
