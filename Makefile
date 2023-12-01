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
	@PYTHONPATH=. python tools/openapi/build-spec.py $(FLAGS)
	npx redoc-cli@0.13.21 bundle openapi.json \
          --title "SkyPortal API docs" \
          --options.theme.logo.gutter 2rem \
          --cdn
	rm -f openapi.{yml,json}
	mkdir -p doc/_build/html
	mv redoc-static.html doc/openapi.html

docs: ## Build the SkyPortal docs
docs: | doc_reqs api-docs
	export SPHINXOPTS=-W; make -C doc html

prepare_seed_data: FLAGS := $(if $(FLAGS),$(FLAGS),--config=config.yaml)
prepare_seed_data:
	@PYTHONPATH=. python tools/prepare_seed_data.py $(FLAGS)

load_demo_data: ## Import example dataset
load_demo_data: FLAGS := $(if $(FLAGS),$(FLAGS),--config=config.yaml)
load_demo_data: | dependencies prepare_seed_data
	@PYTHONPATH=. python tools/data_loader.py data/db_demo.yaml $(FLAGS)

load_seed_data: ## Seed database with common telescopes, instruments, and a taxonomy
load_seed_data: FLAGS := $(if $(FLAGS),$(FLAGS),--config=config.yaml)
load_seed_data: | dependencies prepare_seed_data
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

FLAGS:=$(if $(FLAGS),$(FLAGS),--config=config.yaml)
PYTHON=PYTHONPATH=. python
ENV_SUMMARY=$(PYTHON) baselayer/tools/env_summary.py $(FLAGS)

SUPERVISORD_CFG_APP=baselayer/services/app/supervisor.conf
SUPERVISORD_APP=$(PYTHON) -m supervisor.supervisord -s -c $(SUPERVISORD_CFG_APP)

run_app: ## Start the web application.
run_app: FLAGS:=$(FLAGS) --debug
run_app:
	@echo
	$(call LOG, Starting APP)
	@echo
	@echo " - Run \`make log\` in another terminal to view logs"
	@echo " - Run \`make monitor\` in another terminal to restart services"
	@echo
	@export FLAGS="$(FLAGS)" && \
	$(ENV_SUMMARY) && echo && \
	echo "Press Ctrl-C to abort the server" && \
	echo && \
	$(SUPERVISORD_APP)

SUPERVISORD_CFG_WS=baselayer/services/websocket_server/supervisor.conf
SUPERVISORD_WS=$(PYTHON) -m supervisor.supervisord -s -c $(SUPERVISORD_CFG_WS)

run_websocket:
	@echo
	$(call LOG, Starting websocket server)
	@echo
	@echo " - Run \`make log\` in another terminal to view logs"
	@echo " - Run \`make monitor\` in another terminal to restart services"
	@echo
	@export FLAGS="$(FLAGS)" && \
	echo "Press Ctrl-C to abort the server" && \
	echo && \
	$(SUPERVISORD_WS)

SUPERVISORD_CFG_MP=baselayer/services/message_proxy/supervisor.conf
SUPERVISORD_MP=$(PYTHON) -m supervisor.supervisord -s -c $(SUPERVISORD_CFG_MP)

run_message_proxy:
	@echo
	$(call LOG, Starting message proxy)
	@echo
	@echo " - Run \`make log\` in another terminal to view logs"
	@echo " - Run \`make monitor\` in another terminal to restart services"
	@echo
	@export FLAGS="$(FLAGS)" && \
	echo "Press Ctrl-C to abort the server" && \
	echo && \
	$(SUPERVISORD_MP)

SUPERVISORD_CFG_FAKEOAUTH=baselayer/services/fake_oauth2/supervisor.conf
SUPERVISORD_FAKEOAUTH=$(PYTHON) -m supervisor.supervisord -s -c $(SUPERVISORD_CFG_FAKEOAUTH)

run_fake_oauth:
	@echo
	$(call LOG, Starting fake OAuth2 server)
	@echo
	@echo " - Run \`make log\` in another terminal to view logs"
	@echo " - Run \`make monitor\` in another terminal to restart services"
	@echo
	@export FLAGS="$(FLAGS)" && \
	echo "Press Ctrl-C to abort the server" && \
	echo && \
	$(SUPERVISORD_FAKEOAUTH)

SUPERVISORD_CFG_NGINX=baselayer/services/nginx/supervisor.conf
SUPERVISORD_NGINX=$(PYTHON) -m supervisor.supervisord -s -c $(SUPERVISORD_CFG_NGINX)

run_nginx:
	@echo
	$(call LOG, Starting nginx)
	@echo
	@echo " - Run \`make log\` in another terminal to view logs"
	@echo " - Run \`make monitor\` in another terminal to restart services"
	@echo
	@export FLAGS="$(FLAGS)" && \
	echo "Press Ctrl-C to abort the server" && \
	echo && \
	$(SUPERVISORD_NGINX)
