# Bundler swap: rspack → Vite

A focused, ~1–2 week one-shot to replace the bundler with Vite for fast cold
starts and real HMR in development. This doc records what is already scaffolded
and the integration work that remains.

## Honest framing

The current bundler is **rspack** (`rspack.config.js`), a Rust, webpack-API
bundler — not classic Webpack. It is already fast for production builds and
already does manual code-splitting. So the win from Vite is primarily the
**dev experience** (instant server start, real module-level HMR), not a "10×
production build" — be clear about that when justifying the work.

The build command lives in the **baselayer submodule** (`baselayer/Makefile`),
so this swap spans two repos.

## What is already scaffolded (this branch)

- `vite.config.js` — production-build parity with `rspack.config.js`: entry
  (`Main.jsx`), `outDir: static/build`, `base: /static/build/`, hashed
  `*.bundle.js` names, `manualChunks` mirroring the rspack cacheGroups
  (mui/d3/plotly/vega/vendors), node polyfills (process/Buffer/path/buffer) via
  `vite-plugin-node-polyfills`, aliases (`baselayer`, the grid/resizable CSS),
  and a dev-server proxy stub for `/api` + `/socket.io`.
- `package.json` — adds `vite`, `@vitejs/plugin-react`,
  `vite-plugin-node-polyfills`; scripts `vite:build` and `vite:dev`.
- `baselayer/Makefile` — `bundle`/`bundle-watch` are parameterized on
  `BUNDLER` (default `rspack`). `make bundle BUNDLER=vite` runs `vite build`;
  `bundle-watch BUNDLER=vite` runs `vite build --watch`. **rspack remains the
  default until the Vite build is validated**, so nothing is broken in the
  meantime. Cutover = flip the default (or delete the rspack branch).

`tools/check_js_deps.sh` (run by `make dependencies`) will want the new deps;
run `npm install` before `make run`.

## Remaining integration work (the actual 1–2 weeks)

1. **HTML + Tornado serving.** `MainPageHandler` does `self.render("index.html")`
   (Tornado template), and rspack's HtmlPlugin generates `static/index.html`
   injecting the hashed bundle. Vite emits `index.html` into `outDir`
   (`static/build/index.html`) referencing hashed assets under `base`. Decide:
   - (a) point `MainPageHandler` at `static/build/index.html`, or
   - (b) post-build step that writes the Vite-emitted HTML to `static/index.html`,
     or
   - (c) read `static/build/.vite/manifest.json` (already enabled:
     `build.manifest: true`) server-side and inject the hashed entry into the
     existing Tornado template.
   Option (c) keeps the auth-gated server render (`login.html` vs `index.html`)
   intact and is the least invasive.

2. **Dev server + HMR with the auth-gated shell.** In production the shell is
   server-rendered with auth. For dev HMR you run the Vite dev server (`vite:dev`)
   and proxy `/api` + websocket to Tornado (stub already in `vite.config.js` —
   set the target to the app's real port from `config.yaml`). The wrinkle is the
   login flow: the Vite-hosted `index.html` bypasses `MainPageHandler`. Options:
   keep auth entirely API/cookie-driven in dev, or have Vite proxy `/` to Tornado
   and use Vite only for the module graph. Wire `bundle-watch BUNDLER=vite` (or a
   new supervisor entry) so `make run` launches the dev server.

3. **CSS Modules scope difference.** rspack applies CSS Modules to *every* `.css`
   under `static/js` (see its `localIdentName`). Vite only treats `*.module.css`
   as modules by default. Audit `static/js` CSS imports: either rename
   module-used files to `*.module.css`, or add a Vite plugin that forces module
   treatment for the `static/js` globs. Plain global CSS imports (vendor CSS for
   react-grid-layout, react-resizable, react-big-calendar) must stay global.

4. **Special module handling.** rspack uses `raw-loader`, `exports-loader`,
   `imports-loader`, `json-loader` for specific deps. In Vite: JSON is native;
   raw text uses the `?raw` import suffix; `exports-loader`/`imports-loader`
   usages (legacy globals — check `kapsule`, `underscore.template`, `timezone`,
   `dygraphs`) need per-case shims or small wrapper modules. Grep the rspack
   loader rules and the imports they target, and convert each.

5. **Polyfills.** Confirm `vite-plugin-node-polyfills` covers everything the
   rspack `ProvidePlugin(process/Buffer)`, `resolve.fallback`
   (path/buffer/url:false), and the `node:` `NormalModuleReplacementPlugin` did.
   With Vite/esbuild's modern target, the `core-js/stable` +
   `regenerator-runtime` entry polyfills can likely be dropped — verify against
   the supported-browser matrix first.

6. **Validation.** `make bundle BUNDLER=vite` must produce a bundle Tornado
   serves identically; then run the full frontend Selenium suite (the real
   regression gate). Keep rspack as the default until that passes, then cut over
   and remove `rspack.config.js` + the rspack deps in a dedicated PR.

## Interaction with the TypeScript migration

Independent of this swap — esbuild (Vite) strips TS types just like babel does
under rspack, so `.ts`/`.tsx` work either way. Keep type-*checking* in a separate
`tsc --noEmit` CI step regardless of bundler. See `doc/typescript_migration.md`.
