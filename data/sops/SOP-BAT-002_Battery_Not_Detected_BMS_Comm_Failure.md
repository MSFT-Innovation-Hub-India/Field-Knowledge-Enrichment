# SOP-BAT-002: Battery Not Detected / BMS Communication Failure / Physical Damage

| Field | Value |
|---|---|
| SOP ID | SOP-BAT-002 |
| Applies to | All battery models; all stations |
| Error codes | E-603 (BMS CAN timeout / battery not detected), E-620 (Physical damage reported) |
| Severity | P3 (P2 if damage involves the casing seal or the battery was dropped) |
| Owner | Field Engineer, Battery Service Centre |
| Version | 2.2 (2026-05-20) |

## 1. Symptoms
- The station shows "Battery not detected" after insertion.
- CAN handshake timeout in the station log.
- A rider reports a dropped, cracked, or dented battery.

## 2. Step 1: Isolate battery vs slot
1. Insert the same battery into another slot.
   - Detected in another slot: slot fault. Go to section 3.
   - Not detected in any slot: battery fault. Go to section 4.
2. Insert a known-good battery into the original slot to confirm.

## 3. Slot connector fault
1. Disable the slot. Switch off the slot breaker.
2. Inspect the slot connector pins (CAN-H, CAN-L, power). Look for recessed, bent, burnt, or worn pins.
3. Clean with contact cleaner. If pins are worn or recessed, replace the connector assembly (part CONN-SLT-48V-G2).
4. Verify the CAN handshake with 3 different batteries before re-enabling.

## 4. Battery-side fault
1. Inspect the battery connector for oxidation, debris, or bent pins. Clean with contact cleaner.
2. Check whether the BMS is in sleep mode (pack voltage low). If the pack voltage is below 40 V, follow SOP-BAT-003 (deep discharge).
3. Try a BMS wake-up using the service tool. If there is still no communication, send to the Battery Service Centre for BMS diagnosis.

## 5. Physical damage (E-620)
1. Quarantine the battery for 24 hours and watch for temperature rise, voltage drop, swelling, or odour.
2. If any of these occur, follow SOP-BAT-001 section 5.
3. If none occur, the service centre replaces damaged external parts (handle, casing panel) and runs an IP67 seal test before returning the battery to service.

## 6. Reference past incidents
- INC-2026-05561 / INC-2026-05560 (WMQISXM1V1-01044, battery INSMOMAH8210F2625D13): slot 3 CAN pins worn; connector replaced, battery connector cleaned.
- INC-2026-08877 (battery INSMOMAH8210F2625D13): dropped battery, cracked handle; 24 h observation passed, handle replaced.
