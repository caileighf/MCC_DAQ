import argparse
import pathlib
import glob
import os
import sys
import time
from datetime import datetime
from prompt_toolkit.shortcuts import ProgressBar
# Methods for interactive prompt when user chooses interactive mode at runtime
from prompt_utils import (print_title,
                          print_line,
                          print_lines, 
                          print_pre_prompt, 
                          print_post_prompt, 
                          prompt_user, 
                          path_validator, PathCompleter,
                          number_validator, float_validator, style)

def get_root_data_dir():
    pass

def get_time_window():
    # prompt user for times
    pass

def extract_data_from(source, channel, file_length_sec, start_epoch, end_epoch):
    start = datetime.fromtimestamp(start_epoch)
    end   = datetime.fromtimestamp(end_epoch)

def main(args):
    extract_data_from()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--channel', help='Which channel data should be used', required=False, type=int)
    parser.add_argument('--file-length-sec', help='Duration of each data file', required=False, type=int)
    parser.add_argument('--data-directory', help='Root directory for the data', required=True)
    parser.add_argument('--start', help='Start time for window of data', required=False, type=float)
    parser.add_argument('--end', help='End time for window of data', required=False, type=float)
    parser.add_argument('--debug', help='Show debugging print messages', action='store_true')
    parser.add_argument('--quiet', help='No Console Output', action='store_true')
    parser.add_argument('--verbose', help='Verbose output - may slow process on slower CPUs', action='store_true')
    parser.add_argument('--mode', help='Data output mode', choices=['binary', 'text'], required=False)
    parser.add_argument('--role', nargs='*', help='Prefix to data directory for multiple DAQs Defaults to MASTER/SLAVE', required=False)
    parser.add_argument('-s', '--script', help='Run from script (Will not ask for user input)', action='store_true')
    parser.set_defaults(channel=0, 
                        file_length_sec=1.0,
                        start=None,
                        end=None,
                        mode='text',
                        role=['MASTER', 'SLAVE'])
    args = parser.parse_args()
    try:
        main(args)
    except KeyboardInterrupt:
        print('\n\n\tEnding...\n')
        exit()