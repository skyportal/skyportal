const path = require("path");
const webpack = require("webpack");

// const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

const config = {
  entry: {
    main: [
      "@babel/polyfill",
      path.resolve(__dirname, "static/js/components/templates/Main.jsx"),
    ],
  },
  output: {
    path: path.resolve(__dirname, "static/build"),
    publicPath: "/static/build/",
    filename: "[name].bundle.js",
    chunkFilename: "[name].[contenthash].bundle.js",
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)?$/,
        loader: "babel-loader",
        include: /static\/js/,
        exclude: /node_modules/,
        options: {
          presets: ["@babel/preset-env", "@babel/preset-react"],
          plugins: [
            "@babel/plugin-transform-async-to-generator",
            "@babel/plugin-transform-arrow-functions",
            "@babel/plugin-proposal-class-properties",
            "@babel/plugin-proposal-object-rest-spread",
          ],
          compact: false,
        },
      },
      // Enable CSS Modules for Skyportal
      {
        test: /\.css$/,
        include: [/static\/js/, /node_modules\/react-datepicker\/dist/],
        use: [
          {
            loader: "style-loader",
          },
          {
            loader: "css-loader",
            options: {
              modules: {
                localIdentName: "[path][name]__[local]--[hash:base64:5]",
              },
            },
          },
        ],
      },

      // react-grid-layout for Home page
      {
        test: /\.css$/,
        include: /node_modules\/react-grid-layout\/css/,
        use: ["style-loader", "css-loader"],
      },
      {
        test: /\.css$/,
        include: /node_modules\/react-resizable\/css/,
        use: ["style-loader", "css-loader"],
      },
      {
        test: /\.css$/,
        include: /node_modules\/react-big-calendar\/lib\/css/,
        use: ["style-loader", "css-loader"],
      },
    ],
  },
  plugins: [
    // Uncomment the following line to enable bundle size analysis
    // new BundleAnalyzerPlugin(),
    // Needed for non-polyfilled node modules; we aim to remove this when possible
    new webpack.ProvidePlugin({
      process: path.resolve(__dirname, "node_modules/process/browser.js"),
    }),
    new webpack.ProvidePlugin({
      Buffer: ["buffer", "Buffer"],
    }),
    new webpack.NormalModuleReplacementPlugin(/^node:/, (resource) => {
      resource.request = resource.request.replace(/^node:/, "");
    }),
  ],
  resolve: {
    alias: {
      baselayer: path.resolve(__dirname, "baselayer/static/js"),
      reactgridlayoutcss: path.resolve(
        __dirname,
        "node_modules/react-grid-layout/css",
      ),
      reactresizablecss: path.resolve(
        __dirname,
        "node_modules/react-resizable/css",
      ),
    },
    extensions: [".js", ".jsx", ".json"],
    // Needed for non-polyfilled node modules; we aim to remove this when possible
    fallback: {
      path: path.resolve(__dirname, "node_modules/path-browserify"),
      buffer: path.resolve(__dirname, "node_modules/buffer"),
      url: false,
    },
  },

  watchOptions: {
    ignored: /node_modules/,
    // Set to true if you have trouble with JS change monitoring
    poll: false,
  },
  mode: "development",
  devtool: "eval-source-map",
};

module.exports = config;
