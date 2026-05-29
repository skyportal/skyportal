import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { nodePolyfills } from "vite-plugin-node-polyfills";
import path from "path";

// Vite replacement for rspack.config.js. This is the production-build scaffold
// for the rspack -> Vite swap; see doc/vite_migration.md for the remaining
// dev-server/HMR + Tornado-serving integration work.
//
// Parity notes vs rspack.config.js:
//   * entry            -> build.rollupOptions.input (the generated Main.jsx)
//   * output/static    -> build.outDir + base, hashed asset names
//   * splitChunks      -> build.rollupOptions.output.manualChunks
//   * ProvidePlugin    -> vite-plugin-node-polyfills (process / Buffer globals)
//   * node: rewrite,   -> vite-plugin-node-polyfills
//     path/buffer
//   * babel-loader     -> @vitejs/plugin-react (esbuild; strips TS types too)
export default defineConfig(({ mode }) => {
  const isProduction = mode === "production";
  return {
    base: "/static/build/",
    plugins: [
      react(),
      // Replaces the rspack ProvidePlugin(process/Buffer), the path/buffer
      // resolve.fallback entries, and the node: NormalModuleReplacementPlugin.
      nodePolyfills({
        include: ["buffer", "path", "process"],
        globals: { Buffer: true, process: true },
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
    },
    css: {
      // rspack applies CSS Modules to ALL *.css under static/js. Vite only
      // treats *.module.css as modules by default -- see doc/vite_migration.md
      // for the cutover options (rename to *.module.css, or a custom plugin).
      modules: {
        localsConvention: "camelCaseOnly",
        generateScopedName: "[name]__[local]--[hash:base64:5]",
      },
    },
    build: {
      outDir: path.resolve(__dirname, "static/build"),
      emptyOutDir: true,
      // Match Tornado's expectation of /static/build/*.bundle.js (and an
      // index.html that MainPageHandler can render). See migration doc.
      manifest: true,
      sourcemap: true,
      rollupOptions: {
        input: path.resolve(
          __dirname,
          "static/js/components/templates/Main.jsx",
        ),
        output: {
          entryFileNames: "[name].[hash].bundle.js",
          chunkFileNames: "[name].[hash].bundle.js",
          assetFileNames: "[name].[hash][extname]",
          // Mirror of rspack's splitChunks cacheGroups.
          manualChunks(id) {
            if (!id.includes("node_modules")) return undefined;
            if (/[\\/]node_modules[\\/]@mui[\\/]/.test(id)) return "mui";
            if (/[\\/]node_modules[\\/]d3(?:-|[\\/])/.test(id)) return "d3";
            if (/[\\/]node_modules[\\/]plotly/.test(id)) return "plotly";
            if (/[\\/]node_modules[\\/]vega(?:-|[\\/])/.test(id)) return "vega";
            return "vendors";
          },
        },
      },
      minify: isProduction ? "esbuild" : false,
    },
    server: {
      // Dev only. Proxy the API + websocket to the running Tornado app so the
      // Vite dev server (with HMR) can host the SPA. Port/targets must match
      // the app's config.yaml; see doc/vite_migration.md.
      proxy: {
        "/api": { target: "http://localhost:5000", changeOrigin: true },
        "/socket.io": {
          target: "http://localhost:5000",
          ws: true,
          changeOrigin: true,
        },
      },
    },
  };
});
