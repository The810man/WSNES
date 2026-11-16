# Masterplan: WLAN-fähige SNES-Flashcart (ESP32-S3 + 4-MB-SRAM)

> **Stand 2026-11-16: historisches Planungsdokument.** Die aktuelle Hardware ist v0.3 in [`../pcb/`](../pcb/README.md).
> Bekannte Fehler in diesem Plan: Edge-Connector-Pinout, SuperCIC (PIC12F629 statt ATtiny), GPIO35–37 kollidieren mit dem Octal-PSRAM.
> Die unten genannten Fremd-Repos dienten nur der Recherche; aus ihnen ist nichts in diesem Repo enthalten.

Dieses Dokument enthält die komplette Systemarchitektur, alle KiCad-Vorlagen zum Mergen, die exakte Bauteilliste sowie die vollständigen Pinout-Tabellen für den Aufbau einer eigenen SNES-Flashcart mit Game-Manager und WLAN-Funktion.

NOTICE: Dieses dokument habe ich mit AI-Generiert, bzw verbessert aus meiner research und meinen ideen zusammen gefasst in dieser Markdown datei.

---

## 1. Systemarchitektur & Ablauf

Da der **ESP32-S3** wegen WLAN-Interrupts das ~120-ns-Bus-Timing des SNES nicht direkt bedienen kann, übernimmt ein echter paralleler **4-MB-SRAM (`AS6C3208`)** die Rolle des ROMs. Über **Bus-Switches (`74CB3T3245`)** wird der SRAM entweder mit dem ESP32 (zum Beschreiben) oder mit dem SNES (zum Spielen) verbunden.

1. **Boot-Phase (Game Manager laden):**
   * ESP32 zieht `/RESET` am SNES auf `LOW` (SNES pausiert).
   * Bus-Switches trennen das SNES vom SRAM (`/OE_SNES = HIGH`) und schalten den ESP32 frei (`/OE_ESP = LOW`).
   * ESP32 lädt das SNES-Menü-ROM von der microSD-Karte in den SRAM.
   * Bus-Switches schalten den SRAM wieder auf das SNES (`/OE_ESP = HIGH`, `/OE_SNES = LOW`).
   * ESP32 gibt `/RESET` frei (`HIGH` / High-Z) → Das SNES startet das Menü nativ.
2. **Spielauswahl & WLAN:**
   * Das SNES-Menü kommuniziert über eine festgelegte Mailbox-Adresse (z. B. `$00:21F0`) mit dem ESP32 (Spieleliste abfragen, WLAN-Status prüfen, per Web-Interface hochgeladene ROMs empfangen).
3. **Spielstart:**
   * Nach Auswahl im Menü legt der ESP32 das SNES wieder kurz in den Reset, kopiert die `.sfc`-Datei von SD in den SRAM, schaltet die Bus-Switches zurück auf das SNES und gibt `/RESET` frei.

---

## 2. KiCad-Vorlagen zum Mergen (Copy & Paste in dein Projekt)

Lade diese drei Repositories herunter, um Schaltplan-Blöcke und Platinen-Umrisse direkt in dein eigenes KiCad-Projekt zu kopieren:

### A. SNES-Platinenform, Edge-Connector & SuperCIC (Deine Hauptbasis)

* **GitHub-Repo:** [MouseBiteLabs / Super-Nintendo-Cartridges](https://github.com)
* **Konkrete Ordner/Dateien im Repo:**
  * `LoROM (No Save)/` → Öffne die `.kicad_sch` und `.kicad_pcb`.
  * **Was du behältst:** Den äußeren Platinen-Umriss (*Edge.Cuts*), den 62-Pin-Modulstecker (*Cartridge Edge Connector*) sowie die Schaltung rund um den **ATtiny13A (`SuperCIC`)**.
  * **Was du löschst:** Den Mask-ROM/TSOP-Footprint und die LoROM/HiROM-Jumper (diese ersetzt du durch deinen SRAM und die Bus-Switches).

### B. Flashcart-Schaltplan-Referenz (SRAM + Level-Shifter + Adress-Logik)

* **GitHub-Repo 1:** [mrehkopf / sd2snes (KiCad RevF)](https://github.com)
  * **Nutzen:** Zeigt im Schaltplan (`sd2snes.kicad_sch`), wie der 5V-SNES-Bus sauber über Bus-Transceiver auf 3,3V gewandelt und an einen parallelen SRAM angebunden wird.
* **GitHub-Repo 2:** [soniccd123 / SNES-FeRAM-Cart](https://github.com)
  * **Nutzen:** Sehr übersichtliches KiCad-Projekt für moderne 3,3V-Speicherchips auf einer SNES-Platine inklusive Pegelwandler-Beschaltung.

### C. ESP32-S3 Schaltungs-Vorlage (Falls du später ohne DevKit baust)

* **GitHub-Repo:** [AMIFEX-IT / ESP32-S3-SMALL](https://github.com)
* **Nutzen:** Enthält den fertigen Schaltplan-Block für `ESP32-S3-WROOM-1`, 3,3V-Spannungsregler, Pufferkondensatoren und `BOOT`/`RESET`-Taster. *(Für Prototyp v1 empfiehlt sich aber das aufsteckbare `ESP32-S3-DevKitC-1` über 2× 22-Pin Buchsenleisten).*

---

## 3. Vollständige Bauteilliste (BOM)

| Bauteil | Typ / Bezeichnung | Menge | Aufgabe |
| :--- | :--- | :---: | :--- |
| **Mikrocontroller** | **ESP32-S3-DevKitC-1** (N16R8) | 1 | WLAN, Webserver, SD-Karte, Ablaufsteuerung. |
| **4-MB-SRAM (32 Mbit)** | **AS6C3208-55TIN** (TSOP-48) | 1 | Paralleler 3,3V-SRAM (4M × 8 Bit, 55 ns). Simuliert das SNES-ROM. |
| **Bus-Switches (8-Bit)** | **74CB3T3245PW** (TSSOP-20) | 4 | Trennt/verbindet die 22 Adress- und 8 Datenleitungen zwischen SNES (5V) und SRAM (3,3V). |
| **Steuer-Logik (LoROM)** | **74LVC1G08** oder **74LVC08** (AND-Gate) | 1 | Verknüpft SNES `/CART` und `A15` für die LoROM-Chip-Auswahl (`/CE`). |
| **Schieberegister** | **74HC595PW** (TSSOP-16) | 3 | Erzeugt die 22 SRAM-Adressen über nur 3 SPI-Pins des ESP32. |
| **Region-Lock-Chip** | **ATtiny13A-SSU** (SOIC-8) | 1 | Geflasht mit *SuperCIC*-Hex-Datei (schaltet PAL/NTSC SNES frei). |
| **MicroSD-Slot** | **Molex 503398-1892** (oder ähnlich) | 1 | Speichert Menü-ROM und `.sfc`-Spiele (im SPI-Modus betrieben). |
| **Spannungsregler** | **AMS1117-3.3** oder **TPS563201** | 1 | Wandelt SNES `5V` in `3.3V` (mind. 600–800 mA für WLAN-Spitzen). |
| **Kondensatoren** | **100 µF Elko** + **10× 100 nF Keramik** | 11 | Entkopplung an jedem IC (`VCC` nahe `GND`) und Puffer für WLAN. |
| **Pull-Up-Widerstände** | **10 kΩ** (0603 oder 0805) | 4 | Hält `/CE` und `/WE` des SRAMs beim Umschalten sicher auf `HIGH` (inaktiv). |

---

## 4. Exaktes Pinout & Verdrahtung (LoROM-Modus, bis 32 Mbit)

### A. SNES Edge-Connector → Bus-Switches (`74CB3T3245`) → SRAM (`AS6C3208`)

Im **LoROM-Modus** liegen die ROM-Daten in jeder Speicherbank bei `$8000–$FFFF`. Deshalb wird die SNES-Adressleitung **`A15` nicht an den SRAM angeschlossen**, sondern steuert zusammen mit `/CART` die Aktivierung des SRAMs. Alle höheren SNES-Adressleitungen rutschen um eins nach unten:

| SNES Edge-Connector Pin | SNES Signal | Bus-Switch (5V → 3,3V) | SRAM Pin (`AS6C3208`) | Hinweis |
| :--- | :--- | :--- | :--- | :--- |
| **Pin 5, 36** | `GND` | `GND` | `VSS` (Pin 13, 36) | Gemeinsame Masse |
| **Pin 27, 58** | `+5V` | – (nur 3,3V an IC!) | – (nur 3,3V an IC!) | `74CB3T3245` und SRAM laufen mit **3,3V**! |
| **Pin 18–25** | `A0` – `A7` | Switch 1 (`A1`–`A8` → `B1`–`B8`) | `A0` – `A7` | Untere Adressleitungen 1:1 |
| **Pin 10–16** | `A8` – `A14` | Switch 2 (`A1`–`A7` → `B1`–`B7`) | `A8` – `A14` | Mittlere Adressleitungen 1:1 |
| **Pin 17** | `A15` | **Nicht an SRAM!** | – | Geht an LoROM-Logik (s. u.) |
| **Pin 41–47** | `A16` – `A22` | Switch 3 (`A1`–`A7` → `B1`–`B7`) | **`A15` – `A21`** | **LoROM-Shift!** (`A16`→`A15`, ..., `A22`→`A21`) |
| **Pin 19–22, 50–53** | `D0` – `D7` | Switch 4 (`A1`–`A8` ↔ `B1`–`B8`) | `DQ0` – `DQ7` | Bidirektionaler Datenbus |
| **Pin 23** | `/RD` | Switch 2 (`A8` → `B8`) | `/OE` (Output Enable) | SNES liest Daten aus SRAM |
| **Pin 49** | `/CART` (`/ROMSEL`) | LoROM-Logik (s. u.) | `/CE` (Chip Enable) | Aktiviert SRAM im ROM-Bereich |
| **Pin 26** | `/RESET` | Direkt an ESP32 GPIO (mit Spannungsteiler/Diode!) | – | ESP32 hält SNES beim Laden im Reset |
| **Pin 24, 55, 56, 57** | `CIC` Pins | Direkt an `ATtiny13A` | – | Exakt wie in der *MouseBiteLabs*-Vorlage |

> **Wichtige LoROM-Logik für `/CE` (Chip Enable):**
> Im LoROM-Modus darf der SRAM nur antworten, wenn `/CART == LOW` **UND** `A15 == HIGH` ist.
>
> * **Einfachste Umsetzung (1 IC):** Invertiere `A15` (oder nutze ein `74LVC139` / `74LVC00` NAND-Gate): Wenn `A15 = 1` und `/CART = 0`, wird `/CE` des SRAM auf `0` (`LOW`) gezogen.
> * **Pull-Up Pflicht:** Lege einen **10-kΩ-Widerstand** von SRAM `/CE` nach `3,3V` und von SRAM `/WE` nach `3,3V`, damit der SRAM während der Bus-Umschaltung nicht versehentlich beschrieben wird.

---

### B. ESP32-S3 → Schieberegister (`74HC595`) → SRAM (`AS6C3208`)

Um den SRAM zu beschreiben, nutzt der ESP32 drei verkettete **74HC595**-Schieberegister (24 Ausgänge für die 22 Adressleitungen `A0`–`A21`) sowie 8 direkte GPIOs für den Datenbus `DQ0`–`DQ7`.

| ESP32-S3 Pin | Ziel-Bauteil | Funktion |
| :--- | :--- | :--- |
| **SPI MOSI** (z. B. `GPIO 11`) | `74HC595 #1` Pin 14 (`SER`) | Schiebt die 24 Adress-Bits seriell hinein |
| **SPI SCK** (z. B. `GPIO 12`) | Alle `74HC595` Pin 11 (`SRCLK`) | Schiebetakt |
| **GPIO 10** (Latch) | Alle `74HC595` Pin 12 (`RCLK`) | Übernimmt die 24 Bits gleichzeitig an die Ausgänge |
| **GPIO 13** (`BUS_SEL`) | `74CB3T3245` `/OE` (SNES) + `74HC595` `/OE` | **`HIGH`:** SNES spielt (74HC595 hochohmig).<br>**`LOW`:** ESP32 lädt Spiel (SNES-Switches hochohmig). |
| **GPIO 4 – GPIO 9, 14, 15** | Direkt an SRAM `DQ0` – `DQ7` | 8-Bit-Datenbus vom ESP32 (im Spielbetrieb als `INPUT` / High-Z schalten!) |
| **GPIO 16** (`ESP_WE`) | Direkt an SRAM `/WE` (Write Enable) | Kurzer `LOW`-Puls speichert das Byte an der aktuellen Adresse |
| **GPIO 17** (`SNES_RESET`) | Über Transistor/Open-Drain an SNES `/RESET` | Zieht SNES `/RESET` auf `GND` während des Ladens |
| **SPI2 (SD-Karte)** | MicroSD-Kartenslot (`CS, MOSI, MISO, SCK`) | Eigener SPI-Bus (z. B. `GPIO 35–38`) für schnelles Lesen der ROMs |

---

## 5. Checkliste für das KiCad-Layout & die Platinenbestellung

1. **Bus-Konflikte verhindern:** Niemals dürfen die SNES-Bus-Switches (`74CB3T3245`) und die ESP32-Leitungen (`74HC595` + ESP-GPIOs) gleichzeitig aktiv sein. Nutze einen Inverter (`74LVC1G04`) auf der `BUS_SEL`-Leitung, sodass hardwareseitig immer nur **eine Seite** `/OE = LOW` hat.
2. **Sicherheit auf dem Datenbus:** Bevor der ESP32 `BUS_SEL` auf `HIGH` stellt (Übergabe an das SNES), muss die Firmware zwingend alle 8 Daten-GPIOs (`DQ0`–`DQ7`) sowie `ESP_WE` per `pinMode(..., INPUT)` hochohmig schalten.
3. **Antennen-Position:** Das `ESP32-S3-DevKitC-1` ganz nach oben an den Rand der Cartridge setzen, sodass die PCB-Antenne aus dem SNES-Modulschacht herausragt.
4. **Fertigungsparameter (JLCPCB / PCBWay):**
   * **Platinendicke:** `1.2 mm` (zwingend erforderlich für den SNES-Slot!)
   * **Oberfläche:** `ENIG` (Immersion Gold) für langlebige Modul-Kontakte.
   * **Gold Fingers:** `Yes`, mit `45°` Abschrägung (*Chamfer*).
