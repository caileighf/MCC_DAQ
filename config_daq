from scripts.prompt_utils import (print_title,
                                  print_line,
                                  print_lines, 
                                  print_pre_prompt,
                                  print_pre_prompt_options,
                                  print_verbose_options, 
                                  print_post_prompt, 
                                  prompt_user, 
                                  path_validator, PathCompleter,
                                  number_validator, float_validator, style,
                                  mode_validator, mode_completer,
                                  trigger_type_validator, trigger_type_completer)
import json
import datetime
import os
import sys

default_config_file = '{}/.default_config.json'.format(os.getcwd())
user_set_config_file = '{}/config.json'.format(os.getcwd())

def main(override):
    os.system('clear')

    if not override and os.path.exists(user_set_config_file):
        # use previous config
        with open(user_set_config_file, 'r') as f:
            user_data = json.load(f)
        user_set_config = user_data
        # open default json file for defaults and options
        with open(default_config_file, 'r') as f:
            data = json.load(f)
    else:
        # open default json file only
        with open(default_config_file, 'r') as f:
            data = json.load(f)
        user_set_config = data['USER_SET_CONFIG'][0]

    print_title('Configure DAQ Parameters:')

    #
    #   MODE
    print_pre_prompt(title='DAQ Mode',
                     default=user_set_config['mode'],
                     default_style='token')
    print_verbose_options('Mode Options', data['MODES'])
    user_input = prompt_user(completer=mode_completer, validator=mode_validator)
    if user_input != '':
        user_set_config['mode'] = user_input

    print_post_prompt(arg='DAQ Mode',
                      val=user_set_config['mode'],
                      val_style='token')

    #
    #   IF Mode is TRIGGERED find out what type of trigger the user wants
    if user_set_config['mode'] == 'TRIGGERED':
        if 'trig_type' not in user_set_config:
            user_set_config['trig_type'] = data['DEFAULT_TRIGGERED'][0]['trig_type'][0] # first opt POS_EDGE
        print_pre_prompt(title='DAQ Mode',
                         default=user_set_config['trig_type'][0],
                         default_style='token')
        print_verbose_options('Trigger Options', data['DEFAULT_TRIGGERED'][0]['trig_type'])
        user_input = prompt_user(completer=trigger_type_completer, validator=trigger_type_validator)
        if user_input != '':
            user_set_config['trig_type'] = user_input

        print_post_prompt(arg='DAQ Mode',
                          val=user_set_config['trig_type'],
                          val_style='token')

    #
    #   DATA DIRECTORY
    print_pre_prompt(title='Directory to store csv data from DAQ buffer',
                     default=user_set_config['data_directory'],
                     default_style='path')
    user_input = prompt_user(completer=PathCompleter(), validator=path_validator)
    if user_input != '':
        user_set_config['data_directory'] = os.path.abspath(user_input)
    else:
        user_set_config['data_directory'] = os.path.abspath(user_set_config['data_directory'])
        if not os.path.exists(user_set_config['data_directory']):
            os.mkdir(user_set_config['data_directory'])
            print(user_set_config['data_directory'])
    print_post_prompt(arg='Data Directory',
                      val=user_set_config['data_directory'],
                      val_style='path')

    #
    #   CHANNEL COUNT
    print_pre_prompt(title='Number of channels or elements on the array to record with',
                     default=user_set_config['channels'],
                     default_style='token')
    user_input = prompt_user(validator=number_validator)
    if user_input != '':
        user_set_config['channels'] = int(user_input)
    if user_set_config['channels'] <= 0:
        user_set_config['channels'] = 1
        print_line('Not enough channels, setting to minimum (1)', l_style='error')
    print_post_prompt(arg='Numer of Channels',
                      val=user_set_config['channels'],
                      val_style='token')

    # 
    #   SAMPLE RATE
    print_pre_prompt(title='Sample rate in Hz',
                     default=user_set_config['sample_rate'],
                     default_style='token')
    user_input = prompt_user(validator=number_validator)
    if user_input != '':
        user_set_config['sample_rate'] = int(user_input)
    print_post_prompt(arg='Sample rate in Hz',
                      val=user_set_config['sample_rate'],
                      val_style='token')

    # 
    #   FILE LENGTH 
    print_pre_prompt(title='File Length (seconds) Duration of each data file',
                     default=user_set_config['file_length_sec'],
                     default_style='token')
    user_input = prompt_user(validator=float_validator)
    if user_input != '':
        user_set_config['file_length_sec'] = float(user_input)
    print_post_prompt(arg='File Length (seconds)',
                      val=user_set_config['file_length_sec'],
                      val_style='token')

    # write to config file
    with open(user_set_config_file, 'w') as f:
        json.dump(user_set_config, f, indent=4, sort_keys=True)

    print_line('<info_italic>DAQ Configuration Saved!</info_italic>\nRun <exe>./start_collect</exe> to start collection using this config')

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        if sys.argv[1] == '--override':
            override = True
    else:
        override = False
    try:
        main(override)
    except KeyboardInterrupt:
        pass
    except KeyError:
        import traceback
        traceback.print_exc()
        print('Config file missing attributes! Run with --override to reset to defaults')
    finally:
        print('\n\tEnding...\n')