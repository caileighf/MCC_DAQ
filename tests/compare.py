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

def get_data_across_files(files, Fs=19100):
    data = []
    start = float(files[0].stem)
    for file in files:
        data.extend(get_data(filename=file))
    return(start, data[:len(files)*Fs])

def main(args):
    if args.data_dir[-1] == '/':
        master_dir = '{}MASTER_DAQ'.format(args.data_dir)
        slave_dir  = '{}SLAVE_DAQ'.format(args.data_dir)
    else:
        master_dir = '{}/MASTER_DAQ'.format(args.data_dir)
        slave_dir  = '{}/SLAVE_DAQ'.format(args.data_dir)

    prompt('Hit enter when the test leads are connected to the payload box and the DAQs are running.')

    filename = 'singletone.wav'
    wave_obj = sa.WaveObject.from_wave_file(filename)
    # set start time for tone
    # start_t = time.time()
    # print('\nTone started at: {}\n'.format(start_t))
    # play_obj = wave_obj.play()
    # print('About to sleep for 3 seconds to allow the daq to collect data WITH the tone')
    # time.sleep(.5)
    # play_obj.stop()
    # stop_t = time.time()
    # print('\nTone stopped at: {}\n'.format(stop_t))
    # print('Waiting 3 seconds for DAQ file writer to catch up...')
    # time.sleep(3)
    # grab data files from both daqs

    for i in range(3):
        play_obj = wave_obj.play()
        time.sleep(0.5)
        play_obj.stop()
        time.sleep(0.8)
    time.sleep(1)

    master_files = sorted(pathlib.Path(master_dir).glob('1*.txt'))
    slave_files  = sorted(pathlib.Path(slave_dir).glob('1*.txt'))

    try:
        assert len(master_files) == len(slave_files)
    except AssertionError:
        stop_index = min([len(master_files), len(slave_files)])
        master_files = master_files[:stop_index]
        slave_files = slave_files[:stop_index]
        assert len(master_files) == len(slave_files)

    print('Length of master files list: {}'.format(len(master_files)))
    print('Length of slave files list: {}'.format(len(slave_files)))

    file_with_tone = {
        'MASTER': master_files[-6:-1],
        'SLAVE': slave_files[-6:-1],
        }

    print('Master files WITH tone:')
    [print('[{}]: {}'.format(i, file)) for i, file in enumerate(file_with_tone['MASTER'])]
    print('Slave files WITH tone:')
    [print('[{}]: {}'.format(i, file)) for i, file in enumerate(file_with_tone['SLAVE'])]

    t_start_master, master_data = get_data_across_files(file_with_tone['MASTER'])
    t_start_slave, slave_data = get_data_across_files(file_with_tone['SLAVE'])

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

    plt.plot(time_vector_m, master_data, 'r,', markersize=0.4, label='MASTER')
    plt.plot((time_vector_s+t_start_slave-t_start_master), slave_data, 'b,', markersize=0.4, label='SLAVE')

    lgnd = plt.legend(loc='upper left', numpoints=1, fancybox=True, shadow=True)

    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--project-dir', help='project root', type=str)
    parser.add_argument('--data-dir', help='root of data directory that DAQ writes MASTER and SLAVE data too', type=str)
    args = parser.parse_args()

    try:
        main(args)
    except KeyboardInterrupt:
        pass
    finally:
        print('Leaving test!\n')


