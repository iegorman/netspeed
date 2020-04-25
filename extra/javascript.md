# Javascript for Neophytes

_DRAFT_

The project is my first use of javascript.  I do not consider myself an expert in the language.  But I can use it effectively.

I learned to use javascript in the same way that I learned to use assembly, Fortran and Cobol half a century ago: by working on a project (this one) that requires the language.  Learning this way is about as easy (or as difficult) now as it was then; there is more to learn, but we now have better tools.

## Overview

Javascript is a language that supports conccurrency, but unlike some other languages, does not require you to know very much about the details of managing concurrent operations. This makes Javascript very useful for programs in web servers that must respond to a number of simultaneous but unrelated requests, and in web browsers that must respond to many other needs while building or modifying a particular web page.

Concurrency (as in "multi-tasking" and "multi-threading") allows a computer to keep a number of different activities going on at the same time.  Although it looks like everything is happening at once, the computer normally manages this by taking turns with each activity, moving one activity along a little bit before working on the next activity.

Web applications require concurrency.  At the front end, a user may be entering data or clicking a button while a data download is in progress.  At the back end, a request from a second client may arrive while work is in progress on a request from the first client.  At both ends, a computer has more than enough power to handle everything, but must be able to shift to another activity when any one activity is stalled (for example, by waiting for another chunk of data to arrive over a network connection).

Modern computer applications can handle large numbers of activities, changing from one to another so quickly that everything seems to happen at once and everything gets done.  Javascript is a very convenient programming language for developing that kind of application, because the language is designed for easy management of concurrent activities.

Javascript supports an _asynchrronous_ approach to concurrent programming:
* Set up an activity
* Provide a way to get the resuts of that activity at some later time
* Start the activity
* Leave the activity and go on to other activities while the first activity runs in the backgound
* Use the result of the first activity later, when that activity has completed

## An Example of Event-Based Programming

The server [boomerang.js](boomerang.js) illustrates the older (_events_ and _event handlers_) of two ways that javascript supports concurrent programming.  A HTTP request from a client starts a sequence of operations in the server that ends with sending a response back to the client.

### Some Useful Information

For this example, all you need to know about [events and event handlers](#events-and-event-handlers) is that javascript can trigger (or _"fire"_) a named _event_ each time something happens, and will invoke a function (the _event handler_) to do something about whatever happened.  The name identifies a particular kind of event, such as data becoming available, or reaching the end of some data.

Javascript allows you te define un-named (anonymous) functions by using the _arrow function_ notataion to associate an argument list with the corresponding function body:

```javascript
(arg1, arg2) => {

  // function body

}
```
Some reference documentation:
* [Anatomy of an HTTP Transaction](https://nodejs.org/es/docs/guides/anatomy-of-an-http-transaction/)
* The [HTTP Interface](https://nodejs.org/api/http.html)
* The [Stream Interface](https://nodejs.org/api/stream.html)
  * [http.IncomingMessage](https://nodejs.org/api/http.html#http_class_http_incomingmessage) is a [Readable Stream](https://nodejs.org/api/stream.html#stream_readable_streams)
  * [http.ServerResponse](https://nodejs.org/api/http.html#http_class_http_serverresponse) is a [Writable Stream](https://nodejs.org/api/stream.html#stream_writable_streams)

### A Simple Server

In [boomerang.js](boomerang.js), the function [http.createServer()](https://nodejs.org/api/http.html#http_http_createserver_options_requestlistener) takes a server function (in _arrow function_ notation) as an argument and
* creates a server that will invoke the server function on each HTTP request that comes in
* exits without starting the server.

The function [server.listen()](https://nodejs.org/api/http.html#http_server_listen)
* starts the server
* exits while the server is still idle, waiting for incoming HTTP requests

When a HTTP request comes in from a client, the server
* creates a [http.IncomingMessage](https://nodejs.org/api/http.html#http_class_http_incomingmessage) object as a _request_ object for accessing data from the incoming HTTP _request_
* creates a [http.ServerResponse](https://nodejs.org/api/http.html#http_class_http_serverresponse) object as a _response_ object for sending a reply to the client
* invokes the server function on the _(request, response)_ pair

The server function
* gets some data from the _request_ URL
* installs an _'error'_ event handler to report errors (we hope there won't be any)
* installs an _'end'_ event handler to send a _response_ to the client after all the data has been read from the _request_ object
* installs a _'data'_ event handler to receive chunks of data as they become avaialble
* exits

After the server function exits
* the first _'data'_ event occurs (if there is any data) and invokes the _'data'_ handler to collect and saves a chunk of data
* _'data'_ events occur until all the data has been saved
* the '_end_' event occurs when there is no more data and the _'end'_ event handler
  * sorts the request headers by name and writes them to the _response_ object
  * collects and writes other information to the _response_ object
  * joins the chunks saved by the _'data'_ event handler into one large block and writes the block to the _response_ object
  * ends the _reponse_ object, so that the completed response will be sent to the client
  * exits

At this point, the server has completed all work on that particular HTTP request.

Since the work proceeds in separate discrete stages, other HTTP requests could come in and be in progress before work on the first request is completed.  Thus each request can be handled in short steps and the server can be working on several requests, each in turn, from different clients at the same time.

## Technical Notes

### Events and Event Handlers
