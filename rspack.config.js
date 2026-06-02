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
        {
          // TypeScript / TSX
          test: /\.tsx?$/,
          loader: "builtin:swc-loader",
          include: /static\/js/,
          exclude: /node_modules/,
          options: {
            jsc: {
              parser: { syntax: "typescript", tsx: true },
              transform: {
                react: {
                  // matches @babel/preset-react default (React must be in scope)
                  runtime: "classic",
                  development: false,
                  refresh: false,
                },
              },
              // class-properties, object-rest-spread, arrow fns, async→generator
              // are all handled by lowering to the env targets below; no
              // per-feature plugins needed. (`jsc.target` is intentionally
              // omitted: SWC forbids it alongside `env`, which drives lowering.)
              externalHelpers: false,
              loose: false,
            },
            // Browser polyfill + lowering behavior (replaces @babel/preset-env's
            // job). The entry still imports core-js/stable + regenerator-runtime,
            // so use mode "entry" for byte-for-runtime-behavior parity.
            env: {
              mode: "entry",
              coreJs: "3",
              targets: "defaults",
            },
          },
        },
        {
          // Plain JS / JSX
          test: /\.jsx?$/,
          loader: "builtin:swc-loader",
          include: /static\/js/,
          exclude: /node_modules/,
          options: {
            jsc: {
              parser: { syntax: "ecmascript", jsx: true },
              transform: {
                react: {
                  runtime: "classic",
                  development: false,
                  refresh: false,
                },
              },
            },
            env: { mode: "entry", coreJs: "3", targets: "defaults" },
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
