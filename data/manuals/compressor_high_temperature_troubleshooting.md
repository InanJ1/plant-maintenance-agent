---
doc_type: troubleshooting
asset_family: CMP
title: Compressor high discharge temperature, technician notes
---
# Troubleshooting notes: high discharge temperature on the RS-75 compressors

Synthetic Corvane document. Written up from technician notes at IND1 and MTY1 so the
knowledge is not only in people's heads.

## What to check first

1. Read the cooler approach temperature (cooler outlet minus ambient) on the controller.
   - Above 15 °C: the cooler is fouled. Blow out or wash the cooler core. This is the most
     common cause, especially at MTY1 from May to September. No parts needed.
   - Normal (under 10 °C) but oil injection temperature above 85 °C: the thermostatic valve
     is stuck in bypass. Replace element SP-VLV-0520.
2. Check fluid level in the sight glass. Low fluid also raises discharge temperature.
3. Check the oil filter differential pressure. A blocked oil filter starves the airend.

## When the reading itself is wrong

- If discharge temperature jumps above 120 °C in seconds while the compressor sounds normal
  and the oil injection temperature is normal, suspect the discharge RTD, not the machine.
  Check the airend outlet with the IR gun. A failed RTD reads high or open.
- The discharge RTD (Tolland part TA-RTD-100) is not stocked at either plant. Order from
  Tolland Air Systems, about 10 days. Until then CMP-01 and CMP-02 can run lead/lag on the
  good unit.

## Seasonal note for MTY1

- Clean the CMP-03 cooler every month from May to September. Ambient in the Monterrey
  compressor room reaches 42 °C in summer.
