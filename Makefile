.DEFAULT_GOAL := run

-include baselayer/Makefile

baselayer/Makefile:
	git submodule update --init --remote
	$(MAKE) baselayer-update

.PHONY: baselayer-update
baselayer-update:
	./baselayer/tools/submodule_update.sh

docker-images:
	# Add --no-cache flag to rebuild from scratch
	docker build -t skyportal/web . && docker push skyportal/web

doc_reqs:
	pip install -q -r requirements.docs.txt

html: | doc_reqs
	export SPHINXOPTS=-W; make -C doc html
