#!/usr/bin/python3
# Connmand line client for repeated internet speed tests.

import os
import sys
import collections
import gc
import getopt
import json
import math
import time
import traceback
import urllib.error
import urllib.request
import re

class Client(object):
    """
    Python class and connmand line client for repeated internet speed tests.
    Reports results to local file system and to a remote server.

    The client and server exchange JSON strings that represent Python
    dictionaries.  The entries of each object will be a subset of the entries
    shown as javascript object attributes in comments at the top of file
    './server.js'.
    """

    # defaults for adjustment of transmit length -- treat as class constants
    defaultInterval = 3_600             # seconds
    initialDownloadLength = 20_000_000  # bytes
    initialUploadLength = 2_000_000     # bytes
    minLength = 200_000                 # at least this length after adjustment
    maxLength = 100_000_000             # at most this length after adjustment
    desiredRuntime = 10                 # ideal test run time, seconds
    maxRatio = 1.5          # minimum time devation to cause change in length

    maxUploadLength = 125_000_000   # upload will fail if upload is too large
    # download limit is unknown, seems to be more than 1_000_000_000

    # default output destimations
    defaultLog = sys.stdout             # message log
    defaultReport = sys.stderr          # summary reports and errors

    # count only the bits in actual data, ignore protocal bits
    # protocol bit are a small proportion of message exceopt in smalll packets
    bitsPerDataByte = 8

    @classmethod
    def js_time(cls):
        '''
        JavaScript time -- milliseconds from Unix epoch.

        This is the millisecond offset from 1970-01-01  00:00:00 UTC.
        '''
        return math.floor(1000 * time.time())    # integer from float
    
    @classmethod
    def js_clock(cls, milliseconds=None):
        """
        Format javascript time from Unix epoch to local 'YYYY-MM-DD hh:mm:ss'.

        This is the time in the local time zone.  If no Javascript time is
        given, it will the the current time.
        """
        seconds = milliseconds / 1000 if milliseconds else None
        return time.strftime('%Y-%m-%d  %H:%M:%S', time.localtime(seconds))

    def __init__(self,  serverURL,
                        log=defaultLog,             # JSON log of transactions
                        report=defaultReport,       # human-readable report
                        interval=defaultInterval,
                        downloadLength=initialDownloadLength,
                        uploadLength=initialUploadLength,
                        testID = None   # default: will be set by the server
                        ):
        """
        Create an instance for download and upload tests.

        serverURL may be specified with or without trailing slash.  A
        slash will be appended if trailing slash is omitted.
        report and log are the names of output destinations of destinations ins
        the local filesystem.
        """

        super()

        # Accept server URL with or without trailing slash, strip the slash
        self._serverURL = (serverURL.rstrip('/')
                                if serverURL.endswith('/')
                                else serverURL)
        # Paths relative to server
        self._rootPath = '/'
        self._setupPath = '/begin'
        self._downloadPath = '/download'
        self._downreportPath = '/downreport'
        self._uploadPath = '/upload'
        self._upreportPath = '/upreport'
        self._pingPath = '/echo'

        # output to file system
        self._report = report
        self._log = log
    
        # Initial settings
        self._interval = ( interval if interval
                                    else self.__class__.defaultInterval)
        self._downloadLength = ( downloadLength if downloadLength
                                    else self.__class__.initialDownloadLength)
        self._uploadLength = ( uploadLength if uploadLength
                                    else self.__class__.initialUploadLength)
        self._testID = testID
        self._testNumber = 0        # Incremented on each test cycle
        self._externalIP = None     # client IP seen by server at each contact
        self._testBegin = None      # date-time of first contact with server
        # prevent upload failure caused by large uploads
        self._uploadLength = min(self.maxUploadLength, self._uploadLength)

    def recalculateLength(self, previousLength, previousRuntime):
        """
        Choose a transmit length that gives a test time close to desired time.

        previousLength:     amount of data in last transmission, bytes
        previousRuntime:    time to complete last tranmission, seconds

        When the previous time falls too far below or too far above the
        desired time the previous transmit length will be changed in an
        attempt to come closer to the desired time on the next test.

        There is an upper and a lower limt to the changed length.
        """
        targetRuntime = self.__class__.desiredRuntime
        minLength = self.__class__.minLength
        maxLength = self.__class__.maxLength
        # don't crash on a zero time, replace by a very short time
        lastRuntime = max(previousRuntime, targetRuntime/100)
        if ( lastRuntime > targetRuntime / self.maxRatio
                and lastRunime < targetRuntime * self.maxRatio ):
            return previousLength
        # round to nearest thousand and not too small or large
        transmitLength = previousLength * targetRuntime / lastRuntime
        return max(minLength, min(maxLength, round(transmitLength, -3)))

    def bytesource(self, count):
        """
        Iterate a sequence of blocks of bytes.

        count is the total number of bytes.
        Last block may be shorter than the others.
        """
        byt = ((b'0123456789' * 7) + b'012345678\n') * 50
        n = count
        blen = len(byt)
        while n > blen:
            yield byt
            n -= blen
        yield byt[0:n]      # may have zero length

    def begin(self):
        '''
        Make initial contact with server.

        The server will check donfiguration and provide some test information.
        The server may replace out-of-range values by default values.
        '''
        timestamp = self.js_time()
        params = collections.OrderedDict((
                ('externalIP', self._externalIP),
                ('testID', self._testID),
                ('testBegin', self.js_time()),  # server may revise this time
                ('pathname', self._setupPath),
                ('clientTimeStamp', timestamp),
                ('interval', self._interval),
                ('downloadLength', self._downloadLength),
                ('uploadLength', self._uploadLength),
        ))
        content = bytes(json.dumps(params), 'utf-8')
        try:
            url = self._serverURL + self._setupPath
            request = urllib.request.Request(
                        url,
                        headers = {
                            'Content-Type': 'application/json',
                            # Content-Length is automatically calculated
                            'Accept': 'application/json',
                        },
                        data=content,
                        method='POST'
                        )
            with urllib.request.urlopen(request) as f:
                # failure of the next assignments would be a system failure
                info = json.loads(f.read())
                self._testID = info["testID"]
                self._interval = info["interval"]
                self._downloadLength = info["downloadLength"]
                self._uploadLength = info["uploadLength"]
                self._testBegin = info['testBegin']
                print(json.dumps(info), file=self._log)
                self._log.flush()
                print( 'Begin:\n    Test ID = ' + info['testID']
                        + '\n    External IP = ' + info['externalIP']
                        + '\n    Test Begin Time = '
                            + self.js_clock(info['testBegin'])
                        + '\n', file=self._report)
                self._report.flush()
        except Exception as e:
            raise RuntimeError('timestamp=' + ': '.join([str(timestamp),
                           'Failed to begin communication with server at',
                           self._serverURL])) from e
        return

    def reportToServer(self, params, reportPath):
        """
        Report the result of a download or upload test to the server.

        This is the second stage of a download or upload test and is
        invoked by downloadTest()

        Takes a dictionary of informations and returns a similar
        dictionary from the server.
        """
        timestamp = self.js_time()
        try:
            params['clientTimestamp'] = timestamp
            params['pathname'] = reportPath
            # prepare the request
            content = bytes(json.dumps(params), 'utf-8')
            url = self._serverURL + reportPath
            request = urllib.request.Request(
                        url,
                        headers = {
                            'Content-Type': 'application/json',
                            # Content-Length is automatically calculated
                            'Accept': 'application/json',
                        },
                        data=content,
                        method='POST'
                        )
            with urllib.request.urlopen(request) as f:
                data = f.read(4096).decode(encoding='iso-8859-1',
                                            errors='replace')
        except Exception as e:
            raise RuntimeError('timestamp=' + ': '.join([str(timestamp),
                                'Failed to report result to', url])) from e
        # data should be JSON text in canonical form
        return json.loads(data)

    def download(self, params):
        """
        Run a download test with data received from the server.

        This is the first stage of a download test and is invoked by
        downloadTest()

        Takes a dictionary of informations and returns a modified
        dictionary.
        """
        timestamp = self.js_time()
        clientRequestBegin = 0
        clientRequestEnd = 0
        clientResponseBegin = 0
        clientResponseEnd = 0
        clientReceiveLength = 0
        try:
            # prepare the request
            content = bytes(json.dumps(params), 'utf-8')
            url = self._serverURL + self._downloadPath
            request = urllib.request.Request(
                        url,
                        headers = {
                            'Content-Type': 'application/json',
                            # Content-Length is automatically calculated
                            'Accept': 'text/plain, application/octet',
                        },
                        data=content,
                        method='POST'
                        )
            # send the request, mark the times
            clientRequestBegin = self.js_time()
            with urllib.request.urlopen(request) as f:
                clientRequestEnd = self.js_time()
                # get the response, mark the times
                # we only need the total length of downloaded data
                clientResponseBegin = self.js_time()
                size = len(f.read(1024))
                while size > 0:
                    clientReceiveLength += size
                    size = len(f.read(16_384))
            clientResponseEnd = self.js_time()
            # update the information and return it
            params.setdefault('clientReceiveLength', clientReceiveLength)
            params.setdefault('downloadReceiveLength', clientReceiveLength)
            params.setdefault('clientRequestBegin', clientRequestBegin)
            params.setdefault('clientRequestEnd', clientRequestEnd)
            params.setdefault('clientResponseBegin', clientResponseBegin)
            params.setdefault('clientResponseEnd', clientResponseEnd)
        except Exception as e:
            raise RuntimeError('timestamp=' + ': '.join([str(timestamp),
                           'Failed to download data from server at',
                           self._serverURL])) from e
        return params

    def downloadTest(self):
        """
        Run a download test and report result to server.

        There are two exchanges.  The first exchange does the download and
        reports partial information to the server.  The second exchange
        includes information that becomes available after completion of the
        first exchange, and reports full information to the server.
        """

        gc.collect()    # try to avoid garbage collection during test

        timestamp = self.js_time()
        # allocation of data to make the request
        params = collections.OrderedDict((
                ('externalIP', self._externalIP),
                ('testID', self._testID),
                ('testBegin', self._testBegin),
                ('testNumber', self._testNumber),
                ('pathname', self._downloadPath),
                ('clientTimestamp', timestamp),
                ('interval', self._interval),
                ('downloadLength', self._downloadLength),
        ))

        params = self.download(params)

        # computer-readable JSON report
        print(json.dumps(params), file=self._log)
        self._log.flush()
        # human-readable repot
        megabytes = math.floor(params['clientReceiveLength'] / 1_000) / 1_000
        seconds = (params['clientResponseEnd']
                        - params['clientResponseBegin']) / 1_000
        print( 'Download\n    Time: '
                + self.js_clock(params['clientTimestamp'])
                + '\n    Megabytes: ' + str(megabytes)
                + '\n    Seconds: ' + str(seconds)
                + '\n    Megabits / Second: ' + str(round(
                    (self.bitsPerDataByte * megabytes / seconds), 3))
                + '\n', file=self._report)
        self._report.flush()

        # revise the download size for the next run, to get approximately the
        # desired length of time on each test run.
        self._downloadLength = self.recalculateLength(
                                    params['downloadReceiveLength'], seconds)

        params = self.reportToServer(params, self._downreportPath)

        # computer-readable JSON report
        print(json.dumps(params), file=self._log)
        self._log.flush()

        return

    def upload(self, params):
        """
        Run an upload test with data sent to the server.

        This is the first stage of an upload test and is invoked by
        uploadTest()

        Takes a dictionary of informations and returns a modified
        dictionary.
        """
        timestamp = self.js_time()
        clientRequestBegin = 0
        clientRequestEnd = 0
        clientResponseBegin = 0
        clientResponseEnd = 0
        clientReceiveLength = 0
        try:
            # prepare the request
            url = self._serverURL + self._uploadPath
            request = urllib.request.Request(
                        url,
                        headers = {
                            'Content-Type': 'application/octet',
                            'Content-Length': self._uploadLength,
                            'Accept': 'application/json',
                        },
                        data=self.bytesource(self._uploadLength),
                        method='POST'
                        )
            # send the request, mark the times
            clientRequestBegin = self.js_time()
            with urllib.request.urlopen(request) as f:
                clientRequestEnd = self.js_time()
                # get the response, mark the times, save the info
                clientResponseBegin = self.js_time()
                text = f.read(4096)     # should be JSON text, < 1K
                clientResponseEnd = self.js_time()
                size = len(text)
                while size > 0:
                    # should be no remaining text
                    clientReceiveLength += size
                    size = len(f.read(4096))
            clientResponseEnd = self.js_time()
            info = json.loads(text)
            # update data report for printing as JSON to the log
            params.setdefault('clientReceiveLength', clientReceiveLength)
            params.setdefault('clientRequestBegin', clientRequestBegin)
            params.setdefault('clientRequestEnd', clientRequestEnd)
            params.setdefault('clientResponseBegin', clientResponseBegin)
            params.setdefault('clientResponseEnd', clientResponseEnd)
            params.setdefault('serverReceiveLength',
                                info['serverReceiveLength'])
            params.setdefault('serverRequestBegin', info['serverRequestBegin'])
            params.setdefault('serverRequestEnd', info['serverRequestEnd'])
            params.setdefault('serverResponseBegin',
                                info['serverResponseBegin'])
            params.setdefault('uploadReceiveLength',
                                info['uploadReceiveLength'])
        except Exception as e:
            raise RuntimeError('timestamp=' + ': '.join([str(timestamp),
                           'Failed to upload data from server at',
                           self._serverURL])) from e

        return params

    def uploadTest(self):
        """
        Run upload test and report result to server.

        There are two exchanges.  The first exchange does the upload and
        reports partial information to the server.  The second exchange
        includes information that becomes available after completion of the
        first exchange, and reports full information to the server.
        """

        gc.collect()    # try to avoid garbage collection during test

        timestamp = self.js_time()
        # allocation of data to make the request
        params = collections.OrderedDict((
                ('externalIP', self._externalIP),
                ('testID', self._testID),
                ('testBegin', self._testBegin),
                ('testNumber', self._testNumber),
                ('pathname', self._uploadPath),
                ('clientTimestamp', timestamp),
                ('interval', self._interval),
                ('uploadLength', self._uploadLength),
        ))

        params = self.upload(params)

        # computer-readable JSON report
        print(json.dumps(params), file=self._log)
        self._log.flush()
        # human-readable repot
        megabytes = math.floor(params['uploadLength'] / 1_000) / 1_000
        seconds = (params['clientResponseEnd']
                        - params['clientRequestBegin']) / 1_000
        print( 'Upload\n    Time: '
                + self.js_clock(params['clientTimestamp'])
                + '\n    Megabytes: ' + str(megabytes)
                + '\n    Seconds: ' + str(seconds)
                + '\n    Megabits / Second: ' + str(round(
                    (self.bitsPerDataByte * megabytes / seconds), 3))
                + '\n', file=self._report)
        self._report.flush()

        # revise the upload size for the next run, to get approximately the
        # desired length of time on each test run.
        self._uploadLength = min(self.maxUploadLength,
                self.recalculateLength(params['uploadReceiveLength'], seconds))

        params = self.reportToServer(params, self._upreportPath)

        # computer-readable JSON report
        print(json.dumps(params), file=self._log)
        self._log.flush()

        return

    def run_test_cycle(self):
        """
        Run a single set of upload and upload tests.
        """
        self.downloadTest()
        self.uploadTest()

    def run(self):
        """
        Invoke startup and ongoing test runs.
        """
        self.begin()
        while True:
            self.run_test_cycle()
            time.sleep(self._interval)

if __name__ == "__main__":
    shortopts = "h"
    longopts = ["help", "testid=", "interval=", "download=", "upload="]
    cmdline = getopt.getopt(sys.argv[1:], shortopts, longopts=longopts)
    argv = cmdline[1]
    opt = dict(cmdline[0])

    def printerr(s):
        print(s, file=sys.stderr)
        sys.stderr.flush()

    if len(argv) < 1 or '-h' in opt or '--help' in opt:
        printerr("Usage: " + sys.argv[0] + " [options] host[:port]")
        printerr("       Client to estimate download and upload times")
        printerr("     host (required): domain name or IP address of server")
        printerr("     port (optional, default = 80): "
              + "destination port on server")
        printerr("   options:")
        printerr("       -h|--help     print this message")
        printerr("      --interval=n   time (seconds) between runs"
              + " (default = " + str(Client.defaultInterval) +")")
        printerr("      --download=n   number of bytes to download"
              + " (default = " + str(Client.initialDownloadLength) + ")")
        printerr("      --upload=n     number of bytes to upload"
              + " (default = " + str(Client.initialUploadLength) + ")")
        printerr("      --testid=ID    test ID"
              + " (default = test ID will be set by server)")
        printerr("   JSON log goes to stdout")
        printerr("   Human-readable report goes to stderr")
        printerr("   See script for details")
        exit(2)
    testID = opt["--testid"] if "--testid" in opt else None
    interval = (int(opt["--interval"]) if "--interval" in opt
                                        else Client.defaultInterval)

    download = (int(opt["--download"]) if "--download" in opt
                                        else Client.initialDownloadLength)

    upload = (int(opt["--upload"]) if "--upload" in opt
                                    else Client.initialUploadLength)

    try:
        Client(argv[0], interval=interval,
                        downloadLength=download,
                        uploadLength=upload,
                        testID=testID).run()
    except KeyboardInterrupt as e:
        printerr("Teiminated by Keyboard Interrupt\n")
        exit(1)
