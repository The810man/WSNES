# WSNES Cart v0.4 (work in progress): mixed SMD/THT, two-sided, standard SNES PCB shape

v0.4 fits the standard SNES cartridge PCB outline: 112.2 × 66.7 mm plus the 11.1 mm contact tab, 1.2 mm thick, 4 layers. A custom housing can therefore look like a normal PAL / Super Famicom cartridge.

- **JLCPCB assembles all the small SMD parts, now on both sides.**
- **Hand-soldered after assembly:** the ESP module, the PIC, the battery holder, and the optional ICSP header.

**State on 2026-11-18:** the schematic is split into sheets, parts are re-sourced, and the board is re-placed on two sides with power pre-routed into the planes. **Signal routing is removed and has to be redone** (see [Routing](#routing-v04)). The gerbers in `production/jlc/` belong to the old, routed v0.3 board.

| | |
|---|---|
| Schematic | `WSNES_Proto.kicad_sch` (root overview) + 9 sheets: `edge_cic`, `snes_buffers`, `rom_glue`, `esp_serial`, `level_reset`, `esp32`, `microsd`, `power_usb`, `save_ram`. ERC: 0 errors. All 600 pins checked against the design table. |
| PCB | `WSNES_Proto.kicad_pcb`: 92 parts placed (49 top, 43 bottom), power fanned out into the planes, signals unrouted. DRC (KiCad 10.0.8): 0 errors, schematic parity 0, 268 unconnected pads left to route. |
| Routing input | `freerouting/WSNES_Proto.dsn` (In1/In2 exported as power planes, so freerouting stays on F.Cu / B.Cu) |
| JLC assembly | `production/jlc/WSNES_BOM_JLC.csv` + `production/jlc/WSNES_CPL_JLC.csv` (only the parts JLC solders, top and bottom) |
| Full BOM | `production/WSNES_Proto_BOM.csv` (the `Assembly` column says who solders what) |
| Cheap prototype | `production/jlc-cheap/`: smaller JLC bill. JLC leaves off U1 (low stock), SW1, SW2 and U23, and the LEDs are all red basic parts. Includes a hand-assembly list. See its README. |
| 3D model | `../cad/WSNES_Proto.step` / `.stl` are still the v0.3 export. Re-export after routing: the back now carries parts, about 1 mm high. |
| Schematic PDF | `../docs/WSNES_Proto_schematic.pdf` |

## DRC status

0 errors, schematic parity 0, 268 unconnected pads (the signal routing). The warnings are reviewed and harmless:

- **`silk_overlap` / `silk_over_copper` (about 90):** silkscreen of the small back-side passives touching each other or their pads. Their references are hidden, and the fab clips silk on pads.
- **`silk_edge_clearance` ×2 (U21):** the ESP32 module outline overhangs the top edge by design, because the antenna sits at the edge. The fab clips silk there.
- **`lib_footprint_mismatch` (J2, J5):** these were placed from the KiCad 9 library. The KiCad 10 copies have identical pad geometry but name the shield pads `SH` (this project uses `S1`/`11` to match its symbols), and J5's pads are roundrect. Do **not** "update from library": it would renumber the shield pads. ERC shows the matching `lib_symbol_mismatch` warnings.

Project rules in `WSNES_Proto.kicad_dru`:

- **No tracks on In1 / In2.** Both are "power" layers (planes only). Reach a plane with a via.
- **Power tracks at least 0.3 mm** (the net class default is 0.5 mm).
- **SMD IC GND pins** (all `U*` except the hand-soldered ESP U21) connect solidly to the GND pours.
- **USB pair:** gap 0.18–0.3 mm, skew at most 1 mm.
- **Via floor 0.45/0.2 mm.** Signals default to 0.5/0.25, power to 0.6/0.3.

Four `tab_no_pour` rule areas (F.Cu, In1, In2, B.Cu; x 119–181, y ≥ 156) keep every pour out of the gold-finger band and the bevelled tip. The GND and +5V fingers (5/36, 27/58) have their own 0.8 mm stubs and two vias each just above the fingers, because the pour does not reach them. Two small `no_pour_sliver` keepouts on In2 (around x 158–166, y 152–155) remove thin, unconnected slivers of the +5V plane.

**In2 split (v0.4):** +3V3 covers the top band (USB, LDO, microSD; y < 101–105.5) and the ESP column (x > 171, y < 113.3). +5V covers everything else and now reaches up under both SRAMs, so U1's VCC pin, D1, D4 and U20 sit over +5V. U14 (CD74HC4050, the only 3.3 V chip in the 5 V area) and its cap C17 get their +3V3 through one short track.

## Assembly split

| Hand-soldered (`HAND`) | JLC (`JLC`), top | JLC (`JLC`), bottom |
|---|---|---|
| U21 ESP32-S3-WROOM-1-N16R8. Solder the castellated edge pads; the centre GND pad is optional, since pins 1 and 40 are GND too. | 74xx logic except U2, both SRAMs, regulator, diodes, FET, MCP100, microSD socket, USB-C with U23, buttons, LEDs, bulk caps, microSD pull-ups, CC resistors | U2 (A0–A7 buffer, right above the B-side fingers), every 100 nF decoupling cap except C18, the control-line pull-ups and series resistors (R1, R3, R6–R16, R25, R26, R28, R29), C22 |
| U15 PIC12F629 (DIP-8), flashed with the SuperCIC key firmware, ideally beforehand | | |
| BT1 CR2032 holder (THT) | | |
| J3 ICSP header: optional, only for flashing the PIC in place | | |

Parts on both sides need **JLC Standard PCBA with two-sided assembly**. Economic PCBA is top-side only. The second side adds a setup fee to the quote.

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

Distances are measured from the board's left edge, with the label side facing the viewer.

| Feature | Position | Notes |
|---|---|---|
| microSD slot | centre 21.5 mm | the card sticks out above the top edge |
| USB-C | centre 62.5 mm | about 9 × 3.5 mm opening |
| ESP antenna | 85.5–103.5 mm | plastic is fine; no cutout strictly needed |
| Contact tab | centre 58.5 mm | |

The tallest parts are the PIC (DIP-8, about 4.5 mm without a socket) and the CR2032 holder (about 6 mm). `../cad/WSNES_Proto.step` can be loaded into a CAD tool to check them against the shell.

**The outline should be verified against an original cart with calipers before a housing is built.** It follows the standard Nintendo SNES PCB shape (body width, corner steps, side notches). If a PAL shell has posts in different places, please open an issue with the measurements. The outline is `OUTLINE` in `tools/gen_pcb.py`.

## Routing (v0.4)

The v0.3 routing came from freerouting: long detours, 3.9 m of signal on the inner planes, and odd tree shapes. For v0.4 all signal routing was removed. What is already done:

- **Power is finished.** Every SMD pad on GND, +5V or +3V3 has a short stub and a via into its plane (125 vias). THT pads reach the planes directly. Only U14 pin 1 and C17 pin 1 (+3V3) still need a short track. So the ratsnest now shows signals only, with no more "resistor to resistor" lines on the supply nets.
- **Decoupling caps are on the back, under their IC,** tied to the IC's supply via. Do not move them away.
- **Net classes colour the ratsnest** (View → Net colour mode: Ratsnest): red = Power, purple = USB, orange = Clock, blue = AddrBus (SA*, SNES_A*, SV_A*, EA19), green = DataBus (SD0–7, SNES_D0–7), grey = everything else.
- **Track widths and vias come from the net class.** Leave the width box on "use net class" (first entry), or cycle with W / Shift+W: 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.8 mm. Vias: 0.45/0.2, 0.5/0.25, 0.6/0.3, 0.8/0.4.

Why the ratsnest connected resistors to resistors: KiCad draws the shortest tree between all pads of a net. Ten pull-ups on +3V3 are one net, so their +3V3 pads got chained together. With the supplies now done through vias, those lines are gone. On a signal net with several loads (BUS_ESP goes to the ESP, a pull-up and 8 gate inputs), any tree is electrically correct. The ratsnest only suggests the shortest one; the net can be routed in any order.

### Suggested order

1. **USB** (purple): J5 → U23 → U21 pins 13/14, with the diff-pair router (key 6) on F.Cu.
2. **Clocks** (orange): SR_SCK and SR_LATCH from R28/R29 as one daisy chain along U9 → U10 → U11 → U12 → U13. Keep them short and away from the data bus.
3. **SNES edge to the buffers:** U2 is on the back right above fingers 10–17, so A0–A7 go straight on B.Cu with no via. U3, U4, U5 and U17 take the F-side fingers.
4. **Buses** (blue / green): SA* and SD* run between the buffers, the shift registers and both SRAMs. Use **F.Cu mostly horizontal and B.Cu mostly vertical**, and change layer with a via. That convention keeps crossings cheap.
5. **The rest** (grey), then the U14 / C17 +3V3 track.
6. Press B to refill the zones, then run DRC.

### Interactive router settings (Route → Interactive Router Settings)

These are KiCad user settings, not project settings, so they are not stored in the repository:

- **Mode: Shove** rather than Walk around. Shove pushes neighbouring tracks aside, which suits a dense bus board.
- Optimizer effort **High**. Enable *Smooth dragged segments*, *Remove redundant tracks* and *Smart pads*.
- *Allow DRC violations*: off.
- Useful keys: X route, 6 diff pair, V via while routing, / switch posture, D drag, L lock.

### Using freerouting

`freerouting/WSNES_Proto.dsn` now declares In1/In2 as power planes, so freerouting stays on the two outer layers. Route USB, the clocks and the edge-connector fan-out by hand first and **lock** them (L): locked tracks are exported as fixed wiring. Then:

    java -jar freerouting-2.5.0.jar -de freerouting/WSNES_Proto.dsn -do freerouting/WSNES_Proto.ses -mp 100

Import with **File → Import → Specctra Session**. Expect to clean up by hand.

### JLC order options

- 4 layers, **1.2 mm**, ENIG
- gold fingers with **45° bevel**
- assembly: **both sides**, using the two files in `production/jlc/`. Check rotations in JLC's placement preview on both sides. SOT-23 / SOT-23-5 / SOT-23-6 parts often need 180°, and bottom-side parts are shown mirrored.

## Save RAM (unchanged from v0.2)

- U16 is battery-backed and mapped to LoROM `$70-$7D:0000-7FFF`.
  - Since 2026-11-17 it is a CY62128ELL-45SXI (`C2953613`), because the AS6C1008-55SIN was out of stock. Same pinout and SOP-32 footprint.
  - The CY62128E is rated 4.5–5.5 V, but VSAVE is one BAT54C drop (≈ 0.35 V) below +5V, so it is only in spec while the console delivers about 4.9 V or more. Go back to the AS6C1008 (2.7–5.5 V) when it is in stock.
- U17 74HCT138 decodes the save area.
- U19 masks the size to match the ROM header.
- U20 MCP100 blocks writes below about 4.4 V.

The ESP copies the save to `<game>.srm` on SD on return to the menu or on reset. If the console is switched off mid-game, the battery keeps the save, and the ESP backs it up at the next power-up.

## Before ordering

Stock was checked on 2026-11-18 against the LCSC catalogue, which feeds JLC assembly:

- **Replaced, because the old parts were at 0:**
  - U1 AS6C4008-55SIN → **CY62148ELL-55SXI** (`C2953576`): same JEDEC pinout and 450-mil SOIC-32 land pattern, 4.5–5.5 V, 55 ns. Only **5** were in stock: order early, or source it separately and hand-solder it (the cheap variant does that).
  - U5 74AHCT245PW → **TI SN74AHCT245PWR** (`C10910`), same pinout.
  - U13 74HCT165PW → **TI SN74HCT165PWR** (`C3304572`), same pinout, still HCT.
- **Low but enough for a prototype:** U21 ESP32-S3-WROOM-1-N16R8 (11 in stock), U15 PIC12F629-I/P (12), U16 CY62128ELL-45SXI (63). U21 and U15 are hand-soldered anyway.
- **Everything else** is in stock in the thousands.
- JLC's parts page has the final word on stock at order time.

Still open from the 2026-11-17 production review:

- **Bench checks:**
  - Edge pinout: check continuity against an original cart. The finger at x = 177.5 (pin 5/36) must be GND on the same face.
  - Console /RESET driver: Q1 pulls pin 26 low by default. Measure whether the console drives that line push-pull before relying on it.
- **U16 supply:** the CY62128E is rated 4.5–5.5 V, and VSAVE is one BAT54C drop below +5V. Go back to the AS6C1008 (2.7–5.5 V) when it is in stock.
- **SNES 5 V budget:** ESP32 WiFi peaks reach about 350–500 mA. Lowering the TX power helps if the console struggles.
- **Timing:** SlowROM games have margin. FastROM games are marginal with HCT glue; AHCT versions of the glue chips would help.
- **USB-only power** (no console): only the ESP, SD and 3.3 V side is powered. The firmware must not drive the 5 V logic while `SNES_5V_SENSE = 0`. Also, the 10 k pull-ups R10–R16 go to +3V3 and feed the unpowered 5 V logic through its input clamp diodes (about 0.3 mA each). That is harmless, but it lifts the dead +5V rail a little.

## Bus map, GPIO map, firmware flow

These are unchanged from v0.2 and documented on the schematic sheet (`../docs/WSNES_Proto_schematic.pdf`):

- **Bus ownership:** a single `BUS_ESP` GPIO, pulled high, so the ESP owns the bus at power-up.
- **Shift word:** 32 bits, MSB first: `[DATA, A23..16 (A19 = save-chip select), A15..8, A7..0]`.

## Regenerate

Run these from `pcb/`.

```
python3 tools/gen_project.py .        # libraries + hierarchical schematic + net classes from tools/design.py
kicad-cli sch export netlist --format kicadsexpr -o /tmp/p.net WSNES_Proto.kicad_sch
python3 tools/verify_netlist.py /tmp/p.net tools/intended_pins.json
kicad-cli sch erc WSNES_Proto.kicad_sch

# after a schematic change: in KiCad, Tools -> Update PCB from Schematic (F8). Footprints are linked by path.
# tools/board_v04.py was the one-shot v0.4 conversion (rip-up, two-sided placement, power fan-out).
# Do not rerun it on a routed board: it removes all routing.
python3 tools/gen_pcb.py .            # DO NOT RUN: rebuilds the PCB from scratch and discards the placement

# production files
python3 tools/export_bom.py .
python3 tools/export_cheap.py .
kicad-cli sch export pdf -o ../docs/WSNES_Proto_schematic.pdf WSNES_Proto.kicad_sch
kicad-cli pcb export step -f -o ../cad/WSNES_Proto.step WSNES_Proto.kicad_pcb

# refill zones + full check
kicad-cli pcb drc --refill-zones --save-board --schematic-parity WSNES_Proto.kicad_pcb
```

`gen_project.py` updates only the net classes, the track/via presets and the rule minimums in `WSNES_Proto.kicad_pro`. Everything else set in KiCad (zone defaults, ERC map, plot settings) is kept.

BT1, J5 and U1/U16 use vendor models from `lib/3dmodels/`, because KiCad's 3D library has none for those footprints. See `lib/3dmodels/README.md` for where they come from and their offsets.
