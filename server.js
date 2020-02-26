#!/usr/bin/node
// node.js server side for repeated internet speed tests
//
// logs info about each request to stdout (JSON)
// logs some errors to stdout (JSON) and others to sterr (various formats)
//
// For ES6 or later and node.js LTS Version 12.13.0 or later
//

/*
  The client maintains state between requests, but the server does not.

  The server and client communicate by sending JSON objects back and forth.
  No message is sent to the client in response to a download request because
  the body of the response is the download data.
  No message is sent from the client in an upload request because the body of
  the request is the upload data.

  The JSON objects are similar to this one, but may not have all the attributes
  shown:

    var testInfo = {
      testID:               null,
      externalIP:           null,
      testBegin:            null,
      testNumber:           null;
      pathname:             null,
      serverTimestamp:      null,
      clientTimestamp:      null,
      interval:             null,
      clientRequestBegin:   null,
      clientRequestEnd:     null,
      clienResponseBegin:   null,
      clienResponseEnd:     null,
      serverRequestBegin:   null,
      serverRequestEnd:     null,
      serverResponseBegin:  null,
      serverResponseEnd:    null,
      downloadLength:       null,
      uploadLength:         null,
      serverBodyLength:     null,
    }
 */

'use strict';

const http = require('http');
const path = require('path')
const fs = require('fs');
const stream = require('stream');

const hostname = '0.0.0.0';
const port = 8080;

// URLs relative to server
// See request 'end' event in http.createServer() 
const rootPath = '/';
const setupPath = '/begin';
const downloadPath = '/download'
const downreportPath = '/downreport'
const uploadPath = '/upload'
const upreportPath = '/upreport'
const pingPath = '/echo';

// running server will look for some resources arter script has completed
const scriptpath = module.filename ? module.filename : null;
const scriptdir = path.dirname(scriptpath)  // throw exception if no path
const clientPage = new URL('file://' + path.resolve(scriptdir, 'client.html'));
const echoPage = new URL('file://' + path.resolve(scriptdir, 'echo.html'));;
const e404Page = new URL('file://' + path.resolve(scriptdir, 'e404.html'))
const e418PostPage = new URL('file://' + path.resolve(scriptdir, 'e418.html'))

// defaults and range limits for numeric values
const default_config = {
  downloadLength  : 1000,       // 0000,
  uploadLength    : 120,        // 0000,
  interval        : 36          // 00
};
const range_min = {
  downloadLength  : 100,  //0000,
  uploadLength    : 50,   //0000,
  interval        : 6     //0
};
const range_max = {
  downloadLength  : 50000000,
  uploadLength    : 10000000,
  interval        : 14400
};


// asynchronous output streams.
// same destinations as console.out and console.error, which are synchronous
// timestamp any failures to aid in troubleshooting
const logStream = fs.createWriteStream('/dev/stdout', { autoClose : false });
logStream.on('error', (err) => {
  console.error({ errorTime : Date.now() });
  console.error(err);
});
const errorStream = fs.createWriteStream('/dev/stderr', { autoClose : false });
errorStream.on('error', (err) => {
  console.error({ errorTime : Date.now() });
  console.error(err);
});

// data block for large downloads of meaningless data
const tx = '012345678901234567890123456789012345678901234567890123456789012\n';
function makeDatablock()  {
  var block = [];
  var n = 256;
  while (n > 0) {
    n -= 1;
    block.push(tx);
  }
  return block.join('');
}
const datablock = makeDatablock();  // 16,384 bytes

// a Readable to generate meaningles data for large downloads
//    https://nodejs.org/api/stream.html#stream_implementing_a_readable_stream
// In node.js 12.3.0 or later, this could be replaced by stream/Readable.from()
class DataStream extends stream.Readable  {
  constructor(size) {   // size of download to send
    super();
    this.n = size;
    this.b = datablock.length;
  }
  // function used to request that more data be placed in buffer
  // data is "pushed" into a buffer to make it available from the reader
  _read(size) {   // recommended size (ignored) for next block of data
    while (this.n > this.b)  {
      this.n -= this.b;
      if (!this.push(datablock))  {   // if (expandable) buffer "full"
        return;                       //    wait for more data to be read
      }
    }
    this.push(datablock.slice(0, this.n));  // last block, may be zero length
    this.push(null);  // end of data
  }
};

// I'm alive!
function showRequest(req, res, info)  {
  res.write('method=' + req.method + '\n');
  res.write('url=' +  req.url +'\n');
  res.write(JSON.stringify(info) + '\n')
  res.write(JSON.stringify(req.socket.remoteAddress) + '\n');
}

function checkInfoRange(info) {
  // default test parameters if not set by client, or if out-of-range
  for (let name in default_config)  {  // fix missing or out-of-range items
    if (info[name] == null
        || ! isNaN(parseInt(default_config[name]))
        && isNaN(parseInt(info[name]))) {
      info[name] = default_config[name];
    }
    if (! isNaN(parseInt(default_config[name])))  { // for numeric values
      if (info[name] < range_min[name]) {           // check not too low
        info[name] = range_min[name];
      }
      if (info[name] > range_max[name]) {           // check not too high
        info[name] = range_max[name];
      }
    }
  }
  return info;    // is original reference, to modified object
}

// send a file as a complete reply
function sendFile(req, res, info, filePath, contentType)  {
  const fileStream = fs.createReadStream(filePath)

  res.setHeader('Content-Type', contentType);

  fileStream.on('error', (err) => {
    // onstall error handler before any other handler
    errorStream.write(JSON.stringify(err));

  }).on('end', () => {
    res.end();

  }).on('data', (chunk) => {
    // install data handler last so that ReadStream will not go into
    // "flow mode" until all the other handlers have been installed.
    res.write(chunk);
  });
}

// send a web page as a complete reply
function sendPage(req, res, info, pagePath) {
  sendFile(req, res, info, pagePath, 'text/html');
}

// reply to a request for page that does not exist
function reply_404(req, res, info)  {
  info.error = { 'errorTime' : Date.now(), 'err' : 'NotFound' } 
  res.statusCode = 404;
  sendPage(req, res, info, e404Page);
};

// reply to a request that did not use (required) POST method
function reply_418Post(req, res, info)  {
  info.error = { 'errorTime' : Date.now(), 'err' : 'POST method required' } 
  res.statusCode = 418;  // "I'm a teapost"  rfc2324
  res.statusMessage = "This URL requires 'POST' method"; 
  sendPage(req, res, info, e418PostPage);
};

// reply to request for the normal web interface
function reply_slash(req, res, info)  {
  sendPage(req, res, info, clientPage);
};

// reply to request for a development and test web interface
function reply_echo(req, res, info)  {
  sendPage(req, res, info, echoPage);
}

// reply to client request to start a run of tests.
// check parameters, revise as needed, return updated parameters
function reply_begin(req, res, info)  {
  res.setHeader('Content-Type', 'application/json');
  // default test identifier if not set by client
  info.testID = (info.externalIP + '-' + info.serverTimestamp + '-'
                      + ('00' + Math.floor(Math.random() * 1000)).slice(-3));
  info.testBegin = info.serverTimestamp;
  checkInfoRange(info);
  res.write(JSON.stringify(info));
  res.end();
  // info will be written to logStream when the response is finished.
};

// reply to a data download request, send requested length of meaningless data
function reply_download(req, res, info)  {
  var downloadLength = parseInt(info.downloadLength);
  var datastream = new DataStream(downloadLength);
  res.setHeader('Content-Type', 'application/octet');
  datastream.on('error', (err) => {
    // onstall error handler before any other handler
    errorStream.write(JSON.stringify(err));
  }).on('end', () => {
    res.end();
  });
  datastream.pipe(res);
};

// reply to a download report from a client
function reply_downreport(req, res, info)  {
  res.setHeader('Content-Type', 'application/json');
  res.write(JSON.stringify(info));
  res.end();
};

// reply to a data upload from a client
function reply_upload (req, res, info, body)  {
  res.setHeader('Content-Type', 'application/json');
  info.uploadLength = body.size;
  res.write(JSON.stringify(info));
  res.end();
};

// reply to a upload report from a client
function reply_upreport(req, res, info)  {
  res.setHeader('Content-Type', 'application/json');
  res.write(JSON.stringify(info));
  res.end();
};

const server = http.createServer((req, res) => {

  // respond to one incoming request

  const timestamp = Date.now();
  const url = new URL('http://' + hostname + req.url);
  const pathname = url.pathname;
  // References to info object will be passed to various functions, which will
  // modify the object.  This places the object within the scope of the other
  // functions without putting the object itself into the global scope.
  var info = {};
  var body = '';
  var bodyLength = 0;
  var bodychunks = [];

  // response event handlers

  res.on('error', (err) => {
    // error handler should be in place before any other handler
    logStream.write(JSON.stringify(
      { clientIP  : this.socket.remoteAddress,
        errorTime : Date.now(),
        error     : err
      }) + '\n');

  }).on('finish', () => {
    // all data has been delivered from res to OS for output to client
    info.serverResponseEnd = Date.now();
    logStream.write(JSON.stringify(info) + '\n');

  }).on('end', () => {
    ;   // all data received by res, but may still be in transit to OS
  });       // last response event handler

  // request event handlers

  req.on('error', (err) => {
    // error handler should be in place before any other handler
    logStream.write(JSON.stringify(
      { clientIP  : this.socket.remoteAddress,
        errorTime : Date.now(),
        error     : err
      }) + '\n');

  }).on('end', () => {
    // body data (if any) has been completely read from reg 

    var requestEnd = Date.now();
    body = bodychunks.join('');
    // body = Buffer.concat(body).toString(); // https://nodejs.org/es/docs/guides/anatomy-of-an-http-transaction/
    var headers = req.headers;    // req.getHeader "not a function".
    var contentType = headers['content-type'];  // may be undefined or null
    // console.log(headers);
    // console.log(req.method);
    if (contentType && contentType.startsWith('application/json'))   {
      // Note that upload request content should not be JSON because all data
      // is discarded from the body.  See the request 'data' event for details.
      try {
        info = JSON.parse(body);  // replace empty info with incoming content
      }
      catch(error)  {
        info.error = 'Incoming data was not valid JSON';
      }
    }
    if (info.externalIP && info.externalIP != req.socket.remoteAddress) {
      // if client IP address has changed, save the old one before replacing it
      info.oldExternalIP = info.externalIP;
    }
    info.externalIP = req.socket.remoteAddress;
    info.serverTimestamp = timestamp;
    info.pathname = pathname;
    info.serverRequestBegin = timestamp;
    info.serverRequestEnd = requestEnd;
    info.serverResponseBegin = Date.now();
    info.serverBodyLength = bodyLength;

    if (pathname == rootPath)  {   // no content expected: GET, PUT, or POST
      reply_slash(req, res, info);
    }
    else if (pathname == pingPath)  {
      reply_echo(req, res, info);
    }
    else if (pathname == setupPath)  {
      if (req.method == 'POST')  {   // content is in body
        reply_begin(req, res, info);
      } else {
        reply_418Post(req, res, info);
      }
    }
    else if (pathname == downloadPath)  {
      if (req.method == 'POST')  {   // content is in body
        reply_download(req, res, info);
      } else {
        reply_418Post(req, res, info);
      }
    }
    else if (pathname == downreportPath)  {
      if (req.method == 'POST')  {   // content is in body
        reply_downreport(req, res, info);
      } else {
        reply_418Post(req, res, info);
      }
    }
    else if (pathname == uploadPath)  {
      if (req.method == 'POST')  {   // content is in body
        reply_upload(req, res, info, body);
      } else {
        reply_418Post(req, res, info);
      }
    }
    else if (pathname == upreportPath)  {
      if (req.method == 'POST')  {   // content is in body
        reply_upreport(req, res, info);
      } else {
        reply_418Post(req, res, info);
      }
    }
    else {
      reply_404(req, res, info);
    }

  }).on('data', (chunk) => {
    // should be last handler because this one puts readStream in "flow mode"
    // other handlers should be in place before input (flow mode) begins

    // count incoming POST bytes, discard if large upload
    // Note that upload content should not be JSON.
    //See the request 'end' event for details.
    if (pathname != uploadPath) { // keep POST (or PUT) data except for upload
      bodychunks.push(chunk)
    }
    bodyLength += chunk.length;        // count bytes for all data
  });       // last request event handler
});       //  end of function http.createServer((req, res)

// server event handlers

server.on('error', (err) => {
    // error handler should be in place before any other handler
    logStream.write(JSON.stringify(
      { errorTime : Date.now(),
        error     : err
      }) + '\n');

}).on('listening', () => {
  // the .listen() callback runs after this event
  const startTime = Date.now();
  logStream.write(JSON.stringify(
    { serverTimestamp : startTime,
      startTime : startTime
    }) + '\n');

});       // last server event handler

// start server

server.listen(port, hostname, () => {
  const message = (JSON.stringify({
    serverTimestamp : Date.now(),
    hostname : hostname,
    port : port,
    scriptpath : scriptpath
  }) + '\n');
  logStream.write(message);
  errorStream.write(message);

});
