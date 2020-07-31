#!/bin/bash

set -ex

section "load_demo_data"
make run & sleep 5 && make load_demo_data && kill %1
section_end "load_demo_data"

section "ESLint"
npx eslint --version
make lint
section_end "ESLint"

section "Tests"
make log &
make ${TEST_TARGET}
section_end "Tests"

section "Build.docs"
make docs
section_end "Build.docs"
