SHELL = /bin/bash

BOLD=\033[1m
NORMAL=\033[0m

VER := $(shell cat skyportal/__init__.py | grep -o -P "(?<=__version__ = .)[0-9a-zA-Z\.]*")
BANNER := $(shell echo -e "Welcome to $(BOLD)SkyPortal v$(VER)$(NORMAL) (https://skyportal.io)")
$(info $(BANNER))
$(info $())

help:
	@echo -e "  To $(BOLD)start$(NORMAL) the web application, do \`make run\`."
	@echo -e "  To $(BOLD)customize$(NORMAL) the configuration, edit \`config.yaml.defaults\`."
	@echo
	@echo Please choose one of the following make targets:
	@echo
	@$(MAKE) --no-print-directory -C . -f baselayer/Makefile help

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

api-docs: | doc_reqs
	@PYTHONPATH=. python tools/openapi/build-spec.py
	npx redoc-cli@0.8.3 bundle openapi.json
	mkdir -p doc/_build/html
	mv redoc-static.html doc/openapi.html

docs: | doc_reqs api-docs
	export SPHINXOPTS=-W; make -C doc html

load_demo_data: | dependencies
	@PYTHONPATH=. python tools/load_demo_data.py

# https://www.gnu.org/software/make/manual/html_node/Overriding-Makefiles.html
%: baselayer/Makefile force
	@$(MAKE) --no-print-directory -C . -f baselayer/Makefile $@

.PHONY: Makefile force
