const path = require("path");
const rspack = require("@rspack/core");

// const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

const config = (env, argv) => {
  const isProduction = argv?.mode === "production";
  return {
    entry: {
      main: [
        "core-js/stable",
        "regenerator-runtime/runtime",
        path.resolve(__dirname, "static/js/components/templates/Main.tsx"),
      ],
    },
    output: {
      path: path.resolve(__dirname, "static/build"),
      publicPath: "/static/build/",
      filename: "[name].[contenthash].bundle.js",
      chunkFilename: "[name].[contenthash].bundle.js",
      clean: true,
    },
    optimization: {
      splitChunks: {
        chunks: "all",
        cacheGroups: {
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: "vendors",
            chunks: "all",
            priority: 10,
          },
          mui: {
            test: /[\\/]node_modules[\\/]@mui[\\/]/,
            name: "mui",
            chunks: "all",
            priority: 20,
          },
          d3: {
            test: /[\\/]node_modules[\\/]d3(?:-|[\\/])/,
            name: "d3",
            chunks: "all",
            priority: 20,
          },
          plotly: {
            test: /[\\/]node_modules[\\/]plotly[\\.]/,
            name: "plotly",
            chunks: "all",
            priority: 20,
          },
          vega: {
            test: /[\\/]node_modules[\\/]vega(?:-|[\\/])/,
            name: "vega",
            chunks: "all",
            priority: 20,
          },
        },
      },
      runtimeChunk: "single",
    },
    module: {
      rules: [
        // Transform JS/TS with rspack's built-in Rust/SWC loader instead of
        // babel-loader. SWC needs an explicit parser per syntax, so this is
        // split into two rules (TS/TSX and JS/JSX). Type *checking* remains a
        // separate `tsc --noEmit` step (npm run typecheck); SWC, like the old
        // @babel/preset-typescript, only strips types during bundling.
        //
        // `jsc.target: "es5"` reproduces what @babel/preset-env emitted here:
        // with no `targets`/browserslist configured, preset-env lowers all
        // ES2015+ down to ES5. Matching that target is deliberate — it keeps
        // runtime behavior identical (e.g. `const`/`let` lower to hoisted `var`,
        // so code that reads a not-yet-initialized binding gets `undefined`
        // instead of a TDZ ReferenceError). A more modern target would change
        // that behavior and surface latent bugs. No `env` block is used: like
        // preset-env's default `useBuiltIns: false`, polyfills come solely from
        // the `core-js/stable` + `regenerator-runtime/runtime` entry imports,
        // not per-file/usage injection.
        {
          // TypeScript / TSX
          test: /\.tsx?$/,
          loader: "builtin:swc-loader",
          include: /static\/js/,
          exclude: /node_modules/,
          options: {
            presets: [
              "@babel/preset-env",
              // Use the automatic JSX runtime so `import React from "react"`
              // is no longer required in every JSX file. Matches the tsconfig
              // setting "jsx": "react-jsx".
              ["@babel/preset-react", { runtime: "automatic" }],
              // Strips TS types during bundling. Type *checking* is a separate
              // `tsc --noEmit` step (npm run typecheck), so a type error fails
              // CI without blocking local bundling.
              "@babel/preset-typescript",
            ],
            plugins: [
              "@babel/plugin-transform-async-to-generator",
              "@babel/plugin-transform-arrow-functions",
              "@babel/plugin-transform-class-properties",
              "@babel/plugin-transform-object-rest-spread",
            ],
            compact: false,
          },
        },
        // Enable CSS Modules for Skyportal
        {
          test: /\.css$/,
          include: [
            /static\/js/,
            /node_modules\/react-datepicker\/dist/,
            /node_modules\/@mui\/x-data-grid\/esm/,
          ],
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
      new rspack.HtmlRspackPlugin({
        template: "./static/index_base.html",
        filename: "../index.html",
        inject: "body",
      }),
      // Needed for non-polyfilled node modules; we aim to remove this when possible
      new rspack.ProvidePlugin({
        process: path.resolve(__dirname, "node_modules/process/browser.js"),
      }),
      new rspack.ProvidePlugin({
        Buffer: ["buffer", "Buffer"],
      }),
      new rspack.NormalModuleReplacementPlugin(/^node:/, (resource) => {
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
      extensions: [".js", ".jsx", ".ts", ".tsx", ".json"],
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
    mode: isProduction ? "production" : "development",
    devtool: isProduction ? "source-map" : "eval-source-map",
  };
};

module.exports = config;
