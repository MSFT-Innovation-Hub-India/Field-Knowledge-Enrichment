# SOP-GEN-001: Preventive Maintenance, Power Quality, Earth Leakage and Water Ingress

| Field | Value |
|---|---|
| SOP ID | SOP-GEN-001 |
| Applies to | All SwapStation-X1 |
| Error codes | E-402 (Grid under/over-voltage), E-405 (Earth leakage / RCCB trip), E-501 (Water ingress / moisture alarm) |
| Severity | P1 for E-405 or E-501 with exposed live parts; P2 otherwise |
| Owner | Field Engineer |
| Version | 5.2 (2026-07-15) |

## 1. Preventive maintenance (every 90 days)
1. Clean or replace the cabinet intake filter.
2. Check all fans (RPM above 70% of rated).
3. Torque-check the busbar and terminal connections.
4. Inspect slot connectors for wear or burn marks.
5. Test 20 open/close cycles of each door lock.
6. Test the RCCB with its test button.
7. Measure insulation resistance (should be more than 10 MΩ at 500 V DC).
8. Inspect the door gasket and cable glands; replace any that are cracked. Add silica gel packs before monsoon.
9. Check firmware versions and pending OTA updates.
10. Record everything in the PM checklist and update the asset's last PM date.

## 2. Grid under/over-voltage (E-402)
1. Check the voltage log (`power.log`). The normal range is 380–440 V phase-to-phase.
2. If dips below 360 V happen repeatedly, enable under-voltage auto-recovery (120 s delay) in station config.
3. Raise a complaint with the electricity distribution company with the logged evidence.
4. If the issue continues for more than 30 days, propose a servo voltage stabiliser.

## 3. Earth leakage / RCCB trip (E-405)
1. Do NOT reset the RCCB repeatedly. Isolate the station at the main switch.
2. Disconnect slots one at a time and measure insulation resistance for each slot harness.
3. Isolate the faulty slot or harness and restore the rest of the station.
4. Replace the damaged harness; add edge protection where it passes metal edges.

## 4. Water ingress (E-501)
1. Isolate the station at the main switch immediately.
2. Remove water and dry the cabinet with a heat blower (at least 2 hours).
3. Measure insulation resistance; restore power only if above 10 MΩ.
4. Replace the door gasket or cable glands at the entry point; add silica gel packs.

## 5. Reference past incidents
- INC-2026-10158 (WMQISXM1V1-02614): evening under-voltage to 342 V; auto-recovery enabled and complaint raised.
- INC-2026-07023 (WMQISXM1V1-00369): monsoon water ingress via cracked gasket.
- INC-2026-11087 (WMQISXM1V1-01044): chafed slot 6 harness causing RCCB trips (open).
