import threading
import time
from datetime import datetime
import sys
import traceback
        
class AsyncDAQDataHandler(object):
    """docstring for AsyncDAQDataHandler"""
    def __init__(self, float_buffer, 
                       role,
                       file_length_sec, 
                       ai_device, 
                       channel_count, 
                       data_dir,
                       sample_rate,
                       scan_options,
                       v_range,
                       input_mode,
                       flags):
        super(AsyncDAQDataHandler, self).__init__()
        self.float_buffer     = float_buffer
        self.buffer_length    = len(self.float_buffer)
        self.role             = role
        self.file_length_sec  = file_length_sec
        # samples per file per channel (# of rows in file)
        self.samples_pfpc     = sample_rate * file_length_sec
        self.ai_device        = ai_device
        self.channel_count    = channel_count
        self.data_dir         = data_dir
        self.start_time_epoch = None
        self.status           = None
        self.transfer_status  = None
        self.current_index    = 0
        self.previous_index   = 0
        self.log_filename     = '{}/{}_log.log'.format(self.data_dir, self.role)

        self.shutdown = False
        self.ready    = False

        output =  ('\n*** NEW SESSION! {}\n'.format(datetime.now()))
        output += (' Channels on {} device: {}\n'.format(self.role, self.channel_count))
        output += ('*** Device Configuration\n')
        output += (' Sample Rate (Hz): {}\n'.format(sample_rate))
        output += (' Scan Options:     {}\n'.format(scan_options))
        output += (' Voltage Range:    {}\n'.format(v_range.name))
        output += (' Input Mode:       {}\n'.format(input_mode.name))
        output += (' Flags:            {}\n\n'.format(flags.name))
        self.write_to_log(output)
        #
        #   Create thread for logging
        #
        self.t = threading.Thread(target=self.do_write, name=self.role)
        self.t.start()

    def begin(self, start_time_epoch):
        self.start_time_epoch = start_time_epoch
        self.ready = True

    def stop(self):
        self.shutdown = True

    def _kill(self):
        sys.exit(0)

    def do_write(self, start_time=None):
        # global shutdown
        # global ready
        start=time.time()
        try:
            # while not shutdown:
            while not self.shutdown:
                if time.time() - start > (self.file_length_sec + 0.01):
                    start=time.time()
                    # if ready:
                    if self.ready:
                        self.run()
        except ValueError:
            pass
        except Exception as e:
            self.write_to_log('\n![{}] Caught exception: {}\n repr({}) \n'.format(datetime.now(), e, repr(e)))
            # self.write_to_log(traceback.format_exc())
        else:
            self.write_to_log('\n[{}] No exception thrown! sentinel value, shutdown={}\n'.format(datetime.now(), shutdown))
        finally:
            self.write_to_log('[{}] Broke out of do_write loop. \n'.format(datetime.now()))
            self._kill()

    def write_to_log(self, output):
        with open(self.log_filename, 'a') as l:
            l.write(output)

    def get_filename(self, update_start_time):
        file_name = '{}/{:.6f}.txt'.format(self.data_dir, self.start_time_epoch)
        if update_start_time:
            self.start_time_epoch += self.file_length_sec
        return(file_name)

    def run(self):
        # Get the status of the background operation
        self.status, self.transfer_status = self.ai_device.get_scan_status()
        self.current_index = self.transfer_status.current_index
        self.write_to_log('\n[{}] current_index={}, scan_status={}\n'.format(datetime.now(),
                                                                             self.current_index,
                                                                             'RUNNING' if self.status==1 else 'IDLE'))
        if self.current_index == -1:
            # nothing has been written to the buffer yet!
            self.write_to_log('\n![{}] EMPTY BUFFER...\n'.format(datetime.now()))
            return(0.0)

        row = iter(range(int(self.samples_pfpc)))
        last_written_index = self.previous_index
        file_name = self.get_filename(update_start_time=True)
        write_start = time.time()
        try:
            with open(file_name, 'w') as f:
                i=1
                # check if buffer has wrapped
                if self.previous_index > self.current_index:
                    # start at self.previous_index and read to the end of buffer
                    for val in self.float_buffer[self.previous_index:self.buffer_length]:
                        f.write('{}'.format(val))
                        if i%self.channel_count == 0 and i!=0:
                            next(row)
                            f.write('\n')
                        else:
                            f.write(',')

                        last_written_index += 1
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
                        next(row)
                        f.write('\n')
                    else:
                        f.write(',')

                    last_written_index += 1
                    i+=1
        except StopIteration:
            # we have written all the rows for this file
            self.previous_index = last_written_index
        else:
            output = 'Wrote {} rows! Need to write {} rows for valid file'.format(i-1, self.samples_pfpc)
            self.write_to_log(output)
            raise ValueError(output)

        write_stop = time.time()

        output =  ('------------------------------------\n')
        output += ('Data dump to:   {}\n'.format(file_name))
        output += ('Write Duration: {} (seconds)\n'.format((write_stop - write_start)))
        self.write_to_log(output)

        return(write_stop - write_start)
