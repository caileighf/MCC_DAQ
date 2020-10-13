#!/bin/bash

if [ "$PYTHON_EXE" = "" ]; then
    echo -e "\n You MUST set the PYTHON_EXE env variable!"
    echo -e " To set it for this bash session by running:"
    echo -e "   $ export PYTHON_EXE=/path/to/python \n"
else
    $PYTHON_EXE scripts/single_DAQ_collect_trigger.py --use-config --script
fi