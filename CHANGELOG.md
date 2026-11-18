# Changelog

All notable changes to WSNES are listed here. Hardware revisions (the `v0.3` on the silkscreen) and project releases are separate: one hardware revision can span several project releases.

## [Unreleased]

Hardware v0.4, work in progress on branch `hw/v0.4`.

### Added
- **R28 and R29, 33 Ω series resistors** (`C23140`, JLC basic) at the ESP end of SR_SCK and SR_LATCH. These are the two fast multi-drop lines: SR_SCK drives 5 loads over about 96 mm, SR_LATCH 4 loads over about 81 mm. About 25 Ω of GPIO drive plus 33 Ω roughly matches the trace impedance, which damps the ringing that could double-clock the '595/'165. They are now also on the board (they were only in the schematic before).
- **`tools/board_v04.py`**: the one-shot board update for v0.4 (rip-up, re-link, two-sided placement, power fan-out). See "Board" below.
- **Routing net classes with ratsnest colours** (generated into `WSNES_Proto.kicad_pro`): Power (red), USB pair (purple), Clock (orange), AddrBus (blue), DataBus (green), Default.

### Changed
- **Parts, after a stock check on 2026-11-18** (LCSC catalogue, which feeds JLC assembly):
  - **U1: AS6C4008-55SIN → CY62148ELL-55SXI** (`C2953576`). The AS6C4008 is at 0, including the reel version. The CY62148E is 512K × 8, 4.5–5.5 V and 55 ns, with the same JEDEC pinout and the same 450-mil SOIC-32 land pattern as U16. Only 5 were in stock, so order early or hand-solder it.
  - **U5: 74AHCT245PW,118 → TI SN74AHCT245PWR** (`C10910`), same TSSOP-20 pinout. The Nexperia part went to 0.
  - **U13: 74HCT165PW,118 → TI SN74HCT165PWR** (`C3304572`), same TSSOP-16 pinout, still HCT.
  - Every other part is in stock. Low but enough for a prototype: U21 ESP32-S3 (11), U15 PIC12F629 (12), U16 CY62128E (63).
- **Schematic split into 9 sheets** (root overview + `edge_cic`, `snes_buffers`, `rom_glue`, `esp_serial`, `level_reset`, `esp32`, `microsd`, `power_usb`, `save_ram`):
  - Every 100 nF decoupling cap is on the sheet of the IC it decouples.
  - Nets that cross sheets are global labels, so their names stay the same (`SA0`, `BUS_ESP`, ...). Nets used on one sheet only are local (`/Save_RAM/VBAT_R`).
  - `gen_project.py` lays the sheets out by itself (column packer from the real symbol extents), picks the paper size per sheet, and writes power-symbol names horizontally on horizontal pins.
  - `gen_project.py` now **merges** into `WSNES_Proto.kicad_pro` instead of overwriting it, so board settings made in KiCad (zone defaults, ERC map, ...) survive a regeneration.
  - ERC: 0 errors (2 known `lib_symbol_mismatch` warnings for J2/J5). Netlist check: 600 pins, 0 errors.
- **Board:**
  - **All routing removed** for a clean re-route. Zones, rule areas and the tab keep-outs stay.
  - **Footprints are linked to their symbols by path** (`/sheet/symbol`). Before, the board had no paths and parity only worked through the reference fallback.
  - **Two-sided placement.** On B.Cu: 18 decoupling caps (each under its IC, tied to the IC's supply via), the control-line pull-ups and series resistors (R1, R3, R6–R16, R25, R26, R28, R29, C22), and U2. U2 is the A0–A7 buffer, and all eight of its inputs come from the B.Cu fingers 10–17. ICs, connectors, LEDs, buttons, bulk caps and the THT parts stay on top. Nothing is placed on the B.Silkscreen artwork. **JLC needs two-sided (Standard) PCBA for this.**
  - **Power is pre-routed into the planes:** every SMD pad on GND / +5V / +3V3 has a short stub and a 0.6/0.3 via into its plane, so the ratsnest shows only real work.
  - **In1 and In2 are "power" layers** and a DRC rule forbids tracks on inner layers. In v0.3, freerouting had put 3.9 m of signal on the planes.
  - **In2 split moved:** +5V now reaches up under the SRAMs (U1 VCC, D4, U20 were over the +3V3 region). +3V3 keeps the USB/LDO/microSD band and the ESP column.
  - Back silkscreen says v0.4.
- **`WSNES_Proto.kicad_dru`:** no tracks on inner layers, a minimum of 0.3 mm for power tracks, USB diff-pair gap/skew, a 0.45/0.2 via floor. The single-via exception for the old U12 pocket is gone.
- **`export_bom.py`** reads every sheet of the hierarchical schematic. **`export_cheap.py`** no longer leaves off U13 (back in stock as the TI part) but still leaves off U1 (low stock). Its hand-assembly list is now `WSNES_HandAssembly.csv` (was `WSNES_SelfBuy.csv`).
- **Docs:** written in neutral project voice throughout (no instructions addressed to one builder).

## [0.3.2] - 2026-11-17

First release with a final gerber package. It includes the fixes from the 2026-11-17 production review, made with the KiCad MCP tools. Verified with KiCad 10.0.8 after refilling the zones: DRC 0 errors, 0 unconnected, schematic parity 0. The committed gerbers match a fresh export of the committed board.

### Fixed
- **Gold-finger tab:** four `tab_no_pour` rule areas (all copper layers, y ≥ 156) keep every pour out of the finger band and the bevelled tip.
  - GND fingers 5 and 36 were grounded only through that pour. They now have their own 0.6 mm tracks and a GND via.
  - The review's original fix instruction (rule area only) would have disconnected them. The review now says so.
  - The cut also isolated the F.Cu GND patch that feeds U5 pin 10. A new GND via at (140.64, 150.2) ties it to the In1 plane.
- **U23 footprint** now carries the schematic's `Note` field, which clears a schematic-parity warning.

### Added
- **Gerber package** `pcb/production/jlc/WSNES_Proto_v0.3_gerbers.zip`: 4 copper layers, masks, paste, silkscreen, outline, PTH/NPTH drill files and the job file (KiCad 10.0.8).
- **Cheap prototype variant** in `pcb/production/jlc-cheap/`, generated by `pcb/tools/export_cheap.py`. It uses the same board and gerbers, with a smaller JLC bill:
  - JLC leaves off U1 and U13 (out of stock) and SW1, SW2 and U23 (optional).
  - D3 and D7 become the red basic LED `C2286`, the same part as D2.
  - Extended part types drop from 21 to 15.
  - `WSNES_SelfBuy.csv` (renamed to `WSNES_HandAssembly.csv` in v0.4) lists the parts sourced separately and hand-soldered, with quantities for the 2 boards JLC assembles.
- **Board artwork** on the silkscreen: logo, "WSNES" and "810-Studios.com".
- **U23 USBLC6-2SC6 USB ESD protection** at J5 (D+, D−, VBUS):
  - Added in `pcb/tools/design.py`, then regenerated the schematic and `intended_pins.json` (ERC 0/0, netlist check passes on 596 pins).
  - Placed and routed on the board; added to the BOMs and the CPL.
- **LCSC part numbers** for all 35 lines in `production/jlc/WSNES_BOM_JLC.csv`, each checked against the LCSC catalogue.
  - Green and blue LEDs: switched to in-stock KT-0603G and KT-0603B.
  - U18/U19: assigned to TI SN74HCT08PWR, which is pin-compatible.

### Changed
- **U16 save RAM: AS6C1008-55SIN → CY62128ELL-45SXI** (`C2953613`), because the AS6C1008 was out of stock. It has the same JEDEC pinout and the same 450-mil SOP-32 footprint.
  - The CY62128E is rated 4.5–5.5 V. VSAVE is one BAT54C drop (≈ 0.35 V) below +5V, so it is only in spec while the console delivers about 4.9 V or more.
  - Data retention works from 2.0 V, so the CR2032 backup is fine. Go back to the AS6C1008 (2.7–5.5 V) when it is in stock.
- **Schematic PDF** regenerated with KiCad 10.0.8.
- **`pcb/README.md`:** the before-ordering status now reflects the current stock and the final gerbers.
- **Housing CAD** updated, together with a new 3D board export.
- **`.gitignore`:** FreeCAD backups and loose gerber exports in `pcb/` are no longer tracked.

### Known issues
- **U1 AS6C4008-55SIN and U13 74HCT165PW are out of stock** at LCSC and JLC (2026-11-17). Use Global Sourcing, or source them separately and hand-solder them.
- **Signal integrity, planned for hardware v0.4:**
  - The In1 GND plane carries 1.7 m of signal routing and is sliced under the bus logic.
  - USB D+/D− are not routed as a pair. That is uncritical at Full Speed, but untidy.
  - SR_SCK and SR_LATCH have no series resistors.
  - The SOT-23-5 LDO has little thermal margin under sustained full-power Wi-Fi TX.
- **Bench checks still open:** edge-connector pinout and the console /RESET driver type.

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
