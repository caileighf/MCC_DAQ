import argparse
import matplotlib.pyplot as plt
import numpy as np
import pathlib
import glob
import os
import sys
import time
from datetime import datetime
from matplotlib.gridspec import GridSpec
from prompt_toolkit.shortcuts import ProgressBar
#
# This method pull n channel data from file and returns list of floats
def get_data(filename, selected_channel):
    data = []
    with open(filename, 'r') as f:
        start = time.time()
        for i, line in enumerate(f.readlines()):
            if time.time()-start >= 1:
                start = time.time()
                # print('Still working...')
            channel_data = line.split(',')
            data.append(float(channel_data[selected_channel]))
    return(data)

def get_data_across_files(files, selected_channel):
    data = []
    start = float(files[0].stem)
    for file in files:
        data.extend(get_data(filename=file, selected_channel=selected_channel))
    return(start, data)

#
# This method takes a list of files and a chunk size and
# .. yields the list of floats returned by get_data() for chunk_size # of files
# .. Use this in a for loop for getting data that spans multiple files
def batch_files(files, chunk_size, selected_channel):
    start = float(files[0].stem)
    for i, file in enumerate(files):
        # append file data to list
        data = get_data(file, selected_channel)
        if i % chunk_size == 0:
            yield start, data
            # now reset start time to next file
            try:
                start = float(files[i+1].stem)
            except IndexError:
                # done! return
                return(None, None)

    return(start, data)

#
# This method returns only the files that fall within the specified 
# .. window of time (or all of them if no start/end time provided)
def get_files_in_window(files, start_t, end_t):
    if start_t == None or end_t == None:
        return(files)

    files_in_window = []
    # keep files that are between start_t and end_t
    for file in files:
        if float(file.stem) >= start_t and\
           float(file.stem) <= end_t:
            files_in_window.append(file)
    return(files_in_window)

#
# This method takes the voltage and time data for a specific roles
# .. data on a selected channel to create multiple plots
def make_fig(t, x, NFFT, Fs, png_file_name, title, start_time, selected_channel, show=False):
    fig = plt.figure(constrained_layout=True)
    fig.set_size_inches(17, 11)

    gs = GridSpec(3, 6, figure=fig)
    
    ax1 = plt.subplot(gs.new_subplotspec((0, 0), colspan=6))
    ax1.plot(t, x)
    ax1.set_title('Voltage vs. Sample Number')
    ax1.set_xlabel('Sample Number')
    ax1.set_ylabel('Voltage')

    ax2 = plt.subplot(gs.new_subplotspec((1, 0), colspan=6))
    Pxx, freqs, bins, im = ax2.specgram(x, NFFT=NFFT, Fs=Fs)
    ax2.set_title('Channel {} Spectrogram Fs={}Hz, NFFT={}'.format(selected_channel, Fs, NFFT))
    ax2.set_xlabel('Time in seconds since {}'.format(start_time))
    ax2.set_ylabel('Frequency Hz')

    ax3 = plt.subplot(gs.new_subplotspec((2, 0), colspan=3))
    ax3.psd(Pxx, NFFT, Fs)
    ax3.set_title('Power Spectral Density')

    ax4 = plt.subplot(gs.new_subplotspec((2, 3), colspan=3))
    ax4.psd(freqs, NFFT, Fs)
    ax4.set_title('Frequencies Corresponding to Power Spectral Density')

    fig.suptitle(title, fontsize=16)

    # save fig and output progress to console
    plt.savefig(png_file_name)
    print('Created: ' + png_file_name)

    if show:
        plt.show()
    plt.close(fig)

def get_files(path, role):
    return(sorted(pathlib.Path('{}/{}_DAQ/'.format(path, role)).glob('1*.txt')))

def get_fig_dir(path, role):
    fig_dir = '{}/{}_DAQ/figs'.format(path, role)
    fig_dir = os.path.abspath(fig_dir)

    if not os.path.exists(fig_dir):
        os.mkdir(fig_dir)

    return(fig_dir)

def main(args):
    data_files = {}
    data = {}
    fig_dir = {}
    figs = {}
    role = args.role

    for r in role:
        data_files[r] = get_files(path=args.data_directory, role=r)
        fig_dir[r]    = get_fig_dir(path=args.data_directory, role=r)
        data[r]       = []
        figs[r]       = []
    print('Sorted and aggregated all data files')

    NFFT = args.nfft  # the length of the windowing segments
    Fs   = args.sample_rate  # the sampling frequency

    # loop through all the roles and create plots
    for i in range(len(role)):
        files_in_window = get_files_in_window(files=data_files[role[i]], start_t=args.start, end_t=args.end)
        j = 0

        start_time, data = get_data_across_files(files_in_window, args.channel)
        if len(data) <= 0:
            break
        print('Aggregated all {} DAQ data'.format(role[i]))
        # Now plot data and save
        title = 'Data for Channel {} on {} DAQ device data start (local time): {}'\
                .format(args.channel, role[i], datetime.fromtimestamp(start_time))
        # import ipdb; ipdb.set_trace() # BREAKPOINT
        # setup our time vector and data vector for this data
        t = np.linspace(0.0, len(data), len(data))
        x = data
        # create the png file name
        png_file_name = '{}/{}_ch{}_{}.png'.format(fig_dir[role[i]], role[i], args.channel, start_time)
        # this will create and save the figure

        print('Creating Spectrogram for {} DAQ data:'.format(role[i]))
        if not args.script:
            make_fig(t, x, NFFT, Fs, png_file_name, title, datetime.fromtimestamp(start_time), args.channel, show=args.show_fig)
        else:
            make_fig(t, x, NFFT, Fs, png_file_name, title, datetime.fromtimestamp(start_time), args.channel)

        print('[{}/{}]: '.format(j, len(files_in_window)), end='')
        j+=1

        if not args.script:
            input('Hit enter to continue...')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--channel', help='Which channel data should be used', required=False, type=int)
    parser.add_argument('--sample-rate', help='Sample rate in Hz', required=False, type=int)
    parser.add_argument('--nfft', help='NFFT', required=False, type=int)
    parser.add_argument('--file-length-sec', help='Duration of each data file', required=False, type=int)
    parser.add_argument('--data-directory', help='Root directory for the data', required=True)
    parser.add_argument('--start', help='Start time for window of data', required=False, type=float)
    parser.add_argument('--end', help='End time for window of data', required=False, type=float)
    parser.add_argument('--debug', help='Show debugging print messages', action='store_true')
    parser.add_argument('--quiet', help='No Console Output', action='store_true')
    parser.add_argument('--show-fig', help='Show each fig? Default is False', action='store_true')    
    parser.add_argument('--tone-test', help='Cancel out signals from both DAQs - default False', action='store_true')    
    parser.add_argument('--verbose', help='Verbose output - may slow process on slower CPUs', action='store_true')
    parser.add_argument('--mode', help='Data output mode', choices=['binary', 'text'], required=False)
    parser.add_argument('--role', nargs='*', help='Prefix to data directory for multiple DAQs Defaults to MASTER/SLAVE', required=False)
    parser.add_argument('-s', '--script', help='Run from script (Will not ask for user input)', action='store_true')
    parser.set_defaults(channel=0, 
                        sample_rate=19200,
                        nfft=256,
                        file_length_sec=1.0,
                        start=None,
                        end=None,
                        mode='text',
                        role=['MASTER', 'SLAVE'])
    args = parser.parse_args()
    try:
        main(args)
    except KeyboardInterrupt:
        print('\n\n\tEnding...\n')
        exit()