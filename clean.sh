#!/bin/bash

# Script to clear all data files from <cwd>/data
# User can change the data directory by passing the path
DATA_DIR="./data"

# check if arg passed
if [ ! -z "$1" ] ; then
    DATA_DIR="$1"
fi

if rm $DATA_DIR/*.txt > /dev/null 2>&1 ; then
    echo "Deleted Data Files"
else
    echo "Could not delete data files"
    echo "Possible reasons:"
    echo "-----------------"
    echo "1. The data directory is empty"
    echo "2. You do not have the necessary permissions for [$DATA_DIR]"
    echo "3. [$DATA_DIR] does not exist/path is incorrect"
fi
