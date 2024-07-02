// eslint.config.js
const global = require("globals");
const eslint = require("@eslint/js");

const reactPlugin = require("eslint-plugin-react");
const prettierPlugin = require("eslint-config-prettier");
const importPlugin = require("eslint-plugin-import");
const reactHookPlugin = require("eslint-plugin-react-hooks");
const airbnbPlugin = require("eslint-config-airbnb");

const { fixupPluginRules } = require("@eslint/compat");

module.exports = [
  eslint.configs.recommended,
  // run on all js and jsx files in the static directory and subdirectories
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
        ecmaFeatures: {
          jsx: true,
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
      ...reactHookPlugin.configs.recommended.rules,
      ...prettierPlugin.rules,
      camelcase: "off",
      "no-unused-vars": "off",
      "no-unsafe-optional-chaining": "off",
      "no-useless-escape": "off",
      "no-constant-binary-expression": "warn",
      "jsx-a11y/click-events-have-key-events": 0,
      "jsx-a11y/label-has-associated-control": 0,
      "jsx-a11y/control-has-associated-label": 0,
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "react/jsx-wrap-multilines": 0,
      "react/jsx-one-expression-per-line": 0,
      "react/jsx-props-no-spreading": 0,
      "react/jsx-curly-newline": 0,
      "no-param-reassign": 0,
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
