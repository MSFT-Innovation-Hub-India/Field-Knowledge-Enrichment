# SOP-BAT-003: Cell Imbalance / Rapid SoC Drop / Deep Discharge / Low State of Health

| Field | Value |
|---|---|
| SOP ID | SOP-BAT-003 |
| Applies to | All battery models |
| Error codes | E-610 (Cell voltage imbalance), E-612 (Rapid SoC drop), E-615 (Deep discharge), E-616 (Low SoH) |
| Severity | P3 (P2 if SoH is below 70%) |
| Owner | Battery Service Centre |
| Version | 3.0 (2026-06-10) |

## 1. Thresholds
| Parameter | Normal | Watchlist | Retire / RMA |
|---|---|---|---|
| Cell voltage delta (at rest) | below 50 mV | 50–100 mV | above 100 mV after balancing |
| State of Health | 80% or more | 75–80% | below 75% |
| Pack voltage (48V NMC) | 42–54.6 V | 39–42 V | below 39 V more than twice |
| Pack voltage (51.2V LFP) | 44–58.4 V | 40–44 V | below 40 V more than twice |

## 2. Cell imbalance / rapid SoC drop (E-610, E-612)
1. Pull the battery from circulation and send it to the service bench.
2. Fully charge it, then allow 12 hours of passive balancing.
3. Recalibrate SoC with one full discharge–charge cycle at 0.5C.
4. Measure the cell voltage delta and the internal resistance of each cell group.
5. Update the BMS firmware to the latest approved version if it is older.
6. If the delta is still above 100 mV, or one cell group's resistance is more than 25% above average, retire the battery.

## 3. Deep discharge (E-615)
1. Do NOT charge at normal current. Use a low-current pre-charge (0.05C) until the pack voltage reaches the minimum normal level.
2. Then charge at the standard rate while monitoring cell temperatures.
3. Run a capacity test to update SoH.
4. Tell the fleet partner or rider to remove batteries from vehicles parked for more than 3 days.

## 4. Low SoH (E-616)
1. Batteries with SoH between 75% and 80% go on the watchlist and are reviewed monthly.
2. Batteries below 75% are retired from swapping and evaluated for second-life use (stationary storage) or recycling.
3. Check the warranty status before raising an RMA.

## 5. Reference past incidents
- INC-2026-05902 / INC-2026-10233 (battery INSMOMAH2109A271AD13): SoC drift and imbalance in cell group 9; balanced, recalibrated, placed on watchlist.
- INC-2026-01467 (battery INSMOMAH1209C176F813): deep discharge after 9 days of parking; recovered with 0.05C pre-charge.
