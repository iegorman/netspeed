# Javascript for Neophytes

_DRAFT_

The project is my first use of javascript.  I do not consider myself an expert in the language.  But I can use it effectively.

I learned to use javascript in the same way that I learned to use assembly, Fortran and Cobol half a century ago: by working on a project (this one) that requires the language.  Learning this way is about as easy (or as difficult) now as it was then; there is more to learn, but we now have better tools.

## Overview

Web applications require a number of activities to happen simultaneously.  At the front end, a user may be entering data or clicking a button while a data download is in progress.  At the back end, a request from a second client may arrive while work is in progress on a request from the first client.  At both ends, a computer has more than enough power to handle everything, but must be able keep many activities going while other activities are stalled (for example, by waiting for another chunk of data to arrive over a network connection).

Modern computers with multiple processors can run several activities concurrently, but they run a much larger number of activities in apparent concurrency by moving each activity forward a little before changing to another to move that one forward a little.  Computers do this so quickly that everything seems to happen at once and everything gets done.  Javascript makes it easy for a developer to use this second form of concurrency (actually, apparent concurrency) in web applications.

Javascript allows a developer to manage concurrent activities with less technical knowledge than would be required in assembly, C, Java, or Python.  But, at a minimum, a developer must still understand the difference between a synchronous function and an asynchronous function, and how asynchronous functions are used in javascript.

_Synchronous functions_ do all their work before they return and can return the result (if any) of their work.  This is the kind of function I have used in other programming languages.

_Asysnchronous functions_ set up some work to be done and return before the work is completed (possibly before the work is even started).  They cannot return the result of their work and a developer has to get that result in some other way.  They cannot throw exceptions because most, if not all, errors will occur after the function has returned; errors must be reported in another way.

In javascript an _asynchronous function_ works like this:
* Set up an activity
* Provide a way to get the resuts of that activity at some later time
* Provide a way to get any error reports that may be required
* Start the activity
* Leave the activity and go on to other activities while the first activity runs in the backgound
* Use the result of the first activity later, when that activity has completed, or do whatever is necessary when the activity has failed

Asysnchronous functions deliver the results of their background activity via _callback functions_ (aka _event handlers_). The backgorund activity invokes a _callback function_ whenever there is something to be delivered.  The _callback function_ can start another activity or store some data for later use.

When one activity requires the result of another, the first activity must be postponed (i.e. stalled, or simply not started) until the result of the second activity becomes available.

Although there is [more](#technical-notes) to javascript, the information above is enough to understand the following example:

## An Example of Event-Based Programming in Node.js

The server [boomerang.js](boomerang.js) illustrates one of the ways that javascript supports concurrent programming.  A HTTP request from a client starts a sequence of operations in the server that ends with sending a HTTP response back to the client.

### Some Useful Information

For this example, all you need to know about [events and event handlers](#events-and-event-handlers) is:
* Javascript can trigger (or _"fire"_) a named _event_ each time something happens.
* Each _event_ will invoke a corresponding _callback_ function (the _event handler_) to do something about whatever happened.
* The _event name_ identifies a particular kind of _event_, such as data becoming available, or reaching the end of some data.

Javascript allows you te define un-named (anonymous) functions by using the _arrow function_ notataion to associate an argument list with the corresponding function body:

```javascript
(arg1, arg2) => {

  // function body

}
```
Some [Node.js](https://nodejs.org/) reference documentation:
* [Anatomy of an HTTP Transaction](https://nodejs.org/es/docs/guides/anatomy-of-an-http-transaction/)
* The [HTTP Interface](https://nodejs.org/api/http.html)
* The [Stream Interface](https://nodejs.org/api/stream.html)
  * [http.IncomingMessage](https://nodejs.org/api/http.html#http_class_http_incomingmessage) is a [Readable Stream](https://nodejs.org/api/stream.html#stream_readable_streams)
  * [http.ServerResponse](https://nodejs.org/api/http.html#http_class_http_serverresponse) is a [Writable Stream](https://nodejs.org/api/stream.html#stream_writable_streams)

### A Simple Server in Node.js

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
* installs an _'error'_ event handler on the _request_ object to report errors (we hope there won't be any)
* installs an _'end'_ event handler on the _request_ object to send a reply via the _response_ object to the client after all the data has been read from the _request_ object
* installs a _'data'_ event handler on the _request_ object to receive and store chunks of data as they become avaialble
* exits

The server function is an _asynchronous_ function because
* Installation of the _'data'_ handler on the _request_ object causes the _request_ to start firing zero or more _'data'_ events, followed by an _'end'_ event, after the server function has exited.
* Each event invokes the corresponding event handler to carry out the activity required by that event.

After the _asynchronous_ server function exits
* zero or more _'data'_ events occur and each event invokes the _'data'_ handler to store a chunk until all the data has been saved
* the '_end_' event occurs and invokes the _'end'_ event handler to:
  * sort the request headers by name and write them to the _response_ object
  * collect and write other information to the _response_ object
  * join the chunks saved by the _'data'_ event handler into one large block and write the block to the _response_ object
  * end the _reponse_ object. The _reponse_ object will send (or finish sending) a reply to the client

When the _'end'_ event handler exits, all work on that particular HTTP request has been completed.

Since the work proceeds in separate discrete stages, other HTTP requests could come in and be in progress before work on the first request is completed.  Thus each request can be handled in short steps and the server can be working on several requests, each in turn, from different clients at the same time.  The switches from one activity to another happen so quickly that all reguests appear to be hanled simultaneously.

## Technical Notes

### Events and Event Handlers
