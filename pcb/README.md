# WSNES Cart v0.3: mixed SMD/THT, standard SNES PCB shape

v0.3 fits the standard SNES cartridge PCB outline: 112.2 × 66.7 mm plus the 11.1 mm contact tab, 1.2 mm thick, 4 layers. A custom housing can therefore look like a normal PAL / Super Famicom cartridge.

- **JLCPCB assembles all the small SMD parts.**
- **You solder the rest yourself:** the ESP module, the PIC, the battery holder, and the optional ICSP header.

| | |
|---|---|
| Schematic | `WSNES_Proto.kicad_sch`. ERC: 0 errors, 0 warnings. All 596 pins checked against the design table. |
| PCB | `WSNES_Proto.kicad_pcb`: 90 parts, **fully routed**, zones filled. DRC (KiCad 10.0.8, 2026-11-17, after the review fixes): 0 errors, 0 unconnected, schematic parity 0. See [DRC status](#drc-status). |
| Routing input | `freerouting/WSNES_Proto.dsn` (inner planes only, see below) |
| JLC assembly | `production/jlc/WSNES_BOM_JLC.csv` + `production/jlc/WSNES_CPL_JLC.csv` (only the parts JLC solders) |
| Full BOM | `production/WSNES_Proto_BOM.csv` (the `Assembly` column says who solders what) |
| 3D model | `../cad/WSNES_Proto.step` and `../cad/WSNES_Proto.stl` (every part has a model), for designing the housing |
| Schematic PDF | `../docs/WSNES_Proto_schematic.pdf` |

## DRC status

0 errors, 0 unconnected items, schematic parity 0. Two warnings remain (four once the KiCad 10 libraries are installed), all reviewed and harmless:

- **`silk_edge_clearance` ×2 (U21):** the ESP32 module outline overhangs the top edge by design, because the antenna sits at the edge. The fab clips silk there.
- **`lib_footprint_mismatch` (J2, J5):** these were placed from the KiCad 9 library. The KiCad 10 copies have identical pad geometry but name the shield pads `SH` (this project uses `S1`/`11` to match its symbols), and J5's pads are roundrect. Do **not** "update from library": it would renumber the shield pads. ERC shows the matching `lib_symbol_mismatch` warnings.

Project rules in `WSNES_Proto.kicad_dru`:

- **SMD IC GND pins** (all `U*` except the hand-soldered ESP U21, plus C14) connect solidly to the F.Cu GND pour. Several were left with a single thermal spoke.
- **One 0.3/0.15 mm GND via** at U12 pin 8 (152.60, 130.39). That pin sits in a pocket fenced by SD6/SD7 on F.Cu, SV_A14 on In1 and the EA19/SD6 bus on In2, and 0.3 mm is the largest via that fits. Every other via is ≥ 0.45/0.2.

Two small `no_pour_sliver` keepouts on In2 (around x 158–166, y 152–155) remove thin, unconnected slivers of the +5V plane.

Four `tab_no_pour` rule areas (F.Cu, In1, In2, B.Cu; x 119–181, y ≥ 156) keep every pour out of the gold-finger band and the bevelled tip. The GND fingers 5 and 36 are connected by their own tracks and a GND via just above the fingers, because the pour no longer reaches them. Cutting the pour also isolated the small F.Cu GND patch that feeds U5 pin 10, so a GND via at (140.64, 150.2) ties that patch to the In1 plane.

## Who solders what

| You (`HAND`) | JLC (`JLC`) |
|---|---|
| U21 ESP32-S3-WROOM-1-N16R8. Solder the castellated edge pads; the centre GND pad is optional, since pins 1 and 40 are GND too. | All 74xx logic (TSSOP), both SRAMs (SOP-32), regulator, diodes, FETs |
| U15 PIC12F629 (DIP-8), flashed with the SuperCIC key firmware, ideally beforehand | microSD socket, USB-C with U23 USB ESD protection, BOOT/RESET buttons, LEDs, all R/C (0603/0805/1206) |
| BT1 CR2032 holder (THT) | |
| J3 ICSP header: optional, only for flashing the PIC in place | |

## What changed vs. v0.2 (the circuit is the same, the packages are smaller)

- **ESP:** DevKitC-1 → bare **ESP32-S3-WROOM-1 module**. The board now carries what the DevKit used to provide:
  - AP2112K-3.3 regulator
  - USB-C on the native USB pins (GPIO19/20) for flashing and the serial console
  - BOOT and RESET buttons, plus a status LED on GPIO48
- **microSD:** the plug-in module became a push-push socket at 3.3 V with pull-ups. Card detect is on GPIO38.
- **DIP → SMD:**
  - 74xx logic → TSSOP
  - AS6C4008 / AS6C1008 → SOP-32 (same pinout)
  - 2N7000 → 2N7002 (different pin order; the netlist is already remapped)
  - MCP100 → SOT-23, BAT85 ×2 → BAT54C, the bussed SIP resistor network → 8 × 0603
- **Removed:** the SD VCC jumper and the EXP header.
- **4 layers:**
  - In1 = GND plane.
  - In2 = +3V3 in the top strip (ESP, SD, regulator) and +5V below it (logic, SRAMs, PIC).
  - Top and bottom layers get GND pours after routing.

GPIO numbers are the same as before, so firmware written for v0.2 still applies. New pins: GPIO0 BOOT, GPIO38 SD card detect, GPIO48 LED, GPIO19/20 USB.

## Housing cutouts (top edge)

Distances are measured from the board's left edge, with the label side facing you.

| Feature | Position | Notes |
|---|---|---|
| microSD slot | centre 21.5 mm | the card sticks out above the top edge |
| USB-C | centre 62.5 mm | about 9 × 3.5 mm opening |
| ESP antenna | 85.5–103.5 mm | plastic is fine; no cutout strictly needed |
| Contact tab | centre 58.5 mm | |

The tallest parts are the PIC (DIP-8, about 4.5 mm without a socket) and the CR2032 holder (about 6 mm). Load `../cad/WSNES_Proto.step` into your CAD tool to check them against the shell.

**Please verify the outline against one of your own carts with calipers.** It follows the standard Nintendo SNES PCB shape (body width, corner steps, side notches). If your PAL shell has posts in different places, send me the measurements and I'll adjust `OUTLINE` in `tools/gen_pcb.py`.

## Routing with freerouting

Why your earlier attempt produced such long routes:
- The old board had two layers.
- The outer GND pours were exported as solid copper, and freerouting has to route around them.

The new `.dsn` contains only the inner planes. GND, +5V and +3V3 just need a via to the plane, so freerouting has two free signal layers left.

1. Run freerouting (GUI or CLI): `java -jar freerouting.jar -de freerouting/WSNES_Proto.dsn -do freerouting/WSNES_Proto.ses -mp 30`
2. In KiCad: **File → Import → Specctra Session** → `WSNES_Proto.ses`.
3. Press `B` to refill the zones, then run **DRC**.
4. Export the gerbers and drill files. JLC order options:
   - 4 layers, **1.2 mm**, ENIG
   - gold fingers with **45° bevel**
   - assembly: top side, using the two files in `production/jlc/`

The JLC BOM has a verified `LCSC Part #` on 26 of its 35 lines (see [Before ordering](#before-ordering) for the 9 without). Check part rotations in JLC's placement preview; SOT-23 / SOT-23-5 / SOT-23-6 parts often need 180°.

## Save RAM (unchanged from v0.2)

- U16 AS6C1008 is battery-backed and mapped to LoROM `$70-$7D:0000-7FFF`.
- U17 74HCT138 decodes the save area.
- U19 masks the size to match the ROM header.
- U20 MCP100 blocks writes below about 4.4 V.

The ESP copies the save to `<game>.srm` on SD when you return to the menu or press reset. If you power off mid-game, the battery keeps the save, and the ESP backs it up at the next power-up.

## Before ordering

The production review of 2026-11-17 ([`../docs/reviews/2026-11-17_production-review.md`](../docs/reviews/2026-11-17_production-review.md)) found one blocker and five checks. Status after the same-day fixes:

- **Tab copper: fixed and verified.** The zones are refilled and the KiCad 10 DRC is clean. Measured on the refilled board, no copper is left between the fingers or within 1 mm of the bevelled tip, on any layer. See [DRC status](#drc-status).
- **USB ESD: added.** U23 USBLC6-2SC6 sits next to J5 and is routed.
- **LCSC part numbers: 26 of 35 lines filled.** These 9 ICs have no JLC listing in their family and package, so order them through JLC Global Sourcing, consign them, or hand-solder them:
  - U1 AS6C4008-55SIN and U16 AS6C1008-55SIN (SOP-32)
  - U13 74HCT165PW, U14 CD74HC4050PWR, U17 74HCT138PW, U8 74HCT157PW (TSSOP-16)
  - U2–U4 74AHCT541PW, U5 74AHCT245PW (TSSOP-20)
  - U7 74HCT32PW (TSSOP-14)

  HCT drop-ins exist for the '541 (SN74HCT541PWR, C436096) and the '245 (74HCT245PW, C52140501), but they are slower than AHCT.
- **Still open, bench checks:**
  - Edge pinout: check continuity against an original cart. The finger at x = 177.5 (pin 5/36) must be GND on the same face.
  - Console /RESET driver: Q1 pulls pin 26 low by default. Measure whether the console drives that line push-pull before relying on it.
- **Gerbers:** a test export from KiCad 10.0.8 passed the gerber check (all layers present and aligned, 112.3 × 77.9 mm, 437 vias, one 0.15 mm drill). Export the final set for the order.

Notes from before the review:

- **Fine via:** the one 0.3/0.15 mm GND via (see [DRC status](#drc-status)) needs the fab's multilayer small-via option. If you want to avoid it, re-route SD7's branch under U12 so pin 8 can reach a normal via.
- **Inner layers carry signals:** freerouting also used In1 (GND) and In2 (+5V/+3V3) for about 1.7 m + 2.2 m of signal track. The planes are still each one connected region, but they are cut up. That's fine at SNES bus speeds; keep an eye on the ESP/RF area if you re-route.
- **MCP100 SOT-23 pinout:** the footprint uses 1 = RST, 2 = VDD, 3 = VSS. This was checked against Microchip DS11187F (p.1 package drawing, p.9 pin numbering) in the 2026-11-17 review, and it is correct.
- **CR2032 holder:** `+` is the square pad. Check its height against your housing.
- **SNES 5 V budget:** ESP32 WiFi peaks reach about 350–500 mA. Lowering the TX power helps if the console struggles.
- **Timing:** SlowROM games have margin. FastROM games are marginal with HCT glue; AHCT versions of the glue chips would help.
- **USB-only power** (no console): only the ESP, SD and 3.3 V side is powered. The firmware must not drive the 5 V logic while `SNES_5V_SENSE = 0`.

## Bus map, GPIO map, firmware flow

These are unchanged from v0.2 and documented on the schematic sheet (`../docs/WSNES_Proto_schematic.pdf`):

- **Bus ownership:** a single `BUS_ESP` GPIO, pulled high, so the ESP owns the bus at power-up.
- **Shift word:** 32 bits, MSB first: `[DATA, A23..16 (A19 = save-chip select), A15..8, A7..0]`.

## Regenerate

Run these from `pcb/`.

```
python3 tools/gen_project.py .        # libraries + schematic from tools/design.py
kicad-cli sch export netlist --format kicadsexpr -o /tmp/p.net WSNES_Proto.kicad_sch
python3 tools/verify_netlist.py /tmp/p.net tools/intended_pins.json
python3 tools/gen_pcb.py .            # DO NOT RUN: rebuilds the PCB from scratch and discards routing

# refresh the exported docs / 3D model
kicad-cli sch export pdf -o ../docs/WSNES_Proto_schematic.pdf WSNES_Proto.kicad_sch
kicad-cli pcb export step -f -o ../cad/WSNES_Proto.step WSNES_Proto.kicad_pcb
kicad-cli pcb export stl  -f -o ../cad/WSNES_Proto.stl  WSNES_Proto.kicad_pcb

# refill zones + full check
kicad-cli pcb drc --refill-zones --save-board --schematic-parity WSNES_Proto.kicad_pcb
```

BT1, J5 and U1/U16 use vendor models from `lib/3dmodels/`, because KiCad's 3D library has none for those footprints. See `lib/3dmodels/README.md` for where they come from and their offsets.

Routing has started, so KiCad is now the source of truth. Don't rerun `gen_pcb.py`.
