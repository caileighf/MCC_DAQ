from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter, WordCompleter, ExecutableCompleter
from prompt_toolkit.shortcuts import yes_no_dialog
import os
#
#   For prompt interactive section
#
style = Style.from_dict({
    'error': '#ff0000 italic',
    'title': '#1245A8 bold',
    'path': '#44ff00 underline',
    'exe': '#44ffff underline',
    'token': '#44ff00 italic',
    'info': '#EEEEEE',
    'info_italic': '#EEEEEE italic',
    'subtitle': '#A9A9A9',
})

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

def print_title(title, print_bar=True):
    print_formatted_text(HTML('<title>{}</title>'.format(title)), style=style)
    if print_bar:
        print_formatted_text(HTML('<title>{}</title>'.format('-'*len(title))), style=style)

def print_line(line, l_style='subtitle'):
    print_formatted_text(HTML('<{}>{}</{}>'.format(l_style, line, l_style)), style=style)

def print_lines(lines, l_style='info'):
    for line in lines:
        print_formatted_text(HTML('<{}>{}</{}>'.format(l_style, line, l_style)), style=style)

def print_pre_prompt_options(title, list_options):
    print_formatted_text(HTML('<subtitle>{}</subtitle>'.format(title)), style=style)
    for i in range(len(list_options)):
        print_formatted_text(HTML(' [<b>{}</b>] <subtitle>{}</subtitle>'.format(i+1, list_options[i])), style=style)
    print('\n')

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

def prompt_user(text='> ', completer=None, validator=None):
    if completer is not None:
        if validator == serial_port_validator or validator == path_validator:
            print_line(line='Hit TAB to see options in cwd', l_style='info_italic')
        else:
            print_line(line='Hit TAB to see options', l_style='info_italic')
    return('{}'.format(prompt(text, completer=completer, validator=validator)))

def get_yes_no(title, text):
    result = yes_no_dialog(title=title,
                           text=text).run()
    return(result)