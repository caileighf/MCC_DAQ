from uldaq import (get_daq_device_inventory, DaqDevice, AInScanFlag, ScanStatus,
                   ScanOption, create_float_buffer, InterfaceType, AiInputMode, ULException)
import time
import os

#
#   DAQ Helper methods
#
def display_scan_options(bit_mask):
    """Create a displays string for all scan options."""
    options = []
    if bit_mask == ScanOption.DEFAULTIO:
        options.append(ScanOption.DEFAULTIO.name)
    for option in ScanOption:
        if option & bit_mask:
            options.append(option.name)
    return ', '.join(options)

def print_config(sample_rate, file_length, data_directory, input_mode, channel_range, voltage_range, scan_options, print_head_space=True, mode='Text',**kwargs):
    if print_head_space:
    	print('{}'.format('\n'*(channel_range[1]+6)))
    else:
    	print('')
    print(' |----------------------------------------------------- ')
    print(' | DAQ Configuration:                                   ')
    print(' |----------------------------------------------------- ')
    print(' | Sample Rate (Hz)     : %ld        '%sample_rate)
    print(' | File Length (seconds): %d         '%file_length)
    print(' | Data Directory       : %s         '%data_directory)
    print(' | Mode {Binary | Text} : %s         '%mode)
    print(' | Input Mode           : %s         '%input_mode)
    print(' | Scan Options         : %s         '%display_scan_options(scan_options))
    print(' | Voltage Range        : %s         '%voltage_range)
    print(' | Low Channel          : %d         '%(channel_range[0]))
    print(' | High Channel         : %d         '%(channel_range[1]))
    print(' |----------------------------------------------------- ')

def config_daq_options(interface_type, script=False):
    # Get descriptors for all of the available DAQ devices.
    devices = get_daq_device_inventory(interface_type)
    number_of_devices = len(devices)
    if number_of_devices == 0:
        raise RuntimeError('Error: No DAQ devices found')

    print('Found', number_of_devices, 'DAQ device(s):')
    for i in range(number_of_devices):
        print('  [', i, '] ', devices[i].product_name, ' (',
              devices[i].unique_id, ')', sep='')

    if script:
    	descriptor_index = 0
    else:
	    descriptor_index = input('\nPlease select a DAQ device, enter a number'
	                             + ' between 0 and '
	                             + str(number_of_devices - 1) + ': ')
    descriptor_index = int(descriptor_index)
    if descriptor_index not in range(number_of_devices):
        raise RuntimeError('Error: Invalid descriptor index')

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
    # print('\nConnecting to', descriptor.dev_string, '- please wait...')
    # For Ethernet devices using a connection_code other than the default
    # value of zero, change the line below to enter the desired code.
    # daq_device.connect(connection_code=0)

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