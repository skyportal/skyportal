#!/bin/bash

set -ex


section "Tests"

make log &
make ${TEST_TARGET}

section_end "Tests"

