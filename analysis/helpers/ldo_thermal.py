#!/usr/bin/env python3
"""Junction-temperature estimate for U22 (AP2112K-3.3, SOT-23-5).

Usage: python3 analysis/helpers/ldo_thermal.py

Inputs (cited in docs/reviews/2026-11-17_production-review.md):
  * theta_JA = 184 C/W, SOT25, no heatsink (AP2112 datasheet p.3).
    The real board (4 layers, GND pour on pin 2) will do better; this is the
    datasheet worst case.
  * Tj max = 150 C (AP2112 datasheet p.3, operating junction temperature).
  * VIN = SNES +5V minus a 1N5819WS drop (D1); 0.40 V assumed at these currents.
    On USB power VBUS goes through D6 instead, with the same drop.
  * ESP32-S3 load currents are typical figures, not measured on this board.
"""
THETA_JA = 184.0
TJ_MAX = 150.0
VOUT = 3.3
VIN = 5.0 - 0.40

for ambient in (25.0, 40.0, 50.0):
    for label, amps in (("idle / BLE", 0.05), ("WiFi average", 0.15),
                        ("WiFi busy", 0.25), ("TX peak, sustained", 0.50)):
        p = (VIN - VOUT) * amps
        tj = ambient + p * THETA_JA
        flag = "OVER Tj max" if tj > TJ_MAX else ("<15 C margin" if tj > TJ_MAX - 15 else "ok")
        print(f"Ta={ambient:4.0f}C  {label:19} I={amps*1000:4.0f} mA  P={p:5.3f} W  Tj={tj:6.1f} C  {flag}")
