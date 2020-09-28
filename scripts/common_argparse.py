import argparse
import datetime
import pathlib

def get_specgram_bounded_args():
    parser = argparse.ArgumentParser(description='', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--postfix', help='Postfix for fig directory', required=False, type=str)
    parser.add_argument('--channel', help='Which channel data should be used', required=False, type=int)
    parser.add_argument('--sample-rate', help='Sample rate in Hz', required=False, type=int)
    parser.add_argument('--nfft', help='NFFT', required=False, type=int)
    parser.add_argument('--file-length-sec', help='Duration of each data file', required=False, type=int)
    parser.add_argument('--data-directory', help='Root directory for the data', required=True)
    parser.add_argument('--start', help='Start time for window of data', required=False, type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S'))
    parser.add_argument('--end', help='End time for window of data', required=False, type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S'))
    parser.add_argument('--debug', help='Show debugging print messages', action='store_true')
    parser.add_argument('--quiet', help='No Console Output', action='store_true')
    parser.add_argument('--verbose', help='Verbose output - may slow process on slower CPUs', action='store_true')
    parser.add_argument('--mode', help='Data output mode', choices=['binary', 'text'], required=False)
    parser.add_argument('--role', nargs='*', help='Prefix to data directory for multiple DAQs Defaults to MASTER/SLAVE', required=False)
    parser.add_argument('-s', '--script', help='Run from script (Will not ask for user input)', action='store_true')
    parser.add_argument('-i', '--interactive', help='Interactive time', action='store_true')
    parser.add_argument('--display', help='Display each plot as they are created -- this will pause execution until the plot is closed', action='store_true')
    parser.add_argument('--pickle', help='By default, figures are NOT pickled (allowing user to look at plots interactively later)', action='store_true')
    parser.add_argument('--mat', help='By default, figures are NOT accompanied by a .mat that includes all the data that went into the figure', action='store_true')
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
            # tstamp is not embedded in dir name so we don't have default start times to pass
            pass

    return(args)


def get_postion_bounded_args():
    parser = argparse.ArgumentParser(description='', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--postfix', help='Postfix for fig directory', required=False, type=str)
    parser.add_argument('--data-directory', help='Root directory for the data', required=True)
    parser.add_argument('--start', help='Start time for window of data', required=False, type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S'))
    parser.add_argument('--end', help='End time for window of data', required=False, type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S'))
    parser.add_argument('--debug', help='Show debugging print messages', action='store_true')
    parser.add_argument('--quiet', help='No Console Output', action='store_true')
    parser.add_argument('--verbose', help='Verbose output - may slow process on slower CPUs', action='store_true')
    parser.add_argument('--mode', help='Data output mode', choices=['binary', 'text'], required=False)
    parser.add_argument('--pos_type', nargs='*', help='Prefix for position sensor log file. Default: [AIS, GPS, IMU]', required=False)
    parser.add_argument('-s', '--script', help='Run from script (Will not ask for user input)', action='store_true')
    parser.add_argument('-i', '--interactive', help='Interactive time', action='store_true')
    parser.add_argument('--use-quat', help='Use the Quaturnion to calculate roll/pitch/yaw (IMU Only) Defaults to using Euler vector', action='store_true')
    parser.add_argument('--display', help='Display each plot as they are created -- this will pause execution until the plot is closed', action='store_true')
    parser.add_argument('--pickle', help='By default, figures are NOT pickled (allowing user to look at plots interactively later)', action='store_true')
    parser.add_argument('--mat', help='By default, figures are NOT accompanied by a .mat that includes all the data that went into the figure', action='store_true')
    parser.set_defaults(postfix='position',
                        start=None,
                        end=None,
                        mode='text',
                        pos_type=['AIS', 'IMU', 'GPS'])
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
            # tstamp is not embedded in dir name so we don't have default start times to pass
            pass

    return(args)