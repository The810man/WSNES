# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 The810man
"""WSNES cart v0.3 (mixed SMD/THT, fits the standard SNES PCB outline) — single source of truth.

Every part lists its connections as {pin_number: net}. Special nets:
  '+5V', '+3V3', 'GND'  -> power symbols
  None                 -> no-connect flag
Everything else becomes a local net label.

asm='JLC'  -> assembled by JLCPCB (SMD)
asm='HAND' -> ordered and soldered by you (ESP module, PIC, battery holder, optional ICSP header)
"""

import os
# Symbol snapshot (KiCad 9 library versions, taken from the schematic's embedded cache on 2026-11-17).
# Regeneration must not depend on the installed KiCad: the KiCad 10 library renames some pins
# (e.g. the microSD/USB-C shield pins), which would break the pin assignments below.
SYMDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'symcache') + os.sep
PROJLIB = 'WSNES_Proto'

# ---------------------------------------------------------------- helpers
def bus(prefix, rng):
    return ['%s%d' % (prefix, i) for i in rng]

def mapn(pins, nets):
    assert len(pins) == len(nets), (pins, nets)
    return dict(zip([str(p) for p in pins], nets))

FP_R = 'Resistor_SMD:R_0603_1608Metric'
FP_C = 'Capacitor_SMD:C_0603_1608Metric'
FP_C0805 = 'Capacitor_SMD:C_0805_2012Metric'
FP_C1206 = 'Capacitor_SMD:C_1206_3216Metric'
FP_LED = 'LED_SMD:LED_0603_1608Metric'
FP_SOT23 = 'Package_TO_SOT_SMD:SOT-23'
FP_TSSOP20 = 'Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm'
FP_TSSOP16 = 'Package_SO:TSSOP-16_4.4x5mm_P0.65mm'
FP_TSSOP14 = 'Package_SO:TSSOP-14_4.4x5mm_P0.65mm'
FP_SOP32 = 'Package_SO:SOP-32_11.305x20.495mm_P1.27mm'
FP_SOD323 = 'Diode_SMD:D_SOD-323'

parts = []
def part(ref, lib, sym, value, fp, pos, conns, unit_pos=None, asm='JLC', mpn='', **kw):
    parts.append(dict(ref=ref, lib=lib, sym=sym, value=value, fp=fp, pos=pos, asm=asm, mpn=mpn,
                      conns={str(k): v for k, v in conns.items()}, unit_pos=unit_pos or {}, **kw))

SNES_A = bus('SNES_A', range(23))
SNES_D = bus('SNES_D', range(8))
SA = bus('SA', range(19))
SD = bus('SD', range(8))

# ---------------------------------------------------------------- SNES edge + CIC
edge = {5: 'GND', 36: 'GND', 27: '+5V', 58: '+5V',
        17: 'SNES_A0', 16: 'SNES_A1', 15: 'SNES_A2', 14: 'SNES_A3', 13: 'SNES_A4', 12: 'SNES_A5',
        11: 'SNES_A6', 10: 'SNES_A7', 9: 'SNES_A8', 8: 'SNES_A9', 7: 'SNES_A10', 6: 'SNES_A11',
        37: 'SNES_A12', 38: 'SNES_A13', 39: 'SNES_A14', 40: 'SNES_A15',
        41: 'SNES_A16', 42: 'SNES_A17', 43: 'SNES_A18', 44: 'SNES_A19',
        45: 'SNES_A20', 46: 'SNES_A21', 47: 'SNES_A22', 48: None,
        49: 'SNES_ROMSEL_N',
        19: 'SNES_D0', 20: 'SNES_D1', 21: 'SNES_D2', 22: 'SNES_D3',
        50: 'SNES_D4', 51: 'SNES_D5', 52: 'SNES_D6', 53: 'SNES_D7',
        23: 'SNES_RD_N', 54: 'SNES_WR_N', 18: None,
        24: 'CIC_D1', 25: 'CIC_RST', 55: 'CIC_D0', 56: 'CIC_CLK',
        26: 'SNES_RESET_N', 57: None}
part('P1', PROJLIB, 'SNES_Cart_Edge', 'SNES_Cart_Edge',
     PROJLIB + ':SNES_Cart_Edge_46P_P2.50mm', (63.5, 99.06), edge, asm='PCB')

part('U15', 'MCU_Microchip_PIC12', 'PIC12F629-xP', 'PIC12F629 (SuperCIC key)', 'Package_DIP:DIP-8_W7.62mm',
     (63.5, 180.34), {1: '+5V', 8: 'GND', 2: 'CIC_CLK', 3: 'CIC_LED', 4: 'CIC_PAIR_N',
                      5: 'CIC_RST', 6: 'CIC_D1', 7: 'CIC_D0'}, asm='HAND', mpn='PIC12F629-I/P')
part('J3', 'Connector_Generic', 'Conn_01x05', 'ICSP (PIC, optional)',
     'Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical', (55.88, 218.44),
     {1: 'CIC_PAIR_N', 2: '+5V', 3: 'GND', 4: 'CIC_D0', 5: 'CIC_D1'}, asm='HAND', mpn='(optional)')
part('R2', 'Device', 'R', '10k', FP_R, (93.98, 210.82), {1: '+5V', 2: 'CIC_PAIR_N'})
part('R4', 'Device', 'R', '1k', FP_R, (93.98, 233.68), {1: 'CIC_LED', 2: 'LED_CIC_A'})
part('D3', 'Device', 'LED', 'LED green (CIC OK)', FP_LED, (93.98, 254.0), {2: 'LED_CIC_A', 1: 'GND'})

# ---------------------------------------------------------------- SNES-side buffers (5 V)
OE541 = {1: 'BUS_ESP', 19: 'BUS_ESP', 20: '+5V', 10: 'GND'}
IN541 = [2, 3, 4, 5, 6, 7, 8, 9]          # A0..A7
OUT541 = [18, 17, 16, 15, 14, 13, 12, 11]  # Y0..Y7
part('U2', '74xx', '74HCT541', '74AHCT541', FP_TSSOP20, (157.48, 60.96),
     {**OE541, **mapn(IN541, SNES_A[0:8]), **mapn(OUT541, SA[0:8])}, mpn='74AHCT541PW')
part('U3', '74xx', '74HCT541', '74AHCT541', FP_TSSOP20, (157.48, 119.38),
     {**OE541, **mapn(IN541, SNES_A[8:15] + ['SNES_A16']), **mapn(OUT541, SA[8:16])}, mpn='74AHCT541PW')
part('U4', '74xx', '74HCT541', '74AHCT541', FP_TSSOP20, (157.48, 177.8),
     {**OE541, **mapn(IN541, SNES_A[17:20] + ['GND'] * 5), **mapn(OUT541, SA[16:19] + [None] * 5)}, mpn='74AHCT541PW')
part('U5', '74xx', '74HC245', '74AHCT245', FP_TSSOP20, (157.48, 236.22),
     {1: 'SNES_RD_N', 19: 'DBUF_OE_N', 20: '+5V', 10: 'GND',
      **mapn(IN541, SNES_D), **mapn(OUT541, SD)}, mpn='74AHCT245PW')

# ---------------------------------------------------------------- ROM SRAM (game image)
sram_addr = {12: 'SA0', 11: 'SA1', 10: 'SA2', 9: 'SA3', 8: 'SA4', 7: 'SA5', 6: 'SA6', 5: 'SA7',
             27: 'SA8', 26: 'SA9', 23: 'SA10', 25: 'SA11', 4: 'SA12', 28: 'SA13', 3: 'SA14',
             31: 'SA15', 2: 'SA16', 30: 'SA17', 1: 'SA18'}
sram_data = {13: 'SD0', 14: 'SD1', 15: 'SD2', 17: 'SD3', 18: 'SD4', 19: 'SD5', 20: 'SD6', 21: 'SD7'}
part('U1', 'Memory_RAM', 'AS6C4008-55PCN', 'AS6C4008-55SIN (ROM, 512K x 8)', FP_SOP32,
     (256.54, 86.36), {**sram_addr, **sram_data, 22: 'SRAM_CE_N', 24: 'SRAM_OE_N', 29: 'SRAM_WE_N',
                       32: '+5V', 16: 'GND'}, mpn='AS6C4008-55SIN')

# ---------------------------------------------------------------- glue logic (5 V, HCT inputs accept 3.3 V)
# U8 is AHCT (pin-compatible): it sits in the /ROMSEL -> SRAM /CE path and saves ~24 ns worst case
# against the HCT157 (34 -> 9.8 ns), which helps FastROM timing.
part('U8', '74xx', '74LS157', '74AHCT157', FP_TSSOP16, (256.54, 162.56),
     {1: 'BUS_ESP', 15: 'GND', 16: '+5V', 8: 'GND',
      2: 'ROM_SEL_N', 3: 'EA19', 4: 'SRAM_CE_N',          # ROM chip /CE
      5: 'SNES_RD_N', 6: 'ESP_OE_N', 7: 'SRAM_OE_N',      # shared /OE
      11: 'SNES_WE_N', 10: 'ESP_WE_N', 9: 'SRAM_WE_N',    # shared /WE
      14: 'SAVE_SEL_N', 13: 'EA19_N', 12: 'SAVE_CE_N'},   # save chip /CE1
     mpn='SN74AHCT157PWR')
part('U6', '74xx', '74HCT00', '74HCT00', FP_TSSOP14, None,
     {1: 'SNES_ROMSEL_N', 2: 'SNES_ROMSEL_N', 3: 'ROMSEL',
      4: 'SNES_A15', 5: 'ROMSEL', 6: 'ROM_SEL_N',
      9: 'BUS_ESP', 10: 'BUS_ESP', 8: 'BUS_ESP_N',
      12: 'EA19', 13: 'EA19', 11: 'EA19_N',
      14: '+5V', 7: 'GND'},
     unit_pos={1: (228.6, 205.74), 2: (228.6, 223.52), 3: (228.6, 241.3), 4: (228.6, 259.08), 5: (205.74, 259.08)},
     mpn='74HCT00PW')
part('U7', '74xx', '74LS32', '74HCT32', FP_TSSOP14, None,
     {1: 'ROM_SEL_N', 2: 'MENU_WE_N', 3: 'ROM_WE_OK_N',
      4: 'SNES_WR_N', 5: 'WE_GATE_N', 6: 'SNES_WE_N',
      9: 'ROM_SEL_N', 10: 'BUS_ESP', 8: 'DB_ROM_N',
      12: 'DOUT_OE_N', 13: 'BUS_ESP_N', 11: 'DOUT_OE_G_N',
      14: '+5V', 7: 'GND'},
     unit_pos={1: (287.02, 205.74), 2: (287.02, 223.52), 3: (287.02, 241.3), 4: (287.02, 259.08), 5: (312.42, 259.08)},
     mpn='74HCT32PW')

# ---------------------------------------------------------------- ESP-side shift registers (5 V)
SR_COMMON = {11: 'SR_SCK', 12: 'SR_LATCH', 10: '+5V', 16: '+5V', 8: 'GND'}
Q595 = [15, 1, 2, 3, 4, 5, 6, 7]  # QA..QH
part('U9', '74xx', '74HCT595', '74HCT595', FP_TSSOP16, (360.68, 55.88),
     {**SR_COMMON, 14: 'SR_MOSI', 13: 'BUS_ESP_N', 9: 'SR_CH1', **mapn(Q595, SA[0:8])}, mpn='74HCT595PW')
part('U10', '74xx', '74HCT595', '74HCT595', FP_TSSOP16, (360.68, 104.14),
     {**SR_COMMON, 14: 'SR_CH1', 13: 'BUS_ESP_N', 9: 'SR_CH2', **mapn(Q595, SA[8:16])}, mpn='74HCT595PW')
part('U11', '74xx', '74HCT595', '74HCT595', FP_TSSOP16, (360.68, 152.4),
     {**SR_COMMON, 14: 'SR_CH2', 13: 'BUS_ESP_N', 9: 'SR_CH3', **mapn(Q595, SA[16:19] + ['EA19'] + [None] * 4)},
     mpn='74HCT595PW')
part('U12', '74xx', '74HCT595', '74HCT595', FP_TSSOP16, (360.68, 200.66),
     {**SR_COMMON, 14: 'SR_CH3', 13: 'DOUT_OE_G_N', 9: None, **mapn(Q595, SD)}, mpn='74HCT595PW')
part('U13', '74xx', '74HC165', '74HCT165', FP_TSSOP16, (360.68, 248.92),
     {1: 'RD_LOAD_N', 2: 'SR_SCK', 15: 'GND', 10: 'GND', 16: '+5V', 8: 'GND',
      9: 'RB_Q7', 7: None, **mapn([11, 12, 13, 14, 3, 4, 5, 6], SD)}, mpn='74HCT165PW')

# ---------------------------------------------------------------- 5 V -> 3.3 V (CD74HC4050 on 3V3, inputs 5 V tolerant)
part('U14', '4xxx', '4050', 'CD74HC4050', FP_TSSOP16, None,
     {3: 'RB_Q7', 2: 'SR_MISO',
      5: 'SNES_WE_N', 4: 'MBX_IRQ_N',
      7: 'SNES_RESET_N', 6: 'RESET_SENSE_N',
      9: 'V5_SENSE_IN', 10: 'SNES_5V_SENSE',
      11: 'GND', 12: None, 14: 'GND', 15: None,
      1: '+3V3', 8: 'GND'},
     unit_pos={1: (452.12, 45.72), 2: (452.12, 60.96), 3: (452.12, 76.2), 4: (452.12, 91.44),
               5: (452.12, 106.68), 6: (452.12, 121.92), 7: (482.6, 83.82)},
     mpn='CD74HC4050PWR')
part('R3', 'Device', 'R', '10k', FP_R, (414.02, 101.6), {1: '+5V', 2: 'V5_SENSE_IN'})

# ---------------------------------------------------------------- SNES reset driver + pull-ups (10k to 3V3)
part('Q1', 'Transistor_FET', '2N7002', '2N7002', FP_SOT23, (449.58, 157.48),
     {3: 'SNES_RESET_N', 2: 'GND', 1: 'RST_GATE'}, mpn='2N7002')
part('R1', 'Device', 'R', '100R', FP_R, (419.1, 165.1), {1: 'SNES_RST_DRV', 2: 'RST_GATE'})
for i, net in enumerate(['BUS_ESP', 'ESP_WE_N', 'ESP_OE_N', 'DOUT_OE_N', 'RD_LOAD_N', 'MENU_WE_N', 'RST_GATE', 'SD_CS']):
    part('R%d' % (10 + i), 'Device', 'R', '10k', FP_R, (431.8 + i * 7.62, 205.74), {1: '+3V3', 2: net})

# ---------------------------------------------------------------- ESP32-S3-WROOM-1 module (hand-soldered) + support
esp = {1: 'GND', 40: 'GND', 41: 'GND', 2: '+3V3', 3: 'ESP_EN',
       4: 'BUS_ESP', 5: 'ESP_WE_N', 6: 'ESP_OE_N', 7: 'DOUT_OE_N',              # IO4..IO7
       8: 'RD_LOAD_N', 9: 'MENU_WE_N', 10: 'SNES_RST_DRV', 11: 'MBX_IRQ_N',    # IO15..IO18
       12: 'RESET_SENSE_N', 13: 'USB_DN', 14: 'USB_DP', 15: None, 16: None,   # IO8, D-, D+, IO3, IO46
       17: 'SNES_5V_SENSE', 18: 'SR_LATCH', 19: 'SR_MOSI', 20: 'SR_SCK',        # IO9..IO12
       21: 'SR_MISO', 22: 'SAVE_M11', 23: 'SAVE_EN', 24: 'SAVE_M12',            # IO13, IO14, IO21, IO47
       25: 'ESP_LED', 26: None, 27: 'ESP_BOOT', 28: None, 29: None, 30: None,   # IO48, IO45, IO0, IO35-37 (PSRAM)
       31: 'SD_CD_N', 32: 'SAVE_M13', 33: 'SAVE_M14', 34: 'SD_MISO',            # IO38..IO41
       35: 'SD_MOSI', 36: None, 37: None, 38: 'SD_SCK', 39: 'SD_CS'}            # IO42, RXD0, TXD0, IO2, IO1
part('U21', 'RF_Module', 'ESP32-S3-WROOM-1', 'ESP32-S3-WROOM-1-N16R8', 'RF_Module:ESP32-S3-WROOM-1',
     (556.26, 99.06), esp, asm='HAND', mpn='ESP32-S3-WROOM-1-N16R8')
part('R25', 'Device', 'R', '10k', FP_R, (599.44, 60.96), {1: '+3V3', 2: 'ESP_EN'})
part('C22', 'Device', 'C', '1uF', FP_C, (612.14, 71.12), {1: 'ESP_EN', 2: 'GND'})
part('SW2', 'Switch', 'SW_Push', 'RESET', 'Button_Switch_SMD:SW_SPST_PTS810', (627.38, 71.12),
     {1: 'ESP_EN', 2: 'GND'}, mpn='PTS810SJM250SMTRLFS')
part('R26', 'Device', 'R', '10k', FP_R, (599.44, 93.98), {1: '+3V3', 2: 'ESP_BOOT'})
part('SW1', 'Switch', 'SW_Push', 'BOOT', 'Button_Switch_SMD:SW_SPST_PTS810', (627.38, 104.14),
     {1: 'ESP_BOOT', 2: 'GND'}, mpn='PTS810SJM250SMTRLFS')
part('R27', 'Device', 'R', '1k', FP_R, (599.44, 127.0), {1: 'ESP_LED', 2: 'LED_ESP_A'})
part('D7', 'Device', 'LED', 'LED blue (ESP)', FP_LED, (612.14, 139.7), {2: 'LED_ESP_A', 1: 'GND'})

# microSD socket (SPI mode, 3.3 V)
part('J2', 'Connector', 'Micro_SD_Card_Det_Hirose_DM3AT', 'microSD (push-push)',
     'Connector_Card:microSD_HC_Hirose_DM3AT-SF-PEJM5', (548.64, 195.58),
     {1: 'SD_DAT2', 2: 'SD_CS', 3: 'SD_MOSI', 4: '+3V3', 5: 'SD_SCK', 6: 'GND', 7: 'SD_MISO', 8: 'SD_DAT1',
      10: 'SD_CD_N', 9: 'GND', 11: 'GND'}, mpn='DM3AT-SF-PEJM5')
for i, net in enumerate(['SD_MISO', 'SD_MOSI', 'SD_DAT1', 'SD_DAT2', 'SD_CD_N']):
    part('R%d' % (18 + i), 'Device', 'R', '10k', FP_R, (594.36 + i * 7.62, 172.72), {1: '+3V3', 2: net})

# USB-C (programming / bench power for the ESP side) + 3.3 V regulator
part('J5', 'Connector', 'USB_C_Receptacle_USB2.0_16P', 'USB-C', 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',
     (632.46, 279.4), {'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND', 'S1': 'GND',
                       'A4': 'VBUS', 'A9': 'VBUS', 'B4': 'VBUS', 'B9': 'VBUS',
                       'A5': 'USB_CC1', 'B5': 'USB_CC2', 'A6': 'USB_DP', 'B6': 'USB_DP', 'A7': 'USB_DN', 'B7': 'USB_DN',
                       'A8': None, 'B8': None}, mpn='TYPE-C-31-M-12')
part('R23', 'Device', 'R', '5.1k', FP_R, (594.36, 254.0), {1: 'USB_CC1', 2: 'GND'})
part('R24', 'Device', 'R', '5.1k', FP_R, (604.52, 254.0), {1: 'USB_CC2', 2: 'GND'})
part('D6', 'Diode', '1N5819WS', '1N5819WS', FP_SOD323, (680.72, 266.7), {2: 'VBUS', 1: 'ESP_5V'}, mpn='1N5819WS')
# ESD protection for the USB port (added after the 2026-11-17 production review)
part('U23', 'Power_Protection', 'USBLC6-2SC6', 'USBLC6-2SC6', 'Package_TO_SOT_SMD:SOT-23-6', (675.64, 309.88),
     {1: 'USB_DP', 6: 'USB_DP', 3: 'USB_DN', 4: 'USB_DN', 5: 'VBUS', 2: 'GND'}, mpn='USBLC6-2SC6', note='USB ESD')
part('U22', 'Regulator_Linear', 'AP2112K-3.3', 'AP2112K-3.3', 'Package_TO_SOT_SMD:SOT-23-5', (723.9, 284.48),
     {1: 'ESP_5V', 3: 'ESP_5V', 2: 'GND', 4: None, 5: '+3V3'}, mpn='AP2112K-3.3TRG1')
part('C23', 'Device', 'C', '10uF', FP_C0805, (701.04, 299.72), {1: 'ESP_5V', 2: 'GND'})
part('C24', 'Device', 'C', '22uF', FP_C0805, (749.3, 299.72), {1: '+3V3', 2: 'GND'})
part('C25', 'Device', 'C', '100nF', FP_C, (762.0, 299.72), {1: '+3V3', 2: 'GND'}, note='ESP 3V3 pin')
part('C26', 'Device', 'C', '10uF', FP_C0805, (774.7, 299.72), {1: '+3V3', 2: 'GND'}, note='microSD VDD')

# ---------------------------------------------------------------- SAVE RAM (battery backed, LoROM $70-$7D:0000-7FFF)
part('U17', '74xx', '74HCT138', '74HCT138', FP_TSSOP16, (175.26, 391.16),
     {1: 'SNES_A20', 2: 'SNES_A21', 3: 'SNES_A22', 4: 'SNES_ROMSEL_N', 5: 'SNES_A15', 6: 'SAVE_G1',
      7: 'SAVE_SEL_N', 9: None, 10: None, 11: None, 12: None, 13: None, 14: None, 15: None,
      16: '+5V', 8: 'GND'}, mpn='74HCT138PW')
part('U18', '74xx', '74LS08', '74HCT08', FP_TSSOP14, None,
     {1: 'SAVE_SEL_N', 2: 'ROM_WE_OK_N', 3: 'WE_GATE_N',
      4: 'DB_ROM_N', 5: 'SAVE_SEL_N', 6: 'DBUF_OE_N',
      9: 'SAVE_EN', 10: 'BUS_ESP_N', 8: 'SAVE_G1',
      12: 'GND', 13: 'GND', 11: None,
      14: '+5V', 7: 'GND'},
     unit_pos={1: (243.84, 365.76), 2: (243.84, 383.54), 3: (243.84, 401.32), 4: (243.84, 419.1), 5: (220.98, 419.1)},
     mpn='74HCT08PW')
part('U19', '74xx', '74LS08', '74HCT08', FP_TSSOP14, None,
     {1: 'SA11', 2: 'SAVE_M11', 3: 'SV_A11',
      4: 'SA12', 5: 'SAVE_M12', 6: 'SV_A12',
      9: 'SA13', 10: 'SAVE_M13', 8: 'SV_A13',
      12: 'SA14', 13: 'SAVE_M14', 11: 'SV_A14',
      14: '+5V', 7: 'GND'},
     unit_pos={1: (309.88, 365.76), 2: (309.88, 383.54), 3: (309.88, 401.32), 4: (309.88, 419.1), 5: (335.28, 419.1)},
     mpn='74HCT08PW')
save_addr = {12: 'SA0', 11: 'SA1', 10: 'SA2', 9: 'SA3', 8: 'SA4', 7: 'SA5', 6: 'SA6', 5: 'SA7',
             27: 'SA8', 26: 'SA9', 23: 'SA10', 25: 'SV_A11', 4: 'SV_A12', 28: 'SV_A13', 3: 'SV_A14',
             31: 'GND', 2: 'GND', 1: None}
part('U16', 'Memory_RAM', 'AS6C1008-xxP', 'CY62128ELL-45SXI (save, 32K used)', FP_SOP32,
     (83.82, 408.94), {**save_addr, **sram_data, 22: 'SAVE_CE_N', 30: 'SAVE_CE2', 24: 'SRAM_OE_N',
                       29: 'SRAM_WE_N', 32: 'VSAVE', 16: 'GND'}, mpn='CY62128ELL-45SXI')
part('U20', 'Power_Supervisor', 'MCP100-450D', 'MCP100-450', FP_SOT23, (172.72, 462.28),
     {1: 'PWR_OK', 2: '+5V', 3: 'GND'}, mpn='MCP100T-450I/TT')
part('R6', 'Device', 'R', '1k', FP_R, (198.12, 462.28), {1: 'PWR_OK', 2: 'SAVE_CE2'})
part('R7', 'Device', 'R', '100k', FP_R, (215.9, 472.44), {1: 'SAVE_CE2', 2: 'GND'})
part('D4', 'Diode', 'BAT54C', 'BAT54C', FP_SOT23, (101.6, 474.98), {1: '+5V', 2: 'VBAT_R', 3: 'VSAVE'}, mpn='BAT54C')
part('R9', 'Device', 'R', '1k', FP_R, (76.2, 505.46), {1: 'VBAT', 2: 'VBAT_R'})
part('BT1', 'Device', 'Battery_Cell', 'CR2032', 'Battery:BatteryHolder_MYOUNG_BS-07-A1BJ001_CR2032',
     (55.88, 513.08), {1: 'VBAT', 2: 'GND'}, asm='HAND', mpn='BS-07-A1BJ001 + CR2032')
part('R8', 'Device', 'R', '10k', FP_R, (238.76, 472.44), {1: 'EA19', 2: 'GND'})

# ---------------------------------------------------------------- power
part('D1', 'Diode', '1N5819WS', '1N5819WS', FP_SOD323, (50.8, 314.96), {2: '+5V', 1: 'ESP_5V'}, mpn='1N5819WS')
part('C1', 'Device', 'C', '22uF', FP_C1206, (76.2, 317.5), {1: 'ESP_5V', 2: 'GND'})
part('C2', 'Device', 'C', '22uF', FP_C1206, (93.98, 317.5), {1: '+5V', 2: 'GND'})
part('R5', 'Device', 'R', '1k', FP_R, (111.76, 307.34), {1: '+5V', 2: 'LED_PWR_A'})
part('D2', 'Device', 'LED', 'LED red (5V)', FP_LED, (111.76, 327.66), {2: 'LED_PWR_A', 1: 'GND'})

# 100 nF decoupling, one per IC
dec = ['U1', 'U2', 'U3', 'U4', 'U5', 'U6', 'U7', 'U8', 'U9', 'U10', 'U11', 'U12', 'U13', 'U15', 'U14',
       'U16', 'U17', 'U18', 'U19']
RAIL = {'U14': '+3V3', 'U16': 'VSAVE'}
for i, ic in enumerate(dec):
    part('C%d' % (i + 3), 'Device', 'C', '100nF', FP_C, (139.7 + i * 15.24, 317.5), {1: RAIL.get(ic, '+5V'), 2: 'GND'},
         note='decouples ' + ic)

# ---------------------------------------------------------------- sourcing (checked 2026-11-17)
# (manufacturer, MPN, LCSC part number). LCSC numbers were looked up and their package checked against
# the LCSC catalogue; pinouts of every substitute were checked against the maker's datasheet.
# Not stocked at LCSC on 2026-11-17 (use JLC parts pre-order / Global Sourcing, or hand-solder):
#   U1 AS6C4008-55SIN, U13 74HCT165PW,118.
# U16 moved on 2026-11-17 from AS6C1008-55SIN (C1351203, 2.7-5.5 V, out of stock) to the in-stock CY62128ELL-45SXI:
# same JEDEC pinout and 450-mil SOIC-32, but 4.5-5.5 V. VSAVE sits one BAT54C drop below +5V, so it is only in
# spec while the console delivers about 4.9 V or more. Go back to the AS6C1008 when it is stocked again.
SOURCING = {
    'U1': ('Alliance Memory', 'AS6C4008-55SIN', 'C1350086'),
    'U16': ('Infineon (Cypress)', 'CY62128ELL-45SXI', 'C2953613'),   # 4.5-5.5 V, see note above
    'U2': ('Nexperia', '74AHCT541PW,118', 'C84548'),
    'U3': ('Nexperia', '74AHCT541PW,118', 'C84548'),
    'U4': ('Nexperia', '74AHCT541PW,118', 'C84548'),
    'U5': ('Nexperia', '74AHCT245PW,118', 'C173388'),
    'U6': ('Nexperia', '74HCT00PW,118', 'C8206'),
    'U7': ('Texas Instruments', 'SN74HCT32PWR', 'C132266'),
    'U8': ('Texas Instruments', 'SN74AHCT157PWR', 'C2674471'),
    'U9': ('MDD', '74HCT595PW', 'C54411086'),
    'U10': ('MDD', '74HCT595PW', 'C54411086'),
    'U11': ('MDD', '74HCT595PW', 'C54411086'),
    'U12': ('MDD', '74HCT595PW', 'C54411086'),
    'U13': ('Nexperia', '74HCT165PW,118', 'C547409'),          # must stay HCT: CP and /PL are 3.3 V
    'U14': ('Texas Instruments', 'CD74HC4050PWR', 'C352825'),
    'U15': ('Microchip', 'PIC12F629-I/P', 'C9785'),
    'U17': ('Texas Instruments', 'SN74HCT138PWR', 'C8115'),
    'U18': ('Texas Instruments', 'SN74HCT08PWR', 'C8181'),
    'U19': ('Texas Instruments', 'SN74HCT08PWR', 'C8181'),
    'U20': ('Microchip', 'MCP100T-450I/TT', 'C134467'),
    'U21': ('Espressif', 'ESP32-S3-WROOM-1-N16R8', 'C2913202'),
    'U22': ('Diodes Inc.', 'AP2112K-3.3TRG1', 'C51118'),
    'U23': ('STMicroelectronics', 'USBLC6-2SC6', 'C7519'),
    'Q1': ('JSCJ', '2N7002', 'C8545'),
    'D1': ('Hottech', '1N5819WS', 'C191023'),
    'D6': ('Hottech', '1N5819WS', 'C191023'),
    'D4': ('High Diode', 'BAT54C', 'C466637'),
    'D2': ('KENTO', 'KT-0603R', 'C2286'),
    'D3': ('KENTO', 'KT-0603G', 'C12624'),
    'D7': ('KENTO', 'KT-0603B', 'C2288'),
    'J2': ('Hirose', 'DM3AT-SF-PEJM5', 'C114218'),
    'J3': ('DEALON', 'DM254R-11-05-85', 'C2935976'),          # optional ICSP header, 1x5 2.54 mm THT
    'J5': ('HRO', 'TYPE-C-31-M-12', 'C165948'),
    'SW1': ('C&K', 'PTS810SJK250SMTRLFS', 'C221896'),         # SJM (1.6 N) out of stock; SJK = 2.6 N, same footprint
    'SW2': ('C&K', 'PTS810SJK250SMTRLFS', 'C221896'),
    'BT1': ('MYOUNG', 'BS-07-A1BJ001', 'C2979167'),           # holder only; add one CR2032 cell
}
PASSIVES = {  # (value, footprint) -> (manufacturer, MPN, LCSC); all JLC basic parts
    ('10k', FP_R): ('UNI-ROYAL', '0603WAF1002T5E', 'C25804'),
    ('1k', FP_R): ('UNI-ROYAL', '0603WAF1001T5E', 'C21190'),
    ('5.1k', FP_R): ('UNI-ROYAL', '0603WAF5101T5E', 'C23186'),
    ('100R', FP_R): ('UNI-ROYAL', '0603WAF1000T5E', 'C22775'),
    ('100k', FP_R): ('UNI-ROYAL', '0603WAF1003T5E', 'C25803'),
    ('100nF', FP_C): ('YAGEO', 'CC0603KRX7R9BB104', 'C14663'),      # 50 V X7R
    ('1uF', FP_C): ('Samsung', 'CL10A105KB8NNNC', 'C15849'),        # 50 V X5R
    ('10uF', FP_C0805): ('Samsung', 'CL21A106KAYNNNE', 'C15850'),   # 25 V X5R
    ('22uF', FP_C0805): ('Samsung', 'CL21A226MAQNNNE', 'C45783'),   # 25 V X5R
    ('22uF', FP_C1206): ('Samsung', 'CL31A226KAHNNNE', 'C12891'),   # 25 V X5R
}
for _p in parts:
    _src = SOURCING.get(_p['ref']) or PASSIVES.get((_p['value'], _p['fp']))
    if _src:
        _p['mfr'], _p['mpn'], _p['lcsc'] = _src
    elif _p['asm'] != 'PCB':
        raise SystemExit('no sourcing entry for ' + _p['ref'])

# PWR_FLAG for nets fed only through passive pins
pwr_flags = {'ESP_5V': (63.5, 304.8), 'VSAVE': (127.0, 467.36), 'VBUS': (657.86, 254.0)}
