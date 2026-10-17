# Evaluation: Corvane alarms

20 synthetic alarms from `eval/alarms.yaml`. Produced by `python scripts/run_eval.py`.

| Metric | Corvane workflow | machina built-in workflow |
| --- | --- | --- |
| Failure mode correct | 17/20 (85%) | 14/20 (70%) |
| Priority correct | 20/20 (100%) | 6/20 (30%) |
| Required parts correct (exact SKU and qty) | 18/20 (90%) | 4/20 (20%) |
| All three correct | 17/20 (85%) | 0/20 (0%) |

## Per alarm (Corvane workflow)

| Alarm | Asset | Expected FM | Got FM | Exp. priority | Got | Exp. parts | Got parts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ALM-2610-001 | CNC-04 | CNC-SPBRG-WEAR | CNC-SPBRG-WEAR | high | high | SP-BRG-0114 x1, SP-SEAL-0207 x1 | SP-BRG-0114 x1, SP-SEAL-0207 x1 |
| ALM-2610-002 | CNC-02 | CNC-SPIMB | CNC-SPIMB | high | high | - | - |
| ALM-2610-003 | CNC-07 | CNC-SPBRG-WEAR | CNC-SPBRG-WEAR | high | high | SP-BRG-0116 x1, SP-SEAL-0207 x1 | SP-BRG-0116 x1, SP-SEAL-0207 x1 |
| ALM-2610-004 | CNC-01 | CNC-SPLUB | CNC-SPLUB | high | high | SP-FLT-0405 x1, SP-LUB-0402 x1 | SP-FLT-0405 x1, SP-LUB-0402 x1 |
| ALM-2610-005 | CNC-05 | CNC-SPLUB | CNC-SPBRG-WEAR **(miss)** | medium | medium | SP-FLT-0405 x1, SP-LUB-0402 x1 | SP-BRG-0114 x1, SP-SEAL-0207 x1 **(miss)** |
| ALM-2610-006 | CNC-03 | CNC-DBAR | CNC-DBAR | emergency | emergency | SP-SPRG-0031 x1 | SP-SPRG-0031 x1 |
| ALM-2610-007 | CNC-08 | CNC-COOL | CNC-COOL | medium | medium | SP-FLT-0310 x2 | SP-FLT-0310 x2 |
| ALM-2610-008 | CNC-06 | CNC-SPMOT | CNC-SPMOT | emergency | emergency | SP-FAN-0044 x1 | SP-FAN-0044 x1 |
| ALM-2610-009 | CMP-03 | CMP-COOLER-FOUL | CMP-COOLER-FOUL | high | high | - | - |
| ALM-2610-010 | CMP-01 | CMP-TVALVE | CMP-TVALVE | medium | medium | SP-VLV-0520 x1 | SP-VLV-0520 x1 |
| ALM-2610-011 | CMP-02 | CMP-TVALVE | CMP-COOLER-FOUL **(miss)** | medium | medium | SP-VLV-0520 x1 | - **(miss)** |
| ALM-2610-012 | CMP-03 | CMP-SEP-SAT | CMP-SEP-SAT | emergency | emergency | SP-SEP-0503 x1 | SP-SEP-0503 x1 |
| ALM-2610-013 | CMP-01 | CMP-INFLT-CLOG | CMP-INFLT-CLOG | medium | medium | SP-FLT-0501 x1 | SP-FLT-0501 x1 |
| ALM-2610-014 | CMP-02 | CMP-MOTBRG | CMP-MOTBRG | high | high | SP-BRG-0230 x1 | SP-BRG-0230 x1 |
| ALM-2610-015 | CMP-03 | CMP-SHAFTSEAL | CMP-SHAFTSEAL | high | high | SP-OIL-0550 x1, SP-SEAL-0042 x1 | SP-OIL-0550 x1, SP-SEAL-0042 x1 |
| ALM-2610-016 | CMP-01 | - | CMP-COOLER-FOUL **(miss)** | high | high | - | - |
| ALM-2610-017 | CNV-02 | CNV-ROLLER | CNV-ROLLER | low | low | SP-BRG-0301 x2 | SP-BRG-0301 x2 |
| ALM-2610-018 | TST-01 | TST-SEAL | TST-SEAL | medium | medium | SP-SEAL-0350 x1 | SP-SEAL-0350 x1 |
| ALM-2610-019 | CST-01 | - | - | high | high | - | - |
| ALM-2610-020 | CNC-05 | CNC-COOL | CNC-COOL | high | high | SP-FLT-0310 x2 | SP-FLT-0310 x2 |

## Misses (Corvane workflow)

- ALM-2610-005 (CNC-05, spindle_bearing_temp_c): wrong failure_mode, parts. Expected CNC-SPLUB, got CNC-SPBRG-WEAR. Case note: Hot bearing alone. The cause was a clogged lube line filter; the lube pressure sensor on CNC-05 is not wired to the monitoring system.
- ALM-2610-011 (CMP-02, discharge_temp_c): wrong failure_mode, parts. Expected CMP-TVALVE, got CMP-COOLER-FOUL. Case note: Discharge temperature only (CMP-02 has no approach or injection temperature on the network). Turned out to be the thermostatic valve.
- ALM-2610-016 (CMP-01, discharge_temp_c): wrong failure_mode. Expected None, got CMP-COOLER-FOUL. Case note: Failed discharge RTD (reading jumped in seconds, other temperatures normal). Sensor faults are not in the catalog, so the right output is no failure mode; the RTD is not a stocked part. B + critical = high.

## Per alarm (machina built-in workflow)

| Alarm | Got FM | Got priority | Parts on WO | Parts listed in notification |
| --- | --- | --- | --- | --- |
| ALM-2610-001 | CNC-SPBRG-WEAR | medium (miss) | - | 7 |
| ALM-2610-002 | CNC-SPBRG-WEAR (miss) | medium (miss) | - | 7 |
| ALM-2610-003 | CNC-SPBRG-WEAR | medium (miss) | - | 7 |
| ALM-2610-004 | CNC-SPBRG-WEAR (miss) | medium (miss) | - | 7 |
| ALM-2610-005 | CNC-SPBRG-WEAR (miss) | medium | - | 7 |
| ALM-2610-006 | CNC-DBAR | medium (miss) | - | 7 |
| ALM-2610-007 | CNC-COOL | medium | - | 7 |
| ALM-2610-008 | CNC-SPMOT | medium (miss) | - | 7 |
| ALM-2610-009 | CMP-COOLER-FOUL | medium (miss) | - | 7 |
| ALM-2610-010 | CMP-COOLER-FOUL (miss) | medium | - | 7 |
| ALM-2610-011 | CMP-COOLER-FOUL (miss) | medium | - | 7 |
| ALM-2610-012 | CMP-SEP-SAT | medium (miss) | - | 7 |
| ALM-2610-013 | CMP-INFLT-CLOG | medium | - | 7 |
| ALM-2610-014 | CMP-MOTBRG | medium (miss) | - | 7 |
| ALM-2610-015 | CMP-SHAFTSEAL | medium (miss) | - | 7 |
| ALM-2610-016 | CMP-COOLER-FOUL (miss) | medium (miss) | - | 7 |
| ALM-2610-017 | CNV-ROLLER | medium (miss) | - | 1 |
| ALM-2610-018 | TST-SEAL | medium | - | 1 |
| ALM-2610-019 | - | medium (miss) | - | 0 |
| ALM-2610-020 | CNC-COOL | medium (miss) | - | 7 |
