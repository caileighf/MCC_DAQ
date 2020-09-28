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
from plot_utils import (get_pos_fig_dir,
                        get_pos_data_in_window,
                        get_log_parser,
                        create_position_fig,
                        save_mat,
                        get_pos_fig_dir)
from common_argparse import get_postion_bounded_args
# 
from gps_data_packet import GPSDataPacket, GPSLogParser
from imu_data_packet import IMUDataPacket, IMULogParser
from ais_data_packet import AISDataPacket, AISLogParser

def main(args):
    #
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
    
    text = 'Selected window will create a position plot that covers {} of data. Continue?'.format(duration_str)
    if not args.script and not get_yes_no(title='Continue with selected duration', text=text):
        exit()
    elif not args.script:
        print_line('<title>Window Duration:</title> {}\n'.format(duration_str))

    data_log_parser = {}
    data = {}
    fig_dir = {}
    pos_type = args.pos_type

    for p in pos_type:
        data_log_parser[p] = get_log_parser(path=args.data_directory, pos_type=p, imu_use_euler=not args.use_quat)
        fig_dir[p] = get_pos_fig_dir(path=args.data_directory, 
                                     postfix=args.postfix,
                                     mat=args.mat,
                                     pickle_fig=args.pickle)
        data[p] = []

    # loop through all the pos_types and create plots
    while True:
        for i in range(len(pos_type)):
            if pos_type[i] != 'IMU':
                continue

            if not args.script: print_line('Aggregating <info_italic>{}</info_italic> data...'.format(pos_type[i]))   
            try:
                data[pos_type[i]], start_actual = get_pos_data_in_window(parser=data_log_parser[pos_type[i]], 
                                                                         start_t=args.start.timestamp(), 
                                                                         end_t=args.end.timestamp(),
                                                                         pos_type=pos_type[i])
            except RuntimeError as e:
                if not args.script:
                    print_line('{}'.format(e.args[0]), l_style='error')
                    return
                else:
                    raise

            if not args.script: print_line('Starting plots for <info_italic>{}</info_italic> data:'.format(pos_type[i]))

            # create the png file name & other labels
            if isinstance(start_actual, datetime.datetime):
                start_actual = start_actual.timestamp()
            png_file_name = '{}_{}'.format(pos_type[i], float(start_actual))
            title = 'Data from {}'.format(pos_type[i])
            if pos_type[i] == 'IMU':
                title = '{} (Using {} to calculate Roll/Pitch/Yaw)'.format(title, ('Quaturnion components' if args.use_quat else 'Euler angles'))
            title = title.replace(' ', '\ ')
            full_title = r"$\bf{" + title + "}$\n" + 'Start: {}, Stop: {}, Duration: {}'.format(args.start, args.end, duration_str)
            
            try:
                # this will create and save the figure
                create_position_fig(parser=data_log_parser[pos_type[i]],
                                    pos_type=pos_type[i],
                                    fig_dir=fig_dir[pos_type[i]],
                                    png_file_name=png_file_name, 
                                    title=full_title, 
                                    start_time=start_actual, 
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
                if pos_type[i] == 'AIS':
                    params = {
                        # each transmission is one AIS message
                        # .. it includes order_received, location information, and vessel id
                        # .. we can add more
                        'transmission': np.array(data[pos_type[i]]['transmission']),
                        'sensor': pos_type[i],
                    }
                elif pos_type[i] == 'IMU':
                    params = {
                        'uniform_time_vector_ISO': [t.isoformat() for t in data[pos_type[i]]['timestamp']],
                        'uniform_time_vector_epoch': [np.float64(t.timestamp()) for t in data[pos_type[i]]['timestamp']],
                        'roll': np.array(data[pos_type[i]]['roll']),
                        'pitch': np.array(data[pos_type[i]]['pitch']),
                        'yaw': np.array(data[pos_type[i]]['yaw']),
                        'sensor': pos_type[i],
                    }
                elif pos_type[i] == 'GPS':
                    params = {
                        'uniform_time_vector_ISO': [t.isoformat() for t in data[pos_type[i]]['timestamp']],
                        'uniform_time_vector_epoch': [np.float64(t.timestamp()) for t in data[pos_type[i]]['timestamp']],
                        'gps_time': np.array(data[pos_type[i]]['gps_time']),
                        'raw': np.array(data[pos_type[i]]['raw']),
                        'latitude': np.array(data[pos_type[i]]['latitude']),
                        'longitude': np.array(data[pos_type[i]]['longitude']),
                        'sensor': pos_type[i],
                    }
                save_mat(params=params, 
                         fname='{}/{}.mat'.format(fig_dir[pos_type[i]]['mat'], png_file_name), 
                         print_success=(not args.script))


        clean_exit_msg = [
            '-'*88,
            'Done with plots!',
        ]
        for k, v in fig_dir.items():
            clean_exit_msg.append('\nPlots for ' + k + ' Data:')
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
    args = get_postion_bounded_args()

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