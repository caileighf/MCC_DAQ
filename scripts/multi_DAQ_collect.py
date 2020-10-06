#
# Woods Hole Oceanographic Institution
# Author: Caileigh Fitzgerald
# Email:  cfitzgerald@whoi.edu
# Date:   06/20/2020
#
# File: multi_DAQ_collect.py
#
from __future__ import print_function
import sys
import time
import os
import argparse
from datetime import datetime
from uldaq import (get_daq_device_inventory, DaqDevice, AInScanFlag, ScanStatus,
                   ScanOption, create_float_buffer, InterfaceType, AiInputMode, ULException)
from async_daq_data_handler5 import AsyncDAQDataHandler
# import async_daq_data_handler2
# Methods for handling DAQ config and setup
from daq_utils import (print_config,
                       print_total_channel_count, 
                       config_daq, 
                       config_daq_options_master_slave, 
                       config_ai_device,
                       create_output_str,
                       display_scan_options,
                       clear_eol,
                       reset_cursor)
# Methods for interactive prompt when user chooses interactive mode at runtime
from prompt_utils import (print_title,
                          print_line,
                          print_lines, 
                          print_pre_prompt, 
                          print_post_prompt, 
                          prompt_user, 
                          path_validator, PathCompleter,
                          number_validator, float_validator, style)

def get_loading_char(mod):
    return('/' if mod%2==0 else '\\')

def main(args, master_dir, slave_dir):
    """Multiple DAQs Collecting in CONTINUOUS mode."""
    daq_device     = {'MASTER': None, 'SLAVE': None}
    ai_device      = {'MASTER': None, 'SLAVE': None}
    ai_info        = {'MASTER': None, 'SLAVE': None}
    ao_device      = {'MASTER': None, 'SLAVE': None} # needed for setting SYNC pin
    ao_config      = {'MASTER': None, 'SLAVE': None} # needed for setting SYNC pin
    input_mode     = {'MASTER': None, 'SLAVE': None}
    status         = {'MASTER': ScanStatus.IDLE, 'SLAVE': ScanStatus.IDLE}
    interface_type = InterfaceType.USB
    scan_options   = {
                      'MASTER': ScanOption.CONTINUOUS | ScanOption.PACEROUT, 
                      'SLAVE':  ScanOption.EXTCLOCK | ScanOption.CONTINUOUS
                      }
    flags          = {
                      'MASTER': AInScanFlag.DEFAULT, 
                      'SLAVE':  AInScanFlag.DEFAULT
                      }
    data_dir       = {
                      'MASTER': master_dir, 
                      'SLAVE': slave_dir
                      }
    data           = {'MASTER': None, 'SLAVE': None}
    #
    # SLAVE DAQ will use all 8 Channels
    # MASTER DAQ will use remaining channels up to args.channels
    #
    low_channel    = {'MASTER': 0, 'SLAVE': 0}
    high_channel   = {'MASTER': int(args.channels/2)-1, 'SLAVE': int(args.channels/2)-1}
    channel_count  = {'MASTER': args.channels/2, 'SLAVE': args.channels/2}
    rate           = { # rate (float) A/D sample rate in samples per channel per second.
                      'MASTER': args.sample_rate, 
                      'SLAVE': args.sample_rate
                      }     
    samples_per_channel = args.sample_rate * 30 # *30 gives use extra time to read
    file_length_sec = float(args.file_length_sec)
    v_range = {'MASTER': None, 'SLAVE': None}
    #
    #   Takes passed args and gathers all connected DAQ devices
    #   .. user selects DAQ from list - return val is passed to context mngr
    #
    daq_device_params = {'MASTER': None, 'SLAVE': None}
    try:
        devices = config_daq_options_master_slave(interface_type=interface_type, 
                                                  script=args.script, 
                                                  master_id='01C5B1B5', 
                                                  slave_id='01B6492D')
        daq_device_params['SLAVE']  = devices[0]
        daq_device_params['MASTER'] = devices[1]
    except RuntimeError as e:
        print_line(e)
        exit(1)

    start_test = time.time()
    # 
    #   Connect to the selected DAQ with the context manager
    #
    #   Starting with the 'SLAVE' DAQ Device
    #
    with DaqDevice(daq_device_params['SLAVE']) as daq_device['SLAVE']:
        # configure the ai_device with the daq_device instance
        ai_device['SLAVE'], ai_info['SLAVE'] = config_ai_device(daq_device=daq_device['SLAVE'])
        # finish configuring the options for the daq_device instance
        input_mode['SLAVE'], channel_count['SLAVE'], v_range['SLAVE'] = config_daq(daq_device=daq_device['SLAVE'], 
                                                        ai_info=ai_info['SLAVE'], 
                                                        channel_range=(low_channel['SLAVE'], high_channel['SLAVE']))
        os.system('clear')
        data['SLAVE'] = create_float_buffer(channel_count['SLAVE'], samples_per_channel)

        # Start the acquisition for the 'SLAVE' DAQ.
        # .. it will wait for the 'MASTER' DAQ's EXTCLOCK signal
        rate['SLAVE'] = ai_device['SLAVE'].a_in_scan(low_channel['SLAVE'], 
                                                     high_channel['SLAVE'], 
                                                     input_mode['SLAVE'],
                                                     v_range['SLAVE'], 
                                                     samples_per_channel,
                                                     rate['SLAVE'], 
                                                     scan_options['SLAVE'], 
                                                     flags['SLAVE'], 
                                                     data['SLAVE'])
        if not args.quiet:
            # Print config options
            print_config(sample_rate=rate['SLAVE'], 
                         file_length=file_length_sec, 
                         data_directory=data_dir['SLAVE'], 
                         input_mode=input_mode['SLAVE'].name, 
                         channel_range=(low_channel['SLAVE'], high_channel['SLAVE']), 
                         voltage_range=v_range['SLAVE'], 
                         scan_options=scan_options['SLAVE'],
                         role='SLAVE',
                         print_head_space=False,
                         is_actual=True)
            print_total_channel_count(args.channels)

        async_writer_SLAVE = AsyncDAQDataHandler(float_buffer=data['SLAVE'], 
                                                 role='SLAVE', 
                                                 ai_device=ai_device['SLAVE'], 
                                                 channel_count=channel_count['SLAVE'], 
                                                 data_dir=data_dir['SLAVE'],
                                                 sample_rate=args.sample_rate,
                                                 scan_options=display_scan_options(scan_options['SLAVE']),
                                                 v_range=v_range['SLAVE'],
                                                 input_mode=input_mode['SLAVE'],
                                                 flags=flags['SLAVE'],
                                                 file_length=file_length_sec,)
        #
        # Now setup 'MASTER' DAQ
        # 
        with DaqDevice(daq_device_params['MASTER']) as daq_device['MASTER']:
            # configure the ai_device with the daq_device instance
            ai_device['MASTER'], ai_info['MASTER'] = config_ai_device(daq_device=daq_device['MASTER'])
            # finish configuring the options for the daq_device instance
            input_mode['MASTER'], channel_count['MASTER'], v_range['MASTER'] = config_daq(daq_device=daq_device['MASTER'], 
                                                            ai_info=ai_info['MASTER'], 
                                                            channel_range=(low_channel['MASTER'], high_channel['MASTER']))

            # Allocate a buffer to receive the data.
            data['MASTER'] = create_float_buffer(channel_count['MASTER'], samples_per_channel)

            # Start the acquisition for the 'MASTER' DAQ.
            # .. when it starts it will thrigger the 'SLAVE'\
            pre_call = datetime.now()
            rate['MASTER'] = ai_device['MASTER'].a_in_scan(low_channel['MASTER'], 
                                                         high_channel['MASTER'], 
                                                         input_mode['MASTER'],
                                                         v_range['MASTER'], 
                                                         samples_per_channel,
                                                         rate['MASTER'], 
                                                         scan_options['MASTER'], 
                                                         flags['MASTER'], 
                                                         data['MASTER'])
            post_call = datetime.now()
            # average times from pre scan start and post scan start
            start_time_epoch = datetime.fromtimestamp(int(pre_call.timestamp() + post_call.timestamp()) / 2)

            if not args.quiet:
                # Print config options
                print_config(sample_rate=rate['MASTER'], 
                             file_length=file_length_sec, 
                             data_directory=data_dir['MASTER'], 
                             input_mode=input_mode['MASTER'].name, 
                             channel_range=(low_channel['MASTER'], high_channel['MASTER']), 
                             voltage_range=v_range['MASTER'], 
                             scan_options=scan_options['MASTER'],
                             role='MASTER',
                             print_head_space=False,
                             is_actual=True)

            print_line(' <info><b>ACTUAL START TIME:</b></info> <time>{}</time> epoch:[<time>{}</time>]'.format(start_time_epoch, start_time_epoch.timestamp()))
            print_line(' --data-dir \"{}\" --start-time {} '.format(data_dir['MASTER'][:data_dir['MASTER'].rfind('/')+1], 
                                                                     start_time_epoch.timestamp()))
            #
            #   In CONTINUOUS scan mode the start time for MASTER and SLAVE
            #   .. is the same. get the current time and use that as the start time for 
            #   .. both AsyncDAQDataHandler-s
            #

            async_writer_MASTER = AsyncDAQDataHandler(float_buffer=data['MASTER'], 
                                                      role='MASTER', 
                                                      ai_device=ai_device['MASTER'], 
                                                      channel_count=channel_count['MASTER'], 
                                                      data_dir=data_dir['MASTER'],
                                                      sample_rate=args.sample_rate,
                                                      scan_options=display_scan_options(scan_options['MASTER']),
                                                      v_range=v_range['MASTER'],
                                                      input_mode=input_mode['MASTER'],
                                                      flags=flags['MASTER'],
                                                      file_length=file_length_sec)
            
            #
            #   Let Async file writes know we're ready 
            #   .. so they can start writing
            #
            async_writer_MASTER.begin(start_time_epoch.timestamp())
            async_writer_SLAVE.begin(start_time_epoch.timestamp())

            prev_index      = {'MASTER': 0, 'SLAVE': 0}
            index           = {'MASTER': 0, 'SLAVE': 0}
            status          = {'MASTER': 0, 'SLAVE': 0}
            transfer_status = {'MASTER': 0, 'SLAVE': 0}
            output_str      = []
            f               = {'MASTER': None, 'SLAVE': None}
            try:
                start=time.time()
                if not args.quiet:
                    print('')
                    print_line(' | <info>CTRL + C to terminate the process</info>       ')
                    print_line(' |----------------------------------------------------- ')
                time.sleep(0.1)
                heart_beat_count = 0
                log = '{}/00log.log'.format(args.data_directory)
                while True:
                    reset_cursor()
                    clear_eol()
                    heart_beat_count += 1
                    if heart_beat_count >= 1000:
                        heart_beat_count = 0
                    print('Scanning... {}'.format(get_loading_char(heart_beat_count)))
                    try:
                        if not args.quiet and args.verbose:
                            # Get the status of the background operation
                            status['MASTER'], transfer_status['MASTER'] = ai_device['MASTER'].get_scan_status()
                            status['SLAVE'], transfer_status['SLAVE'] = ai_device['SLAVE'].get_scan_status()
                            index['MASTER'] = transfer_status['MASTER'].current_index
                            index['SLAVE'] = transfer_status['SLAVE'].current_index
                            reset_cursor()
                            clear_eol()
                            output_str = create_output_str(transfer_status['MASTER'], rate['MASTER'], role='MASTER')
                            # now append channel values for MASTER
                            for i in range(channel_count['MASTER']):
                                output_str.append('<b>Channel</b> [<b>{}</b>] = {:.6f}'.format(i+low_channel['MASTER'], 
                                                                                               data['MASTER'][index['MASTER'] + i]))
                            output_str += create_output_str(transfer_status['SLAVE'], rate['SLAVE'], role='SLAVE')
                            # now append channel values for SLAVE
                            for i in range(channel_count['SLAVE']):
                                output_str.append('<b>Channel</b> [<b>{}</b>] = {:.6f}'.format(i+low_channel['SLAVE'], 
                                                                                               data['SLAVE'][index['SLAVE'] + i]))
                            print_lines(output_str)

                        #
                        #   All file writing happens in another thread. 
                        #   .. run time.sleep(file_length) to print out info for user
                        #
                        time.sleep(file_length_sec)
                        if time.time() - start_test >= 10 and args.test:
                            # breakout!
                            print_line('Leaving from test!')
                            time.sleep(1)
                            raise(KeyboardInterrupt)

                    except Exception as e:
                        raise
                    except (ValueError, NameError, SyntaxError):
                        raise

                os.system('clear')
                print('Outside While true!')
            except KeyboardInterrupt:
                time.sleep(0.2)
                if not args.test:
                    os.system('clear')
                if not args.quiet:
                    # Print config options
                    print_config(sample_rate=rate['MASTER'], 
                                 file_length=file_length_sec, 
                                 data_directory=data_dir['MASTER'], 
                                 input_mode=input_mode['MASTER'].name, 
                                 channel_range=(low_channel['MASTER'], high_channel['MASTER']), 
                                 voltage_range=v_range['MASTER'], 
                                 scan_options=scan_options['MASTER'],
                                 role='MASTER',
                                 print_head_space=False,
                                 is_actual=True)
                    print_total_channel_count(args.channels)
                    print_config(sample_rate=rate['SLAVE'], 
                                 file_length=file_length_sec, 
                                 data_directory=data_dir['SLAVE'], 
                                 input_mode=input_mode['SLAVE'].name, 
                                 channel_range=(low_channel['SLAVE'], high_channel['SLAVE']), 
                                 voltage_range=v_range['SLAVE'], 
                                 scan_options=scan_options['SLAVE'],
                                 role='SLAVE',
                                 print_head_space=False,
                                 is_actual=True)
                    print_line(' <info><b>ACTUAL START TIME:</b></info> <time>{}</time> epoch:[<time>{}</time>]'.format(start_time_epoch, start_time_epoch.timestamp()))

                raise(KeyboardInterrupt)
            finally:
                async_writer_MASTER.stop()
                async_writer_SLAVE.stop()
                time.sleep(2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--channels', help='Number of channels or elements on the array to record with', required=False, type=int)
    parser.add_argument('--sample-rate', help='Sample rate in Hz', required=False, type=int)
    parser.add_argument('--file-length-sec', help='Duration of each data file', required=False, type=int)
    parser.add_argument('--data-directory', help='Directory to store csv data from DAQ buffer', required=False)
    parser.add_argument('--debug', help='Show debugging print messages', action='store_true')
    parser.add_argument('--quiet', help='No Console Output', action='store_true')
    parser.add_argument('--verbose', help='Verbose output - may slow process on slower CPUs', action='store_true')
    parser.add_argument('--mode', help='Data output mode', choices=['binary', 'text'], required=False)
    parser.add_argument('-i', '--interactive', help='Set parameters interactively or, use passed values (or default values)', action='store_true')
    parser.add_argument('-s', '--script', help='Run from script (Will not ask for user input)', action='store_true')
    parser.add_argument('-t', '--test', help='Run as test and exit smoothly', action='store_true')
    parser.set_defaults(channels=16, sample_rate=19200, file_length_sec=1.0, data_directory='{}/data_{}'.format(os.getcwd(), datetime.now()), mode='text')
    args = parser.parse_args()
    if args.test:
        args.quiet = True
    time.sleep(0.2)
    os.system('clear')
    
    try:
        #
        # Handle interactive config
        #
        if args.interactive and not args.script:
            os.system('clear')
            print_title(title='Interactive Mode')
            print_pre_prompt(title='Directory to store csv data from DAQ buffer',
                             default=args.data_directory,
                             default_style='path')
            user_input = prompt_user(completer=PathCompleter(), validator=path_validator)
            if user_input != '':
                args.data_directory = os.path.abspath(user_input)
            else:
                if not os.path.exists(args.data_directory):
                    os.mkdir(args.data_directory)
            print_post_prompt(arg='Data Directory',
                              val=args.data_directory,
                              val_style='path')

            # get number of channels
            print_pre_prompt(title='Number of channels or elements on the array to record with (Minimum 2)',
                             default=args.channels,
                             default_style='token')
            user_input = prompt_user(validator=number_validator)
            if user_input != '':
                args.channels = int(user_input)
            if args.channels <= 1:
                args.channels = 2
                print_line('Not enough channels, setting to minimum', l_style='error')
            print_post_prompt(arg='Numer of Channels',
                              val=args.channels,
                              val_style='token')

            # get sample rate
            print_pre_prompt(title='Sample rate in Hz',
                             default=args.sample_rate,
                             default_style='token')
            user_input = prompt_user(validator=number_validator)
            if user_input != '':
                args.sample_rate = int(user_input)
            print_post_prompt(arg='Sample rate in Hz',
                              val=args.sample_rate,
                              val_style='token')

            # get file length
            print_pre_prompt(title='File Length (seconds) Duration of each data file',
                             default=args.file_length_sec,
                             default_style='token')
            user_input = prompt_user(validator=float_validator)
            if user_input != '':
                args.file_length_sec = float(user_input)
            print_post_prompt(arg='File Length (seconds)',
                              val=args.file_length_sec,
                              val_style='token')
        else:
            # make sure the default data_directory exists
            if not os.path.exists(args.data_directory):
                os.mkdir(args.data_directory)
            else:
                args.data_directory = os.path.abspath(args.data_directory)

        # 
        #   Setup 2 directories one for SLAVE data and one for MASTER
        #
        if not os.path.exists('{}/MASTER_DAQ'.format(args.data_directory)):
            os.mkdir('{}/MASTER_DAQ'.format(args.data_directory))
        if not os.path.exists('{}/SLAVE_DAQ'.format(args.data_directory)):
            os.mkdir('{}/SLAVE_DAQ'.format(args.data_directory))

        master_dir = os.path.abspath('{}/MASTER_DAQ'.format(args.data_directory))
        slave_dir  = os.path.abspath('{}/SLAVE_DAQ'.format(args.data_directory))
        #
        #   Start main thread
        #
        main(args=args,
             master_dir=master_dir,
             slave_dir=slave_dir)
    except ULException as e:
        print_line('\n UL Specific Exception Thrown: {}\n'.format(e))

    except KeyboardInterrupt:
        print_line('\n\n\tEnding...\n')
