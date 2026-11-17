# SOP-BAT-001: Battery Over-Temperature / Thermal Event / Station Cabinet Overheating

| Field | Value |
|---|---|
| SOP ID | SOP-BAT-001 |
| Applies to | All battery models (LFP and NMC); all stations |
| Error codes | W-310 (Cabinet high temperature, derating), E-604 (Battery over-temperature) |
| Severity | P1 for any cell above 60°C, smoke, swelling or odour. P2 for a warning between 50°C and 60°C |
| Owner | Field Engineer, Battery Service Centre |
| Version | 4.0 (2026-04-30) |

## 1. Temperature thresholds
| Level | Max cell temperature | Station action |
|---|---|---|
| Normal | below 45°C | Charge normally |
| Warning | 45–55°C | Reduce charge current by 50% |
| Alarm | 55–60°C | Stop charging, keep battery in slot, lock door |
| Critical | above 60°C, or a cell 15°C or more above the pack average | Stop charging, lock slot, alert P1, start isolation |

## 2. Safety (critical events)
- Do NOT open the slot if there is smoke, a hissing sound, or a sweet/solvent odour. Evacuate 10 m and call the emergency number.
- Use only the Class D or lithium-rated extinguisher / AVD extinguisher kept at site; for LFP and NMC, large amounts of water for cooling are acceptable once the area is safe.
- Wear thermal gloves and a face shield when moving a hot battery.

## 3. Step 1: Decide whether it is the battery or the station
1. Check the cabinet temperature on the dashboard. If the cabinet is above 50°C and several batteries show warnings, it is most likely a station cooling issue (W-310). Go to section 4.
2. If only one battery is hot, or one cell is much hotter than others in the same pack, it is a battery fault (E-604). Go to section 5.

## 4. Station cooling issue (W-310)
1. Inspect and clean or replace the intake air filter.
2. Check exhaust fan RPM (`fan.status`). Replace any fan below 70% rated RPM.
3. Check for blocked vents (posters, stored items, dust).
4. Verify that cabinet temperature drops below 45°C within 30 minutes. Batteries resume charging automatically.

## 5. Battery fault (E-604)
1. Leave the slot locked until the battery temperature falls below 45°C (monitor remotely).
2. Remove the battery using thermal gloves; inspect for swelling, leakage, discolouration, or casing deformation.
3. Place the battery in the sand-filled quarantine bin, at least 3 m from other batteries and away from combustibles.
4. Monitor for 24 hours (temperature, voltage).
5. Mark the battery "Quarantined - Do Not Use" in the asset system and raise an RMA with the Battery Service Centre.
6. Inspect the slot connector for burn marks before re-enabling the slot.

## 6. Reference past incidents
- INC-2026-04117 / INC-2026-04121 (WMQISXM1V1-02616, battery INSMOMAH0809A061E913): cabinet overheating from a clogged filter and weak fan; battery was healthy.
- INC-2026-10401 / INC-2026-10402 (WMQISXM1V1-00369, battery INSMOMAH1209C176F813): cell group 11 hotspot at 61°C; battery quarantined and sent for RMA.
