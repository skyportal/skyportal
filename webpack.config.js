const webpack = require('webpack');
const path = require('path');

const config = {
  entry: ['babel-polyfill',
          path.resolve(__dirname, 'static/js/components/Main.jsx')],
  output: {
    path: path.resolve(__dirname, 'static/build'),
    filename: 'bundle.js'
  },
  module: {
    rules: [
      { test: /\.js?$/,
        exclude: /node_modules/,
        loader: 'babel-loader',
        options:
        {
          presets: ['es2015', 'react', 'stage-2'],
          plugins: ['transform-async-to-generator'],
          compact: false
        }
      },
      { test: /\.jsx?$/,
        exclude: /node_modules/,
        loader: 'babel-loader',
        options:
        {
          presets: ['es2015', 'react', 'stage-2'],
          compact: false
        }
      },

      // Enable CSS Modules for Skyportal
      { test: /\.css$/,
        exclude: /node_modules/,
        use: [
          {
            loader: 'style-loader'
          },
          {
            loader: 'css-loader',
            options: {
              modules: true,
            }
          }
        ]
      },

      // bokehjs doesn't like css-modules, but it
      // does need style-loader and css-loader
      { test: /\.css$/,
        include: /node_modules\/bokehjs/,
        use: ['style-loader', 'css-loader']
      }
    ],
  },
  plugins: [
    new webpack.ProvidePlugin({
      fetch: 'imports-loader?this=>global!exports-loader?global.fetch!whatwg-fetch'
    }),

    // We do not use JQuery for anything in this project; but Bootstrap
    // depends on it
    new webpack.ProvidePlugin({
      $: "jquery",
      jQuery: "jquery",
    })
  ],
  resolve: {
    alias: {
      baselayer: path.resolve(__dirname, 'baselayer/static/js')
    },
    extensions: ['.js', '.jsx']
  }
};

module.exports = config;
