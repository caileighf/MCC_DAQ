import matplotlib.pyplot as plt
import numpy as np
import pathlib
import glob
import os
import sys
import time
import datetime
from matplotlib.gridspec import GridSpec
import matplotlib.dates as mdate
from interactive_params import interactive_params, get_blank_param, get_available_methods
from prompt_utils import print_line, print_lines, get_yes_no
import scipy.io as sio
import pickle as pl
import traceback

from gps_data_packet import GPSDataPacket, GPSLogParser, GPSPlotter
from imu_data_packet import IMUDataPacket, IMULogParser, IMUPlotter
from ais_data_packet import AISDataPacket, AISLogParser, AISPlotter

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

def get_log_parser(path, pos_type, imu_use_euler=True):
    # TODO: handle possible failure if path does not have GPS.csv etc...
    if pos_type == 'AIS':
        log_file = sorted(pathlib.Path('{}/'.format(path)).glob('AIS.json'))[0]
        return(AISLogParser(log_file=log_file))
    elif pos_type == 'GPS':
        log_file = sorted(pathlib.Path('{}/'.format(path)).glob('{}*.csv'.format(pos_type)))[0]
        return(GPSLogParser(log_file=log_file))
    elif pos_type == 'IMU':
        log_file = sorted(pathlib.Path('{}/'.format(path)).glob('{}*.csv'.format(pos_type)))[0]
        return(IMULogParser(log_file=log_file, use_euler=imu_use_euler))
    else:
        raise RuntimeError('There is no log parser to match \"{}\" position data'.format(pos_type))

#
# This method returns only the data that fall within the specified 
# .. window of time 
def get_pos_data_in_window(parser, start_t, end_t, pos_type):
    # TODO: this is a hack... should have required fields as a key,val pair in pos_type
    required_fields = []
    if pos_type == 'AIS':
        required_fields = ['transmission',]
    elif pos_type == 'IMU':
        required_fields = ['timestamp', 'roll', 'pitch', 'yaw',]
    elif pos_type == 'GPS':
        required_fields = ['timestamp', 'gps_time', 'raw', 'latitude', 'longitude',]

    data, start_actual = parser.parse(start=start_t, end=end_t, required_fields=required_fields)
    return(data, start_actual)

def get_files(path, role):
    return(sorted(pathlib.Path('{}/{}_DAQ/'.format(path, role)).glob('1*.txt')))

def create_data_dir(path):
    if not os.path.exists(path):
        os.mkdir(path)
    return(os.path.abspath(path))

def get_fig_dir(path, role, postfix, pickle_fig, mat):
    fig_dir = '{}/{}_DAQ/figs_{}'.format(path, role, postfix)
    fig_dir = os.path.abspath(fig_dir)

    if not os.path.exists(fig_dir):
        os.mkdir(fig_dir)

    pickled_fig_dir = create_data_dir('{}/interactive_figs'.format(fig_dir)) if pickle_fig else None
    mat_dir         = create_data_dir('{}/matlab'.format(fig_dir)) if mat else None

    return({
        'fig': fig_dir, 
        'pickle': pickled_fig_dir, 
        'mat': mat_dir
        })

def get_pos_fig_dir(path, postfix, pickle_fig, mat):
    fig_dir = '{}/figs_{}'.format(path, postfix)
    fig_dir = os.path.abspath(fig_dir)

    if not os.path.exists(fig_dir):
        os.mkdir(fig_dir)

    pickled_fig_dir = create_data_dir('{}/interactive_figs'.format(fig_dir)) if pickle_fig else None
    mat_dir         = create_data_dir('{}/matlab'.format(fig_dir)) if mat else None

    return({
        'fig': fig_dir, 
        'pickle': pickled_fig_dir, 
        'mat': mat_dir
        })

#
# This method takes the voltage and time data for a specific roles
# .. data on a selected channel to create multiple plots
def create_specgram_fig(t, x, NFFT, Fs, fig_dir, png_file_name, title, start_time, selected_channel, pickle_fig=False, show=False, print_success=True):
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
    fig_filename = '{}/{}.png'.format(fig_dir['fig'], png_file_name)

    plt.savefig(fig_filename)
    if pickle_fig:
        if show:
            # we can't pickle a file AND display it.
            # .. raise RuntimeError so user knows they are not pickling
            raise RuntimeError('Displaying the plot AND pickling the fig is not supported at this time.')
        # Save figure handle to disk
        with open('{}/{}.pickle'.format(fig_dir['pickle'], png_file_name), 'wb') as f:
            pl.dump(fig, f)
            if print_success:
                print_line('<info_italic>Created:</info_italic> {}.pickle'.format('{}/{}'.format(fig_dir['pickle'], png_file_name)))

    if show:
        plt.show()
    if print_success: 
        print_line('<info_italic>Created:</info_italic> {}'.format(fig_filename))
    plt.close(fig)

#
# This method takes the voltage and time data for a specific roles
# .. data on a selected channel to create multiple plots
def create_position_fig(parser, pos_type, fig_dir, png_file_name, title, start_time, pickle_fig=False, show=False, print_success=True):
    fig = plt.figure()#constrained_layout=True)
    fig.set_size_inches(17, 11)

    ax = fig.add_subplot(1, 1, 1)

    if pos_type == 'AIS':
        plotter = AISPlotter(data_set=parser.data_set)
    elif pos_type == 'GPS':
        plotter = GPSPlotter(data_set=parser.data_set)
    elif pos_type == 'IMU':
        plotter = IMUPlotter(data_set=parser.data_set)
    else:
        raise RuntimeError('There is no plotter to match \"{}\" position data'.format(pos_type))

    ax, rotate_xticks = plotter.plot(ax)

    if rotate_xticks:
        plt.xticks(rotation=25)

    fig.suptitle(title, fontsize=16)

    # save fig and output progress to console
    fig_filename = '{}/{}.png'.format(fig_dir['fig'], png_file_name)

    plt.savefig(fig_filename)
    if pickle_fig:
        if show:
            # we can't pickle a file AND display it.
            # .. raise RuntimeError so user knows they are not pickling
            raise RuntimeError('Displaying the plot AND pickling the fig is not supported at this time.')
        # Save figure handle to disk
        with open('{}/{}.pickle'.format(fig_dir['pickle'], png_file_name), 'wb') as f:
            pl.dump(fig, f)
            if print_success:
                print_line('<info_italic>Created:</info_italic> {}.pickle'.format('{}/{}'.format(fig_dir['pickle'], png_file_name)))

    if show:
        plt.show()
    if print_success: 
        print_line('<info_italic>Created:</info_italic> {}'.format(fig_filename))
    plt.close(fig)

def save_mat(params, fname, print_success=True):
    sio.savemat('{}.mat'.format(fname), params)
    if print_success:
        print_line('<info_italic>Created:</info_italic> {}.mat'.format(fname))

def create_mat_params(t_vect, t_vect_precision_error, x, NFFT, Fs, fig_dir, png_file_name, selected_channel, role):
    params = {
        'uniform_time_vector_ISO': [t.isoformat() for t in t_vect],
        'uniform_time_vector_epoch': [np.float64(t.timestamp()) for t in t_vect],
        'time_vector_step_precision_error_sec': np.float64(t_vect_precision_error),
        'voltage_vector': np.array(x),
        'NFFT': np.uint32(NFFT),
        'Fs': np.uint32(Fs),
        'channel': np.uint8(selected_channel),
        'role': role,
    }
    return(params, '{}/{}'.format(fig_dir['mat'], png_file_name))

def create_time_vector(data, dt_between_samples, start_t, is_data_contiguous):
    if not is_data_contiguous:
        raise RuntimeError('Creating a uniform time vector is only supported for contiguous data at this time.')
    # create a uniform time vector
    # .. the DAQ data is recorded continuously with no gaps
    # .. the timestamp first the first value is the only one that matters
    # .. for this context.
    t_vect = []
    total_seconds = (len(data) * dt_between_samples)
    # np.linspace because it's inclusive
    # .. and adding a 0.0 time delta to the start seemed more intuitive
    t, t_step_actual = np.linspace(0.0, total_seconds, len(data), retstep=True)
    # record floating point precision error for time vector
    precision_error = np.abs(t_step_actual - dt_between_samples)

    for dt in t:
        t_vect.append(start_t + datetime.timedelta(seconds=dt))

    return(precision_error, t_vect)

def fill_non_uniform_tvec(t_vect, d_vect, handle_null):
    pass