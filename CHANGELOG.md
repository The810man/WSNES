# Changelog

All notable changes to WSNES are listed here. Hardware revisions (the `v0.3` on the silkscreen) and project releases are separate: one hardware revision can span several project releases.

## [0.3.1] - 2026-11-17

### Added
- **Production review** in `docs/reviews/2026-11-17_production-review.md`. This is an AI-agentic review, co-authored by The810man and Claude (Claude Code with the kicad-happy 3.0.2 skills). It covers ERC, schematic/PCB parity, layout, DFM, EMC screening, thermal, sourcing, and datasheet checks of the critical parts.
- **Review evidence** in `analysis/`: `deep_review.json`, validated by the kicad-happy evidence gate, and the helper scripts `helpers/tab_copper.py` and `helpers/ldo_thermal.py`.
- **First housing draft**: `cad/Cardridge.FCStd` (FreeCAD), plus a new 3D board export `cad/WSNES.step` / `.stl`.

### Changed
- **PCB fully routed:** DRC 0 errors, 0 unconnected, schematic parity 0 in KiCad 10. The board file is now saved in KiCad 10 format.
- **New `pcb/WSNES_Proto.kicad_dru` rules:**
  - SMD IC GND pads connect solidly to the pour.
  - One 0.3/0.15 mm GND via is allowed in the U12-8 pocket.
- **`pcb/README.md`:**
  - New "Before ordering" list from the review.
  - The MCP100 SOT-23 pinout is now marked as checked against the datasheet.
- **`README.md`:** release and status, KiCad 10 requirement, updated repository layout.
- **`.gitignore`:** downloaded datasheets and analyzer run folders are no longer tracked.

### Known issues (from the review; fix before ordering)
- **Copper pour fills the gold-finger tab on all four layers**, both between the fingers and along the bevelled tip. Fix it with a no-pour rule area over the tab.
- **Edge-connector orientation and the console /RESET driver type** still need checking on real hardware.
- **JLC BOM has no LCSC part numbers**, and stock is unconfirmed for the SRAMs, the CD74HC4050 and the connectors.
- **No ESD protection on USB-C** (planned for the next hardware spin).

## [0.3.0] - 2026-11-16

### Added
- **Initial import of the v0.3 hardware:**
  - mixed SMD/THT board on the standard SNES cartridge outline, 4 layers, 1.2 mm
  - ESP32-S3-WROOM-1 with USB-C, microSD and an AP2112K 3.3 V regulator
  - LoROM SRAM, plus battery-backed save RAM with MCP100 write protection
  - SuperCIC key on a PIC12F629
- **JLCPCB assembly files**, full BOM, schematic PDF, 3D model.
- **Non-commercial licensing:** CC BY-NC-SA 4.0 for hardware and docs, PolyForm Noncommercial 1.0.0 for code.
- **AI notice** in the README.
