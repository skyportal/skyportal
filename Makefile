SHELL = /bin/bash

BOLD=\033[1m
NORMAL=\033[0m

PYTHON:=PYTHONPATH=. uv run python
FLAGS:=$(if $(FLAGS),$(FLAGS),--config=config.yaml)

VER := $(shell uv run python -c "import skyportal; print(skyportal.__version__)")
BANNER := $(shell echo -e "Welcome to $(BOLD)SkyPortal v$(VER)$(NORMAL) (https://skyportal.io)")

SKYPORTAL_UID ?= 1000
SKYPORTAL_GID ?= 1000
DOCKER_IMAGENAME ?= skyportal/web

$(info $())
$(info $(BANNER))
$(info $())

help: baselayer/Makefile
	@echo -e "  To $(BOLD)start$(NORMAL) the web application, do \`make run\`."
	@echo -e "  To $(BOLD)configure$(NORMAL), copy \`config.yaml.defaults\` to \`config.yaml\` and edit."
	@echo
	@echo Please choose one of the following make targets:
	@$(PYTHON) baselayer/tools/makefile_to_help.py "Web Server":baselayer/Makefile "SkyPortal-specific":Makefile
	@echo

baselayer/Makefile:
	git submodule update --init

dependencies_no_js:
	@uv sync --inexact  # don't remove additional dependencies installed by the user
	@$(PYTHON) ./baselayer/tools/check_app_environment.py

docker-images: ## Make and upload docker images
docker-images: docker-local
	@# Add --no-cache flag to rebuild from scratch
	cd baselayer && git submodule update --init --remote
	docker build -t $(DOCKER_IMAGENAME) \
			--build-arg SKYPORTAL_UID=$(SKYPORTAL_UID) \
			--build-arg SKYPORTAL_GID=$(SKYPORTAL_GID) . && \
		docker push $(DOCKER_IMAGENAME)

docker-local: ## Build docker images locally
	cd baselayer && git submodule update --init --remote
	docker build -t $(DOCKER_IMAGENAME) \
		--build-arg SKYPORTAL_UID=$(SKYPORTAL_UID) \
		--build-arg SKYPORTAL_GID=$(SKYPORTAL_GID) .

doc_reqs:
	uv sync --group docs --inexact

api-docs: | doc_reqs
	@$(PYTHON) tools/docs/build-spec.py $(FLAGS)
	@$(PYTHON) tools/docs/patch-api-doc-template.py $(FLAGS)
	rm -f openapi.{yml,json}

docs: ## Build the SkyPortal docs
docs: | doc_reqs api-docs
	export SPHINXOPTS=-W; uv run make -C doc html

prepare_seed_data:
	@$(PYTHON) tools/prepare_seed_data.py $(FLAGS)

load_demo_data: ## Import example dataset
load_demo_data: | dependencies_no_js prepare_seed_data
	@$(PYTHON) tools/data_loader.py data/db_demo.yaml $(FLAGS)

load_seed_data: ## Seed database with common telescopes, instruments, and a taxonomy
load_seed_data: | dependencies_no_js prepare_seed_data
	@$(PYTHON) tools/data_loader.py data/db_seed.yaml $(FLAGS)

db_create_tables: ## Create tables in the database
db_create_tables: | dependencies_no_js
	@$(PYTHON) skyportal/initial_setup.py $(FLAGS)

db_migrate: ## Migrate database to latest schema
db_migrate: FLAGS := $(subst --,-x ,$(FLAGS))
db_migrate:
	@$(PYTHON) -m alembic $(FLAGS) upgrade head

# https://www.gnu.org/software/make/manual/html_node/Overriding-Makefiles.html
%: baselayer/Makefile force
	@$(MAKE) --no-print-directory -C . -f baselayer/Makefile $@

.PHONY: Makefile force
