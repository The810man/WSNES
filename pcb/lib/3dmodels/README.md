# Vendor 3D models

KiCad's own 3D library has no models for these three footprints, even though the footprints reference them. Without these files, the STEP/STL export would be missing those parts.

| File | Used by | Part | Source |
|---|---|---|---|
| `BatteryHolder_MYOUNG_BS-07-A1BJ001_CR2032.step` | BT1 | MYOUNG BS-07-A1BJ001 | LCSC C2979167 (EasyEDA model) |
| `USB_C_Receptacle_HRO_TYPE-C-31-M-12.step` | J5 | Korean Hroparts TYPE-C-31-M-12 | LCSC C165948 (EasyEDA model) |
| `SOP-32_11.305x20.495mm_P1.27mm.step` | U1, U16 | AS6C4008 / AS6C1008, SOP-32 | LCSC C1350086 (EasyEDA model) |

The footprints point at them through `${KIPRJMOD}/lib/3dmodels/`, using these offsets:

- BT1: rotate Z 180°, offset X +10.57 mm
- J5: rotate Z 180°, offset Y −1.045 mm
- U1/U16: no offset

The offsets were derived by matching each model's leads and pins to the footprint pads, then checked in a KiCad render.

These files belong to their manufacturers / LCSC and are **not** covered by the project licence (CC BY-NC-SA / PolyForm). They are included only so the board's 3D export is complete.
