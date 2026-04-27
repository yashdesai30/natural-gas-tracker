const path = require('path');
/** @type {import('next').NextConfig} */
module.exports = {
  turbopack: {
    root: __dirname, // absolute path works as well: path.resolve(__dirname)
  },
};
