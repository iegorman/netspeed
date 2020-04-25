#!/usr/bin/node
// node.js demo -- using a generator function

'use strict';   // disable some of the ways to make mistakes in javascript

function* generate(n)  {
  var i = 0;
  while (i < n)  {
    yield i;
    i += 1;
  }
}

console.log('start');

// implicit iteration over generator
for (let j of generate(5)) {
  console.log(j);
}

console.log('next()');

// wxplicit iteration over generator
const iter = generate(4);
var item = iter.next();
while (!item.done)  {
  console.log(item.value);
  item = iter.next();
}

console.log('end');
