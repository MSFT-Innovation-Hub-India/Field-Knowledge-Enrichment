# SOP-STN-003: Slot Door / Lock Mechanism Failure

| Field | Value |
|---|---|
| SOP ID | SOP-STN-003 |
| Applies to | All SwapStation-X1 |
| Error codes | E-305 (Door lock not engaged), E-306 (Door open timeout), E-307 (Door sensor mismatch) |
| Severity | P2 if a battery is trapped or a swap cannot complete; otherwise P3 |
| Owner | Field Engineer |
| Version | 1.9 (2026-02-01) |

## 1. Symptoms
- Door does not close or lock after a battery is inserted; the swap stays incomplete.
- Door does not open when a swap is requested.
- Door sensor shows "closed" while the door is physically open (or the reverse).

## 2. Immediate actions
1. If a rider is waiting, assign a different slot from the NOC console to complete the swap.
2. Disable the faulty slot.
3. If a battery is trapped, use the manual override key (kept by the site supervisor) only after the slot is disabled.

## 3. Troubleshooting steps
1. Check the solenoid operation with `door.test <slot>`. Listen for the click.
2. Inspect the latch bracket and strike plate for misalignment or loose screws.
3. Clean the latch with contact cleaner; apply dry PTFE lubricant only (no grease, as it attracts dust).
4. Check the door sensor (reed switch) gap: it should be 3–5 mm.
5. Measure solenoid coil resistance (expected 18–24 Ω). Replace the solenoid if it is out of range.

## 4. Resolution verification
- 20 consecutive open/close cycles without error.
- Re-enable the slot and complete one test swap.

## 5. Reference past incidents
- INC-2026-03390 (WMQISXM1V1-02614): Loose latch bracket on slot 5; realigned, cleaned, lubricated.
