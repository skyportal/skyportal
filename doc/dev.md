# Developer notes
## Testing
To execute the test suite:
- Install ChromeDriver from https://sites.google.com/a/chromium.org/chromedriver/home and place the binary on your path
- Install Chrome or Chromium
- To run all tests: `make test`
- To run a single test: `./tools/test_frontend.py skportal/tests/frontend/<test_file>.py::test_<specific_test>`

On Linux, the tests can be run in "headless" mode (no browser display):
  - Install xfvb
  - `make test_headless`

## Debugging
  - Run `make log` to watch log output
  - Run `make stop` to stop any running web services.
  - Run `make attach` to attach to output of webserver, e.g. for use with `pdb.set_trace()`
  - Run `make check-js-updates` to see which Javascript packages are eligible for an upgrade.

## Standards
We use ESLint to ensure that our JavaScript & JSX code is consistent and conforms with recommended standards.

- Install ESLint using `make lint-install`.  This will also install a git pre-commit hook so that any commit is linted before it is checked in.
- Run `make lint`  to perform a style check

## Docker images
  - Run `make docker-images` to build and push to Docker hub.
