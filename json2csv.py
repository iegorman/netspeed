#!/usr/bin/python3
# Connmand line client for repeated internet speed tests.

import os
import sys
import csv
import getopt
import json
import math
import time

class JsonToCsv(object):
    """
    Copy and transform JSON text to CSV text, with headings.

    Each input line is a one-level JSON dictionary of strings and integers.
    """

    # Test information, other than times
    # all will be formatted for output as as strings
    testInfo = (
        "testID",
        "externalIP",
        "testBegin",
        "testNumber",
        "pathname",
        "interval",
        "downloadLength",
        "uploadLength",
    )

    # millisecond times from Unix epoch
    # will be formatted as either YYYY-MM-DD hh:mm:ss.sss or as str(int)
    times = (
        "clientTimestamp",
        "clientRequestBegin",
        "clientRequestEnd",
        "clienResponseBegin",
        "clienResponseEnd",
        "serverTimestamp",
        "serverRequestBegin",
        "serverRequestEnd",
        "serverResponseBegin",
        "serverResponseEnd",
    )

    @classmethod
    def formatTime(cls, milliseconds):
        """
        Format javascript time from Unix epoch to local 'YYYY-MM-DD hh:mm:ss'.

        This is the time in the local time zone.
        """
        secondsInt = math.floor(milliseconds / 1000)
        secondsFrac = '.' + str(milliseconds)[-3::1]
        return (time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(secondsInt))
                                + secondsFrac)

    def __init__(self):
        """
        Copy input streams (JSON) to output streams (CSV), with headings.
        """
        super().__init__()

    @classmethod
    def copy(cls, lineReader, csvWriter, isRaw=False):
        """
        Transform JSON input text to CSV output text, with headings.

        lineReader is a text source with a readline() method.
        Each input line is a one-level JSON dictionary of strings and
        integers.

        csvWriter is a csv.writer()
        """
        if isRaw:
            format = str
        else:
            format = cls.formatTime
        MaxJsonLength = 4096        # including a newline
        field = []      # column headingss for output to CVS
        for name in cls.testInfo:
            field.append(name)
        for name in cls.times:
            field.append(name)
        csvWriter.writerow(field)
        line = lineReader.readline(MaxJsonLength)
        while len(line) > 0:
            # print(line, file=sys.stdout)
            value = json.loads(line.strip())    # JSON to dictionary
            field = []      # column values for output to CVS
            for name in cls.testInfo:
                if name in value:
                    field.append(str(value[name]))
                else:
                    field.append('')
            for name in cls.times:
                if name in value:
                    field.append(format(value[name]))
                else:
                    field.append('')
            csvWriter.writerow(field)
            line = lineReader.readline(MaxJsonLength)

if __name__ == "__main__":
    cmdline = getopt.getopt(sys.argv[1:], 'h',
                            longopts=['help', 'raw'])
    argv = cmdline[1]
    opt = dict(cmdline[0])

    if len(argv) > 1 or '-h' in opt or '--help' in opt:
        print("Usage: " + sys.argv[0] + " [-h|--help] [--raw] [filename]",
                file=sys.stderr)
        print("       Convert simple JSON format to CSV format",
                file=sys.stderr)
        print("       Input: JSON name-value pairs, one JSON per line",
                file=sys.stderr)
        print("       Output: CSV file with JSON names as headings",
                file=sys.stderr)
        print("   Options:",
                file=sys.stderr)
        print("       -h|--help     print this message",
                file=sys.stderr)
        print("       --raw         do not format times",
                file=sys.stderr)
        print("   Input times are interpreted as milliseconds from Unix epoch",
                file=sys.stderr)
        print("   See script for details",
                file=sys.stderr)
        exit(1)

    isRaw = ('--raw' in opt)

    # Input text source
    if len(argv) > 0:
        lineReader = open(argv[0])
    else:
        lineReader = sys.stdin

    # Output columns of CSV data from the JSON input.
    try:
        csvWriter = csv.writer(sys.stdout)
        JsonToCsv.copy(lineReader, csvWriter, isRaw)
    finally:
        if not lineReader is sys.stdin:
            lineReader.close()
