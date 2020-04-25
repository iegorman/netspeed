#!/bin/bash
# Run server with stdout > file, stderr > file

set -e      # exit non-interactive shell on script error
set -u      # unset variable is an error

if [ "$#" != 3 ]
then
    echo "Usage: \"$0\" url serverTag clientTag" 1>&2
    echo "     Run Python client with stdout and stderr to files" 1>&2
    echo "     url is location of server"
    echo "     Tags can be any short string allowed in file names" 1>&2
    echo "     See script for details" 1>&2
    exit 1
fi

OPTIONS="${PYCLIENTOPTIONS:=}"      # options for client.py, set with 'env'
URL="$1"        # string representation of a valid URL
SERVER="$2"     # arbitrary short strings containing only filename characters
CLIENT="$3"     #

if ! "$(dirname '$0')/../client.py" ${OPTIONS} "$URL" \
    > "${SERVER}-js-${CLIENT}-py-log.json" \
    2> "${SERVER}-js-${CLIENT}-py-report.txt"
then
    echo -n "Client terminated with exit code $?, see file" 1>&2
    echo " '${SERVER}-js-${CLIENT}-py-report.txt':" 1>&2
    tail "${SERVER}-js-${CLIENT}-py-report.txt" 1>&2
    exit 1
fi
