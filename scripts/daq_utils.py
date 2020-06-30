from uldaq import (get_daq_device_inventory, DaqDevice, AInScanFlag, ScanStatus,
                   ScanOption, create_float_buffer, InterfaceType, AiInputMode, ULException)
import time
import os
import sys
import prompt_utils
from prompt_utils import (daq_validator, 
                          prompt_user, 
                          print_pre_prompt_options,
                          print_line,
                          available_devices,
                          get_yes_no)
from prompt_toolkit.completion import WordCompleter
#
#   For displaying to stdout
#
def reset_cursor():
    """Reset the cursor in the terminal window."""
    sys.stdout.write('\033[1;1H')

def clear_eol():
    """Clear all characters to the end of the line."""
    sys.stdout.write('\x1b[2K')
#
#   DAQ Helper methods
#
def display_scan_options(bit_mask):
    """Create a displays string for all scan options."""
    # import ipdb; ipdb.set_trace() # BREAKPOINT
    options = []
    if bit_mask == ScanOption.DEFAULTIO:
        options.append(ScanOption.DEFAULTIO.name)
    for option in ScanOption:
        if option & bit_mask:
            options.append(option.name)
    return ', '.join(options)

def print_total_channel_count(num_channels):
    print_line('\nTotal Channels (combined DAQ channel count): <token><b>{}</b></token>'.format(num_channels), l_style='info')

def print_config(sample_rate, file_length, data_directory, input_mode, channel_range, voltage_range, scan_options, role=None, print_head_space=True, mode='Text',**kwargs):
    if print_head_space:
    	print('{}'.format('\n'*(channel_range[1]+10)))
    else:
    	print('')
    print_line(' |----------------------------------------------------- ')
    if role is None:
        print_line(' | <info><b>DAQ Configuration:</b></info>')
    else:
        print_line(' | <info><b>DAQ Configuration for <title>{}</title> device</b></info>'.format(role))
    print_line(' |----------------------------------------------------- ')
    print_line(' | Sample Rate (Hz)     : %ld        '%sample_rate)
    print_line(' | File Length (seconds): %d         '%file_length)
    print_line(' | Data Directory       : %s         '%data_directory)
    print_line(' | Mode {Binary | Text} : %s         '%mode)
    print_line(' | Input Mode           : %s         '%input_mode)
    print_line(' | Scan Options         : %s         '%display_scan_options(scan_options))
    print_line(' | Voltage Range        : %s         '%voltage_range)
    print_line(' | Low Channel          : %d         '%(channel_range[0]))
    print_line(' | High Channel         : %d         '%(channel_range[1]))
    print_line(' |----------------------------------------------------- ')

def get_daq_choice(role):
    device_completer = WordCompleter(prompt_utils.available_devices)
    descriptor_index = prompt_user(text='Select {} Device > '.format(role), 
                                   completer=device_completer, 
                                   validator=daq_validator)
    descriptor_index = int(prompt_utils.available_devices.index(descriptor_index))
    # import ipdb; ipdb.set_trace() # BREAKPOINT
    return(descriptor_index)

def confirm_daq_choice(device_params, current_role):
    # Flash device LED so user can make sure the device is the one they want
    with DaqDevice(device_params) as daq_device:
        # start flashing. 0=flash until flash_led() is called with an non-zero value
        daq_device.flash_led(0)
        title = 'Confirm {} DAQ Device Selection'.format(current_role)
        is_correct_device = get_yes_no(title=title, text='The LED of the selected device is flashing. Is it the correct one?')
        # pass 1 to get it to stop after 1 one flash
        daq_device.flash_led(1)
        time.sleep(0.2)
        return(is_correct_device)

def update_available_devices(devices, descriptor_index):
    # now remove selected device from options list
    devices.remove(devices[descriptor_index])
    prompt_utils.available_devices = ['{} ({})'.format(d.product_name, d.unique_id) for d in devices]

def config_daq_options_master_slave(interface_type, script=False, master_id=None, slave_id=None):
    # Get descriptors for all of the available DAQ devices.
    # import ipdb; ipdb.set_trace() # BREAKPOINT
    devices = list(get_daq_device_inventory(interface_type))
    number_of_devices = len(devices)
    if number_of_devices == 0:
        raise RuntimeError('Error: No DAQ devices found')

    selected_devices = []
    if script and master_id != None and slave_id != None:
        master = None
        slave  = None
        for device in devices:
            if device.unique_id == master_id:
                master = device
            elif device.unique_id == slave_id:
                slave = device
        if master == None or slave == None:
            print_line('Could not find know {} ID'.format('MASTER' if master == None else 'SLAVE'))
            # call method again without script arg
            selected_devices = config_daq_options_master_slave(interface_type=interface_type)
        else:
            selected_devices.append(slave)
            selected_devices.append(master)
    else:
        prompt_utils.available_devices = ['{} ({})'.format(d.product_name, d.unique_id) for d in devices]
        print_pre_prompt_options(title='Found {} DAQ device(s):'.format(number_of_devices), 
                                 list_options=prompt_utils.available_devices)

        # SLAVE DAQ first
        descriptor_index = get_daq_choice(role='SLAVE')
        while not confirm_daq_choice(device_params=devices[descriptor_index],
                                     current_role='SLAVE'):
            descriptor_index = get_daq_choice(role='SLAVE')
        selected_devices.append(devices[descriptor_index])
        update_available_devices(devices, descriptor_index)

        # MASTER DAQ second
        descriptor_index = get_daq_choice(role='MASTER')
        while not confirm_daq_choice(device_params=devices[descriptor_index],
                                     current_role='MASTER'):
            descriptor_index = get_daq_choice(role='MASTER')
        selected_devices.append(devices[descriptor_index])

    return(selected_devices)

def config_daq_options(interface_type, script=False):
    # Get descriptors for all of the available DAQ devices.
    # import ipdb; ipdb.set_trace() # BREAKPOINT
    devices = list(get_daq_device_inventory(interface_type))
    number_of_devices = len(devices)
    if number_of_devices == 0:
        raise RuntimeError('Error: No DAQ devices found')

    if script:
        descriptor_index = 0
    else:
        prompt_utils.available_devices = ['{} ({})'.format(d.product_name, d.unique_id) for d in devices]
        print_pre_prompt_options(title='Found {} DAQ device(s):'.format(number_of_devices), 
                                 list_options=prompt_utils.available_devices)
    
        device_completer = WordCompleter(prompt_utils.available_devices)
        descriptor_index = prompt_user(completer=device_completer, validator=daq_validator)
        descriptor_index = int(prompt_utils.available_devices.index(descriptor_index))

    return(devices[descriptor_index])

def config_ai_device(daq_device):
    # Get the AiDevice object and verify that it is valid.
    ai_device = daq_device.get_ai_device()
    if ai_device is None:
        raise RuntimeError('Error: The DAQ device does not support analog '
                           'input')

    # Verify the specified device supports hardware pacing for analog input.
    ai_info = ai_device.get_info()
    if not ai_info.has_pacer():
        raise RuntimeError('\nError: The specified DAQ device does not '
                           'support hardware paced analog input')
    return(ai_device, ai_info)

def config_daq(daq_device, ai_info, channel_range):
    low_channel  = channel_range[0]
    high_channel = channel_range[1]
    # Establish a connection to the DAQ device.
    descriptor = daq_device.get_descriptor()

    # The default input mode is SINGLE_ENDED.
    input_mode = AiInputMode.SINGLE_ENDED
    # If SINGLE_ENDED input mode is not supported, set to DIFFERENTIAL.
    if ai_info.get_num_chans_by_mode(AiInputMode.SINGLE_ENDED) <= 0:
        input_mode = AiInputMode.DIFFERENTIAL

    # Get the number of channels and validate the high channel number.
    number_of_channels = ai_info.get_num_chans_by_mode(input_mode)
    if high_channel >= number_of_channels:
        high_channel = number_of_channels - 1
    channel_count = high_channel - low_channel + 1

    # range index selects the voltage gain
    # https://www.mccdaq.com/PDFs/Manuals/UL-Linux/python/api.html?highlight=a_in_scan#uldaq.Range
    range_index    = 0
    # Get a list of supported ranges and validate the range index.
    ranges = ai_info.get_ranges(input_mode)
    if range_index >= len(ranges):
        range_index = len(ranges) - 1

    return(input_mode, channel_count, ranges[range_index])

def create_output_str(transfer_status, rate, role=None):
    # Build output string
    output_str = []
    if role is None:
        output_str.append('\n')
    else:
        output_str.append('Data from <title>{}</title> Device'.format(role))
    output_str.append('<b>Actual scan rate  =</b> {:.3f} Hz'.format(rate))
    output_str.append('<b>CurrentTotalCount =</b> {}'.format(transfer_status.current_total_count))
    output_str.append('<b>CurrentScanCount  =</b> {}'.format(transfer_status.current_scan_count))
    output_str.append('<b>CurrentIndex      =</b> {}'.format(transfer_status.current_index))
    output_str.append('\n')
    output_str.append('<b>Channel   | Raw Voltage</b>')
    output_str.append('<b>------------------------</b>')
    return(output_str)