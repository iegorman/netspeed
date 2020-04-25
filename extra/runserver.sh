#!/bin/bash
# Run server with stdout > file, stderr > file

# This script qas used for development and test 

set -e      # exit non-interactive shell on script error
set -u      # unset variable is an error

if [ "$#" != 2 ]
then
    echo "Usage: \"$0\" serverTag clientTag" 1>&2
    echo "     Run server with stdout and stderr to files" 1>&2
    echo "     Tags can be any short string allowed in file names" 1>&2
    echo "     See script for details" 1>&2
    exit 1
fi

SERVER="$1"     # arbitrary short strings containing only filename characters
CLIENT="$2"     #

if ! "$(dirname '$0')/../server.js" \
    > "${SERVER}-server-${CLIENT}-client-log.json" \
    2> "${SERVER}-server-${CLIENT}-client-err.txt"
then
    echo -n "Server terminated with exit code $?, see file" 1>&2
    echo " '${SERVER}-server-${CLIENT}-client-err.txt':" 1>&2
    tail "${SERVER}-server-${CLIENT}-client-err.txt" 1>&2
    exit 1
fi
