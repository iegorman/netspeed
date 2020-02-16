#!/bin/bash
# generate data files for test downloads

# This is part of a temporary fix for slow downloads in server.js.
# Denerated download data was being produced at speeds less than line speed.
# For the time being, data will be downloaded from pre-existing files.

# This script should be run in the same directory as file 'server.js'.

DIR=$(dirname $0)
set -x
for i in 6 10 15 25 50
do
    ${DIR}/gendata.py ${i}000000 > text${i}meg.dat
done