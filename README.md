# SkyPortal

The SkyPortal web application consumes and displays events from the
Zwicky Transient Facility.

## Developer notes

### Important Makefile targets

DB preparation:

- db_init : Create database
- db_clear : Drop and re-create DB

Launching:

- debug : Launch app in debug mode, which auto-refreshes files and
          monitors micro-services
- log : Tail all log files

Testing:

- test : Launch web app & execute frontend tests
- test_headless : (Linux only) The above, but without a visible
                  browser

Development:

- lint-install : Install ESLint and dependencies
- lint : Run ESLint on all files
- lint-unix : Same as above, but outputs in a format that most text
              editors can parse
- lint-githook : Install a Git pre-commit hook that lints staged
                 chunks
