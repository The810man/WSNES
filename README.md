# WSNES: WiFi SNES flashcart

AI NOTICE: Hey so i use claude code for making my commits cleaner sometimes, also for release taggin. Code, pcb and CAD is hand made. No generative ai in use, only assistive agentic workflows for documentation and versioning.

WSNES is a SNES flash cartridge built around an **ESP32-S3** and parallel SRAM:

- The ESP loads a game from **microSD**, or one uploaded over **WiFi**, into SRAM.
- The SNES then reads that SRAM as a normal **LoROM** cartridge.
- Saves sit in a battery-backed SRAM and are backed up to the SD card.

The board uses the standard SNES cartridge PCB outline, so it fits a custom PAL / Super Famicom style housing.

## Status

| Part | State |
|---|---|
| Hardware v0.3 | Schematic done (ERC: 0 errors), all 89 parts placed, **fully routed, DRC 0 errors** |
| Housing | Not in this repo yet; the board's full 3D model (STEP + STL) is in `cad/` |
| Firmware | Not in this repo yet |

## Repository layout

```
.
├── pcb/                    KiCad 9 project (open WSNES_Proto.kicad_pro)
│   ├── README.md           board details: who solders what, routing, ordering
│   ├── lib/                project symbols + footprints (cart edge drawn from scratch), vendor 3D models
│   ├── tools/              Python generators; design.py is the design table
│   ├── freerouting/        Specctra DSN for the autorouter
│   └── production/         full BOM + JLCPCB assembly files (BOM, CPL)
├── cad/
│   ├── WSNES_Proto.step    3D model of the board with all parts, for designing the housing
│   └── WSNES_Proto.stl     same, as a mesh (for slicers / mesh tools)
├── docs/
│   ├── WSNES_Proto_schematic.pdf   schematic incl. bus map, GPIO map, firmware flow
│   └── masterplan.md               original architecture notes (German, historical)
├── LICENSES/               full licence texts
├── LICENSE.md              which licence covers what
└── CONTRIBUTING.md         terms for contributions
```

Start with [`pcb/README.md`](pcb/README.md) for the hardware.

## Tools

- KiCad 9 (`kicad-cli` and the `pcbnew` Python module are needed for the generators)
- freerouting, for autorouting
- Python 3

## Research references

These projects were studied while designing WSNES. None of their files are included here.

- [mrehkopf/sd2snes](https://github.com/mrehkopf/sd2snes): FPGA-based SNES flashcart
- [soniccd123/SNES-FeRAM-Cart](https://github.com/soniccd123/SNES-FeRAM-Cart): SNES cart with modern 3.3 V memory
- [MouseBiteLabs/Super-Nintendo-Cartridges](https://github.com/MouseBiteLabs/Super-Nintendo-Cartridges): open SNES cartridge PCBs

## Licence

WSNES is free for non-commercial use: you can build, modify and share it, but selling it needs my permission.

- Hardware and docs: [CC BY-NC-SA 4.0](LICENSES/CC-BY-NC-SA-4.0.txt)
- Code: [PolyForm Noncommercial 1.0.0](LICENSES/PolyForm-Noncommercial-1.0.0.md)

See [LICENSE.md](LICENSE.md) for what counts as non-commercial, and [CONTRIBUTING.md](CONTRIBUTING.md) before sending changes.
