.DEFAULT_GOAL := run

-include baselayer/Makefile

baselayer/Makefile:
	git submodule update --init --remote

docker-images:
	# Add --no-cache flag to rebuild from scratch
	cd baselayer && git submodule update --init --remote
	docker build -t skyportal/web . && docker push skyportal/web

docker-local:
	cd baselayer && git submodule update --init --remote
	docker build -t skyportal/web .

doc_reqs:
	pip install -q -r requirements.docs.txt

html: | doc_reqs
	export SPHINXOPTS=-W; make -C doc html

test:
	PYTHONPATH="." ./tools/test_frontend.py
