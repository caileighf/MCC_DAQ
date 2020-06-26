#
# Woods Hole Oceanographic Institution
# Author: Caileigh Fitzgerald
# Email:  cfitzgerald@whoi.edu
# Date:   06/20/2020
#
# File: single_DAQ_collect.py
#
from __future__ import print_function
import sys
import time
import os
import argparse
from uldaq import (get_daq_device_inventory, DaqDevice, AInScanFlag, ScanStatus,
                   ScanOption, create_float_buffer, InterfaceType, AiInputMode, ULException)
from async_daq_data_handler import AsyncDAQDataHandler
# Methods for handling DAQ config and setup
from daq_utils import (print_config, 
                       config_daq, 
                       config_daq_options, 
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

def main(args):
    """Single DAQ Collection CONTINUOUS."""
    daq_device     = None
    ai_device      = None
    status         = ScanStatus.IDLE
    interface_type = InterfaceType.USB
    scan_options   = ScanOption.CONTINUOUS
    flags          = AInScanFlag.DEFAULT
    data_dir       = args.data_directory
    low_channel    = 0
    high_channel   = args.channels-1
    rate           = args.sample_rate     # rate (float) 
                                          # A/D sample rate in samples per channel per second.
    samples_per_channel = rate * args.channels * 30 # *30 gives use extra time to read
    file_length_sec = float(args.file_length_sec)
    #
    #   Takes passed args and gathers all connected DAQ devices
    #   .. user selects DAQ from list - return val is passed to context mngr
    #
    try:
        daq_device_params = config_daq_options(interface_type=interface_type, script=args.script)
    except RuntimeError as e:
        print_line(e)
        exit(1)

    # 
    #   Connect to the selected DAQ with the context manager
    #
    with DaqDevice(daq_device_params) as daq_device:
        # configure the ai_device with the daq_device instance
        ai_device, ai_info                 = config_ai_device(daq_device=daq_device)
        # finish configuring the options for the daq_device instance
        input_mode, channel_count, v_range = config_daq(daq_device=daq_device, 
                                                        ai_info=ai_info, 
                                                        channel_range=(low_channel, high_channel))
        os.system('clear')

        # Allocate a buffer to receive the data.
        data = create_float_buffer(channel_count, samples_per_channel)
        # Print config options
        print_config(sample_rate=rate, 
                     file_length=file_length_sec, 
                     data_directory=data_dir, 
                     input_mode=input_mode.name, 
                     channel_range=(low_channel, high_channel), 
                     voltage_range=v_range, 
                     scan_options=scan_options)

        if not args.script:
            try:
                prompt_user(text='\nHit ENTER to continue')
            except (NameError, SyntaxError):
                pass

        # Start the acquisition.
        rate = ai_device.a_in_scan(low_channel, high_channel, input_mode,
                                   v_range, samples_per_channel,
                                   rate, scan_options, flags, data)
        async_writer = AsyncDAQDataHandler(float_buffer=data, 
                                           role='SINGLE', 
                                           ai_device=ai_device, 
                                           channel_count=channel_count, 
                                           data_dir=data_dir,
                                           sample_rate=rate,
                                           scan_options=display_scan_options(scan_options),
                                           v_range=v_range,
                                           input_mode=input_mode,
                                           flags=flags)
        prev_index=0
        try:
            start=time.time()
            print_line('\n | <info>CTRL + C to terminate the process</info>       ')
            print_line(  ' |----------------------------------------------------- ')
            time.sleep(0.1)
            while True:
                try:
                    # Get the status of the background operation
                    status, transfer_status = ai_device.get_scan_status()
                    index = transfer_status.current_index
                    reset_cursor()
                    clear_eol()
                    output_str = create_output_str(transfer_status, rate)
                    # now append channel values
                    for i in range(channel_count):
                        output_str.append('<b>Channel</b> [<b>{}</b>] = {:.6f}'.format(i+low_channel, data[index + i]))
                    print_lines(output_str)
                    print('')

                    #
                    #   Every <file_length_sec> second(s) read from circular buffer,
                    #   .. starting at the previous index up to the current index
                    #   .. then set previous index to current index
                    #
                    if time.time()-start >= file_length_sec:
                        start=time.time()
                        # write data to file
                        async_writer.do_write(start_time=start)

                except (ValueError, NameError, SyntaxError):
                    raise
        except KeyboardInterrupt:
            time.sleep(0.2)
            os.system('clear')
            print_config(sample_rate=rate, 
                         file_length=file_length_sec, 
                         data_directory=data_dir, 
                         input_mode=input_mode.name, 
                         channel_range=(low_channel, high_channel), 
                         voltage_range=v_range, 
                         scan_options=scan_options,
                         print_head_space=False)
            raise(KeyboardInterrupt)

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
    parser.set_defaults(channels=1, sample_rate=38400, file_length_sec=1.0, data_directory=os.getcwd()+'/data', mode='text')
    args = parser.parse_args()
    if args.script:
        args.quiet = True
    time.sleep(0.2)
    os.system('clear')
    
    try:
        #
        # Handle interactive config
        #
        if args.interactive and not args.script:
            os.system('clear')
            print_title(title='Interactive Mode -- Hit Enter to keep the default values')
            print_pre_prompt(title='Directory to store csv data from DAQ buffer',
                             default=args.data_directory,
                             default_style='path')
            user_input = prompt_user(completer=PathCompleter(), validator=path_validator)
            args.data_directory = os.path.abspath(user_input)
            print_post_prompt(arg='Data Directory',
                              val=args.data_directory,
                              val_style='path')

            # get number of channels
            print_pre_prompt(title='Number of channels or elements on the array to record with',
                             default=args.channels,
                             default_style='token')
            user_input = prompt_user(validator=number_validator)
            args.channels = int(user_input)
            print_post_prompt(arg='Numer of Channels',
                              val=args.channels,
                              val_style='token')

            # get sample rate
            print_pre_prompt(title='Sample rate in Hz',
                             default=args.sample_rate,
                             default_style='token')
            user_input = prompt_user(validator=number_validator)
            args.sample_rate = int(user_input)
            print_post_prompt(arg='Sample rate in Hz',
                              val=args.sample_rate,
                              val_style='token')

            # get file length
            print_pre_prompt(title='File Length (seconds) Duration of each data file',
                             default=args.file_length_sec,
                             default_style='token')
            user_input = prompt_user(validator=float_validator)
            args.file_length_sec = float(user_input)
            print_post_prompt(arg='File Length (seconds)',
                              val=args.file_length_sec,
                              val_style='token')
        else:
            # make sure the default data_directory exists
            if not os.path.exists(args.data_directory):
                os.mkdir(os.path.abspath(args.data_directory))
            else:
                args.data_directory = os.path.abspath(args.data_directory)
        #
        #   Start main thread
        #
        main(args)
    except ULException as e:
        print_line('\n\tUL Specific Exception Thrown: ', e)

    except KeyboardInterrupt:
        print_line('\n\n\tEnding...\n')