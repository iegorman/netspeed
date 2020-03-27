# netspeed
Repetitive network speed test that provides a record at both client and server

In development.

## Overview
This is a prototype demo of a package that can run repeated web speed tests for a small internet service provider (ISP), reporting the results to both client and server.  The tests  could be used to look for intermittent low speeds, thereby identifying transmission routes that warrant investigation with tools that are more informative and precise.

The package has one server and two clients:
* The server runs at the ISP to support the tests and log the resuls.
* A web page client can be loaded into a browser.  The web page will run tests automatically while the web page is in the foreground.  The page shows a log and a summary of the tests and also reports back to the server.
* A command-line client will run tests and report both to the server and to local files or a local terminal.  This client can be used in a "black box" setup, such as a Raspberry Pi without keyboard or display.

## Software Required

The javascript server runs in node.js 12.x and may run in earlier versions.

The web page client uses [Bootstrap](https://getbootstrap.com/) and requires a browser that supports HTML5 and javascript ES 6.  This client runs in current versions of Google Chrome, Firefox, and Microsoft Edge.  It may also run in other browsers.

The command line client runs in Python 3.7.

## Package Goals

* Record the results of repeated tests at both server and client
* Avoid over-estimates of speed
* Minimize under-estimates of speed
* A client usable by non-technical people as a downloadable web page
* A client usable in scripts for a plug-and-play black box
* A single server for both clients
* No login or security requirements
  * Web page client runs in a browser on a device already logged in
  * Script client runs in a black box directly connected to user's local network
  * Server is available only to users with currently active direct connection to ISP
* Accuracy and performance should be close to that of currently available tools

## Server
The [server](server.js) runs with the [node.js](https://nodejs.org/) event-based HTTP API, is stateless, and:

* responds to each individual request from any server
* sends a report back for all requests except downloads
* sends the specified amount of data in reponse to a download request
* receives a report from the server with every request except uploads
* receives a specified amount of data in repsonse to an upload requests
* appends summary reports to stdout
* appends copies of message data to stderr

The message data written to stderr combines information from both server and client about download and upload times and sizes, intervals, identifying information, and errors.

The summary reports include calculated upload and download speeds, identifying information, and errors.

## Web Page Client

A [web page client](main.html) is sent as a response to a request for the base URL of the server. The client uses the promise-based 'fetch' API, maintains state between requests and:

* Begins by requesting initial data from the server
* At intervals:
  * requests a download
  * sends a report about the download to the server
  * appends summary reports and copies of messages to display boxes on the web page
  * sends an upload
  * sends a report about the upload to the server
  * appends summary reports and copies of messages to display boxes on the web page
* Is configrable via dropdown lists for different intervals, dowanload sizes, and upload sizes

## Command Line Client

A [command line client](client.py) is invoked from a terminal window or, in a computer with no display and keyboard, from a script.  The client uses the Python 3 library 'urllib.request', maintains state between requests, and:

* Begins by requesting initial data from the server
* At intervals:
  * requests a download
  * sends a report about the download to the server
  * appends summary reports to stdout and copies of messages to stderr
  * sends an upload
  * sends a report about the upload to the server
  * appends summary reports to stdout and copies of messages to stderr
* Is configrable via command line options for different intervals, dowanload sizes, and upload sizes

## Messages Between Server and Client

Messages are carried in the body of POST requests and responses.

The the body of a reply to a request for a client web page will be the web page.

The body of a reply to an erroneous request will be a web page with some information about the error.

The body of an upload request and of a download response is printable text of the length specified in the request for upload or download.

The body of all other requests and responses will be a JSON string representing a javascript object.  The attributes of that object will be a subset of the attifibutes shown in comments at the top of the [server code](server.js).  Most bodies will include some of the [message time points](#request---response-message-time-points) below.

Downloads and uploads each involve two requests.  The first request transfers test data, so no message is carried in one direction (no message down with a download, no message up with an upload).  The client retains state and makes a second request, which sends the server a full report about the first exchange.

The first and second exchange are not recognized as a pair by the server, which does not maintain state.  However, the two exchanges carry identifying information that would allow a post-processor to recognize them as a pair.

### Request - Response Message Time Points

The table below shows the approximate sequence of events during one cycle in which the client sends a request and receives a response.  The relative sequence of client and server events may vary slightly, depending on time delays at various points on the path from client to server and back.

| Client Time Point | Activity | Server Time Point|
| :---: | :---: | :---:|
| clientTimestamp | Prepare upload POST request | |
| clientRequestBegin | Begin sending POST request | |
| | POST header received | serverTimestamp |
| | Begin receiving POST body | serverRequestBegin |
| clientRequestEnd | Finish sending POST request | |
| | Finish receiving POST body | serverRequestEnd |
| | Starf respone | serverResponseBegin
| | Finsh sending response | serverResponseEnd
| clientResponseBegin | Begin receiving response | |
| clientResponseEnd | Finish receiving response | |

## Utilities

### Convert JSON log data to CSV

[jsonformat.py](jsonformat.py) can convert each line of input from a simple JSON dictionary of strings and numbers to a row of Comma-Separated-Values (__CSV__).  Optionally, it can also convert time values from a integer representing milliseonds to a string in the form YYYY-MM-DD hh:mm:ss.sss, with or without conversion to CSV.