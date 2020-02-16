#!/usr/bin/python3
# create a pseudo-random sequence of bytes in a specified length


# This is part of a temporary fix for slow downloads in server.js.
# Denerated download data was being produced at speeds less than line speed.
# For the time being, data will be downloaded from pre-existing files.

# This script should be run from script 'gendata.sh', running in the same
# directory as file 'server.js'.

import sys
import locale
import random

def randombytes(count):
    byte = bytearray(1)
    while (count > 0):
        # randome printable bytes (ASCII)
        sys.stdout.buffer.write(bytes([random.randint(32,126)]))
        count -= 1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: " + sys.argv[0] + " count", file=sys.stderr)
        print("       Produce a pseudo-random sequence of bytes",
              file=sys.stderr)
    else:
        if sys.argv[1].isdigit() and int(sys.argv[1]) > 0:
            randombytes(int(sys.argv[1]))
        else:
            print("count must be an integer greater than zero",
                  file=sys.stderr)
