// eslint.config.js
const globalsLib = require("globals");
const eslint = require("@eslint/js");

const reactPlugin = require("eslint-plugin-react");
const prettierPlugin = require("eslint-config-prettier");
const importPlugin = require("eslint-plugin-import");
const reactHookPlugin = require("eslint-plugin-react-hooks");
const airbnbPlugin = require("eslint-config-airbnb");
const tseslint = require("typescript-eslint");

const { fixupPluginRules } = require("@eslint/compat");

module.exports = [
  eslint.configs.recommended,
  // run on all js/jsx/ts/tsx files in the static directory and subdirectories
  {
    files: [
      "static/**/*.js",
      "static/**/*.jsx",
      "static/**/*.ts",
      "static/**/*.tsx",
    ],
  },
  { ignores: ["docs/*"] },
  {
    // CommonJS config files at repo root use Node globals
    files: ["*.config.js", "*.config.cjs"],
    languageOptions: {
      globals: {
        ...globalsLib.node,
      },
      sourceType: "commonjs",
    },
  },
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
        ...globalsLib.browser,
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
      ...reactPlugin.configs.recommended.rules,
      ...prettierPlugin.rules,
      // React 17+ automatic JSX runtime (tsconfig "jsx": "react-jsx") does
      // not require React to be in scope.
      "react/react-in-jsx-scope": "off",
      "react/jsx-uses-react": "off",
      camelcase: "off",
      "no-unused-vars": "off",
      "no-unsafe-optional-chaining": "off",
      "no-useless-escape": "off",
      "no-constant-binary-expression": "warn",
      "no-await-in-loop": "warn",
      "jsx-a11y/click-events-have-key-events": 0,
      "jsx-a11y/label-has-associated-control": 0,
      "jsx-a11y/control-has-associated-label": 0,
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "react-hooks/set-state-in-effect": "off",
      "react/jsx-wrap-multilines": 0,
      "react/jsx-one-expression-per-line": 0,
      "react/jsx-props-no-spreading": 0,
      "react/jsx-curly-newline": 0,
      "react/forbid-prop-types": "warn",
      "react/destructuring-assignment": 0,
      "prefer-template": "warn",
      "no-param-reassign": 0,
      "react/jsx-no-bind": 0,
      "no-shadow": "error",
    },
  },
  {
    // TypeScript files: use the typescript-eslint parser (overrides the babel
    // parser above for .ts/.tsx). Kept lenient to start -- `tsc --noEmit`
    // (npm run typecheck) is the source of truth for type errors.
    files: ["static/**/*.ts", "static/**/*.tsx"],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        ecmaFeatures: { jsx: true },
        sourceType: "module",
      },
      globals: {
        ...globalsLib.browser,
      },
    },
    plugins: {
      "@typescript-eslint": tseslint.plugin,
    },
    rules: {
      // TS itself handles undefined-symbol and unused checks; turn off the
      // core rules that produce false positives on type-only syntax.
      "no-undef": "off",
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": "off",
      "no-use-before-define": "off",
    },
  },
  {
    settings: {
      import: {
        resolver: {
          node: {},
          webpack: {
            config: "rspack.config.js",
          },
        },
      },
      react: {
        version: "detect",
      },
    },
  },
];
