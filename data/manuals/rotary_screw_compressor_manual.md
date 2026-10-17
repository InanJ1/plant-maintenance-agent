---
doc_type: manual
asset_family: CMP
title: Rotary screw compressor RS-75 service manual
---
# Service manual: Tolland RS-75 rotary screw compressor (CMP-01, CMP-02, CMP-03)

Synthetic Corvane document. CMP-01 and CMP-02 run lead/lag at IND1. CMP-03 is the only
compressor at MTY1, so any CMP-03 stop halts the Monterrey machining hall.

## 1. Data

- Motor 75 kW, drive by Ostrava Motor Works.
- Free air delivery 12.5 m³/min at 7.5 bar. Header pressure setpoint 7.0 bar.
- Fluid: Corvane CF-46 rotary screw fluid, 38 l fill. Pail SP-OIL-0550 (20 l).
- Thermostatic valve opens at 71 °C.

## 2. Alarm limits

| Signal | Normal | Warning | Trip |
| --- | --- | --- | --- |
| Discharge temperature | 80 to 95 °C | 105 °C | 110 °C |
| Cooler approach temperature | under 10 °C | 15 °C | 22 °C |
| Oil injection temperature | 70 to 80 °C | 85 °C | 95 °C |
| Separator differential pressure | under 0.5 bar | 0.8 bar | 1.2 bar |
| Intake filter differential pressure | under 30 mbar | 50 mbar | 75 mbar |
| Oil filter differential pressure | under 0.6 bar | 1.0 bar | 1.5 bar |
| Motor vibration | under 2.8 mm/s | 4.5 mm/s | 7.1 mm/s |

## 3. Service intervals

- Every 2,000 h: replace intake filter element SP-FLT-0501 and oil filter element
  SP-FLT-0502, blow out the cooler.
- Every 4,000 h: change fluid (two pails SP-OIL-0550), replace oil filter SP-FLT-0502 and
  air/oil separator element SP-SEP-0503.

## 4. Separator element replacement

Part: SP-SEP-0503. Time: 3 hours. Apply the lockout/tagout SOP first and vent the
receiver to 0 bar.

1. Remove the scavenge line and the separator tank cover (8 bolts, 85 N·m).
2. Lift out the old element. Check the scavenge line orifice for blockage.
3. Fit the new element with the static-discharge staple in place. Do not remove the staple.
4. Refit the cover with a new gasket. Torque bolts to 85 N·m in a cross pattern.
5. Run loaded for 30 minutes, then check separator differential pressure (should read
   under 0.3 bar on a new element).

## 5. Thermostatic valve element

Part: SP-VLV-0520. Time: 2 hours. If discharge temperature is high while the cooler
approach temperature is normal, the valve may be stuck in bypass. Replace the element and
check that oil injection temperature settles at 70 to 80 °C.

## 6. Shaft seal

Oil under the coupling guard and falling oil level point to the airend shaft seal.
Kit SP-SEAL-0042, 6 hours, plus one pail of fluid to top up.
