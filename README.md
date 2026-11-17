# WSNES „SNES-LoROM-Flashcart mit WLAN-Upload für Homebrew und Entwicklung auf echter Hardware.“

AI NOTICE: Hey so i use claude code for making my commits cleaner sometimes, also for release taggin. Code, pcb and CAD is hand made but also enhanced via mcp tools (for example checking routing and fixing issues like via placement etc.). Agentic workflows used for documentation and versioning.

![WSNES LOGO](./docs/images/wsnes-inverse.svg)

WSNES is a SNES flash cartridge built around an **ESP32-S3** and parallel SRAM:

- The ESP loads a game from **microSD**, or one uploaded over **WiFi**, into SRAM.
- The SNES then reads that SRAM as a normal **LoROM** cartridge.
- Saves sit in a battery-backed SRAM and are backed up to the SD card.

The board uses the standard SNES cartridge PCB outline, so it fits a custom PAL / Super Famicom style housing.

## Status

**Latest release: [v0.3.2](https://github.com/The810man/WSNES/releases/tag/v0.3.2) (2026-11-17)**, with the gerbers and JLC files as release downloads. See [CHANGELOG.md](CHANGELOG.md).

| Part | State |
| --- | --- |
| Hardware v0.3 | Schematic done (ERC: 0 errors), all 90 parts placed, **fully routed, DRC clean** (KiCad 10.0.8: 0 errors, 0 unconnected, parity 0) |
| Production review | [2026-11-17](docs/reviews/2026-11-17_production-review.md): the tab-copper blocker and the missing USB ESD are **fixed and verified**. Every JLC line has an LCSC number. U1 and U13 were out of stock on 2026-11-17, and two bench checks are still open. See [`pcb/README.md`](pcb/README.md#before-ordering). |
| Production files | Gerbers in `pcb/production/jlc/`. JLC assembly as the full variant (`jlc/`) or the cheap prototype variant (`jlc-cheap/`, with a self-buy list) |
| Hardware v0.4 | In progress: clean In1 GND plane, USB routed as a pair, series resistors on the shift-register clock and latch |
| Housing | First draft: `cad/Cardridge.FCStd` (FreeCAD) |
| Firmware | Not in this repo yet |

## Repository layout

```
.
├── pcb/                    KiCad project (open WSNES_Proto.kicad_pro; the board needs KiCad 10)
│   ├── README.md           board details: who solders what, routing, ordering
│   ├── lib/                project symbols + footprints (cart edge drawn from scratch), vendor 3D models
│   ├── tools/              Python generators; design.py is the design table
│   ├── freerouting/        Specctra DSN for the autorouter
│   └── production/         full BOM, gerbers + JLCPCB assembly files (jlc/), cheap variant (jlc-cheap/)
├── cad/
│   ├── Cardridge.FCStd     first housing draft (FreeCAD)
│   ├── WSNES.step / .stl   latest KiCad 3D export of the board with all parts
│   └── WSNES_Proto.step / .stl   earlier export of the same board
├── docs/
│   ├── reviews/            design reviews (production review 2026-11-17)
│   ├── WSNES_Proto_schematic.pdf   schematic incl. bus map, GPIO map, firmware flow
│   └── masterplan.md               original architecture notes (German, historical)
├── analysis/               review evidence: deep_review.json + helper scripts (analyzer runs are not committed)
├── CHANGELOG.md            release history
├── LICENSES/               full licence texts
├── LICENSE.md              which licence covers what
└── CONTRIBUTING.md         terms for contributions
```

Start with [`pcb/README.md`](pcb/README.md) for the hardware.

## Tools

- KiCad 10 to open the board: `WSNES_Proto.kicad_pcb` is saved in KiCad 10 format, and KiCad 9 can't load it. The schematic still opens in KiCad 9.
- `kicad-cli` and the `pcbnew` Python module, for the generators in `pcb/tools/`
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
