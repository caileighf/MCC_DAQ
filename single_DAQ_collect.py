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
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter

from uldaq import (get_daq_device_inventory, DaqDevice, AInScanFlag, ScanStatus,
                   ScanOption, create_float_buffer, InterfaceType, AiInputMode, ULException)
from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator

from daq_utils import print_config, config_daq, config_daq_options, config_ai_device

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
    samples_per_channel = rate * args.channels * 30
    file_length_sec = float(args.file_length_sec)
    #
    #   Takes passed args and gathers all connected DAQ devices
    #   .. user selects DAQ from list - return val is passed to context mngr
    #
    try:
        daq_device_params = config_daq_options(interface_type=interface_type, script=args.script)
    except RuntimeError as e:
        print(e)
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

        # Allocate a buffer to receive the data.
        data = create_float_buffer(channel_count, samples_per_channel)
        # Print config options
        os.system('clear')
        print_config(sample_rate=rate, 
                     file_length=file_length_sec, 
                     data_directory=data_dir, 
                     input_mode=input_mode.name, 
                     channel_range=(low_channel, high_channel), 
                     voltage_range=v_range, 
                     scan_options=scan_options)

        if not args.script:
            try:
                input('\nHit ENTER to continue\n')
            except (NameError, SyntaxError):
                pass

        # Start the acquisition.
        rate = ai_device.a_in_scan(low_channel, high_channel, input_mode,
                                   v_range, samples_per_channel,
                                   rate, scan_options, flags, data)
        prev_index=0
        try:
            start=time.time()
            print(' | CTRL + C to terminate the process                    ')
            print(' |----------------------------------------------------- ')
            while True:
                try:
                    # Get the status of the background operation
                    status, transfer_status = ai_device.get_scan_status()
                    index = transfer_status.current_index
                    reset_cursor()
                    clear_eol()
                    # Build output string
                    output_str = []
                    output_str.append('\n')
                    output_str.append('Actual scan rate  = {:.3f} Hz\n'.format(rate))
                    output_str.append('CurrentTotalCount = {}\n'.format(transfer_status.current_total_count))
                    output_str.append('CurrentScanCount  = {}\n'.format(transfer_status.current_scan_count))
                    output_str.append('CurrentIndex      = {}\n'.format(transfer_status.current_index))
                    output_str.append('\n')

                    for i in range(channel_count):
                        output_str.append('Channel [{}] = {:.6f}\n'.format(i+low_channel, data[index + i]))
                    output_str.append('\n')
                    print(*output_str)

                    if time.time()-start >= file_length_sec:
                        start=time.time()
                        # write data to file
                        with open('{}/{:.6f}.txt'.format(data_dir, start), 'w') as f:
                            i=1
                            # check if buffer has wrapped
                            if prev_index > index:
                                # start at prev_index and read to the end of buffer
                                for val in data[prev_index:len(data)]:
                                    f.write('{}'.format(val))
                                    if i%channel_count == 0 and i!=0:
                                        f.write('\n')
                                    else:
                                        f.write(',')
                                    i+=1
                                # now reset prev_index to 0
                                # ..so we start reading from the begining of the buffer
                                # ..in the next loop
                                prev_index=0

                            # if buffer has not wrapped,
                            # ..read from the prev_index to the current_index
                            for val in data[prev_index:index]:
                                f.write('{}'.format(val))
                                if i%channel_count == 0 and i!=0:
                                    f.write('\n')
                                else:
                                    f.write(',')
                                i+=1
                            prev_index=index

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

def reset_cursor():
    """Reset the cursor in the terminal window."""
    sys.stdout.write('\033[1;1H')

def clear_eol():
    """Clear all characters to the end of the line."""
    sys.stdout.write('\x1b[2K')

#
#   For prompt interactive section
#
style = Style.from_dict({
    'error': '#ff0000 italic',
    'title': '#1245A8 bold',
    'path': '#44ff00 underline',
    'token': '#44ff00 italic',
    'subtitle': '#A9A9A9',
})

def is_number(text):
    return(text.isdigit())
number_validator = Validator.from_callable(is_number,
                                           error_message='This input contains non-numeric characters',
                                           move_cursor_to_end=True)
def is_float(text):
    try:
        float(text)
    except ValueError:
        return(False)
    else:
        return(True)
float_validator = Validator.from_callable(is_float,
                                          error_message='This input is not a float or an int',
                                          move_cursor_to_end=True)
def is_valid_path(text):
    return(os.path.exists(text))
path_validator = Validator.from_callable(is_valid_path,
                                        error_message='Invalid Path',
                                        move_cursor_to_end=True)

def print_title(title, print_bar=True):
    print_formatted_text(HTML('<title>{}</title>'.format(title)), style=style)
    if print_bar:
        print_formatted_text(HTML('<title>{}</title>'.format('-'*len(title))), style=style)

def print_pre_prompt(title, default, default_style):
    print_formatted_text(HTML('<subtitle>{}</subtitle>'.format(title)), style=style)
    print_formatted_text(HTML('<subtitle>Default: <{}>{}</{}></subtitle>'.format(default_style, 
                                                                                 default, 
                                                                                 default_style)), style=style)

def print_post_prompt(arg, val, val_style):
    print_formatted_text(HTML('<subtitle>{}: <{}>{}</{}></subtitle>'.format(arg,
                                                                            val_style,
                                                                            val,
                                                                            val_style)), style=style)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--channels', help='Number of channels or elements on the array to record with', required=False, type=int)
    parser.add_argument('--sample-rate', help='Sample rate in Hz', required=False, type=int)
    parser.add_argument('--file-length-sec', help='Duration of each data file', required=False, type=int)
    parser.add_argument('--known-transmitter-freq', help='If there is a pinger with a know frequency (in Hz)', required=False, type=int)
    parser.add_argument('--data-directory', help='Directory to store csv data from DAQ buffer', required=False)
    parser.add_argument('--display', help='Display the tetraspectragram for each file in the data directory', action='store_true')
    parser.add_argument('--debug', help='Show debugging print messsages', action='store_true')
    parser.add_argument('--verbose', help='Verbose output - may slow process on slower CPUs', action='store_true')
    parser.add_argument('--mode', help='Data output mode', choices=['binary', 'text'], required=False)
    parser.add_argument('-i', '--interactive', help='Set parameters interactively or, use passed values (or default values)', action='store_true')
    parser.add_argument('-s', '--script', help='Run from script (Do not ask for user input)', action='store_true')
    parser.set_defaults(channels=1, sample_rate=38400, file_length_sec=1.0, data_directory=os.getcwd()+'/data', mode='text')
    args = parser.parse_args()
    os.system('clear')
    #
    # Handle interactive config
    #
    try:
        if args.interactive and not args.script:
            os.system('clear')
            print_title(title='Interactive Mode -- Hit Enter to keep the default values')
            # print_formatted_text(HTML('<title>Interactive Mode -- Hit Enter to keep the default values</title>'), style=style)
            # print_formatted_text(HTML('<title>--------------------------------------------------------</title>'), style=style)
            # get data dir
            print_pre_prompt(title='Directory to store csv data from DAQ buffer',
                             default=args.data_directory,
                             default_style='path')
            user_input = '{}'.format(prompt('> ', completer=PathCompleter(), validator=path_validator))
            args.data_directory = os.path.abspath(user_input)
            print_post_prompt(arg='Data Directory',
                              val=args.data_directory,
                              val_style='path')

            # get sample rate
            print_pre_prompt(title='Sample rate in Hz',
                             default=args.sample_rate,
                             default_style='token')
            user_input = '{}'.format(prompt('> ', validator=number_validator))
            args.sample_rate = int(user_input)
            print_post_prompt(arg='Sample rate in Hz',
                              val=args.sample_rate,
                              val_style='token')

            # get file length
            print_pre_prompt(title='File Length (seconds) Duration of each data file',
                             default=args.file_length_sec,
                             default_style='token')
            user_input = '{}'.format(prompt('> ', validator=float_validator))
            args.file_length_sec = float(user_input)
            print_post_prompt(arg='File Length (seconds)',
                              val=args.file_length_sec,
                              val_style='token')
        main(args)
    except ULException as e:
        print('\n\tUL Specific Exception Thrown: ', e)  # Display any error messages

    except KeyboardInterrupt:
        print('\n\n\tEnding...\n')