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
from prompt_utils import print_line, print_lines, get_yes_no
import scipy.io as sio
import pickle as pl
import traceback

# plot utils 
from plot_utils import (get_data_from_list_files,
                        get_files_in_window,
                        create_specgram_fig,
                        save_mat,
                        create_mat_params,
                        get_files,
                        create_data_dir,
                        get_fig_dir,
                        create_time_vector)
from common_argparse import get_specgram_bounded_args

def main(args):
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
    elif not args.script:
        print_line('<title>Window Duration:</title> {}\n'.format(duration_str))

    data_files = {}
    data = {}
    fig_dir = {}
    figs = {}
    role = args.role

    for r in role:
        data_files[r] = get_files(path=args.data_directory, role=r)
        fig_dir[r]    = get_fig_dir(path=args.data_directory, 
                                    role=r, 
                                    postfix=args.postfix,
                                    mat=args.mat,
                                    pickle_fig=args.pickle)
        data[r]       = []
        figs[r]       = []
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
                    if args.script:
                        raise RuntimeError('No files in the provided directory!')
                    print_line('No files in the provided directory!')
                    exit()
                else:
                    # duration is too short
                    message = [
                        'Provided time window too small!',
                        ' <info>Duration:</info>    {} second(s)'.format(duration),
                        ' <info>File Length:</info> {} second(s)\n'.format(args.file_length_sec),
                        'Make sure your duration is greater than <token>{}</token> second(s)'.format(args.file_length_sec)
                    ]
                    if args.script:
                        raise RuntimeError(message)
                        exit()

                    print_line(message[0], l_style='error')
                    print_lines(message[1:-1], l_style='subtitle')
                    print_line(message[-1], l_style='info_italic')
                    exit()

            if not args.script: print_line('Starting plots for <info_italic>{} DAQ</info_italic> data:'.format(role[i]))

            data = get_data_from_list_files(files_in_window, args.channel)

            # Now plot data and save
            title = 'Data for Channel {} on {} DAQ device'.format(args.channel, role[i])
            title = title.replace(' ', '\ ')

            full_title = r"$\bf{" + title + "}$\n" + 'Start: {}, Stop: {}, Duration: {}'.format(args.start, args.end, duration_str)
            # setup our vector for number of samples
            t = np.linspace(0.0, len(data), len(data))

            # creates uniform time vector
            # !! This should not be used for data that is not contiguous !
            err, t_vect = create_time_vector(data=data,
                                             dt_between_samples=(1 / Fs),
                                             start_t=args.start,
                                             is_data_contiguous=True)

            x = np.array(data)
            # create the png file name
            png_file_name = '{}_CH{}_{}'.format(role[i], args.channel, float(files_in_window[0].stem))
            try:
                # this will create and save the figure
                create_specgram_fig(t=t, x=x, NFFT=NFFT, Fs=Fs,
                                    fig_dir=fig_dir[role[i]],
                                    png_file_name=png_file_name, 
                                    title=full_title, 
                                    start_time=args.start, 
                                    selected_channel=args.channel, 
                                    pickle_fig=args.pickle, 
                                    show=args.display,
                                    print_success=(not args.script))
            except RuntimeError as e:
                if not args.script:
                    print_line('{}'.format(e.args[0]), l_style='error')
                    return
                else:
                    raise

            if args.mat:
                # create .mat
                params, fname = create_mat_params(t_vect=t_vect, 
                                                  t_vect_precision_error=err, 
                                                  x=x, 
                                                  NFFT=NFFT, 
                                                  Fs=Fs, 
                                                  fig_dir=fig_dir[role[i]], 
                                                  png_file_name=png_file_name, 
                                                  selected_channel=args.channel, 
                                                  role=role[i])
                save_mat(params=params, 
                         fname=fname, 
                         print_success=(not args.script))


        clean_exit_msg = [
            '-'*88,
            'Done with plots!',
        ]
        for k, v in fig_dir.items():
            clean_exit_msg.append('\nPlots for ' + k + ' DAQ:')
            for _k, _v in v.items():
                clean_exit_msg.append('  {} directory: {}'.format(_k, _v))

        clean_exit_msg.append('-'*88)

        if not args.script: 
            print_line(clean_exit_msg[0])
            print_line(clean_exit_msg[1], l_style='title')
            print_lines(clean_exit_msg[2:-1], l_style='subtitle')
            print_line(clean_exit_msg[-1])
            
        else:
            for line in clean_exit_msg:
                print(line)
        break


if __name__ == '__main__':
    # see common_argparse.py for breakdown
    args = get_specgram_bounded_args()

    try:
        main(args)
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
    finally:
        if not args.script:
            print_line('\n\n\tEnding...\n')
        else:
            print('\n\n\tEnding...\n')
        exit()