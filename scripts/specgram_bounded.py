import argparse
import matplotlib.pyplot as plt
import numpy as np
import pathlib
import glob
import os
import sys
import time
import datetime
from matplotlib.gridspec import GridSpec
from prompt_toolkit.shortcuts import ProgressBar
from interactive_params import interactive_params, get_blank_param, get_available_methods
from prompt_utils import print_line, get_yes_no

#
# This method pull n channel data from file and returns list of floats
def get_data(filename, selected_channel):
    data = []
    with open(filename, 'r') as f:
        start = time.time()
        for i, line in enumerate(f.readlines()):
            if time.time()-start >= 1:
                start = time.time()
            channel_data = line.split(',')
            data.append(float(channel_data[selected_channel]))
    return(data)

def get_data_from_list_files(files, selected_channel):
    data = []
    for file in files:
        d = get_data(file, selected_channel)
        [data.append(x) for x in d]
    return(data)
#
# This method takes a list of files and a chunk size and
# .. yields the list of floats returned by get_data() for chunk_size # of files
# .. Use this in a for loop for getting data that spans multiple files
def batch_files(files, chunk_size, selected_channel):
    if len(files) <= 0:
        yield None, None

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
                # done! 
                yield None, []

    yield start, data

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
    if show:
        plt.show()
    print_line('<info_italic>Created:</info_italic> {}'.format(png_file_name))
    plt.close()

def get_files(path, role):
    return(sorted(pathlib.Path('{}/{}_DAQ/'.format(path, role)).glob('1*.txt')))

def get_fig_dir(path, role, postfix):
    fig_dir = '{}/{}_DAQ/figs_{}'.format(path, role, postfix)
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
        fig_dir[r]    = get_fig_dir(path=args.data_directory, role=r, postfix=args.postfix)
        data[r]       = []
        figs[r]       = []

    #
    # Determine chunk size
    # .. first check is user wants to do more than one file per plot
    if args.interactive:
        methods = get_available_methods(as_dict=True)
        param = get_blank_param()
        param['method'] = methods['Date/time window input']
        param['start_datetime'] = args.start
        param['stop_datetime'] = args.end
        results = interactive_params([param])
        args.start = results[0][1][0]
        args.end   = results[0][1][1]

    # figure out duration of time we care about
    duration = args.end - args.start
    duration_str = str(duration)
    duration = duration.total_seconds()
    
    text = 'Selected window will create a spectrogram that covers {} of data. Continue?'.format(duration_str)
    if not args.script and not get_yes_no(title='Continue with selected duration', text=text):
        exit()
    else:
        print_line('<title>Window Duration:</title> {}\n'.format(duration_str))
    # batch size for how many files to read at once
    # .. if duration is 1 hour,
    # .. 60 sec * 60 mins = 3600 seconds, 
    # .. so, if file_length is 1.0 second and the duration is 3600 seconds, 
    # .. the chunk size will be 3600 files
    #
    chunk_size = int(duration / args.file_length_sec)

    NFFT = args.nfft  # the length of the windowing segments
    Fs   = args.sample_rate  # the sampling frequency

    # loop through all the roles and create plots
    while True:
        for i in range(len(role)):
            files_in_window = get_files_in_window(files=data_files[role[i]], 
                                                  start_t=args.start.timestamp(), 
                                                  end_t=args.end.timestamp())

            if len(files_in_window) <= 0:
                # no files... possible duration is off or empty directory
                if duration > args.file_length_sec:
                    # no files in directory
                    print_line('No files in the provided directory!')
                    exit()
                else:
                    # duration is too short
                    print_line('Provided time window too small!', l_style='error')
                    print_line(' <info>Duration:</info>    {} second(s)'.format(duration))
                    print_line(' <info>File Length:</info> {} second(s)\n'.format(args.file_length_sec))
                    print_line('Make sure your duration is greater than <token>{}</token> second(s)'.format(args.file_length_sec), 
                               l_style='info_italic')
                    exit()

            print_line('Starting batch for {} DAQ data:'.format(role[i]))

            data = get_data_from_list_files(files_in_window, args.channel)

            # Now plot data and save
            title = 'Data for Channel {} on {} DAQ device'.format(args.channel, role[i])
            title = title.replace(' ', '\ ')

            subtitle = r"Start: $\bf{" + str(args.start).replace(' ', '\ ') + "}$ "\
                       + r"End: $\bf{" + str(args.end).replace(' ', '\ ')   + "}$ "\
                  + r"Duration: $\bf{" + duration_str.replace(' ', '\ ')    + "}$ " + '\n'

            full_title = r"$\bf{" + title + "}$\n" + 'Start: {}, Stop: {}, Duration: {}'.format(args.start, args.end, duration_str)
            # setup our time vector and data vector for this data
            t = np.linspace(0.0, len(data), len(data))
            x = data
            # create the png file name
            png_file_name = '{}/{}_ch{}_{}.png'.format(fig_dir[role[i]], role[i], args.channel, float(files_in_window[0].stem))
            # this will create and save the figure
            make_fig(t, x, NFFT, Fs, png_file_name, full_title, args.start, args.channel, show=args.display)

        print_line('\nDone with plots!', l_style='title')
        break


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--postfix', help='Postfix for fig directory', required=False, type=str)
    parser.add_argument('--channel', help='Which channel data should be used', required=False, type=int)
    parser.add_argument('--sample-rate', help='Sample rate in Hz', required=False, type=int)
    parser.add_argument('--nfft', help='NFFT', required=False, type=int)
    parser.add_argument('--file-length-sec', help='Duration of each data file', required=False, type=int)
    parser.add_argument('--data-directory', help='Root directory for the data', required=True)
    parser.add_argument('--start', help='Start time for window of data', required=False, type=float)
    parser.add_argument('--end', help='End time for window of data', required=False, type=float)
    parser.add_argument('--debug', help='Show debugging print messages', action='store_true')
    parser.add_argument('--quiet', help='No Console Output', action='store_true')
    parser.add_argument('--verbose', help='Verbose output - may slow process on slower CPUs', action='store_true')
    parser.add_argument('--mode', help='Data output mode', choices=['binary', 'text'], required=False)
    parser.add_argument('--role', nargs='*', help='Prefix to data directory for multiple DAQs Defaults to MASTER/SLAVE', required=False)
    parser.add_argument('-s', '--script', help='Run from script (Will not ask for user input)', action='store_true')
    parser.add_argument('-i', '--interactive', help='Interactive time', action='store_true')
    parser.add_argument('--display', help='Display each plot as they are created -- this will pause execution until the plot is closed', action='store_true')
    parser.set_defaults(postfix='long_duration',
                        channel=0, 
                        sample_rate=19200,
                        nfft=256,
                        file_length_sec=1.0,
                        start=None,
                        end=None,
                        mode='text',
                        role=['MASTER', 'SLAVE'])
    args = parser.parse_args()

    # if user has run with script flag make sure needed values are set
    if args.script:
        args.interactive = False # just incase. There is probably a cleaner way to do this
        if args.start == None or args.end == None:
            print_line('To run as a script you MUST provide a start time and end time.\n', l_style='error')
            exit()

    # turn data_directory into pathlib obj
    args.data_directory = pathlib.Path(args.data_directory)

    # figure out if we need to interactively enter time
    if args.start == None and args.end == None:
        args.interactive = True
        # setup sane default values
        # .. we may be able to grab the date from the tstamp on the data directory
        try:
            tstamp = args.data_directory.stem[len('data_'):]
            args.start = datetime.datetime.strptime(tstamp, '%Y-%m-%d %H:%M:%S')
            args.end = args.start.replace(second=args.start.second + int(args.file_length_sec) * 2)
        except:
            # tstamp is not embedded in dir name
            pass
    else:
        # user passed both start and end datetime
        args.start = datetime.datetime.strptime(args.start, '%Y-%m-%d %H:%M:%S')
        args.end = datetime.datetime.strptime(args.end, '%Y-%m-%d %H:%M:%S')

    try:
        main(args)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
    finally:
        print_line('\n\n\tEnding...\n')
        exit()