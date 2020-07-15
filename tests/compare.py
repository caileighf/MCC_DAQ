import matplotlib.pyplot as plt
import numpy as np
import simpleaudio as sa
from datetime import datetime
import time
import pathlib
import glob
import os
import sys
import csv
import subprocess
from prompt_toolkit import prompt

def get_data(files):
    data = []
    with open(files) as csvfile:
        data = [float(x[0]) for x in csv.reader(csvfile)]
    return(data)

def main(project_root, data_dir, new_tone_test, start_time):
    master_dir   = '{}/MASTER_DAQ'.format(data_dir)
    slave_dir    = '{}/SLAVE_DAQ'.format(data_dir)

    if new_tone_test:
        # sleep and let daq collect data without tone
        print('About to sleep for 4 seconds to allow the daq to collect data without the tone')
        time.sleep(4)

        filename = 'singletone.wav'

        wave_obj = sa.WaveObject.from_wave_file(filename)

    # get start time for tone
    start_t = time.time()
    if not new_tone_test:
        start_t = start_time
    else:
        # import ipdb; ipdb.set_trace() # BREAKPOINT
        play_obj = wave_obj.play()

    if new_tone_test:
        # TODO confirm wav file is long enough (this one is 20 sec)
        print('About to sleep for 5 seconds to allow the daq to collect data WITH the tone')
        time.sleep(5)
        # get stop time for tone
        stop_t = time.time()

    # import ipdb; ipdb.set_trace() # BREAKPOINT
    master_files = sorted(pathlib.Path(master_dir).glob('1*.txt'))
    slave_files  = sorted(pathlib.Path(slave_dir).glob('1*.txt'))

    file_with_tone = {
        'MASTER': [],
        'SLAVE': [],
        }

    # print(master_dir)
    print('length of master files list: {}'.format(len(master_files)))
    # print(slave_dir)
    print('length of slave files list: {}'.format(len(slave_files)))
    # find file closest to start of tone ---------> MASTER
    for i, file in enumerate(master_files):
        # print(file.name)
        # print(start_t)
        if float(file.stem) >= float(start_t):
            file_with_tone['MASTER'].append(file)
            file_with_tone['MASTER'].append(master_files[i+1])
            break

    # find file closest to start of tone ---------> SLAVE
    for i, file in enumerate(slave_files):
        # print(file.name)
        # print(start_t)
        if float(file.stem) >= float(start_t):
            file_with_tone['SLAVE'].append(file)
            file_with_tone['SLAVE'].append(slave_files[i+1])
            break

    print('Master file: {}'.format(file_with_tone['MASTER']))
    print('Slave file:  {}'.format(file_with_tone['SLAVE']))
    try:
        t_start_slave = float(file_with_tone['SLAVE'][0].stem)
        t_start_master = float(file_with_tone['MASTER'][0].stem)
    except Exception as e:
        import ipdb; ipdb.set_trace() # BREAKPOINT

    master  = get_data(file_with_tone['MASTER'][0])
    master += get_data(file_with_tone['MASTER'][1])

    slave =  get_data(file_with_tone['SLAVE'][0])
    slave += get_data(file_with_tone['SLAVE'][1])

    time_vector_m = np.linspace(0.0, 2.0, len(master))
    time_vector_s = np.linspace(0.0, 2.0, len(slave))

    plt.plot(time_vector_m, master, 'r,', markersize=0.3)
    plt.plot((time_vector_s+t_start_slave-t_start_master), slave, 'b,', markersize=0.3)
    # plt.plot(time_vector_s, slave, 'b')
    plt.show()


if __name__ == '__main__':
    project_root = pathlib.Path(os.getcwd())
    project_root = project_root.parent

    new_tone_test = True
    start_t = None
    if '_TEST' in sys.argv[1]:
        data_dir = os.path.abspath(sys.argv[1])
        new_tone_test = False
        start_t = float(sys.argv[2])
    try:
        prompt('Hit enter when the test leads are connected to the payload box and the DAQs are running.')
        data_dirs = sorted(pathlib.Path(project_root).glob('*_TEST'))
        data_dir  = data_dirs[-1]
        main(project_root, data_dir, new_tone_test, start_t)
    except KeyboardInterrupt:
        pass
    finally:
        print('Leaving test!\n')


