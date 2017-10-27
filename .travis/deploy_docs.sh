#!/bin/bash

set -e

if [[ $TRAVIS_PULL_REQUEST == false && \
      $TRAVIS_BRANCH == "master" ]]
then
    pip install doctr
    doctr deploy . --deploy-repo "skyportal/docs"
else
    echo "-- will only push docs from master --"
fi

