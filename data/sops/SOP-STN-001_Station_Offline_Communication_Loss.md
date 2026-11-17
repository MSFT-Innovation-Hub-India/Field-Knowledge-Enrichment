# SOP-STN-001: Station Offline / Communication Loss / Authentication & OTA Failures

| Field | Value |
|---|---|
| SOP ID | SOP-STN-001 |
| Applies to | All SwapStation-X1 (Gen1, Gen2) |
| Error codes | E-101 (Cloud comm loss), E-110 (OTA update failed), E-120 (Rider authentication failure) |
| Severity | P2 (P1 if more than 4 hours offline at a station with > 100 swaps/day) |
| Owner | NOC Team, Field Engineer |
| Version | 3.1 (2026-06-30) |

## 1. Symptoms
- Station shows "Offline" on the operations dashboard; last heartbeat older than 10 minutes.
- Swaps may still work locally (offline mode) but transactions are not synced.
- Station stuck in "Updating" state (E-110).
- Riders see "Authentication failed" on QR or RFID (E-120).

## 2. Safety
No high-voltage work is needed for this SOP. Do not open the power cabinet; the modem and controller sit in the low-voltage compartment.

## 3. Remote troubleshooting (NOC, first 15 minutes)
1. Check the dashboard for the last heartbeat time and the last error code.
2. Check the SIM status in the telecom portal (active, data balance, last session).
3. Send a remote modem reboot command (`modem.reboot`). Wait 5 minutes.
4. If dual-SIM or Wi-Fi/Ethernet backup exists, force failover (`net.failover secondary`).
5. For E-110: run `ota.status`. If the package is partial or corrupt, run `ota.rollback` to the last stable firmware.
6. If the station is still offline after 30 minutes, create a field ticket.

## 4. On-site troubleshooting (Field Engineer)
1. Check modem LEDs: solid green = connected, blinking = searching, off = no power.
2. Power-cycle the modem (low-voltage breaker LV-MB2) and wait 3 minutes.
3. Reseat the SIM card; clean the contacts. Check the antenna cable and connector for damage or water.
4. Measure signal strength from the controller console (`net.signal`). RSRP worse than -110 dBm means relocate the antenna or install an external high-gain antenna.
5. For E-120: check the RFID reader cable at the controller; clean the QR camera lens and apply anti-fog coating in humid locations. Enable RFID fallback if QR is unreliable.
6. Confirm the offline transaction queue synced (`txn.queue` should show 0).

## 5. Resolution verification
- Heartbeat received for 15 continuous minutes.
- Test swap completed and visible on the dashboard.
- Close the ticket with the root cause category: SIM / Network / Antenna / Modem / Firmware / Reader.

## 6. Preventive notes
- Schedule OTA updates in off-peak windows (01:00–04:00) and only when signal is good or a wired backup is available.
- Stations with more than 2 comm-loss incidents per month should get a dual-SIM upgrade.

## 7. Reference past incidents
- INC-2026-06231 (WMQISXM1V1-02616): SIM session stuck; on-site modem power cycle fixed it.
- INC-2026-07712 (WMQISXM1V1-02614): OTA partial download; rollback from NOC.
- INC-2026-08310 (WMQISXM1V1-00369): QR lens fogging; cleaned and anti-fog applied.
