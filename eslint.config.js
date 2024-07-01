// eslint.config.js
const global = require("globals");

const reactPlugin = require("eslint-plugin-react");
const prettierPlugin = require("eslint-config-prettier");
const importPlugin = require("eslint-plugin-import");
const reactHookPlugin = require("eslint-plugin-react-hooks");
const airbnbPlugin = require("eslint-config-airbnb");

const { fixupPluginRules } = require("@eslint/compat");

module.exports = [
  { files: ["static/**/*.js", "static/**/*.jsx"] },
  { ignores: ["docs/*"] },
  {
    languageOptions: {
      parser: require("@babel/eslint-parser"),
      parserOptions: {
        requireConfigFile: false,
        babelOptions: {
          presets: ["@babel/preset-env", "@babel/preset-react"],
        },
      },
      globals: {
        ...global.browser,
      },
    },
  },
  {
    plugins: {
      import: importPlugin,
      react: reactPlugin,
      "react-hooks": fixupPluginRules(reactHookPlugin),
      airbnb: airbnbPlugin,
      prettier: prettierPlugin,
    },
  },
  {
    rules: {
      camelcase: "off",
      "jsx-a11y/click-events-have-key-events": 0,
      "jsx-a11y/label-has-associated-control": 0,
      "jsx-a11y/control-has-associated-label": 0,
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "react/jsx-wrap-multilines": 0,
      "react/jsx-one-expression-per-line": 0,
      "react/jsx-props-no-spreading": 0,
      "no-param-reassign": 0,
      "react/jsx-curly-newline": 0,
    },
  },
  {
    settings: {
      import: {
        resolver: {
          node: {},
          webpack: {
            config: "webpack.config.js",
          },
        },
      },
      react: {
        version: "detect",
      },
    },
  },
];
