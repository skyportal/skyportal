// Ambient module declarations for third-party packages that ship no TypeScript
// types of their own. Declaring them here (implicitly typed `any`) lets us turn
// on `noImplicitAny` without a wall of TS7016 "could not find a declaration
// file" errors, and without pulling in @types packages.
//
// Note: several of these DO have community types available (@types/papaparse,
// @types/d3, @types/numeral, @types/react-grid-layout, @types/react-big-calendar,
// @types/dygraphs) and could be tightened to real types later.
declare module "react-plotly.js/factory";
declare module "plotly.js-basic-dist";
declare module "emoji-dictionary";
declare module "react-simple-maps";
declare module "papaparse";
declare module "d3";
declare module "versor";
declare module "redux-state-sync";
declare module "react-json-dashboard";
declare module "react-grid-layout";
declare module "react-big-calendar";
declare module "numeral";
declare module "dygraphs";
declare module "d3-geo-projection";
declare module "convert-css-length";
