from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter, WordCompleter, ExecutableCompleter
from prompt_toolkit.shortcuts import yes_no_dialog
import os
import re
import datetime
#                  example: "1:2:5" HR:MIN:SEC
time_pattern_unpadded = re.compile("^([0-9]):([0-9]+):([0-9]+)$")
#                  example: "01:02:05" HR:MIN:SEC
time_pattern = re.compile("^([0-2])([0-9]):([0-5]+)([0-9]):([0-5]+)([0-9])$")

#                  example: "2020-1-1" YEAR-MONTH-DAY
date_pattern_unpadded = re.compile("^([1-2])([0-9])([0-9])([0-9])-([1-9])-([1-9])$")
#                  example: "2020-01-01" YEAR-MONTH-DAY
date_pattern = re.compile("^([1-2])([0-9])([0-9])([0-9])-([0-1]+)([0-9])-([0-1]+)([0-9])$")
#
#   For prompt interactive section
#
style = Style.from_dict({
    'error': '#ff0000 italic',
    'title': '#1245A8 bold',
    'time': '#0B6623 bold',
    'path': '#44ff00 underline',
    'exe': '#44ffff underline',
    'token': '#44ff00 italic',
    'info': '#EEEEEE',
    'red': '#FF0000',
    'info_italic': '#EEEEEE italic',
    'subtitle': '#A9A9A9',
})

# create possible times
times = ['00:00:00'] # default time val
for i in range(10):
    times.append(':0{}'.format(i))
    times.append(':1{}'.format(i))
    times.append(':2{}'.format(i))
    times.append(':3{}'.format(i))
    times.append(':4{}'.format(i))
    times.append(':5{}'.format(i))

    if i <= 9:
        times.append('0{}'.format(i))
        times.append('1{}'.format(i))
    if i <= 4:
        times.append('2{}'.format(i))

time_completer = WordCompleter(sorted(times))

# create possible dates
dates = ['2020-01-01'] # default date val
for i in range(10):
    #
    #   TODO: Handle 28/30/31 day long months?
    #
    # years
    dates.append('198{}-'.format(i))
    dates.append('199{}-'.format(i))
    dates.append('200{}-'.format(i))
    dates.append('201{}-'.format(i))
    dates.append('202{}-'.format(i))
    # months
    if i <= 2:
        dates.append('-1{}'.format(i))
    dates.append('-0{}'.format(i))
    # days
    if i <= 3:
        dates.append('-{}0'.format(i))
    dates.append('-0{}'.format(i))

date_completer = WordCompleter(sorted(dates, reverse=True))

available_devices = []
def is_valid_daq_choice(text):
    global available_devices
    if text in available_devices:
        return(True)
    else:
        return(False)
daq_validator = Validator.from_callable(is_valid_daq_choice,
                                        error_message='Must select one of the available devices',
                                        move_cursor_to_end=True)

valid_trigger_types = ['POS_EDGE', 'NEG_EDGE', 'HIGH', 'LOW']
trigger_type_completer = WordCompleter(valid_trigger_types)
def is_valid_trigger_type(text):
    if text in valid_trigger_types or text == '':
        return(True)
    else:
        return(False)
trigger_type_validator = Validator.from_callable(is_valid_trigger_type,
                                        error_message='Available trigger type are: POS_EDGE, NEG_EDGE, HIGH, LOW',
                                        move_cursor_to_end=True)

valid_modes = ['CONTINUOUS', 'TRIGGERED']
mode_completer = WordCompleter(valid_modes)
def is_valid_mode(text):
    if text in valid_modes or text == '':
        return(True)
    else:
        return(False)
mode_validator = Validator.from_callable(is_valid_mode,
                                        error_message='Available modes are: CONTINUOUS and TRIGGERED',
                                        move_cursor_to_end=True)

def is_number(text):
    if text == '':
        return(True)
    return(text.isdigit())
number_validator = Validator.from_callable(is_number,
                                           error_message='This input contains non-numeric characters',
                                           move_cursor_to_end=True)
def is_float(text):
    if text == '':
        return(True)
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
    if text == '':
        return(True)
    return(os.path.exists(text))
path_validator = Validator.from_callable(is_valid_path,
                                        error_message='Invalid Path',
                                        move_cursor_to_end=True)

def is_valid_serial_port(text):
    if text == '':
        return(True)
    return(os.path.exists(text) and '/dev/' in text)
serial_port_validator = Validator.from_callable(is_valid_serial_port,
                                                error_message='Invalid Serial Port',
                                                move_cursor_to_end=True)

def is_exe(text):
    if text == '':
        return(True)
    return(os.path.isfile(text) and os.access(text, os.X_OK))
exe_validator = Validator.from_callable(is_exe,
                                        error_message='File is not executable',
                                        move_cursor_to_end=True)

def is_valid_time(text):
    if text == '':
        return(True)
    elif time_pattern.match(text) or\
         time_pattern_unpadded.match(text):
        try:
            _h, _m, _s = [int(x) for x in text.split(':')]
            _ = datetime.time(_h, _m, _s)
        except:
            return(False)
        else:
            return(True)
    else:
        return(False)
time_validator = Validator.from_callable(is_valid_time,
                                        error_message='Invalid Time. Format: 00:00:00 (Hour, Min, Second)',
                                        move_cursor_to_end=True)

def is_valid_date(text):
    if text == '':
        return(True)
    elif date_pattern.match(text) or\
         date_pattern_unpadded.match(text):
        try:
            _y, _m, _d = [int(x) for x in text.split('-')]
            _ = datetime.date(_y, _m, _d)
        except:
            return(False)
        else:
            return(True)
    else:
        return(False)
date_validator = Validator.from_callable(is_valid_date,
                                        error_message='Invalid Date. Format: 2020-01-01 (Year, Month, Day)',
                                        move_cursor_to_end=True)


def print_title(title, print_bar=True):
    print_formatted_text(HTML('<title>{}</title>'.format(title)), style=style)
    if print_bar:
        print_formatted_text(HTML('<title>{}</title>'.format('-'*len(title))), style=style)

def print_line(line, l_style='subtitle', end='\n'):
    print_formatted_text(HTML('<{}>{}</{}>'.format(l_style, line, l_style)), style=style, end=end)

def print_lines(lines, l_style='info', end='\n'):
    for line in lines:
        print_line(line=line, l_style=l_style, end=end)

def print_pre_prompt_options(title, list_options):
    print_formatted_text(HTML('<subtitle>{}</subtitle>'.format(title)), style=style)
    for i in range(len(list_options)):
        print_formatted_text(HTML(' [<b>{}</b>] <subtitle>{}</subtitle>'.format(i+1, list_options[i])), style=style)
    print('\n')

def print_verbose_options(title, list_options):
    print_formatted_text(HTML('<subtitle>{}</subtitle>'.format(title)), style=style)
    for i in range(len(list_options)):
        print_formatted_text(HTML(' [<b>{}</b>] <subtitle>{}</subtitle> '.format(i+1, list_options[i][0])), style=style, end='')
        print_formatted_text(HTML('-- <info_italic>{}</info_italic>'.format(list_options[i][1])), style=style)
    print('\n')

def print_pre_prompt(title, default, default_style):
    print_formatted_text(HTML('<subtitle>{}</subtitle>'.format(title)), style=style)
    if default == None:
        print_formatted_text(HTML('<subtitle>Default: <{}>{}</{}></subtitle>'.format(default_style, 
                                                                                     default, 
                                                                                     default_style)), style=style)
    else:
        print_formatted_text(HTML('<subtitle>Default: <{}>{}</{}></subtitle> <info_italic>Hit Enter to keep default</info_italic>'.format(default_style, 
                                                                                     default, 
                                                                                     default_style)), style=style)

def print_post_prompt(arg, val, val_style):
    print_formatted_text(HTML('<subtitle><b>{}</b>: <{}>{}</{}></subtitle>\n'.format(arg,
                                                                                     val_style,
                                                                                     val,
                                                                                     val_style)), style=style)

def prompt_user(text='> ', completer=None, validator=None):
    if completer != None:
        print_title('(TAB Complete Available)', print_bar=False)
    return('{}'.format(prompt(text, completer=completer, validator=validator, complete_while_typing=True)))

def get_yes_no(text, title=None):
    result = yes_no_dialog(title=title,
                           text=text).run()
    return(result)