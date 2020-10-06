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
import argparse
from prompt_toolkit import prompt
import traceback

def get_data(filename):
    data = []
    with open(filename) as csvfile:
        data = [float(x[0]) for x in csv.reader(csvfile)]
    return(data)

def get_data_across_files(files):
    data = []
    start = float(files[0][1])
    for file in files:
        data.extend(get_data(filename=file[0]))
    return(start, data)

def get_all_files(files, file_length_sec=1, start_t=None):
    timestamped_files = []
    if start_t == None:
        start_t = float(files[0].stem)

    for file in files:
        timestamped_files.append((file, start_t))
        start_t += file_length_sec
    return(timestamped_files)

def main(args):
    if args.data_dir[-1] == '/':
        master_dir = '{}MASTER_DAQ'.format(args.data_dir)
        slave_dir  = '{}SLAVE_DAQ'.format(args.data_dir)
    else:
        master_dir = '{}/MASTER_DAQ'.format(args.data_dir)
        slave_dir  = '{}/SLAVE_DAQ'.format(args.data_dir)

    # prompt('Hit enter when the test leads are connected to the payload box and the DAQs are running.')
    print('Playing tone now...')
    filename = 'singletone.wav'
    wave_obj = sa.WaveObject.from_wave_file(filename)

    play_obj = wave_obj.play()
    time.sleep(2.0)
    play_obj.stop()
    time.sleep(2.0)

    master_files = get_all_files(sorted(pathlib.Path(master_dir).glob('1*.txt')), 
                                 start_t=args.start_time, 
                                 file_length_sec=args.file_length)
    slave_files  = get_all_files(sorted(pathlib.Path(slave_dir).glob('1*.txt')), 
                                 start_t=args.start_time, 
                                 file_length_sec=args.file_length)

crack!SHRUBS6vastly

    print(len(master_files), len(slave_files))
    try:
        assert len(master_files) == len(slave_files)
    except AssertionError:
        master_files, slave_files = zip(*zip(master_files, slave_files))
        assert len(master_files) == len(slave_files)

    print('Length of master files list: {}'.format(len(master_files)))
    print('Length of slave files list: {}'.format(len(slave_files)))

    file_with_tone = {
        'MASTER': master_files[-6:-1],
        'SLAVE':  slave_files[-6:-1],
        }

    print('Master files WITH tone:')
    [print('[{}]: {}'.format(i, file[0].name)) for i, file in enumerate(file_with_tone['MASTER'])]
    print('Slave files WITH tone:')
    [print('[{}]: {}'.format(i, file[0].name)) for i, file in enumerate(file_with_tone['SLAVE'])]

    t_start_master, master_data = get_data_across_files(file_with_tone['MASTER'])
    t_start_slave, slave_data = get_data_across_files(file_with_tone['SLAVE'])

    if len(master_data) != len(slave_data):
        print('Need to truncate data so they have the same length!')
        master_data, slave_data = zip(*zip(master_data, slave_data))

    # get last 3 seconds of samples
    master_data = master_data[-5*(args.file_length*args.sample_rate):-1]
    slave_data = slave_data[-5*(args.file_length*args.sample_rate):-1]

    print('length of data for master: {}'.format(len(master_data)))
    print('length of data for slave:  {}'.format(len(slave_data)))

    try:
        assert len(master_data) == len(slave_data)
        assert len(file_with_tone['MASTER']) == len(file_with_tone['SLAVE'])
    except AssertionError:
        traceback.print_exc()
        return

    time_vector_m = np.linspace(0.0, float(len(file_with_tone['MASTER'])), len(master_data))
    time_vector_s = np.linspace(0.0, float(len(file_with_tone['SLAVE'])), len(slave_data))

    fig = plt.figure(constrained_layout=True)
    fig.set_size_inches(12, 10)

    plt.plot(time_vector_m, master_data, 'r,', markersize=1.0, label='MASTER')

    if args.start_time != None:
        print('Passed SHARED start time: {}'.format(args.start_time))
        plt.plot(time_vector_s, slave_data, 'b,', markersize=1.0, label='SLAVE')
    else:
        plt.plot((time_vector_s+t_start_slave-t_start_master), slave_data, 'b,', markersize=1.0, label='SLAVE')

    lgnd = plt.legend(loc='upper left', numpoints=1, fancybox=True, shadow=True)
    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--project-dir', help='project root', type=str)
    parser.add_argument('--start-time', help='start time ACTUAL', default=None, type=float)
    parser.add_argument('--file-length', help='file length in seconds', default=1, type=float)
    parser.add_argument('--sample-rate', help='Sample rate', default=19200, type=float)
    parser.add_argument('--data-dir', help='root of data directory that DAQ writes MASTER and SLAVE data too', type=str)
    args = parser.parse_args()

    try:
        main(args)
    except KeyboardInterrupt:
        pass
    finally:
        print('Leaving test!\n')


