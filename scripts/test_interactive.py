from interactive_params import interactive_params, get_blank_param, get_available_methods
from prompt_utils import print_line

methods = get_available_methods()
params = []

for method in methods:
    param = get_blank_param()
    param['method'] = method
    param['arg_name'] = method[-1]
    params.append(param)

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