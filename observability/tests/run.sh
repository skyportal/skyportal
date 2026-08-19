#!/usr/bin/env bash
# Bring up the stub + real Prometheus/Grafana kit, assert it works, tear down.
# Used locally and in CI (.github/workflows/test_observability.yaml).
set -euo pipefail
cd "$(dirname "$0")"

COMPOSE="docker compose -f docker-compose.test.yaml"

cleanup() {
  $COMPOSE logs prometheus grafana 2>/dev/null | tail -40 || true
  $COMPOSE down -v >/dev/null 2>&1 || true
  rm -f token
}
trap cleanup EXIT

# Token the stub expects and prometheus.yml sends via credentials_file.
printf 'TESTTOKEN' > token

$COMPOSE up -d
python3 validate.py
