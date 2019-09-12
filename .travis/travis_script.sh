#!/bin/bash

set -ex


section "ESLint"

make lint-install
make lint

section_end "ESLint"


section "Tests"

sed -i 's/database: skyportal/database: skyportal_test/g' config.yaml.defaults
make log &
make ${TEST_TARGET}

section_end "Tests"


section "Build.docs"

make docs

section_end "Build.docs"
