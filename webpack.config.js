const path = require("path");

// const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

const config = {
  entry: {
    main: [
      "@babel/polyfill",
      path.resolve(__dirname, "static/js/components/Main.jsx"),
    ],
  },
  output: {
    path: path.resolve(__dirname, "static/build"),
    publicPath: "/static/build/",
    filename: "[name].bundle.js",
    chunkFilename: "[name].[chunkHash].bundle.js",
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

      // bokehjs doesn't like css-modules, but it
      // does need style-loader and css-loader
      {
        test: /\.css$/,
        include: /node_modules\/bokehjs/,
        use: ["style-loader", "raw-loader"],
      },
      {
        test: /\.js$/,
        include: /node_modules\/bokehjs/,

        // See https://webpack.js.org/guides/shimming/
        // Bokeh needs 'this' to be defined, in part since the npm package
        // does not support the Universal Module spec
        use: "imports-loader?this=>window",
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
    ],
  },
  plugins: [
    // Uncomment the following line to enable bundle size analysis
    //    new BundleAnalyzerPlugin()
  ],
  resolve: {
    alias: {
      baselayer: path.resolve(__dirname, "baselayer/static/js"),
      bokehjs: path.resolve(__dirname, "node_modules/bokehjs/build/js"),
      bokehcss: path.resolve(__dirname, "node_modules/bokehjs/build/css"),
      reactgridlayoutcss: path.resolve(
        __dirname,
        "node_modules/react-grid-layout/css"
      ),
      reactresizablecss: path.resolve(
        __dirname,
        "node_modules/react-resizable/css"
      ),
    },
    extensions: [".js", ".jsx"],
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
