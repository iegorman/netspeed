#!/usr/bin/python3
# Connmand line client for repeated internet speed tests.

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
    Copy and transform JSON text to CSV text, with headings.

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
    # will be formatted as either YYYY-MM-DD hh:mm:ss.sss or as str(int)
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
    def copy(cls, lineReader, writer, isRaw=False, isJsonFormat=False):
        """
        Transform JSON input text to CSV output text, with headings.

        lineReader is a text source with a readline() method.
        Each input line is a one-level JSON dictionary of strings and
        integers.

        csvWriter is a csv.writer()
        """
        MaxJsonLength = 4096        # including a newline

        # time format
        if isRaw:
            format = str            # milliseconds from Unix epoch as str
        else:
            format = cls.formatTime # YYYY-MM-DD hh:mm:ss.sss Local

        # output format
        if isJsonFormat:
            writeDict = cls.JsonWriter(writer, format, cls.testInfo,
                                        cls.times).writeDict
        else:
            writeDict = cls.CvsWriter(writer, format, cls.testInfo,
                                        cls.times).writeDict

        # format and copy
        line = lineReader.readline(MaxJsonLength)
        while len(line) > 0:
            strippedLine = line.strip()
            if strippedLine == '':
                value = collections.OrderedDict()   # allow blank lines
            else:
                value = json.loads(line.strip())    # JSON to ordered dictionary
            writeDict(value)
            line = lineReader.readline(MaxJsonLength)

    class CvsWriter(object):
        """
        Write OrderedDicts as rows of CSV values under re-ordered headings.
        """
        def __init__(self, writer, format, testInfo, times):
            self.csvwriter = csv.writer(writer)
            self.format = format
            self.testInfo = testInfo
            self.times = times
            field = []      # column headings for output to CVS
            for name in self.testInfo:
                field.append(name)
            for name in self.times:
                field.append(name)
            self.csvwriter.writerow(field)

        def writeDict(self, value):
            field = []      # column values for output to CVS
            for name in self.testInfo:
                if name in value:
                    field.append(str(value[name]))
                else:
                    field.append('')
            for name in self.times:
                if name in value:
                    field.append(self.format(value[name]))
                else:
                    field.append('')
            # omit unexpected items to keep all rows same length
            self.csvwriter.writerow(field)

    class JsonWriter(object):
        """
        Write OrderedDicts as Json object literals, with names re-ordered.
        """
        def __init__(self, writer, format, testInfo, times):
            self.writer = writer
            self.format = format
            self.testInfo = testInfo
            self.times = times

        def writeDict(self, value):
            if len(value) < 1:
                self.writer.write(json.dumps(value) + '\n')
                return
            newdict = collections.OrderedDict()
            for name in self.testInfo:
                if name in value:
                    newdict.setdefault(name, value[name])
                else:
                    newdict.setdefault(name, None)
            for name in self.times:
                if name in value:
                    newdict.setdefault(name, self.format(value[name]))
                else:
                    newdict.setdefault(name, None)
            # copy unexpected items as-is
            for name in value:
                if not name in newdict:
                    newdict.setdefault(name, value[name])
            self.writer.write(json.dumps(newdict) + '\n')

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
        lineReader = open(argv[0])
    else:
        lineReader = sys.stdin

    # Output columns of CSV data from the JSON input.
    try:
        JsonFormat.copy(lineReader, sys.stdout, isRaw, isJsonFormat)
    finally:
        if not lineReader is sys.stdin:
            lineReader.close()
