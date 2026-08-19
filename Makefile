# Robot-Cell Digital Twin — Makefile (MuJoCo / WSL2-Docker side).
# M2: up / fetch-assets / scenarios / test are wired. verify / render / report /
# demo are STUBS until their milestone. Blender hero rendering is host-side only.
#
# Run inside the container (`make scenarios`) or from the host via
# `docker compose run --rm twin make scenarios`.

PY   ?= python
SCEN ?= cycle_time_pickplace          # default scenario id for `make scenarios`

.DEFAULT_GOAL := help
.PHONY: help up fetch-assets scenarios test verify render report demo clean

help:  ## Show available targets
	@echo "Robot-Cell Digital Twin — targets:"
	@echo "  up            Build the headless MuJoCo image (docker compose build)"
	@echo "  fetch-assets  Fetch Menagerie models -> assets/menagerie/ (gitignored)"
	@echo "  scenarios     Run a scenario headless: make scenarios SCEN=<id>"
	@echo "  test          Run the smoke test (pytest)"
	@echo "  verify        Verify a run: reach/cycle-time/clearance -> catalog (SCEN=<id>)"
	@echo "  render        [stub -> M4] overlay MP4s (HERO=1 -> host Blender, M6)"
	@echo "  report        [stub -> M6] Streamlit summary + assemble deck/"
	@echo "  demo          [stub -> M6] fetch-assets -> scenarios -> verify -> render"
	@echo "  clean         Remove outputs/ contents (keeps .gitkeep)"

up:  ## Build the headless MuJoCo container image
	docker compose build

fetch-assets:  ## Pull the needed Menagerie models (not committed)
	$(PY) -m assets.fetch_menagerie

scenarios:  ## Run one scenario headless (SCEN=<scenario id>)
	$(PY) -m sim.run --scenario config/scenarios/$(SCEN).yaml

test:  ## Run the headless smoke test
	$(PY) -m pytest -q

verify:  ## Verify a run: reach / cycle-time / clearance checks -> sqlite catalog
	$(PY) -m verify.run --scenario config/scenarios/$(SCEN).yaml

render:  ## [stub -> M4] overlaid MP4s (HERO=1 -> host-side Blender OptiX, M6)
	@echo "[stub] make render — MuJoCo overlay in M4, Blender hero (HERO=1) in M6"

report:  ## [stub -> M6] Streamlit summary + assemble deck/
	@echo "[stub] make report — implemented in M6"

demo:  ## [stub -> M6] end-to-end fetch -> scenarios -> verify -> render
	@echo "[stub] make demo — implemented in M6 (definition of done)"

clean:  ## Remove outputs/ contents but keep the directory
	find outputs -mindepth 1 -not -name .gitkeep -delete
