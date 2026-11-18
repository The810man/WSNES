# WSNES v0.3 Production Review

**AI-agentic review, co-authored by The810man and Claude** (Claude Code with the kicad-happy 3.0.2 skill set).
The810man designed the board. Claude ran the analyzers, checked the results against the raw KiCad files and datasheets, and wrote this report.

| | |
|---|---|
| Project | `pcb/WSNES_Proto.kicad_pro`: 1 schematic sheet, 4-layer PCB, 89 parts, 177 nets |
| Files reviewed | schematic (KiCad 9 format), board (KiCad 10 format, file version 20260206), `.kicad_pro`, `.kicad_dru`, `production/jlc/*.csv` |
| Date | 2026-11-17, git `da63820` |
| Analyzers run | `analyze_schematic.py`, `analyze_pcb.py --full --proximity`, `cross_analysis.py`, `cross_verify.py`, `analyze_emc.py`, `analyze_thermal.py`, `lifecycle_audit.py` (LCSC only), `fab_release_gate.py`, deep-review pass plus `deep_review_gate.py`, `kicad-cli sch erc` |
| Evidence | Run `analysis/2026-11-17_1118/` (JSON, not in git), `analysis/deep_review.json`, `analysis/helpers/*.py` |

## Verdict

**Not ready to order as-is.** One blocker remains: copper pour fills the gold-finger tab on all four layers. It takes about 10 minutes to fix (one rule area plus a zone refill).

The electrical design is in good shape:

- ERC is clean.
- Schematic and PCB match pin for pin (590 pins, 141 multi-pin nets).
- Every net is routed as one copper island.
- Every logic IC has a 100 nF capacitor within 3.3 mm.
- The ESP32-S3 pin usage follows the Espressif datasheet.
- None of the 16 flagged 5 V/3.3 V crossings is a real problem.

Before ordering, also do the following:

1. Fix the tab copper.
2. Re-run DRC in KiCad 10.
3. Export gerbers and drill files.
4. Close the four verification items in the WARNING rows below. All of them can be done at the bench or in the JLC order form.

## Follow-up: fixes applied (2026-11-17, same day)

Made with the KiCad MCP tools and checked against the raw board file. None of this is in a committed release yet; see `CHANGELOG.md` → Unreleased.

| Finding | Status | What changed |
|---|---|---|
| Tab copper (CRITICAL) | **Fixed and verified** | Four `tab_no_pour` rule areas (F.Cu, In1, In2, B.Cu) over x 119–181, y ≥ 156, forbidding pour only. Fingers 5 and 36 (GND) had **no track at all**; they were grounded only through the pour, so they now have their own 0.6 mm F.Cu/B.Cu tracks and a GND via 1 mm above the fingers. The first KiCad 10 DRC then showed one more cut-off piece: the F.Cu GND patch feeding U5 pin 10, now tied to In1 with a GND via at (140.64, 150.2), 0.41 mm minimum clearance. After the refill, `tab_copper.py` measures 0 of 23 finger gaps with copper and 0 mm² within 1 mm of the tip, on every layer. |
| No USB ESD | **Fixed** | U23 USBLC6-2SC6 (LCSC C7519; pinout checked against the ST datasheet). Added to `design.py` and regenerated; ERC 0/0, netlist check 596 pins OK. Placed at (146.05, 95.25) and routed: D+, D−, VBUS, GND and the pin-1/6 and 3/4 flow-through links. 0 clearance violations (closest approach 0.26 mm against the 0.2 mm rule); all 177 nets routed, each one copper island. |
| No LCSC part numbers | **Mostly fixed** | 26 of 35 JLC BOM lines now have a verified LCSC number. **9 ICs have no JLC listing** in their family and package: AS6C4008, AS6C1008, 74HCT165, CD74HC4050, 74HCT138, 74AHCT541, 74AHCT245, 74HCT32, 74HCT157. Use JLC Global Sourcing, consign them, or hand-solder them. HCT drop-ins exist for the '541 (SN74HCT541PWR, C436096) and the '245 (74HCT245PW, C52140501), but they are slower than AHCT. |
| Edge pinout, console /RESET, 65 °C | Open | Bench and housing checks, unchanged. |
| DRC and gerbers (previously not performed) | **Done** | KiCad 10.0.8, zones refilled: 0 errors, 0 unconnected, schematic parity 0; only the two known `silk_edge_clearance` warnings at U21 remain. Gerber and drill test export: `analyze_gerbers.py` reports all layers present and aligned, 112.3 × 77.9 mm, 437 vias, no findings. |

## Critical Findings

| Severity | Issue | Section |
|---|---|---|
| CRITICAL | **Copper pour inside the gold-finger tab on all 4 layers.** GND slivers sit between the fingers, and a solid copper bar runs along the bevelled tip. The inner GND and +5V planes reach 0.3 mm from the bevel edge. | [Gold-finger tab](#gold-finger-tab) |
| WARNING | **Edge-connector pinout not checked against real hardware.** It is internally consistent and matches the published SNES numbering, but a left/right mirror would put +5V on a GND contact. | [Edge connector](#edge-connector-p1) |
| WARNING | **Q1 pulls the console's /RESET (pin 26) low by default** (R16 pulls the gate up to +3V3). This is only safe if the console drives that line open-drain or through a resistor. | [Transistor circuits](#transistor-circuits) |
| WARNING | **No ESD protection on the USB-C port.** D+/D- and VBUS go straight to the ESP32-S3 and D6. | [Interfaces](#interface-summary) |
| WARNING | **The JLC BOM has no LCSC part numbers**, and 57 of 89 parts have no MPN. Stock for the SRAMs, the CD74HC4050 and the connectors could not be confirmed. | [Sourcing](#sourcing-audit) |
| WARNING | **The ESP32-S3-WROOM-1-N16R8 is rated for 65 °C ambient at most** (octal-PSRAM variant), and it sits in a closed shell inside a warm console. | [Thermal](#thermal-analysis) |

## Gold-finger tab

*Raw-file verified with `analysis/helpers/tab_copper.py`, which reads the stored zone fills.*

| Layer | Copper in tab | Within 1 mm of tip | Pour between fingers | Pour at y = 164.0 (0.6 mm from tip) |
|---|---|---|---|---|
| F.Cu (GND) | 184.8 mm² | 33.4 mm² | 22 of 23 gaps | 23 of 23 |
| In1.Cu (GND plane) | 592.4 mm² | 40.9 mm² | 23 of 23 | 23 of 23 |
| In2.Cu (+5V plane) | 599.7 mm² | 40.9 mm² | 23 of 23 | 23 of 23 |
| B.Cu (GND) | 190.8 mm² | 33.4 mm² | 22 of 23 gaps | 23 of 23 |

Why this matters:

- **The bevel exposes copper.** The fingers end 1.1 mm before the tip (pads are 1.8 × 7 mm, y 156.5–163.5; the tip is at y 164.6). The zones fill the strip below them up to the 0.3 mm edge clearance. A 45° bevel on a 1.2 mm board grinds into that strip and comes within roughly 0.1–0.2 mm of the inner planes, which sit 0.245 mm below each surface.
- **Every console contact crosses that copper.** All contacts slide over the tip on every insertion.
- **The slivers between fingers will wear through.** They are only covered by solder mask, which wears off at the contact line.
- **The fab may stop the order.** Fabs commonly put gold-finger orders on hold when copper sits between fingers or at the bevel.

Nintendo boards have nothing in the tab except the fingers and their traces.

**Fix:**

1. **First** give GND fingers 5 and 36 their own tracks. They have none and are grounded only through the pour, so a no-pour area alone would disconnect the cart's ground. *(This step was missing from the first version of this report; it was found while applying the fix.)*
2. Add a rule area on F.Cu, In1.Cu, In2.Cu and B.Cu covering the finger band and tip (applied as x 119–181, y ≥ 156). Set it to forbid copper pour only; tracks and pads stay allowed.
3. Press `B` to refill the zones.
4. Re-run DRC.

## Previous Review Delta

This is the first review. There are no earlier review files or analyzer runs, so there is nothing to compare against.

## Component Summary

| Type | Count | Notes |
|---|---|---|
| ICs | 22 | 13× 74(A)HCT logic (TSSOP), 2× Alliance SRAM (SOP-32), ESP32-S3-WROOM-1, PIC12F629 (DIP-8), AP2112K-3.3, MCP100-450, CD74HC4050 |
| Resistors | 27 | 0603; 18× 10k |
| Capacitors | 26 | 20× 100 nF 0603, 22 µF/10 µF bulk |
| Diodes | 3 + 3 LEDs | 2× 1N5819WS (power OR-ing), BAT54C (battery switch) |
| Transistors | 1 | Q1 2N7002 |
| Connectors | 4 | P1 edge (46 contacts), J2 microSD, J3 ICSP, J5 USB-C |
| Other | 3 | 2× PTS810 switches, BT1 CR2032 holder |

There are 590 pins, 557 wires and 36 no-connect markers. The power rails are +5V, +3V3, ESP_5V, VBUS, VSAVE and VBAT.

MPN coverage is 32 of 89 parts (25 of 39 BOM lines). Every part without an MPN is a passive, an LED, or P1.

## Power Tree

```
SNES +5V (P1.27/58) ─┬─ +5V rail: all 74xx, U1 ROM-SRAM, U15 PIC, U20 MCP100-450, LED D2
                     │   bulk C2 22µF + 18× 100nF; In2 plane (lower part of board)
                     ├─ D1 1N5819WS ──┐
USB-C VBUS (J5) ─────── D6 1N5819WS ──┴─ ESP_5V (C1 22µF, C23 10µF)
                                          └─ U22 AP2112K-3.3 (EN tied to VIN, always on)
                                               └─ +3V3: U21 ESP32-S3, J2 microSD, U14 4050, pull-ups
                                                  C24 22µF, C26 10µF, C25 100nF; In2 plane (top strip)
+5V ── D4 BAT54C anode 1 ─┐
BT1 CR2032 ── R9 1k ── D4 anode 2 ─┴─ VSAVE (C18 100nF) ── U16 save SRAM VCC
U20 MCP100-450 /RST ── R6 1k ── U16 CE2 (R7 100k pull-down): writes blocked below 4.35–4.60 V
```

- **U22:** Vout is fixed at 3.3 V by the part (`vref_source: fixed_suffix`), so there is no feedback divider. The pinout (1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT) matches the AP2112 datasheet's pin table (p.2). The datasheet asks for ≥1 µF ceramic on input and output (p.1); the board has 32 µF on VIN and 32 µF on VOUT.
- **OR-ing:** with SNES and USB both connected, neither source back-feeds the other.
- **Save RAM:** the MCP100 trip point is 4.35–4.60 V with a 350 ms power-up hold (DS11187F p.2). CE2 stays low on battery, which the SRAM needs for data retention.
- **Battery:** the 1 kΩ resistor plus Schottky (BAT54C, reverse leakage ≤ 2 µA at 25 V per its datasheet) limits reverse current into the coin cell, as in Nintendo's own carts.

## Analyzer Verification

- **Component count:** 89 schematic parts = 89 footprints. All 89 match by reference, value and footprint, with no orphans or DNP conflicts.
- **Pin and pad nets:** I compared all 590 schematic pins against the PCB pad nets: 0 mismatches. All 141 multi-pin nets have the same pin sets on both sides, and the net count is 177 on both. *(Raw-file verified, from the analyzer's PCB pad data.)*
- **Board outline:** the analyzer warned that Edge.Cuts "does not close". That's a false positive. The 25 board-level lines leave a gap at (120, 153.5)–(180, 153.5), and P1's footprint Edge.Cuts closes it exactly with the tab (11.1 mm, 1 mm chamfers). The full board is 112.2 × 77.8 mm including the tab. *(Raw-file verified.)*
- **Copper connectivity (`--full`):** every net is one island, including GND, +5V and +3V3, with no disconnected pads. All 177 nets are routed.

### Pinout verification

| Ref | Part | Status | Basis |
|---|---|---|---|
| U22 | AP2112K-3.3 | Verified (datasheet) | Pin table p.2, SOT25 |
| U20 | MCP100T-450I/TT | Verified (datasheet, visual) | DS11187F p.1 SOT-23-3 drawing and p.9 outline numbering give 1 = RST, 2 = VDD, 3 = VSS, matching the footprint. The README listed this as open; it can be closed. |
| Q1 | 2N7002 | Verified (datasheet) | onsemi p.1: 1 Gate, 2 Source, 3 Drain |
| D4 | BAT54C | Verified (datasheet, visual) | Diodes Inc. p.1: anodes on 1 and 2, common cathode on 3 |
| U21 | ESP32-S3-WROOM-1-N16R8 | Verified (datasheet) | Pin table p.10–12. IO35/36/37 are NC (octal PSRAM, p.12). IO3/45/46 straps are NC. IO0 has a 10k pull-up and a button. EN uses the recommended 10k/1 µF (p.41). USB is on pin 13 (D-) and pin 14 (D+). |
| U15, J3 | PIC12F629 + ICSP | Verified (datasheet) | DIP-8: 1 VDD, 4 GP3/MCLR, 6 ICSPCLK, 7 ICSPDAT, 8 VSS. J3 follows the PICkit order (MCLR, VDD, GND, PGD, PGC). |
| U2–U13, U17–U19 | 74AHCT541/245, 74HCT00/08/32/138/157/165/595 | Unverified, low risk | Stock KiCad 74xx symbols on standard TSSOP footprints; datasheets downloaded for all but the '165. The 74LS08/32/157 symbols share pinouts with the HCT parts. |
| U14 | CD74HC4050 | Unverified, low risk | No datasheet found. The pinout matches the standard 4050, and unused inputs 5A/6A are tied to GND. |
| U1, U16 | AS6C4008 / AS6C1008 (SOP-32) | Unverified, plausible | No datasheet found. The symbols are the DIP versions; Alliance uses the same pin order for 32-pin SOP and PDIP. |
| D1, D6, LEDs, J2, J5, BT1 | — | Plausible | Stock KiCad symbols and footprints with the KiCad pad convention (pad 1 = cathode on SOD-323). |

### Edge connector (P1)

| x (mm) | B.Cu pin | Net | F.Cu pin | Net |
|---|---|---|---|---|
| 177.5 | 5 | GND | 36 | GND |
| 175.0 → 147.5 | 6 → 17 | A11 → A0 | 37 → 48 | A12 → A22, then A23 (NC) |
| 145.0 | 18 | /IRQ (NC) | 49 | /ROMSEL |
| 142.5 → 135.0 | 19 → 22 | D0 → D3 | 50 → 53 | D4 → D7 |
| 132.5 | 23 | /RD | 54 | /WR |
| 130.0 / 127.5 | 24 / 25 | CIC_D1 / CIC_RST | 55 / 56 | CIC_D0 / CIC_CLK |
| 125.0 | 26 | /RESET | 57 | SYSCLK (NC) |
| 122.5 | 27 | +5V | 58 | +5V |

GND (5/36) and +5V (27/58) sit at the same x on both faces, so swapping front and back would only swap signals. A left/right mirror, however, would put +5V on a GND contact.

**Before ordering**, take an original cart and check continuity from its ROM GND pin to the finger that this board puts at x = 177.5 (pin 5/36), with the label side facing the same way as here. Also confirm the CIC data direction (pins 24/55 vs. PIC GP0/GP1) against the SuperCIC key firmware that will be flashed.

## Deep Review

The full findings are in `analysis/deep_review.json` (gate result: 7 verified, 0 quarantined).

- **Gold-finger tab copper** (manufacturing, error): see [above](#gold-finger-tab).
- **ESP32-S3-WROOM-1-N16R8, 65 °C ambient limit** (warning, datasheet p.3: "R8 and R16V series modules operate at –40 ~ 65 °C ambient temperature"):
  - A cart shell sitting in a running console can get warm.
  - U22 dissipates up to about 0.3 W roughly 15 mm from the module.
  - Leave PSRAM ECC off; it lowers the limit further.
- **Q1 drives /RESET by default** (interface, warning, low confidence):
  - RST_GATE = {Q1.G, R1, R16}, and R16 goes to +3V3.
  - So Q1 conducts during ESP boot and until GPIO17 drives low.
  - See [Transistor circuits](#transistor-circuits).
- **U22 thermal** (info): see [Thermal](#thermal-analysis).
- **Confirmed correct:** IO35–37 left NC, the EN RC values, and the Q1 pad map.

## Signal Analysis Review

### Power regulators
U22 is an LDO from ESP_5V to +3V3 with a 600 mA minimum rating (datasheet p.1). Dropout at 600 mA is 250 mV typical and 400 mV maximum, and VIN is about 4.6 V, so there is enough headroom.

### Dividers and RC networks
Checked by hand; no SPICE simulator is installed.

- **R25/C22:** 10 kΩ × 1 µF gives τ = 10 ms (fc = 15.9 Hz), the ESP32 EN delay Espressif recommends.
- **R6/R7:** not really a divider. It's a series resistor plus a pull-down on CE2, so CE2 = PWR_OK × 100/101.

### Level translation (VM-001 ×16, all false positives)

- **Direction 1:** ESP32 outputs (3.3 V) drive 74HCT/AHCT inputs. Their TTL threshold is V_IH = 2.0 V, so 3.3 V is a valid high (SR_*, SAVE_*, BUS_ESP, *_OE_N, *_WE_N).
- **Direction 2:** every 5 V output headed for the ESP passes through U14 (CD74HC4050 at 3.3 V): RB_Q7, SNES_WE_N, SNES_RESET_N and V5_SENSE.
- No 5 V output connects directly to an ESP32 pin.

### Transistor circuits
Q1 (2N7002, V_GS(th) ≤ 2.5 V per p.2) pulls cart pin 26 /RESET to GND through its channel, with no drain resistor.

- R16 (10k to +3V3) holds it on by default. The design intent (docs/masterplan.md) is to hold the SNES in reset while loading.
- **Risk (inference, not verified):** if the console drives /RESET with a push-pull output, Q1 shorts that output to GND whenever it's on.
- **Check on a console:** pull pin 26 low through 100 Ω and measure the current. Tens of mA would mean a push-pull driver.
- **If it's push-pull:** add about 100–220 Ω in Q1's drain, or reset through the CIC instead.

### LED circuits

| LED | Supply | R | Estimated I_F | Note |
|---|---|---|---|---|
| D2 red | +5V | 1k | ~3 mA | ok |
| D3 green | PIC GP4 (5 V) | 1k | ~3 mA | ok |
| D7 blue | ESP IO48 (3.3 V) | 1k | **~0.1–0.4 mA** | Blue V_F (~2.8–3.2 V) leaves almost no headroom, so it will be very dim. Use 100–150 Ω, or a red/green LED. |

### Bus Topology

- **SNES side:** parallel buses for the edge address A0–A22 and data D0–D7, the SRAM address SA0–SA18 and data SD0–SD7, and the save-mask bits SAVE_M11–M14.
- **ESP shift chain:** an SPI-style link (SR_SCK, SR_MOSI → 4× '595; '165 → SR_MISO via U14, latched by SR_LATCH and RD_LOAD_N). See the ringing note under [Signal integrity](#signal-integrity).
- **SD card:** SPI mode on IO1/2/41/42.
- **No I²C, CAN or UART:** UART0 is left NC, and the console runs over USB-Serial/JTAG.

### Decoupling (from the PCB analyzer, measured on the board)
The closest 100 nF to each IC: U8, U13, U14: 1.56 mm; U2, U5: 1.66 mm; U17: 1.69 mm; most of the others: 2.0–2.2 mm; U15: 3.0 mm; U16: 3.3 mm.

U20 (MCP100) has no capacitor within 10 mm. It's a 45 µA part on the +5V plane, so this is low risk, but an optional 100 nF would help keep the trip point stable.

## Power Analysis

### Power Budget

| Rail | Estimated load | Source | Note |
|---|---|---|---|
| +3V3 | ~250 mA typ (ESP32-S3 ~240 mA, 4050 ~10 mA), WiFi peaks 350–500 mA | U22, 600 mA min | 42 % of rating on average |
| +5V | ~185 mA (analyzer's flat 10 mA × 18 ICs), plus the ESP_5V branch | SNES console regulator | About 0.45 A total from the console, peaking near 0.7 A |
| VSAVE | SRAM standby (µA range) | +5V through D4, or the CR2032 | — |

The console's 5 V regulator also powers the console itself, so the WiFi peaks are the main risk. This is already noted in `pcb/README.md`; capping TX power helps.

The analyzer's 425 mW LDO figure assumes VIN = 5.0 V. With the OR-ing diode it is about 325 mW at 250 mA.

### PDN Impedance
Analyzer model: MLCC parasitics only, with no plane capacitance, so it's pessimistic above about 100 MHz.

| Rail | Capacitors | Total | Minimum \|Z\| | Anti-resonance |
|---|---|---|---|---|
| +5V | 18 | 23.7 µF | 6.3 mΩ at 1 MHz | 31 mΩ at 4 MHz |
| +3V3 | 4 | 32.2 µF | 6.7 mΩ at 1.3 MHz | 66 mΩ at 79 kHz |
| VSAVE | 1 | 100 nF | 0.32 Ω at 20 MHz | — |

The +3V3 target impedance is 0.33 Ω (5 % ripple at a 0.5 A step), and the rail meets it below 200 MHz (PD-001). The ESP module has its own internal decoupling. VSAVE only feeds the slow save SRAM, so 100 nF is enough.

### Power Sequencing

- There is one regulator, and its EN is tied to VIN, so +3V3 follows ESP_5V. +5V (console) and +3V3 come up independently.
- **USB-only power** is the case that matters. The ESP pull-ups R10–R15 (10 kΩ to +3V3) feed HCT/AHCT inputs whose +5V rail is unpowered, so they back-feed that rail through the input clamp diodes. Each pull-up passes ≲0.3 mA. D2's load keeps the floating rail at about 2 V, and the MCP100 holds CE2 low the whole time, so the save RAM stays protected. *(Inference: the AHCT input structure wasn't checked against its datasheet.)*
- This is consistent with the firmware rule in `pcb/README.md`: don't drive the 5 V logic while `SNES_5V_SENSE = 0`.
- On power-up, R16 holds the SNES in reset until GPIO17 releases it (see [Transistor circuits](#transistor-circuits)).

### Sleep Current Audit
The board has no sleep mode; it runs from the console or USB. The analyzer's 3.1 mA "always-on" and 5.95 mA "realistic" figures come from pull-ups and LED D2 on those rails, so they don't matter here.

What does matter is the **battery retention current**. On battery, only VSAVE is powered: BT1 → R9 → D4 → U16 (standby, CE2 low through R7). Nothing else connects to VSAVE, so the CR2032's drain is the SRAM's standby current plus D4's leakage, typically in the low-µA range. That gives a battery life of several years. The AS6C1008 datasheet wasn't available, so I couldn't confirm its standby current figure.

### Inrush Analysis
- **Inrush:** at power-up the console or USB host must charge 22 + 10 µF on ESP_5V plus about 32 µF on +3V3. There is no soft start; only the diode and trace resistance limit the peak. USB 2.0 allows 10 µF on a hot-plugged device, so the USB port exceeds that formal limit. Most ESP32 DevKits do too, and hosts tolerate it in practice. The analyzer estimates 0.21 A of inrush into the +3V3 output caps.

### Voltage Derating and Current Capacity
- **Voltage derating:** the 22 µF/10 µF parts on 5 V nets should be rated 10 V or more, ideally 16 V, because X5R capacitance drops with DC bias. There are no MPNs yet, so pick them when assigning LCSC parts.
- **Trace current capacity:**
  - ESP_5V: 0.4 mm on F.Cu, VBUS: 0.24–0.4 mm, +3V3: 0.4 mm. All are adequate for 0.6 A at 1 oz (IPC-2221 gives about 1 A for a 10 °C rise on a 0.4 mm external track).
  - +5V is fed through the In2 plane, which is 0.5 oz copper.

## PCB Layout Analysis

### Board overview

| Item | Value |
|---|---|
| Size | 112.2 × 66.7 mm body + 11.1 mm tab = 112.2 × 77.8 mm |
| Layers | 4; 1.2 mm total |
| Copper | F.Cu 35 µm / In1 15.2 µm / In2 15.2 µm / B.Cu 35 µm |
| Dielectric | 0.21 mm prepreg to each inner layer |
| Finish | ENIG |
| Placement | 86 SMD + 3 THT, all on F.Cu |
| Vias | 433 |

### Copper planes

- **In1:** GND.
- **In2:** +3V3 in the top strip (y < 113.3) and +5V below it.
- **F.Cu and B.Cu:** GND pours.

The planes carry signals as well: freerouting placed about 1.7 m (In1) and 2.2 m (In2) of track on them, which is why EMC GP-001 fires 88 times. At SNES bus speeds this is acceptable, and every net still forms a single island. Keep RF-area routing off the planes in future spins.

### Antenna

The U21 antenna section (y 86.85–92.85) sits flush with the top board edge. The footprint's own rule area covers x 162–210, y 71.85–92.85 on all four copper layers, blocking tracks, vias, pads, pours and footprints. That matches Espressif's on-board-edge placement option, and DRC enforces it.

The analyzer's `keepout_zones` list misses this zone because it only lists board-level rule areas.

### Edge clearance

The analyzer measured edge clearance to the outline's bounding box, so its PM-002 numbers are unreliable. Measured against the real outline, the closest copper pads to the edge are:

| Part | Clearance | Note |
|---|---|---|
| J2 | 0.62 mm | microSD, overhangs the edge by design |
| C2 | 0.99 mm | |
| C16 | 1.03 mm | |
| P1 | 1.10 mm | |
| BT1 | 2.20 mm | |

The board rule is 0.3 mm. BT1's *body* is about 0.35 mm from the edge, which only matters for the housing wall.

### Signal integrity

- **Shift-register lines:** SR_SCK is 96 mm long with 6 vias and drives 5 loads; SR_LATCH is 81 mm with 5 vias. Both swap reference planes between In1 and In2. They are fast-edged ESP outputs into a multi-drop line, so expect some ringing. A 22–33 Ω series resistor at the ESP (next spin), or a lower GPIO drive strength in firmware now, removes the double-clocking risk on the '595/'165.
- **USB:** D+ is 36.4 mm on B.Cu and D- is 34.3 mm, mostly on In1. That's a 2.1 mm difference, far inside Full-Speed (12 Mbit/s) tolerance, but they are not routed as a coupled pair. Route them as a pair next spin.

### DFM

| Item | Value |
|---|---|
| Minimum track / space | 0.15 / ~0.152 mm |
| Normal vias | 0.45–0.5 mm / 0.2–0.25 mm drill |
| Fine via | One 0.3/0.15 mm GND via (U12-8) |

- The analyzer rates the fine via "challenging" because it uses a generic 0.1 mm annular-ring limit.
- The JLCPCB multilayer table allows 0.25 mm / 0.15 mm, so the via is fabricable. Pick the matching minimum via option on the order form, which may cost extra.
- The fine via is below IPC Class 2 annular ring, which is acceptable for this product.

### Fiducials and test points

- There are no fiducials. The analyzer's "BGA/fine-pitch QFN present" is wrong: the finest pitch is 0.65 mm TSSOP. JLC places these by pad recognition, or adds fiducials on panel rails, so this is a suggestion only.
- There are no test points (0 of 174 nets). Add pads for +5V, +3V3, VSAVE and GND next spin; they help bring-up.

### Silkscreen

- The board name, rev v0.3, and stackup/bevel note are on B.SilkS.
- 85 of 89 reference designators are hidden. Consider showing at least the hand-soldered parts (U21, U15, BT1, J3).
- Label SW1 BOOT and SW2 RESET.

## Thermal Analysis

`analyze_thermal.py` skipped U22 (no dissipation model), so I calculated it by hand with `analysis/helpers/ldo_thermal.py`. Inputs: θ_JA = 184 °C/W (AP2112 p.3, SOT25 with no heatsink, so a worst case), and VIN = 4.6 V.

| Ambient | 150 mA (WiFi average) | 250 mA (busy) | 500 mA sustained |
|---|---|---|---|
| 25 °C | 61 °C | 85 °C | 145 °C |
| 40 °C | 76 °C | 100 °C | **160 °C**, above the 150 °C maximum |

Normal use is fine. A sustained 500 mA isn't a realistic WiFi load (TX current comes in bursts), and the board's GND pour lowers the real θ_JA. Limiting TX power in firmware keeps a margin during long uploads.

The bigger thermal limit is the ESP module's 65 °C ambient rating (see the [Deep Review](#deep-review)).

There are no exposed-pad parts apart from U21. U21's centre GND pad has 12 thermal vias, which the analyzer rates adequate (9 minimum).

## EMC / Cross-Domain Analysis

- **EMC risk score:** 40/100 (54 errors, 61 warnings). These are heuristic pre-compliance screens, **not a compliance result**.
- **What drives the score:** GP-001/RP-001 (signals on the inner planes, explained under [Copper planes](#copper-planes)). The board runs inside a grounded console, so I accept these.
- **One real gap:** no ESD protection on J5 USB-C (IO-001/EG-001). Recommendation: add a USBLC6-2SC6 (or similar) at J5 for D+/D-/VBUS next spin, or at least before a production run that strangers will plug in.
- **CE/FCC:** the module is pre-certified (CERT-001). An end product still needs its own assessment if it is sold. Selling is excluded by the licence anyway without permission.
- **Cross-analysis:** XV-001..004 report no schematic/PCB mismatch. XV-004 skipped MPN comparison for 57 parts that have no MPN.

## Interface Summary

- **P1, SNES edge:** 46 contacts, LoROM bus, CIC on the SuperCIC PIC. See the [table above](#edge-connector-p1). No ESD protection, the same as Nintendo carts.
- **J5, USB-C:**
  - Device (UFP) role, with 5.1 kΩ on CC1 and CC2, which is correct.
  - Both D+/D- rows are tied together.
  - VBUS goes through D6.
  - **No ESD protection.**
- **J2, microSD:**
  - SPI mode at 3.3 V.
  - 10 kΩ pull-ups on CMD, DAT0–3 and card detect (IO38).
- **J3, ICSP:** PICkit pin order.
  - Pin 2 powers the whole +5V rail, which includes the ESP through D1. A PICkit can't supply that.
  - Flash the PIC off-board (as `pcb/README.md` already suggests), or power the board from a console or bench supply while flashing.

## USB Compliance

| Check | Result |
|---|---|
| CC1 and CC2: 5.1 kΩ to GND (R23, R24) | Pass, sink role |
| D+/D- series resistors | Not needed; the ESP32-S3 has an internal PHY |
| ESD protection on D+/D-/VBUS | **Fail**, see WARNING |
| Capacitor directly on VBUS | Fail (analyzer). C23 10 µF sits behind D6 on ESP_5V, so VBUS itself sees almost no capacitance. Fine functionally; a 1 µF on VBUS is optional. |
| D+/D- routing | 36.4 / 34.3 mm, 2 vias each, different layers; fine for Full Speed |

## Quality & Manufacturing

### BOM Optimization

- There are 5 resistor values (10k, 1k, 5.1k, 100R, 100k) and 4 capacitor values, across 20 unique footprints.
- 22 µF appears in both 1206 (C1, C2) and 0805 (C24). Standardizing on one saves a JLC feeder.
- Three values are used only once: R1 100 Ω, R7 100 kΩ and C22 1 µF.

### Sourcing audit

- **MPN coverage:** 32 of 89 parts. The 57 without an MPN are generic R/C/LED parts plus P1.
- **JLC BOM** (`production/jlc/WSNES_BOM_JLC.csv`): the `LCSC Part #` column is empty. Fill it in before ordering; JLC's auto-match by value is unreliable for X5R voltage ratings and LED colours.
- **Datasheets:** synced through the no-key LCSC API, 15 of 24.
- **Stock not confirmed** (the API search returned nothing even for the common 74HCT165): AS6C4008-55SIN, AS6C1008-55SIN, CD74HC4050PWR, DM3AT-SF-PEJM5, TYPE-C-31-M-12.
- **If JLC can't source the SOP-32 SRAMs**, they can be hand-soldered (1.27 mm pitch) or consigned.

### Component lifecycle

`lifecycle_audit.py` ran against LCSC only. That source has no lifecycle data, so all 23 MPNs came back as *unknown*. **The lifecycle audit is effectively not done.** It needs DigiKey, Mouser or element14 API keys.

From general knowledge, and not verified: the PIC12F629 and AS6C-series SRAMs are older but still in production, and none of the parts are known to be EOL.

### CPL check

`production/jlc/WSNES_CPL_JLC.csv` matches the routed board exactly: 84 rows with 0 position, rotation or side mismatches. P1 and the four hand-soldered parts are correctly left out.

The rotations are raw KiCad values. SOT-23, SOT-23-5 and SOD-323 parts usually need a 180° offset at JLC, so check every part in their placement preview.

### Ordering notes

- 4 layers, **1.2 mm**, ENIG, green mask, 1 oz outer / 0.5 oz inner, board 112.2 × 77.8 mm (above the 100 × 100 mm price tier).
- **Gold fingers with 45° bevel** (after the tab fix).
- Minimum via 0.3/0.15 mm option, for the single fine via.
- Assembly: top side only, SMD only, stencil included.
- Hand-solder U21 (castellated), U15 (DIP-8, flashed first), BT1 and J3 (optional).

## False Positives / Reviewer Overrides

| Analyzer finding | Verdict |
|---|---|
| Edge.Cuts "does not close" | False. P1's footprint draws the tab and closes the outline. |
| PP-001 U22 VIN has no DC path | False. It is fed through Schottky diodes D1/D6, which the analyzer's graph walk doesn't follow. |
| VM-001 ×16 5 V/3.3 V crossings | False. HCT TTL thresholds and the 4050 down-shifter cover every case. |
| PM-002 BT1 0.35 mm / J2 0.07 mm / C16 0.77 mm | Measured against the bounding box. Real copper clearance is ≥ 0.62 mm; J2 is edge-mounted by design. |
| DFM-001 error: annular ring 0.075 mm | Within JLC's multilayer 0.25/0.15 via table. Downgraded to an order-form note. |
| FD-001 error, "BGA/fine-pitch QFN present" | No BGA/QFN on the board. Downgraded to a suggestion. |
| RS-001 VBAT has no source | The source is the coin cell. |
| DC-002 U20 no decoupling | Low-risk supervisor on the +5V plane. Kept as a suggestion. |
| IO-001 J5 no EMC filtering | Filtering isn't needed for a Full-Speed debug port. **The ESD part of this finding is valid** (WARNING). |
| GP-001 ×88, RP-001 ×21, GP-004 | Accepted for this design (inner-plane signal routing). |
| Thermal "SKIPPED" | Replaced by the hand calculation above. |
| cross_verify decoupling "not found" | Tool bug (it keys on rails instead of ICs). I used `decoupling_placement` from the PCB analyzer instead. |
| Lifecycle all "unknown" | Limitation of the LCSC source, not a finding. |

## Positive Findings

1. The schematic and PCB match exactly: 590 pins and 141 nets, with no mismatches.
2. Every net is routed and forms a single copper island, including the GND, +5V and +3V3 planes that carry signal tracks.
3. Every logic IC has a 100 nF capacitor within 3.3 mm, most within 2.2 mm.
4. ESP32-S3 integration follows the datasheet: octal-PSRAM pins are free, strapping pins are safe, EN uses 10k/1 µF, and the antenna sits at the edge with a DRC-enforced keepout on all layers.
5. The save RAM is properly protected: write lockout at 4.35–4.60 V (MCP100-450), CE2 pull-down for retention, and a current-limited, diode-isolated coin cell.
6. The diode-ORed 5 V inputs allow USB-only flashing without back-feeding the console.
7. The production CPL matches the routed board exactly.

## Not Performed / Review Limits

- **KiCad DRC not re-run.** The board is saved in KiCad 10 format and this machine has only KiCad 9.0.9, which can't load it. The README's KiCad 10 result (0 errors, 0 unconnected, parity 0) is taken as reported. **Re-run it after the tab fix.**
- **Gerber/drill analysis not performed.** There are no fabrication outputs in the repo, and KiCad 9 can't export this board. Export from KiCad 10, then run `analyze_gerbers.py`.
- **SPICE not performed.** No ngspice, LTspice or Xyce is installed. The two detected subcircuits were checked by hand (above).
- **Lifecycle audit:** effectively not performed; only LCSC was queried, and it has no lifecycle data.
- **Datasheets:** 15 of 24 MPNs downloaded, kept locally in `pcb/datasheets/` and not committed (third-party PDFs). No datasheet was available for AS6C4008/AS6C1008, CD74HC4050, 74HCT165, the USB-C, microSD or holder; their pinouts are plausibility checks only. No structured extraction cache was built.
- **Edge-connector pinout and the console /RESET driver** can only be confirmed on real hardware.
- **Previous review delta:** not applicable (first review).

## All Issues & Suggestions

| Severity | Issue | Action |
|---|---|---|
| CRITICAL | Pour copper in gold-finger tab, all layers | GND tracks for fingers 5/36 first, then a no-pour rule area on all 4 layers, refill, DRC. *Applied 2026-11-17; refill and DRC pending.* |
| WARNING | Edge pinout not checked on hardware | Continuity check against an original cart; confirm CIC data direction |
| WARNING | Q1 forces /RESET low by default | Measure the console driver; add a drain resistor if it's push-pull |
| WARNING | No USB ESD | USBLC6-2SC6 at J5. *Applied 2026-11-17 as U23.* |
| WARNING | No LCSC part numbers; SRAM/4050/connector stock unknown | Fill in the JLC BOM. *26 of 35 lines filled on 2026-11-17; 9 ICs have no JLC listing and need Global Sourcing, consignment or hand-soldering.* |
| WARNING | ESP module rated 65 °C ambient | Ventilate the housing near U21/U22; leave PSRAM ECC off |
| SUGGESTION | 0.3/0.15 mm via | Select the via option on the order form, or re-route U12-8 |
| SUGGESTION | D7 blue LED too dim at 3.3 V/1k | R27 → 100–150 Ω |
| SUGGESTION | SR_SCK/SR_LATCH multi-drop ringing risk | Reduce ESP drive strength now; 22–33 Ω series R next spin |
| SUGGESTION | No fiducials, no test points | Add 3 fiducials and power-rail test pads next spin |
| SUGGESTION | U20 has no local capacitor | Optional 100 nF |
| SUGGESTION | Silkscreen: BOOT/RESET labels, refs of hand-soldered parts | Documentation |
| SUGGESTION | USB pair split across layers | Route as a coupled pair next spin |
| SUGGESTION | CPL rotations | Check each part in JLC's placement preview |
| SUGGESTION | X5R voltage rating on 5 V bulk capacitors | ≥ 10 V (preferably 16 V) when picking LCSC parts |
