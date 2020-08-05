#!/bin/bash

set -ex

section "load_demo_data"
make run &
sleep 5 && make load_demo_data
kill %1
section_end "load_demo_data"

section "pre-commit checks"
pip install pre-commit
if pre-commit run --from-ref origin/master --to-ref HEAD; then
    echo "Linting errored; this will be fatal sometime in the near future"
fi
section_end "pre-commit checks"

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
