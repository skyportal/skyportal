#!/bin/bash

set -e

if [[ $TRAVIS_PULL_REQUEST == false && \
      $TRAVIS_BRANCH == "master" ]]
then
    pip install doctr
    doctr deploy . --deploy-repo "skyportal/docs"
    doctr deploy . --built-docs redoc-static.html
else
    echo "-- will only push docs from master --"
fi
