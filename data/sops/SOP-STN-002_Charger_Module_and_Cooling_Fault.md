# SOP-STN-002: Charger Module Fault / Slot Not Charging / Cooling Fan Failure

| Field | Value |
|---|---|
| SOP ID | SOP-STN-002 |
| Applies to | All SwapStation-X1 (Gen1, Gen2) |
| Error codes | E-204 (Charger overcurrent), E-205 (Charger output undervoltage), E-207 (Charger fan failure) |
| Severity | P3 for a single slot; P2 if 3 or more slots are affected |
| Owner | Field Engineer |
| Version | 2.4 (2026-03-15) |

## 1. Symptoms
- Slot LED is red or amber; a battery in the slot does not charge.
- Charger module reports overcurrent, undervoltage, or fan fault.
- Slot charging is derated (lower current than normal).

## 2. Safety
- This SOP involves the DC power section. Only trained, authorised technicians may perform it.
- Wear insulated gloves (Class 0) and safety shoes.
- Disable the slot remotely and switch off the slot breaker before removing a charger module. Wait 5 minutes for capacitors to discharge, and verify less than 5 V DC with a multimeter.

## 3. Troubleshooting steps
1. Disable the affected slot from the NOC console so no rider is assigned to it.
2. Check whether the fault follows the battery or the slot: move the battery to a known-good slot. If it charges there, the fault is in the slot.
3. Read the charger module log (`cm.log <slot>`) for fault type and count.
4. For E-207 (fan): check the fan visually and audibly. If it is not spinning or is noisy, replace it. On Gen1 stations, use the Gen2 ball-bearing fan (part FAN-80-BB).
5. For E-204/E-205: check the DC output with the module isolated. Replace the charger module if output is abnormal or the fault repeats more than 3 times in 24 hours.
6. Record the serial number of the removed and installed modules.

## 4. Resolution verification
- Test charge a battery for 15 minutes; current within ±5% of rated.
- No fault logged during the test.
- Re-enable the slot from the NOC console.

## 5. Reference past incidents
- INC-2026-09044 (WMQISXM1V1-02616): CM-07 MOSFET failure; module replaced.
- INC-2026-02215 (WMQISXM1V1-00369): Gen1 fan bearing seizure; replaced with FAN-80-BB.
