#!/bin/bash

set -ex


section "ESLint"

make lint-install
make lint

section_end "ESLint"


section "Tests"

make log &
make ${TEST_TARGET}

section_end "Tests"


section "Build.docs"

make docs

section_end "Build.docs"
