#!/usr/bin/node
// node.js server to respond to internet requests
//


'use strict';

const http = require('http');

const hostname = '0.0.0.0';
const port = 8080;
const maxBodySave = 1024;   // discard tail end of large bodies (POST, PUT)

// convert a query string to a javascript object
const queryToObject = (query) => {
  const params = new URLSearchParams(query);
  var paramobject = {};
  for (const [name, value] of params) {
      paramobject[name] = value;
  }
  return paramobject
};

const server = http.createServer((request, response) => {
  // const { headers, method, url } = request;
  const url = new URL('http://' + hostname + request.url);
  const pathname = url.pathname;
  const params = queryToObject(url.search);
  var chunks = [];
  var datacount = 0;

  request.on('error', (err) => {

    console.error(err);

  }).on('end', () => {

    // response.write(JSON.stringify(request.headers));
    { // sort and print headers
      let names = []
      for (let name in request.headers){
        names.push(name);
      }
      for (let name of names.sort())  {
        response.write(name + ': ' + request.headers[name] + '\n');
      }
    }
    response.write('url=' +  request.url +'\n');
    response.write('method=' + request.method + '\n');
    response.write('socket=' + JSON.stringify(request.socket.address()) + '\n');
    response.write('queryparams=' + JSON.stringify(params) + '\n');
    response.write('datacount=' +  datacount +'\n');
    response.write('Boo! Meringue.\n');
    let data = chunks.join('').slice(maxBodySave);
    response.write(data);

    response.end();
  }).on('data', (chunk) => {

    // count incoming POST bytes, discard
    if (datacount < maxBodySave) {
      chunks.push(chunk)
    }
    datacount += chunk.length;

  });
});

server.listen(port, hostname, () => {
  console.log(`Server running at http://${hostname}:${port}/`);
});