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

section "Test.alert.stream.demo"

make load_demo_data
make alert_stream_demo

section_end "Test.alert.stream.demo"


section "Build.docs"

make docs

section_end "Build.docs"
