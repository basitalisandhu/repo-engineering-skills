const { a } = require('./a');
export function b() { return typeof a === 'function' ? 1 : 0; }
