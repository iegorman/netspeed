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
        "clientReceiveLength",
        "serverReceiveLength",
        "downloadReceiveLength",
        "uploadReceiveLength",
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

    # more stuff, miscellaneous, not alwasys present
    appendix = (
        "error",
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
            names = list(cls.testInfo)
            names.extend(list(cls.times))
            names.extend(list(cls.appendix))
            writeDict = cls.CsvWriter(writer, names).writeDict
        try:
            # create and output dictionary from eadh input line (JSON literal)
            line = lineReader.readline(MaxJsonLength)
            line_num = 0
            while len(line) > 0:
                line_num += 1
                strippedLine = line.strip()
                if strippedLine == '':
                    value = collections.OrderedDict()   # allow blank lines
                else:
                    value = json.loads(line.strip())    # ordered dictionary

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
                            newdict.setdefault(name,
                                                cls.formatTime(value[name]))
                for name in cls.appendix:
                    if name in value:
                        newdict.setdefault(name, value[name])
                if isJsonFormat:
                    # names not listed in CSV headings
                    # Copy as-is to JSON, but not to CSV
                    # Each CSV row has same number of columns, no extra columns
                    for name in value:
                        if not name in newdict:
                            newdict.setdefault(name, value[name])

                writeDict(newdict)

                line = lineReader.readline(MaxJsonLength)
        except Exception as e:
            # Error is most likely due to error in creating the inpuy
            raise RuntimeError('Error at line ' + str(line_num)
                                + ' of input.') from e

    class CsvWriter(object):
        """
        Write OrderedDicts as rows of CSV values under headings in order.

        Output uses minimal CVS quoting, quoting only the strings that
        contain characters that have special meaning to CSV.
        """
        def __init__(self, writer, names):
            self.csvwriter = csv.writer(writer)
            self.names = names
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

    def printerr(s):
        print(s, file=sys.stderr)
        sys.stderr.flush()

    if len(argv) > 1 or '-h' in opt or '--help' in opt:
        printerr("Usage: " + sys.argv[0] + " [-h|--help] [--raw] [filename]")
        printerr("       Convert simple JSON format to CSV format")
        printerr("       Input: JSON name-value pairs, one JSON per line")
        printerr("       Output: CSV file with reordered JSON names as" +
                 " headings")
        printerr("               or JSON file with reordered JSON names")
        printerr("       Unexpected JSON items will be omitted from CSV" +
                 " output")
        printerr("   Options:")
        printerr("       -h|--help     print this message")
        printerr("       --json        output JSON instead of CSV")
        printerr("       --raw         do not format times")
        printerr("   Input times are interpreted as milliseconds from Unix" +
                 " epoch")
        printerr("   See script for details")
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
