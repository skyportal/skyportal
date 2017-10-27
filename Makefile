ESLINT=./node_modules/.bin/eslint

.DEFAULT_GOAL := run

baselayer/README.md:
	git submodule update --init --remote
	$(MAKE) baselayer-update

.PHONY: baselayer-update run log
baselayer-update:
	./baselayer/tools/submodule_update.sh

log:
	make -C baselayer log

run:
	make -C baselayer run

run_testing:
	make -C baselayer run_testing

run_production:
	make -C baselayer run_production

test:
	make -C baselayer test

test_headless:
	make -C baselayer test_headless

db_init:
	make -C baselayer db_init

db_clear:
	make -C baselayer db_clear

attach:
	make -C baselayer attach

clean:
	make -C baselayer clean

docker-images:
	# Add --no-cache flag to rebuild from scratch
	docker build -t skyportal/web . && docker push skyportal/web

lint-install: lint-githook
	./baselayer/tools/update_eslint.sh

$(ESLINT): lint-install

lint:
	$(ESLINT) --ext .jsx,.js static/js

lint-unix:
	$(ESLINT) --ext .jsx,.js --format=unix static/js

lint-githook:
	cp .git-pre-commit .git/hooks/pre-commit

doc_reqs:
	pip install -q -r requirements.docs.txt

html: | doc_reqs
	export SPHINXOPTS=-W; make -C doc html

-include "baselayer/README.md"  # always clone baselayer if it doesn't exist
