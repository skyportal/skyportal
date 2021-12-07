const path = require("path");
const TsconfigPathsPlugin = require("tsconfig-paths-webpack-plugin");

// const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

const config = {
  entry: {
    main: [
      "@babel/polyfill",
      path.resolve(
        __dirname,
        "static/transpiled/static/js/components/Main.jsx"
      ),
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
        include: [/static\/transpiled/, /static\/js/],
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
      // For Bokeh's "export * from y" syntax
      {
        test: /\.js?$/,
        include: /node_modules\/@bokeh/,
        use: [
          {
            loader: "babel-loader",
            options: {
              plugins: [
                "@babel/plugin-proposal-export-namespace-from",
                "@babel/plugin-proposal-optional-chaining",
                "@babel/plugin-proposal-nullish-coalescing-operator",
              ],
            },
          },
        ],
      },
      // Enable CSS Modules for Skyportal
      {
        test: /\.css$/,
        include: [/static\/transpiled/, /node_modules\/react-datepicker\/dist/],
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
    ],
  },
  plugins: [
    // Uncomment the following line to enable bundle size analysis
    //    new BundleAnalyzerPlugin()
  ],
  resolve: {
    plugins: [
      new TsconfigPathsPlugin({ extensions: [".ts", ".tsx", ".js", ".jsx"] }),
    ],
    alias: {
      baselayer: path.resolve(__dirname, "baselayer/static/js"),
      reactgridlayoutcss: path.resolve(
        __dirname,
        "node_modules/react-grid-layout/css"
      ),
      reactresizablecss: path.resolve(
        __dirname,
        "node_modules/react-resizable/css"
      ),
      bokehjs: path.resolve(
        __dirname,
        "node_modules/@bokeh/bokehjs/build/js/lib"
      ),
    },
    extensions: [".js", ".jsx", ".json"],
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
