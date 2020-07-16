from prompt_toolkit.shortcuts import button_dialog
# Methods for interactive prompt when user chooses interactive mode at runtime
from prompt_utils import (print_title,
                          print_line,
                          print_lines, 
                          print_pre_prompt, 
                          print_post_prompt, 
                          prompt_user, 
                          PathCompleter,
                          path_validator, 
                          number_validator, 
                          float_validator,
                          time_validator,
                          time_completer,
                          date_validator,
                          date_completer,
                          style,
                          get_yes_no)
import argparse
import os
import time
import datetime

def get_available_methods(as_dict=False):
    methods = [
        (get_date, 'Date input'),
        (get_time, 'Time input'),
        (get_window_of_time, 'Date/time window input'),
        (get_path, 'Path input'),
        (get_int, 'Integer input'),
        (get_float, 'Float input'),
    ]
    if as_dict:
        methods = [(x[1], x[0]) for x in methods]
        methods = dict(methods)
    
    return(methods)

def get_blank_param():
    param = {
        'title': None,
        'arg_name': None,
        'completer': None,
        'validator': None,
        'default': None,
        'default_style': None,
        'method': None,
    }
    return(param)

def mask_null_kwargs(kwargs):
    _kwargs = {}
    for key, val in kwargs.items():
        if val != None and key != 'method':
            _kwargs[key] = val
    return(_kwargs)

def interactive_params(params):
    results = []
    for param in params:
        kwargs = mask_null_kwargs(param)
        results.append((param['arg_name'], param['method'](**kwargs)))
    return(results)

def handle_null(user_input, error, completer, validator, default):
    # user must enter value if no default available
    while user_input == '' and default == None:
        print_line(line=error, l_style='error')
        user_input = prompt_user(completer=completer, validator=validator)

    # if default available and user doesn't provide a new val,
    if user_input == '':
        user_input = default

    return(user_input)

def _get_window_of_time(start_time=None, start_date=None, stop_time=None, stop_date=None):
    #
    #   HANDLE START
    start_date = get_date(title='Please enter a start date',
                          arg_name='Start date',
                          default=start_date)
    start_time = get_time(title='Please enter a start time',
                          arg_name='Start time',
                          default=start_time)
    #
    #   HANDLE STOP
    if stop_date != None:
        stop_date = get_date(title='Please enter a stop date',
                             arg_name='Stop date',
                             default=stop_date)
    else:
        stop_date = get_date(title='Please enter a stop date',
                             arg_name='Stop date',
                             default=start_date)

    if stop_time != None:
        stop_time = get_time(title='Please enter a stop time',
                             arg_name='Stop time',
                             default=stop_time)
    else:
        stop_time = get_time(title='Please enter a stop time',
                             arg_name='Stop time',
                             default=start_time)

    # convert to datetime obj
    start = datetime.datetime.combine(start_date, start_time)
    stop = datetime.datetime.combine(stop_date, stop_time)
    return(start, stop)

def get_window_of_time(start_datetime=None, start_date=None, stop_datetime=None, stop_date=None):
    #
    #   HANDLE START
    if start_datetime != None:
        start_date = start_datetime.date()
        start_time = start_datetime.time()
    elif start_date != None:
        start_date = start_date
        start_time = None

    #
    #   HANDLE STOP
    if stop_datetime != None:
        stop_date = stop_datetime.date()
        stop_time = stop_datetime.time()
    elif stop_date != None:
        stop_date = stop_date
        stop_time = None

    start, stop = _get_window_of_time(start_time=start_time,
                                      start_date=start_date,
                                      stop_time=stop_time,
                                      stop_date=stop_date)

    # check if stop happens after start
    while start > stop:
        print_line('Stop time happens prior to start time... Try again', l_style='error')
        if start.date() > stop.date():
            # potentially an issue with passed start/stop
            # call again but don't pass old values
            start, stop = _get_window_of_time()
        else:
            start, stop = _get_window_of_time(start_time=start_time,
                                              start_date=start_date,
                                              stop_time=stop_time,
                                              stop_date=stop_date)

    return(start, stop)

def get_path(title='Please enter a path',
             arg_name='Path',
             completer=PathCompleter(), 
             validator=path_validator, 
             default=None, 
             default_style='path'):
    print_pre_prompt(title=title,
                     default=default,
                     default_style=default_style) 
    user_input = handle_null(user_input=prompt_user(completer=completer, validator=validator), 
                             error='No Default Path. Try again', 
                             completer=completer, 
                             validator=validator, 
                             default=default)

    path = os.path.abspath(user_input)
    print_post_prompt(arg=arg_name,
                      val=path,
                      val_style=default_style) 
    return(path)

def get_int(title='Please enter an integer',
            arg_name='Integer',
            completer=None, 
            validator=number_validator, 
            default=None, 
            default_style='token'):
    print_pre_prompt(title=title,
                     default=default,
                     default_style=default_style) 
    user_input = handle_null(user_input=prompt_user(completer=completer, validator=validator), 
                             error='No Default Value. Try again', 
                             completer=completer, 
                             validator=validator, 
                             default=default)

    int_val = int(user_input)
    print_post_prompt(arg=arg_name,
                      val=int_val,
                      val_style=default_style) 
    return(int_val)

def get_float(title='Please enter a floating point number',
              arg_name='Floating point number',
              completer=None, 
              validator=float_validator, 
              default=None, 
              default_style='token'):
    print_pre_prompt(title=title,
                     default=default,
                     default_style=default_style) 
    user_input = handle_null(user_input=prompt_user(completer=completer, validator=validator), 
                             error='No Default Value. Try again', 
                             completer=completer, 
                             validator=validator, 
                             default=default)

    float_val = float(user_input)
    print_post_prompt(arg=arg_name,
                      val=float_val,
                      val_style=default_style) 
    return(float_val)

def get_time(title='Please enter a time',
             arg_name='Time',
             completer=time_completer,
             validator=time_validator, 
             default=None, 
             default_style='time',
             tzinfo=None):
    # format default
    if isinstance(default, datetime.time):
        default = default.isoformat()
    print_pre_prompt(title='{}\nISO Format: <b>00:00:00</b> (Hour (24HR), Min, Second)'.format(title),
                     default=default,
                     default_style=default_style) 
    user_input = handle_null(user_input=prompt_user(completer=completer, validator=validator), 
                             error='No Default Time. Try again', 
                             completer=completer, 
                             validator=validator, 
                             default=default)

    if isinstance(user_input, datetime.time):
        time_val = user_input
    else:
        hr, mi, se = [int(x) for x in user_input.split(':')]
        time_val = datetime.time(hour=hr, minute=mi, second=se, tzinfo=tzinfo)
    print_post_prompt(arg=arg_name,
                      val=time_val,
                      val_style=default_style) 
    return(time_val)

def get_date(title='Please enter a date',
             arg_name='Date',
             completer=date_completer,
             validator=date_validator, 
             default=None, 
             default_style='time',):
    # format default
    if isinstance(default, datetime.date):
        default = default.isoformat()
    print_pre_prompt(title='{}\nISO Format: <b>2020-01-01</b> (Year, Month, Day)'.format(title),
                     default=default,
                     default_style=default_style) 
    user_input = handle_null(user_input=prompt_user(completer=completer, validator=validator), 
                             error='No Default Date. Try again', 
                             completer=completer, 
                             validator=validator, 
                             default=default)

    if isinstance(user_input, datetime.date):
        date_val = user_input
    else:
        yr, mo, da = [int(x) for x in user_input.split('-')]
        date_val = datetime.date(year=yr, month=mo, day=da)
    print_post_prompt(arg=arg_name,
                      val=date_val,
                      val_style=default_style) 
    return(date_val)

def main(results_array):
    os.system('clear')
    for method in results_array:
        try:
            print_title('Testing method: {}'.format(getattr(method, '__name__', repr(method))))
            while True:
                print_line('Hit <b>Ctrl-C</b> to stop testing this method', 'info_italic')
                val = method()
        except KeyboardInterrupt:
            result = button_dialog(
                title='Options',
                text='',
                buttons=[
                    ('Go to next method', True),
                    ('Drop a debugger', False),
                    ('Quit', None)
                ],
            ).run()
            if result == None:
                raise KeyboardInterrupt
            elif result:
                continue
            else:
                # drop debugger
                import ipdb; ipdb.set_trace() # BREAKPOINT


if __name__ == '__main__':
    from prompt_toolkit.shortcuts import checkboxlist_dialog

    results_array = checkboxlist_dialog(
        title="Interactive Params \"Menu\" for testing",
        text="Which methods would you like to test?",
        values=get_available_methods()
    ).run()
    try:
        #
        #   Start main thread
        #
        main(results_array)
    except TypeError:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        print_line('\n\n\tEnding...\n')