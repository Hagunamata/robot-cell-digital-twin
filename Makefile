# Robot-Cell Digital Twin — Makefile (MuJoCo / WSL2-Docker side).
# All verbs are wired through M6. Blender hero rendering is a separate host-side
# step (HERO=1 exports geometry here; the OptiX render runs on the Windows host).
#
# Run inside the container (`make scenarios`) or from the host via
# `docker compose run --rm twin make scenarios`.

PY   ?= python
SCEN ?= cycle_time_pickplace          # default scenario id for `make scenarios`
# Scenarios exercised by `make demo`. droid_replay_reach_check is omitted by
# default because it needs the optional lerobot stack; add it once installed.
DEMO_SCENARIOS ?= cycle_time_pickplace human_clearance_pickplace

.DEFAULT_GOAL := help
.PHONY: help up fetch-assets scenarios test verify render report dashboard demo clean

help:  ## Show available targets
	@echo "Robot-Cell Digital Twin — targets:"
	@echo "  up            Build the headless MuJoCo image (docker compose build)"
	@echo "  fetch-assets  Fetch Menagerie models -> assets/menagerie/ (gitignored)"
	@echo "  scenarios     Run a scenario headless: make scenarios SCEN=<id>"
	@echo "  test          Run the smoke test (pytest)"
	@echo "  verify        Verify a run: reach/cycle-time/clearance -> catalog (SCEN=<id>)"
	@echo "  render        Overlay MP4 (SCEN=<id>); HERO=1 -> export for host Blender"
	@echo "  report        Assemble deck/ from the catalog; print the dashboard command"
	@echo "  dashboard     Launch the Streamlit summary (needs streamlit)"
	@echo "  demo          fetch-assets -> scenarios -> verify -> render -> deck"
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

render:  ## Overlay MP4 for a run; HERO=1 exports geometry for the host Blender render
	@if [ "$(HERO)" = "1" ]; then \
		$(PY) -m render.blender.export_scene --scenario config/scenarios/$(SCEN).yaml; \
	else \
		$(PY) -m render.run --scenario config/scenarios/$(SCEN).yaml; \
	fi

report:  ## Assemble deck/slide_outline.md from the catalog
	$(PY) -m deck.build_deck
	@echo "Dashboard: make dashboard   (streamlit run dashboard/app.py)"

dashboard:  ## Launch the Streamlit summary
	streamlit run dashboard/app.py

demo:  ## End-to-end: fetch-assets -> (scenarios -> verify -> render) -> deck
	@$(MAKE) fetch-assets
	@for s in $(DEMO_SCENARIOS); do \
		echo "=== $$s ==="; \
		$(PY) -m sim.run    --scenario config/scenarios/$$s.yaml && \
		$(PY) -m verify.run --scenario config/scenarios/$$s.yaml && \
		$(PY) -m render.run --scenario config/scenarios/$$s.yaml || exit 1; \
	done
	@$(PY) -m deck.build_deck
	@echo "demo complete. Dashboard: make dashboard"

clean:  ## Remove outputs/ contents but keep the directory
	find outputs -mindepth 1 -not -name .gitkeep -delete
