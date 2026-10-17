---
doc_type: manual
asset_family: CNC
title: Spindle service manual, VX-640 and HX-500
---
# Spindle service manual: Varnell VX-640 (IND1) and HX-500 (MTY1)

Synthetic Corvane document. Applies to CNC-01 to CNC-05 (VX-640 vertical machining
centers, Indianapolis) and CNC-06 to CNC-08 (HX-500 horizontal machining centers, Monterrey).

## 1. Spindle data

| Item | VX-640 | HX-500 |
| --- | --- | --- |
| Max speed | 12,000 rpm | 10,000 rpm |
| Taper | CAT40 | CAT50 |
| Bearing set (matched pair) | SP-BRG-0114 | SP-BRG-0116 |
| Labyrinth seal kit | SP-SEAL-0207 | SP-SEAL-0207 |
| Spindle nut torque | 180 N·m | 220 N·m |
| Vibration sensors | overall velocity only | overall velocity, 1x velocity, bearing envelope |

## 2. Vibration and temperature limits

- Overall spindle vibration: warning 4.5 mm/s, trip 7.1 mm/s.
- Bearing envelope (HX-500 only): warning 1.5 g, trip 2.5 g.
- Spindle bearing temperature: warning 55 °C, trip 70 °C.
- On the VX-640 the overall sensor cannot tell bearing damage from toolholder imbalance.
  Before tearing down a VX-640 spindle, swap the toolholder and re-run the vibration
  check at the same speed. If vibration drops below 3 mm/s, it was the holder.
  If vibration stays high and bearing temperature is above 55 °C, plan a bearing change.

## 3. Bearing replacement procedure

Required parts: one bearing set (SP-BRG-0114 for VX-640, SP-BRG-0116 for HX-500) and one
labyrinth seal kit SP-SEAL-0207. Estimated time: 10 hours, two technicians.
Skills: spindle rebuild. Apply the lockout procedure in the lockout/tagout SOP first.

1. Remove the toolholder, front cover and labyrinth seal.
2. Disconnect the oil-air lube lines and cap them.
3. Remove the spindle nut with the spindle wrench. Discard the nut lock washer.
4. Press the spindle shaft out of the housing with the hydraulic fixture. Never hammer.
5. Heat the new bearings to 80 °C on the induction heater. Do not use a flame.
6. Fit the bearings with the matched-pair marks aligned (the "V" on the outer rings points
   to the nose of the spindle).
7. Torque the spindle nut to 180 N·m (VX-640) or 220 N·m (HX-500).
8. Fit the new labyrinth seal kit and reconnect the lube lines.
9. Run-in: 15 minutes each at 2,000, 4,000, 6,000, 8,000 and 10,000 rpm. Bearing
   temperature must stay below 45 °C. If it goes above 50 °C, stop and let it cool
   before continuing.
10. Record the vibration readings after run-in on the work order.

## 4. Lubrication

- Oil-air lubrication, ISO VG 32 spindle oil.
- Normal lube pressure 2.2 to 2.8 bar. Alarm below 1.8 bar.
- Low lube pressure with rising bearing temperature points to lube starvation, not bearing
  wear. Replace the lube cartridge SP-LUB-0402 and the line filter SP-FLT-0405, then bleed
  the lines. Two hours.

## 5. Spindle motor

- Motor winding temperature: warning 100 °C, trip 115 °C.
- The usual cause of motor overtemperature is a seized cooling fan. Replace with
  SP-FAN-0044 (electrician, two hours).
