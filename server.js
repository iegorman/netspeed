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

  Memory requirements are almost independed of upload and download sizes.
  Download data is provided from a stream.Reader that produces any amount of
  data.  Upload data is discarded, except for a small amount sufficient to hold
  any expected JSON data.

  The server and client communicate by sending JSON objects back and forth.
  No message is sent to the client in response to a download request because
  the body of the response is the download data.
  No message is sent from the client in an upload request because the body of
  the request is the upload data.

  The server is expected to keep running no matter what request it redeives and
  may not give the client full information about why a request failed. The
  server reports failures to a local log.

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
      clientReceiveLength:  null,
      serverReceiveLength:  null,
      downloadReceiveLength: null,
      uploadReceiveLength:  null,
      error:                null,
    }
 */

'use strict';

const http = require('http');
const path = require('path')
const fs = require('fs');
const stream = require('stream');

const hostname = '0.0.0.0';
const port = 8080;
const jsonLengthLimit = 2048;   // max length of JSON text in a POST body

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
const e400Page = new URL('file://' + path.resolve(scriptdir, 'e400.html'))
const e404Page = new URL('file://' + path.resolve(scriptdir, 'e404.html'))
const e418PostPage = new URL('file://' + path.resolve(scriptdir, 'e418.html'))

// asynchronous output, console.log may be synchronous
// see  https://nodejs.org/api/process.html#process_a_note_on_process_i_o
//      https://nodejs.org/api/console.html
// timestamp any failures to aid in troubleshooting
const logStream = fs.createWriteStream('/dev/stdout', { autoClose : false });
logStream.on('error', (err) => {
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

// Readable to produce specified amount of meaningless data for large downloads
//    https://nodejs.org/api/stream.html#stream_implementing_a_readable_stream
//    https://nodejs.org/en/docs/guides/backpressuring-in-streams/
class DataStream extends stream.Readable  {
  constructor(size) {   // size of download to send
    super();
    this.n = size;
    this.chunk = datablock;
    this.chunkLength = this.chunk.length;
  }

  // function used to request that more data be placed in buffer
  // data is "pushed" into a buffer to make it available from the reader
  _read(size) {
    // chunk length > 0, <= unused buffer space, <= available data chunk
    var len = Math.max(1, Math.min(size, this.chunkLength));
    while (this.n > len)  {
      this.n -= len;
      if (!this.push(this.chunk))  {
        return;         // buffer temporarily full
      }
    }
    this.push(this.chunk.slice(0, this.n));  // last block, may be zero length
    this.push(null);  // no more data available
  }
};

// I'm alive!
function showRequest(req, res, info)  {
  res.write('method=' + req.method + '\n');
  res.write('url=' +  req.url +'\n');
  res.write(JSON.stringify(info) + '\n')
  res.write(JSON.stringify(req.socket.remoteAddress) + '\n');
}

// send a file as a complete reply
function sendFile(req, res, info, filePath, contentType)  {
  const fileStream = fs.createReadStream(filePath)

  res.setHeader('Content-Type', contentType);

  fileStream.on('error', (err) => {
    // install error handler before any other handler
    console.error(err);

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

// reply to a request with invalid or unacceptable data
function reply_400(req, res, info)  {
  res.statusCode = 400;
  sendPage(req, res, info, e400Page);
};

// reply to a request for page that does not exist
function reply_404(req, res, info)  {
  res.statusCode = 404;
  sendPage(req, res, info, e404Page);
};

// reply to a request that did not use (required) POST method
function reply_418Post(req, res, info)  {
  info.error = '418 POST method required';
  res.statusCode = 418;  // "I'm a teapot"    rfc2324
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
  if (! info.testID) {
    info.testID = (info.externalIP + '-' + info.serverTimestamp + '-'
                      + ('00' + Math.floor(Math.random() * 1000)).slice(-3));
  }
  info.testBegin = info.serverTimestamp;
  res.write(JSON.stringify(info));
  res.end();
  // info will be written to logStream when the response is finished.
};

// reply to a data download request, send requested length of meaningless data
function reply_download(req, res, info)  {
  var downloadLength = parseInt(info.downloadLength);
  if (isNaN(downloadLength) || downloadLength < 1)  {
    info.error = '400 Invalid length for download';
    return reply_400(req, res, info); // null return but will invoke res.end() 
  }
  var datastream = new DataStream(downloadLength);
  res.setHeader('Content-Type', 'application/octet');
  datastream.on('error', (err) => {
    // install error handler before any other handler
    console.error(err);
  }).on('end', () => {
    res.end();
  });
  datastream.pipe(res);   // event handler will invoke res.end() 
};

// reply to a download report from a client
function reply_downreport(req, res, info)  {
  res.setHeader('Content-Type', 'application/json');
  res.write(JSON.stringify(info));
  res.end();
};

// reply to a data upload from a client
function reply_upload (req, res, info)  {
  res.setHeader('Content-Type', 'application/json');
  info.uploadReceiveLength = info.serverReceiveLength
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
        info.externalIP = req.socket.remoteAddress;
        info.serverTimestamp = timestamp;
        info.pathname = pathname;
        info.error = '400 Incoming data was not valid JSON';
        return reply_400(req, res, info);   // null
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
    info.serverReceiveLength = bodyLength;

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
        reply_upload(req, res, info);
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
      info.error = '404 Page Not Found';
      reply_404(req, res, info);
    }

  }).on('data', (chunk) => {
    // should be last handler because this one puts readStream in "flow mode"
    // other handlers should be in place before input (flow mode) begins

    // count incoming POST bytes, keep only enough bytes for expected JSON data
    // Note that upload content should not be JSON, all will be discarded
    //See the request 'end' event for details.
    var headers = req.headers;    // req.getHeader "not a function".
    var contentType = headers['content-type'];  // may be undefined or null
    if (contentType && contentType.startsWith('application/json')
                    && bodyLength < jsonLengthLimit)   {
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
  console.error(message);

});
