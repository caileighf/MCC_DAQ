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
from datetime import datetime
from uldaq import (get_daq_device_inventory, DaqDevice, AInScanFlag, ScanStatus,
                   ScanOption, TriggerType, create_float_buffer, InterfaceType, AiInputMode, ULException)
from async_daq_data_handler_triggered import AsyncDAQDataHandler
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

def get_loading_char(mod):
    return('/' if mod%2==0 else '\\')

def start_scan(ai_device, low_channel, high_channel, input_mode,
               v_range, samples_per_channel,
               rate, scan_options, flags, data):
    # Start the acquisition.
    pre_call = datetime.now()
    rate = ai_device.a_in_scan(low_channel, high_channel, input_mode,
                               v_range, samples_per_channel,
                               rate, scan_options, flags, data)
    post_call = datetime.now()
    # average times from pre scan start and post scan start
    start_time_epoch = datetime.fromtimestamp(int(pre_call.timestamp() + post_call.timestamp()) / 2)
    return(start_time_epoch, rate)

def main(args):
    """Single DAQ Collection CONTINUOUS."""
    daq_device     = None
    ai_device      = None
    status         = ScanStatus.IDLE
    interface_type = InterfaceType.USB
    scan_options   = ScanOption.EXTTRIGGER
    trigger_type   = args.trig_type
    flags          = AInScanFlag.DEFAULT
    data_dir       = args.data_directory
    low_channel    = 0
    high_channel   = args.channels-1
    rate           = args.sample_rate     # rate (float) 
                                          # A/D sample rate in samples per channel per second.
    file_length_sec = float(args.file_length_sec)
    samples_per_channel = int(rate * file_length_sec)
    samples_per_file_per_channel = samples_per_channel * args.channels
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
        # get first trigger type (POS_EDGE for USB1608FS-PLUS)
        trigger_types = ai_info.get_trigger_types()
        print(trigger_types, trigger_type)
        # make sure chosen trigger option is available, otherwise use first option
        if trigger_type[1] not in trigger_types:
            trigger_type = ('NO-{}-USED-DEFAULT', trigger_types[0])

        ai_device.set_trigger(trigger_type[1], 0, 0.0, 0.0, 0)
        os.system('clear')

        # Allocate a buffer to receive the data.
        data = create_float_buffer(channel_count, int(samples_per_channel))
        # Print config options
        print_config(sample_rate=rate, 
                     file_length=file_length_sec, 
                     data_directory=data_dir, 
                     input_mode=input_mode.name, 
                     channel_range=(low_channel, high_channel), 
                     voltage_range=v_range, 
                     scan_options=scan_options,
                     trig_mode=trigger_type[0])

        if not args.script:
            try:
                prompt_user(text='\nHit ENTER to continue')
            except (NameError, SyntaxError):
                pass

        # Start the acquisition.
        pre_call = datetime.now()
        ack_rate = ai_device.a_in_scan(low_channel, high_channel, input_mode,
                                   v_range, samples_per_channel,
                                   rate, scan_options, flags, data)
        post_call = datetime.now()
        # average times from pre scan start and post scan start
        start_time_epoch = datetime.fromtimestamp(int(pre_call.timestamp() + post_call.timestamp()) / 2)

        async_writer = AsyncDAQDataHandler(float_buffer=data, 
                                           role='SINGLE', 
                                           ai_device=ai_device, 
                                           channel_count=channel_count, 
                                           data_dir=data_dir,
                                           sample_rate=rate,
                                           scan_options=display_scan_options(scan_options),
                                           v_range=v_range,
                                           input_mode=input_mode,
                                           flags=flags,
                                           file_length=file_length_sec,
                                           trigger_type=trigger_type[0])
        os.system('clear')
        # Print config options
        print_config(sample_rate=rate, 
                     file_length=file_length_sec, 
                     data_directory=data_dir, 
                     input_mode=input_mode.name, 
                     channel_range=(low_channel, high_channel), 
                     voltage_range=v_range, 
                     scan_options=scan_options,
                     trig_mode=trigger_type[0])

        scans_run=0
        heart_beat_count=0
        prev_index=0
        triggered=False
        try:
            start=time.time()
            print_line('\n | <info>CTRL + C to terminate the process</info>       ')
            print_line(  ' |----------------------------------------------------- ')
            time.sleep(0.1)
            while True:
                try:
                    # wait for scan to complete
                    while ai_device.get_scan_status()[0] == ScanStatus.RUNNING:
                        reset_cursor()
                        clear_eol()
                        heart_beat_count += 1
                        if heart_beat_count >= 1000:
                            heart_beat_count = 0
                        print('Scanning... {}'.format(get_loading_char(heart_beat_count)))
                        status, transfer_status = ai_device.get_scan_status()
                        # print(status, transfer_status.current_scan_count, transfer_status.current_index)
                        # check if DAQ was triggered
                        if not triggered and transfer_status.current_scan_count > 0:
                            start_time_epoch = datetime.now()
                            triggered = True

                        # print(triggered, transfer_status.current_index, samples_per_file_per_channel, transfer_status.current_index >= samples_per_file_per_channel)
                        prev_index = transfer_status.current_index

                    reset_cursor()
                    clear_eol()
                    heart_beat_count += 1
                    print('TRIGGERED Writing data from last scan to file... {}'.format(get_loading_char(heart_beat_count)))
                    status, transfer_status = ai_device.get_scan_status()
                    index = transfer_status.current_index
                    # once DAQ has been triggered and enough samples have been written to the buffer,
                    # .. the scan will spot and will need to be called again
                    if triggered and transfer_status.current_scan_count >= rate:
                        # trigger file write (for last scan)
                        async_writer.trigger(start_time_epoch.timestamp())
                        triggered = False

                    # start another scan
                    start_time_epoch, ack_rate = start_scan(ai_device, low_channel, high_channel, input_mode, v_range, 
                                                        samples_per_channel, rate, scan_options, flags, data)
                    scans_run += 1
                    # print channel data to console
                    output_str = create_output_str(transfer_status, rate, scans_run=scans_run, trig_mode=trigger_type[0])
                    # now append channel values
                    for i in range(channel_count):
                        output_str.append('<b>Channel</b> [<b>{}</b>] = <red>{:.6f}</red>'.format(i+low_channel, data[index + i]))
                    print_lines(output_str)
                    print('')

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
                         print_head_space=False,
                         trig_mode=trigger_type[0])
            print_line('   <info><b>Total Scans Run:</b></info> <b><title>{}</title></b>'.format(scans_run))
            raise(KeyboardInterrupt)
        except:
            import traceback
            traceback.print_exc()
            input('Hit Enter to continue...')
        finally:
            async_writer.stop()

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
    parser.add_argument('--trig-type', help='Trigger type', choices=['POS_EDGE', 'NEG_EDGE', 'HIGH', 'LOW'], required=False)
    parser.add_argument('-i', '--interactive', help='Set parameters interactively or, use passed values (or default values)', action='store_true')
    parser.add_argument('-s', '--script', help='Run from script (Will not ask for user input)', action='store_true')
    parser.set_defaults(channels=1, sample_rate=38400, file_length_sec=1.0, data_directory=os.getcwd()+'/data', mode='text', trig_type='POS_EDGE')
    args = parser.parse_args()
    
    # create tuples for trig type enums to use in setting trigger
    trig_types = [
        ('POS_EDGE', TriggerType.POS_EDGE), 
        ('NEG_EDGE', TriggerType.NEG_EDGE), 
        ('HIGH', TriggerType.HIGH), 
        ('LOW', TriggerType.LOW)
        ]
    args.trig_type = [pair for pair in trig_types if pair[0] == args.trig_type][0]

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