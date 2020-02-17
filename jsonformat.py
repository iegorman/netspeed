#!/usr/bin/python3
# Reformat JSON as CSV or JSON with items in a specific order

import os
import sys
import collections
import csv
import getopt
import json
import math
import time

class JsonFormat(object):
    """
    Copy and transform JSON text to CSV text or reformatted JSON text.

    Each input line is a one-level JSON dictionary of strings and integers.
    """

    # Test information, other than times
    # all will be formatted for output as as strings
    testInfo = (
        "testID",
        "externalIP",
        "testNumber",
        "pathname",
        "interval",
        "downloadLength",
        "uploadLength",
    )

    # millisecond times from Unix epoch
    # will be formatted as either as local YYYY-MM-DD hh:mm:ss.sss
    # or as integer milliseconds
    times = (
        "testBegin",
        "clientTimestamp",
        "clientRequestBegin",
        "clientRequestEnd",
        "clientResponseBegin",
        "clientResponseEnd",
        "serverTimestamp",
        "serverRequestBegin",
        "serverRequestEnd",
        "serverResponseBegin",
        "serverResponseEnd",
    )

    @classmethod
    def formatTime(cls, milliseconds):
        """
        Format integer millesecond time from Unix epoch to local
        YYYY-MM-DD hh:mm:ss.sss.

        This will be the time in the local time zone.
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
    def copy(cls, lineReader, writer, isRaw=False, isJsonFormat=False):
        """
        Transform JSON input text to CSV output text, with headings.

        lineReader is a text source with a readline() method.
        Each input line is a one-level JSON dictionary of strings and
        integers.

        writer is any object with a write() method that accepts a
                string and does not append a terninaiing newline.
        isRaw       Whether times are to be output without reformatting
        isJsonFormat    Whether output should be JSON instead of CSV
        """
        MaxJsonLength = 4096        # including a newline

        # output format
        if isJsonFormat:    # JSON
            writeDict = cls.JsonWriter(writer).writeDict
        else:               # CSV
            writeDict = cls.CsvWriter(writer, cls.testInfo, cls.times
                                        ).writeDict

        # create and output a dictionary from eadh input line (JSON literal)
        line = lineReader.readline(MaxJsonLength)
        while len(line) > 0:
            strippedLine = line.strip()
            if strippedLine == '':
                value = collections.OrderedDict()   # allow blank lines
            else:
                value = json.loads(line.strip())    # JSON to ordered dictionary

            newdict = collections.OrderedDict()
            for name in cls.testInfo:
                if name in value:
                    newdict.setdefault(name, value[name])
            for name in cls.times:
                if name in value:
                    if isRaw:
                        # milliseconds from Unix epoch
                        newdict.setdefault(name, value[name])
                    else:
                        # human-readable local date and time
                        newdict.setdefault(name, cls.formatTime(value[name]))
            if isJsonFormat:
                # names not listed in CSV headings
                # Copy as-is to JSON, but not to CSV
                # Each CSV row has same number of columns, no extra columns
                for name in value:
                    if not name in newdict:
                        newdict.setdefault(name, value[name])

            writeDict(newdict)

            line = lineReader.readline(MaxJsonLength)

    class CsvWriter(object):
        """
        Write OrderedDicts as rows of CSV values under headings in order.

        Output uses minimal CVS quoting, quoting only the strings that
        contain characters that have special meaning to CSV.
        """
        def __init__(self, writer, testInfo, times):
            self.csvwriter = csv.writer(writer)
            self.names = list(testInfo)
            self.names.extend(list(times))      # names of expected fields
            field = []      # column headings of expected fields
            for name in self.names:
                field.append(name)
            self.csvwriter.writerow(field)

        def writeDict(self, valueDict):
            field = []      # column values for output to CSV
            # output values only for the expected fields
            # every CSV row has the same length and the same fields
            for name in self.names:
                if name in valueDict:
                    # numeric strings will be unquoted in mimimal CSV
                    field.append(str(valueDict[name]))      # field has data
                else:
                    field.append('')                # no data for this field

            self.csvwriter.writerow(field)

    class JsonWriter(object):
        """
        Write OrderedDicts as JSON object literals, with names in order.
        """
        def __init__(self, writer):
            self.writer = writer

        def writeDict(self, valueDict):
            self.writer.write(json.dumps(valueDict) + '\n')

if __name__ == "__main__":
    cmdline = getopt.getopt(sys.argv[1:], 'h',
                            longopts=['help', 'json', 'raw'])
    argv = cmdline[1]
    opt = dict(cmdline[0])

    if len(argv) > 1 or '-h' in opt or '--help' in opt:
        print("Usage: " + sys.argv[0] + " [-h|--help] [--raw] [filename]",
                file=sys.stderr)
        print("       Convert simple JSON format to CSV format",
                file=sys.stderr)
        print("       Input: JSON name-value pairs, one JSON per line",
                file=sys.stderr)
        print("       Output: CSV file with reordered JSON names as headings",
                file=sys.stderr)
        print("               or JSON file with reordered JSON names",
                file=sys.stderr)
        print("       Unexpected JSON items will be omitted from CSV output",
                file=sys.stderr)
        print("   Options:",
                file=sys.stderr)
        print("       -h|--help     print this message",
                file=sys.stderr)
        print("       --json        output JSON instead of CSV",
                file=sys.stderr)
        print("       --raw         do not format times",
                file=sys.stderr)
        print("   Input times are interpreted as milliseconds from Unix epoch",
                file=sys.stderr)
        print("   See script for details",
                file=sys.stderr)
        exit(1)

    isRaw = ('--raw' in opt)
    isJsonFormat = ('--json' in opt)

    # Input text source
    if len(argv) > 0:
        lineReader = open(argv[0], newline='')
    else:
        lineReader = sys.stdin

    # Output columns of CSV data from the JSON input.
    try:
        JsonFormat.copy(lineReader, sys.stdout, isRaw, isJsonFormat)
    finally:
        if not lineReader is sys.stdin:
            lineReader.close()
