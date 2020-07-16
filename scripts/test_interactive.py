from interactive_params import interactive_params, get_blank_param, get_available_methods
from prompt_utils import print_line
import datetime

methods = get_available_methods(as_dict=True)
param = get_blank_param()
param['method'] = methods['Date/time window input']

param_with_upper_bounds = get_blank_param()
param_with_upper_bounds['method'] = methods['Date/time window input']
param_with_upper_bounds['start_date'] = datetime.date(2020, 9, 6)

param_with_bounds = get_blank_param()
param_with_bounds['method'] = methods['Date/time window input']
param_with_bounds['start_date'] = datetime.date(2020, 9, 6)
param_with_bounds['start_date'] = datetime.date(2020, 9, 10)

param_with_bad_bounds = get_blank_param()
param_with_bad_bounds['method'] = methods['Date/time window input']
param_with_bad_bounds['start_date'] = datetime.date(2020, 9, 10)
param_with_bad_bounds['stop_date'] = datetime.date(2020, 9, 6)

params = [
    # param,
    param_with_upper_bounds,
    param_with_bounds,
    param_with_bad_bounds,
]

# params = []
# for method in methods:
#     param = get_blank_param()
#     param['method'] = method
#     param['arg_name'] = method[-1]
#     params.append(param)

try:
    results = interactive_params(params)
except KeyboardInterrupt:
    print_line('\n\n\tEnding...\n')
else:
    for result in results:
        print_line('<b>{}:</b> '.format(result[0]), l_style='info', end='')
        if isinstance(result[1], tuple):
            print_line('{}'.format(*result[1]))
        else:
            print_line(result[1])