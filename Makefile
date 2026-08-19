# Robot-Cell Digital Twin — Makefile (MuJoCo / WSL2-Docker side).
# Scaffolded at M0. Recipes are STUBS; each is wired up in the milestone noted.
# Blender hero rendering is a separate, host-side step (not in this container path).

.DEFAULT_GOAL := help
.PHONY: help up fetch-assets scenarios verify render report demo clean

help:  ## Show available targets
	@echo "Robot-Cell Digital Twin — available targets:"
	@echo "  up            Build/start the MuJoCo container (M2)"
	@echo "  fetch-assets  Pull the needed Menagerie models, uncommitted (M2)"
	@echo "  scenarios     Run the v1 scenarios headless (M2)"
	@echo "  verify        Check reach / cycle-time / clearance -> catalog (M3)"
	@echo "  render        MuJoCo overlay MP4s; HERO=1 for host Blender clips (M4/M6)"
	@echo "  report        Build the Streamlit summary + assemble deck/ (M6)"
	@echo "  demo          fetch-assets -> scenarios -> verify -> render (M6 DoD)"
	@echo "  clean         Remove outputs/ contents (keeps the folder)"

up:  ## Build/start the MuJoCo container
	@echo "[stub] make up — implemented in M2"

fetch-assets:  ## Pull specific Menagerie models (not committed)
	@echo "[stub] make fetch-assets — implemented in M2"

scenarios:  ## Run the v1 scenarios headless
	@echo "[stub] make scenarios — implemented in M2"

verify:  ## Run reach / cycle-time / clearance checks -> sqlite catalog
	@echo "[stub] make verify — implemented in M3"

render:  ## Render overlaid MP4s (HERO=1 -> host-side Blender OptiX)
	@echo "[stub] make render — MuJoCo overlay in M4, Blender hero (HERO=1) in M6"

report:  ## Wire the Streamlit summary and assemble deck/
	@echo "[stub] make report — implemented in M6"

demo:  ## End-to-end: fetch-assets -> scenarios -> verify -> render
	@echo "[stub] make demo — implemented in M6 (definition of done)"

clean:  ## Remove outputs/ contents but keep the directory
	@echo "[stub] make clean — removes outputs/ contents (keeps .gitkeep)"
