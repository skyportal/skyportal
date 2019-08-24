const webpack = require('webpack');
const path = require('path');

const config = {
  entry: [
    'babel-polyfill',
    path.resolve(__dirname, 'static/js/components/Main.jsx')
  ],
  output: {
    path: path.resolve(__dirname, 'static/build'),
    filename: 'bundle.js'
  },
  module: {
    rules: [
      {
        test: /\.js?$/,
        include: /static\/js/,
        loader: 'babel-loader',
        options:
        {
          presets: ['env'],
          plugins: [
            'transform-object-rest-spread',
            'transform-async-to-generator',
            'transform-es2015-arrow-functions',
            'transform-class-properties'
          ],
          compact: false
        }
      },

      {
        test: /\.jsx?$/,
        include: /static\/js/,
        loader: 'babel-loader',
        options:
        {
          presets: ['env', 'react'],
          plugins: [
            'transform-object-rest-spread',
            'transform-async-to-generator',
            'transform-es2015-arrow-functions',
            'transform-class-properties'
          ],
          compact: false
        }
      },

      // Enable CSS Modules for Skyportal
      {
        test: /\.css$/,
        include: /static\/js/,
        use: [
          {
            loader: 'style-loader'
          },
          {
            loader: 'css-loader',
            options: {
              modules: true,
              localIdentName: '[path][name]__[local]--[hash:base64:5]'
            }
          }
        ]
      },

      // bokehjs doesn't like css-modules, but it
      // does need style-loader and css-loader
      {
        test: /\.css$/,
        include: /node_modules\/bokehjs/,
        use: ['style-loader', 'raw-loader']
      },
      {
        test: /\.js$/,
        include: /node_modules\/bokehjs/,

        // See https://webpack.js.org/guides/shimming/
        // Bokeh needs 'this' to be defined, in part since the npm package
        // does not support the Universal Module spec
        use: 'imports-loader?this=>window'
      }

    ]
  },
  plugins: [
    new webpack.ProvidePlugin({
      fetch: 'imports-loader?this=>global!exports-loader?global.fetch!whatwg-fetch'
    }),

    // We do not use JQuery for anything in this project; but Bootstrap
    // depends on it
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery'
    }),

  ],
  resolve: {
    alias: {
      baselayer: path.resolve(__dirname, 'baselayer/static/js'),
      bokehjs: path.resolve(__dirname, 'node_modules/bokehjs/build/js'),
      bokehcss: path.resolve(__dirname, 'node_modules/bokehjs/build/css')
    },
    extensions: ['.js', '.jsx']
  }
};

module.exports = config;
