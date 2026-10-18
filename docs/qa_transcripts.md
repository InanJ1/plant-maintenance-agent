# Technician Q&A transcripts

Produced by `python scripts/run_qa.py`. Model `qwen2.5:3b` and embeddings `nomic-embed-text` on the shared local Ollama (CPU only, shared with other jobs). Agent startup (index build) 30.2 s. Docs index: {'mode': 'rag', 'chunk_count': 30}.

Latency per question: median 323.5 s, min 157.7 s, max 559.9 s.

## Q1. CNC-04 has a spindle vibration alarm. What is the bearing replacement procedure and which parts do I need?

Latency 559.9 s, 2 LLM call(s), 5882 prompt + 433 completion tokens. Cited sources: none cited.

> Based on the maintenance SOPs provided, here are the relevant procedures and steps for the maintenance tasks you need to perform:
>
> ### 1. **Disc Spring Stack Replacement**
>    - **Part:** SP-SPRG-0031. Time: 4 hours. Skills: spindle rebuild.
>    - **Steps:**
>      - Use the drawbar press fixture (F-31) to preload the spring stack.
>      - Stack the new springs in the same orientation as the old ones (alternating pairs).
>      - After assembly, verify clamp force with the gauge before releasing the machine.
>
> ### 2. **Lockout/Tagout (LOTO)**
>    - **SOP:** Synthetic Corvane document. Applies to all maintenance work at IND1 and MTY1.
>    - **General Rules:**
>      - Every technician working on the machine puts on a personal lock. One lock per person.
>      - Verify zero energy before starting work: try to start the machine from its controls.
>      - Hot surfaces: wait until surfaces are below 50 \u00b0C or wear heat-rated gloves.
>
> ### 3. **Coolant Filter Change**
>    - **Part:** SP-FLT-0310, 25 micron. Time: one hour.
>    - **Steps:**
>      - Change both cartridges when filter differential pressure reaches 1.2 bar, or when coolant pressure at the spindle drops below 3.0 bar.
>      - Skim tramp oil from the tank at the same time.
>      - If coolant pressure is low within 90 days of a filter change, log it on the work order so the planner can schedule a full flush.
>
> ### 4. **Drawbar Clamp Force Check**
>    - **Nominal Clamp Force:** 20 kN (VX-640) and 32 kN (HX-500).
>    - **Steps:**

## Q2. What are the discharge temperature limits on CMP-03, and what should I check first when it runs hot?

Latency 177.4 s, 1 LLM call(s), 3769 prompt + 192 completion tokens. Cited sources: none cited.

> CMP-03, being a rotating equipment, has a discharge temperature limit of 120°C. When the discharge temperature is high, the first step should be to check the cooler approach temperature. If the cooler approach temperature is normal, the thermostatic valve might be stuck in bypass. In this case, you should replace the thermostatic valve element (SKU: SP-VLV-0520) and ensure that the oil injection temperature settles at 70 to 80°C.
>
> Let's check the cooler approach temperature and the oil injection temperature using the controller. If the cooler approach temperature is normal but the oil injection temperature is above 85°C, the thermostatic valve is likely stuck in bypass. In this scenario, you should replace the thermostatic valve element (SKU: SP-VLV-0520) and verify the oil injection temperature.
>
> Would you like to proceed with these checks now?

## Q3. When was the air/oil separator element last replaced on CMP-01?

Latency 157.7 s, 1 LLM call(s), 3724 prompt + 73 completion tokens. Cited sources: none cited.

> To find out when the air/oil separator element was last replaced on CMP-01, I will need to search through the maintenance history for this specific asset. Let's proceed with fetching the maintenance history for CMP-01.

## Q4. What is the warranty period for the spindle on CNC-06?

Latency 323.5 s, 3 LLM call(s), 9979 prompt + 379 completion tokens. Cited sources: none cited.

> Based on the diagnostic results, the CNC-01 spindle casings (VMC 01 - CP-400 casings) is experiencing high vibration and a bearing temperature above 55°C. The probable failure modes are:
>
> 1. **Spindle lubrication starvation (CNC-SPLUB)**: This mode has a confidence of 0.5, which means the symptoms match this failure mode to some extent. The recommended actions are to replace the lube cartridge, lube line filter, and bleed the oil-air lines.
>
> 2. **Spindle bearing wear (CNC-SPBRG-WEAR)**: This mode has a confidence of 0.33, indicating a lower likelihood but still a possible cause. The recommended actions are to replace the spindle bearing set, labyrinth seal, and run-in the spindle.
>
> Given the high confidence of the spindle bearing wear, it would be advisable to replace the spindle bearing set and labyrinth seal, and run-in the spindle to ensure proper operation. If the issue persists, further investigation into the lubrication system might be necessary.
>
> Would you like to proceed with creating a work order for these recommended actions?

## My assessment of these answers

- Q1: wrong. The answer gives the drawbar disc-spring procedure, not the spindle bearing procedure (parts SP-BRG-0114 and SP-SEAL-0207).
- Q2: partly right. "Check the cooler approach temperature first, then suspect the thermostatic valve (SP-VLV-0520)" matches the notes, but the stated 120 °C limit is wrong (manual: warning 105 °C, trip 110 °C).
- Q3: no answer. The model said it would fetch the history and stopped.
- Q4: wrong. The warranty is not in any document; the model answered about CNC-01 diagnostics instead of saying so.
- No answer carried a citation. With qwen2.5:3b on CPU this agent is not usable yet; the retrieval index works (30 chunks), but the model does not follow machina's tool-calling and citation contract. Next steps: retest with qwen2.5:7b on a server without queueing, and cut the context (machina sends about 3,700 to 10,000 prompt tokens per question).
