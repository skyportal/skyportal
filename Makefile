SHELL = /bin/bash

BOLD=\033[1m
NORMAL=\033[0m

VER := $(shell python -c "import skyportal; print(skyportal.__version__)")
BANNER := $(shell echo -e "Welcome to $(BOLD)SkyPortal v$(VER)$(NORMAL) (https://skyportal.io)")

$(info $())
$(info $(BANNER))
$(info $())

help: baselayer/Makefile
	@echo -e "  To $(BOLD)start$(NORMAL) the web application, do \`make run\`."
	@echo -e "  To $(BOLD)configure$(NORMAL), copy \`config.yaml.defaults\` to \`config.yaml\` and edit."
	@echo
	@echo Please choose one of the following make targets:
	@python baselayer/tools/makefile_to_help.py "Web Server":baselayer/Makefile "SkyPortal-specific":Makefile
	@echo

baselayer/Makefile:
	git submodule update --init

dependencies_no_js: ## Install Python dependencies and check environment, without checking/installing JS dependencies
	@PYTHONPATH=. pip install packaging
	@baselayer/tools/check_app_environment.py
	@PYTHONPATH=. python baselayer/tools/pip_install_requirements.py baselayer/requirements.txt requirements.txt

docker-images: ## Make and upload docker images
docker-images: docker-local
	@# Add --no-cache flag to rebuild from scratch
	cd baselayer && git submodule update --init --remote
	docker build -t skyportal/web . && docker push skyportal/web

docker-local: ## Build docker images locally
	cd baselayer && git submodule update --init --remote
	docker build -t skyportal/web .

doc_reqs:
	pip install -q -r requirements.docs.txt

api-docs: FLAGS := $(if $(FLAGS),$(FLAGS),--config=config.yaml)
api-docs: | doc_reqs
	@PYTHONPATH=. python tools/docs/build-spec.py $(FLAGS)
	@PYTHONPATH=. python tools/docs/patch-api-doc-template.py $(FLAGS)
	rm -f openapi.{yml,json}

docs: ## Build the SkyPortal docs
docs: | doc_reqs api-docs
	export SPHINXOPTS=-W; make -C doc html

prepare_seed_data: FLAGS := $(if $(FLAGS),$(FLAGS),--config=config.yaml)
prepare_seed_data:
	@PYTHONPATH=. python tools/prepare_seed_data.py $(FLAGS)

load_demo_data: ## Import example dataset
load_demo_data: FLAGS := $(if $(FLAGS),$(FLAGS),--config=config.yaml)
load_demo_data: | dependencies_no_js prepare_seed_data
	@PYTHONPATH=. python tools/data_loader.py data/db_demo.yaml $(FLAGS)

load_seed_data: ## Seed database with common telescopes, instruments, and a taxonomy
load_seed_data: FLAGS := $(if $(FLAGS),$(FLAGS),--config=config.yaml)
load_seed_data: | dependencies_no_js prepare_seed_data
	@PYTHONPATH=. python tools/data_loader.py data/db_seed.yaml $(FLAGS)

db_migrate: ## Migrate database to latest schema
db_migrate: FLAGS := $(if $(FLAGS),$(FLAGS),--config=config.yaml)
db_migrate: FLAGS := $(subst --,-x ,$(FLAGS))
db_migrate:
	PYTHONPATH=. alembic $(FLAGS) upgrade head

# https://www.gnu.org/software/make/manual/html_node/Overriding-Makefiles.html
%: baselayer/Makefile force
	@$(MAKE) --no-print-directory -C . -f baselayer/Makefile $@

.PHONY: Makefile force
