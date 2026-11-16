# WSNES: WiFi SNES flashcart

WSNES is a SNES flash cartridge built around an **ESP32-S3** and parallel SRAM:

- The ESP loads a game from **microSD**, or one uploaded over **WiFi**, into SRAM.
- The SNES then reads that SRAM as a normal **LoROM** cartridge.
- Saves sit in a battery-backed SRAM and are backed up to the SD card.

The board uses the standard SNES cartridge PCB outline, so it fits a custom PAL / Super Famicom style housing.

## Status

| Part | State |
|---|---|
| Hardware v0.3 | Schematic done (ERC clean), all 89 parts placed, **routing in progress** |
| Housing | Not in this repo yet; the board's 3D model is in `cad/` |
| Firmware | Not in this repo yet |

## Repository layout

```
.
├── pcb/                    KiCad 9 project (open WSNES_Proto.kicad_pro)
│   ├── README.md           board details: who solders what, routing, ordering
│   ├── lib/                project symbols + footprints (cart edge drawn from scratch)
│   ├── tools/              Python generators; design.py is the design table
│   ├── freerouting/        Specctra DSN for the autorouter
│   └── production/         full BOM + JLCPCB assembly files (BOM, CPL)
├── cad/
│   └── WSNES_Proto.step    3D model of the board, for designing the housing
└── docs/
    ├── WSNES_Proto_schematic.pdf   schematic incl. bus map, GPIO map, firmware flow
    └── masterplan.md               original architecture notes (German, historical)
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
