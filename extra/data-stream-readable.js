#!/usr/bin/node
// node.js demo -- how to create a stream.Readable from any source of bytes.

// Run this script in Node.js to generate data.
// Uses console.log to show when things are actually done.
// Set a small number of bytes to run a simple display to a terminal.
// Set bytesize to a large value and redirect to a file to see what happens
// when there is more data than the default buffer can hold.

'use strict';   // disable some of the ways to make mistakes in javascript

const stream = require('stream');

var bytesize = 37;  // number of bytes to produce

// Readable to produce a specified number of bytes
//    https://nodejs.org/api/stream.html#stream_implementing_a_readable_stream
//    https://nodejs.org/en/docs/guides/backpressuring-in-streams/
class DataStream extends stream.Readable  {

  // Set up, save any information needed for producing the data.
  constructor(datalength) {
    console.log('constuctor');  // for demo
    super();
    this.datablock = 'ABCDEFGHIJ';
    this.blocklength = this.datablock.length;
    this.n = datalength;    // number of bytes to produce
  }

  // Do first, next, or last data transfer.
  _read(size) {
    console.log('_read(', size, ')')  // for demo
    var len = Math.max(0, Math.min(size, this.blocklength));
    while (this.n > len)  {
      this.n -= len;
      if (! this.push(this.datablock))  {
        console.log('full, n = ', this.n)   // for demo
        return; // buffer is temporarily full
      }
    }
    console.log('end of data');   // for demo
    // last transfer, which may be anything from zero length to a full block
    this.push(this.datablock.slice(0, this.n));
    console.log('close');   // for demo
    // indicate no more data, so that Reader will produce EOF
    this.push(null);
  }
};

// Create the new Readable as a source for the requested number of bytes.
var datastream = new DataStream(bytesize);

// event handlers for the Readable
datastream.on('error', (e) => {
  // handle any errors, perhaps by simply reporting them
  console.log(e)
}).on('end', () => {
  // do anything needed when all the data has been read
  console.log('EOF')    // for demo
}).on('data', (chunk) => {
  // Handle the data when it is receiveed (possibly in separate chunks).
  console.log('chunk');   // for demo
  console.log(chunk);     // do something with the data
});

// These will output before any of the data from the Readable because the
// Readable has be set up (with event handlers) to run in the background.
console.log('end of main script');  // for demo
console.log(process.argv);          // for demo