# PCB Layout Guidelines

## Layer stackup (4-layer recommended)
| Layer | Use |
|-------|-----|
| 1 (Top) | Analog signal routing + component placement |
| 2 | Analog ground plane (AGND) - solid pour |
| 3 | Digital ground (DGND) + digital power |
| 4 (Bottom) | Digital routing, MCU, connectors |

## Ground separation
- AGND and DGND are **separate** pours joined at exactly **one** star point,
  located at the ADC input / MCU analog-supply pin.
- Never route digital signals over the AGND plane.
- Never share return currents between analog and digital sections.

## Analog section
- INA input traces <= 15 mm, flanked by an AGND guard ring on both sides.
- Guard ring driven at the common-mode potential (tie to RLD output) so leakage
  currents see ~0 V across the guard gap.
- Patient-protection resistors within 5 mm of the connector.
- Op-amp decoupling: 100 nF X7R || 10 &micro;F tantalum within 2 mm of each
  Vcc/Vss pin.
- Avoid vias in the analog signal path (via inductance picks up noise).
- Electrode connector: shielded 3.5 mm jack / snap at the board edge.

## Noise reduction
- Keep analog and digital traces >= 3 mm apart; avoid long parallel runs.
- Route MCU/SPI/UART clocks away from the analog section.
- Crystal guarded and away from the front-end.
- STM32 VDDA filtered from VDD with 10 &Omega; + 1 &micro;F + 100 nF.
- STM32 VREF+ to a dedicated REF3030 (3.0 V), not VDD.

## Component placement (signal-flow order, left to right)
```
Electrodes -> protection -> INA -> HP -> LP -> gain -> ADC
```
- Each stage placed in flow order; MCU on a separate region >= 20 mm from INA.
- BLE module shielded, on the opposite side of the board from the front-end.
