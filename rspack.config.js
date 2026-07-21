const path = require("path");
const rspack = require("@rspack/core");

// const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

const config = (env, argv) => {
  const isProduction = argv?.mode === "production";
  return {
    entry: {
      main: path.resolve(__dirname, "static/js/components/templates/Main.tsx"),
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
          // `chunks: "initial"` keeps the big shared vendors chunk to only the
          // libs reached on first paint. Modules used solely by lazy routes
          // (mathjs, dygraphs, moment, react-big-calendar, @rjsf/*, etc.) stay
          // in their own async chunks instead of being shipped on initial load.
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: "vendors",
            chunks: "initial",
            priority: 10,
          },
          // `chunks: "initial"` so MUI modules only reached by lazy routes
          // (e.g. @mui/x-data-grid in Sources/Candidates pages) stay async
          // instead of being pulled into the initial mui chunk.
          mui: {
            test: /[\\/]node_modules[\\/]@mui[\\/]/,
            name: "mui",
            chunks: "initial",
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
        // Transform JS/TS with rspack's built-in Rust/SWC loader. Type
        // *checking* remains a separate `tsc --noEmit` step.
        //
        // `jsc.target: "es2020"` covers all browsers from ~2020+ natively (async/await,
        // optional chaining, nullish coalescing, Promise, etc.), so the entry no longer
        // needs `core-js/stable` + `regenerator-runtime/runtime` polyfills. This also
        // restores `const`/`let` TDZ semantics — if a binding is read before init it
        // throws `ReferenceError` instead of returning `undefined` (the ES5 lowering
        // hid these as latent bugs).
        {
          // TypeScript / TSX
          test: /\.tsx?$/,
          loader: "builtin:swc-loader",
          include: /static\/js/,
          exclude: /node_modules/,
          options: {
            jsc: {
              parser: { syntax: "typescript", tsx: true },
              transform: { react: { runtime: "automatic" } },
              target: "es2020",
            },
          },
        },
        {
          // JavaScript / JSX
          test: /\.jsx?$/,
          loader: "builtin:swc-loader",
          include: /static\/js/,
          exclude: /node_modules/,
          options: {
            jsc: {
              parser: { syntax: "ecmascript", jsx: true },
              transform: { react: { runtime: "automatic" } },
              target: "es2020",
            },
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
        // Global (non-module) CSS for the broker filter builder's equation
        // rendering/editing (react-latex-next -> katex, equation-editor-react
        // -> mathquill).
        {
          test: /\.css$/,
          include: [
            /node_modules\/katex\/dist/,
            /node_modules\/mathquill\/build/,
          ],
          use: ["style-loader", "css-loader"],
        },
        // Emit font files referenced by the above stylesheets (KaTeX/Symbola).
        {
          test: /\.(woff2?|ttf|eot|otf)$/,
          type: "asset/resource",
        },
      ],
    },
    plugins: [
      // Uncomment the following line to enable bundle size analysis
      // new BundleAnalyzerPlugin(),
      // Drop moment's per-locale string files (es, fr, ja, ...) — SkyPortal only
      // formats dates in English. Saves ~600 KB on pages that pull in moment
      // (notably `ShiftCalendar` via react-big-calendar). Does NOT affect
      // timezone math: that comes from `moment-timezone`, which is not a dep.
      new rspack.IgnorePlugin({
        resourceRegExp: /^\.\/locale$/,
        contextRegExp: /moment$/,
      }),
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
        // Some transitive deps still ship CJS lodash; alias to lodash-es so
        // both versions dedupe and the ES tree-shakes properly.
        lodash: "lodash-es",
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
