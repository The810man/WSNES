# WSNES Cart v0.3: mixed SMD/THT, standard SNES PCB shape

v0.3 fits the standard SNES cartridge PCB outline: 112.2 × 66.7 mm plus the 11.1 mm contact tab, 1.2 mm thick, 4 layers. A custom housing can therefore look like a normal PAL / Super Famicom cartridge.

- **JLCPCB assembles all the small SMD parts.**
- **You solder the rest yourself:** the ESP module, the PIC, the battery holder, and the optional ICSP header.

| | |
|---|---|
| Schematic | `WSNES_Proto.kicad_sch`. ERC: 0 errors, 0 warnings. All 590 pins checked against the design table. |
| PCB | `WSNES_Proto.kicad_pcb`: 89 parts placed, nets assigned, planes poured. **Routing in progress** (321 connections still open as of 2026-11-16). |
| Routing input | `freerouting/WSNES_Proto.dsn` (inner planes only, see below) |
| JLC assembly | `production/jlc/WSNES_BOM_JLC.csv` + `production/jlc/WSNES_CPL_JLC.csv` (only the parts JLC solders) |
| Full BOM | `production/WSNES_Proto_BOM.csv` (the `Assembly` column says who solders what) |
| 3D model | `../cad/WSNES_Proto.step`, for designing the housing |
| Schematic PDF | `../docs/WSNES_Proto_schematic.pdf` |

**DRC at placement (before routing started):** 0 errors and schematic parity 0. Two harmless leftovers remain:
- the module's silkscreen outline touches the board edge;
- the +3V3 plane shows as isolated until the vias are routed.

## Who solders what

| You (`HAND`) | JLC (`JLC`) |
|---|---|
| U21 ESP32-S3-WROOM-1-N16R8. Solder the castellated edge pads; the centre GND pad is optional, since pins 1 and 40 are GND too. | All 74xx logic (TSSOP), both SRAMs (SOP-32), regulator, diodes, FETs |
| U15 PIC12F629 (DIP-8), flashed with the SuperCIC key firmware, ideally beforehand | microSD socket, USB-C, BOOT/RESET buttons, LEDs, all R/C (0603/0805/1206) |
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

The `LCSC Part #` column in the JLC BOM is still empty. JLC's BOM tool matches by value, footprint and MPN; check each match, and check part rotations in their placement preview.

## Save RAM (unchanged from v0.2)

- U16 AS6C1008 is battery-backed and mapped to LoROM `$70-$7D:0000-7FFF`.
- U17 74HCT138 decodes the save area.
- U19 masks the size to match the ROM header.
- U20 MCP100 blocks writes below about 4.4 V.

The ESP copies the save to `<game>.srm` on SD when you return to the menu or press reset. If you power off mid-game, the battery keeps the save, and the ESP backs it up at the next power-up.

## Before ordering

- **MCP100 SOT-23 pinout:** the footprint assumes 1 = RST, 2 = VDD, 3 = VSS. Check it against the Microchip datasheet.
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
kicad-cli pcb export step -o ../cad/WSNES_Proto.step WSNES_Proto.kicad_pcb
```

Routing has started, so KiCad is now the source of truth. Don't rerun `gen_pcb.py`.
