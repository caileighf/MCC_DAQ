import os
import signal
import subprocess
import time
from datetime import datetime

data_dir = '{}/data'.format(os.getcwd())
python_path = '/home/caileigh/repos/venvs/_MCCDAQ/bin/python'
launch_script = '{}/scripts/multi_DAQ_collect.py'.format(os.getcwd())
daq_args = ['-i']

specgram_launch = '/home/caileigh/repos/cli-spectrogram/cli_spectrogram/cli_spectrogram.py'
spec_args = {
    'SLAVE':  ['--sample-rate 19200', '--file-length 1', '--source {}/{}'.format(data_dir, 'SLAVE_DAQ')],
    'MASTER': ['--sample-rate 19200', '--file-length 1', '--source {}/{}'.format(data_dir, 'MASTER_DAQ')]
}

# launch specgram for SLAVE in new window
slave_proc = subprocess.Popen(['gnome-terminal', '-e', '--disable-factory',
                              '{} {} {}'.format(python_path,
                                                specgram_launch,
                                                ' '.join(spec_args['SLAVE']))],
                              preexec_fn=os.setpgrp)

# launch specgram for MASTER in new window
master_proc = subprocess.Popen(['gnome-terminal', '-e', '--disable-factory',
                              '{} {} {}'.format(python_path,
                                                specgram_launch,
                                                ' '.join(spec_args['MASTER']))],
                              preexec_fn=os.setpgrp)
try:
    daq_proc = subprocess.Popen(['gnome-terminal', '-e', '--disable-factory',
                                '{} {} {}'.format(python_path,
                                                 launch_script,
                                                 ' '.join(daq_args))],
                                preexec_fn=os.setpgrp)
    time.sleep(1)
    os.system('clear')
    while True:
        if daq_proc.poll() != None:
            break
        time.sleep(1)
        print('Current time: {}'.format(datetime.now()))

except KeyboardInterrupt:
    print('\n\n\tEnding...\n')
finally:
    try:
        os.killpg(slave_proc.pid, signal.SIGINT)
        os.killpg(master_proc.pid, signal.SIGINT)
        os.killpg(daq_proc.pid, signal.SIGINT)
        time.sleep(1)
        print('\n\tKilled processes!\n')
    except:
        print('\n\n\tEnding...\n')