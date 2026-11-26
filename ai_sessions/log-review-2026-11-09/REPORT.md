# BFT-SMaRt log comparison

Line order is used throughout; the logs contain no wall-clock timestamps. Any numeric timestamp below is the protocol epoch timestamp. In `main.log`, `[replicaN]` is directly observed. In the other logs, attribution is limited to explicit `I am:N` or `from replica N` fields; untagged local events are not assigned to a replica.

## Per-log overview

| Log | Lines | Propose CIDs | WRITE sends (tagged) | ACCEPT sends (tagged) | Decisions | Timeouts | Regency events | Spliced client lines |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| main.log | 127966 | 1000 (0–999) | 3996 | 3991 | 3995 | 0 | 0 | 857 |
| main_2.log | 128229 | 1000 (0–999) | 4000 | 4002 | 4000 | 6 | 44 | 1150 |
| main_3.log | 128128 | 1000 (0–999) | 4000 | 4000 | 4000 | 0 | 0 | 1145 |
| main_4.log | 129668 | 1000 (0–999) | 4000 | 4002 | 4000 | 7 | 1179 | 1153 |

## Consensus-chain coverage

A quorum marker with count >= 3 is treated as observed quorum evidence (N=4, F=1). Application/reply values are mapped to CID+1 as a workload inference. The order checks below use the first matching source line in each merged log, not a global causal clock.

| Log | PROPOSE CIDs | WRITE quorum CIDs | ACCEPT send CIDs | ACCEPT quorum CIDs | decision CIDs | application values mapped | reply values mapped | ordered through decision | full line-order chain |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| main.log | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 | 857 | 998 | 188 |
| main_2.log | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 |
| main_3.log | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 |
| main_4.log | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 |

## View and WRITE-vote order

The view tuple is inferred as regency:PROPOSE leader:protocol epoch timestamp. WRITE receive order below is the sequence of distinct `from replica N` senders per CID in merged line order. It is not a wall-clock or causal ordering; ACCEPT receive-sender records are not present.

- **main.log:** view patterns [('0:0:0', 1000)]; first WRITE-receive sender counts {0: 607, 1: 115, 2: 141, 3: 137}; last sender counts {0: 72, 1: 318, 2: 304, 3: 306}.
- **main_2.log:** view patterns [('1:1:0', 999), ('0:0:0', 1)]; first WRITE-receive sender counts {0: 158, 1: 513, 2: 153, 3: 176}; last sender counts {0: 303, 1: 88, 2: 326, 3: 283}.
- **main_3.log:** view patterns [('0:0:0', 1000)]; first WRITE-receive sender counts {0: 515, 1: 144, 2: 164, 3: 177}; last sender counts {0: 108, 1: 314, 2: 325, 3: 253}.
- **main_4.log:** view patterns [('1:1:0', 999), ('0:0:0', 1)]; first WRITE-receive sender counts {0: 160, 1: 544, 2: 153, 3: 143}; last sender counts {0: 290, 1: 78, 2: 309, 3: 323}.

## Regency results

- **main.log: no regency-change events.** Regency 0 is the baseline; its view ID 0 is the membership view. View lines: 21, 33, 45, 56.
- **main_2.log:** attempted regencies [1]; installed nonzero regencies [1]. 
  - regency 1: candidate leader 1 (rule-based inference); distinct STOP senders [0, 1, 2, 3] (4; F+1=2 reached); first received sender 0 (starter inferred); order of first observed senders 0>3>1>2; status pairs 0->1 x4, 1->1 x10; untagged local STOP-send lines 173;176;185;190; STOP-receive samples [177, 178, 181, 207, 209]; status samples [179, 187, 192, 220, 223]; installation-status lines (if observed) 196;200;202;208.
- **main_3.log: no regency-change events.** Regency 0 is the baseline; its view ID 0 is the membership view. View lines: 21, 33, 45, 57.
- **main_4.log:** attempted regencies [1, 2]; installed nonzero regencies [1]. 
  - regency 1: candidate leader 1 (rule-based inference); distinct STOP senders [0, 1, 2, 3] (4; F+1=2 reached); first received sender 0 (starter inferred); order of first observed senders 0>3>1>2; status pairs 0->1 x4, 1->1 x573, 1->2 x4; untagged local STOP-send lines 173;176;187;188; STOP-receive samples [177, 179, 181, 208, 218]; status samples [182, 190, 192, 129666, 129668]; installation-status lines (if observed) 200;209;211;215.
  - regency 2: candidate leader 2 (rule-based inference); distinct STOP senders [1] (1; F+1=2 not reached); first received sender 1 (starter inferred); order of first observed senders 1; status pairs 1->2 x4; untagged local STOP-send lines 201; STOP-receive samples [210, 214, 220, 129665, 129667]; status samples [203, 205, 213, 232]; installation-status lines (if observed) none.
  - **Stall evidence:** regency 2 has 567 received STOP records from [1]; first/last STOP lines (210, 129667); 4 status records say `Last regency: 1, next regency: 2` (sample lines 203;205;213;232); no `Last regency: 2, next regency: 2` installation record occurs. Distinct later CIDs >0 with decision markers after the first regency-2 STOP: 999 (1–999), 3996 decision markers. **Hypothesis:** the regency-2 attempt stalled without installing a replacement; observed decisions for later CIDs continue under the previously installed view.

## Interpretation and caveats

- `WRITE` and `ACCEPT` send order means the order of identity-tagged send lines for a CID in the merged file. For a retried CID, it may combine attempts; recovery `Sending WRITE message for CID ...` has no sender identity and is kept separate.
- `WRITE received from:N` gives vote sender identity. Its sequence is merged-file line order, not a proven global causal/clock order. No `ACCEPT received from:N` records were found; ACCEPT receive order is therefore unavailable. Quorum counts establish only observed count thresholds.
- Recovery timeout lines do not carry a CID; the run-summary row leaves them unassigned, while nearby retry WRITEs explicitly identify CID 0 at epoch timestamp 1. Application counter/reply values are mapped to CID+1 only as a workload-based inference.
- `[replicaN]` prefixes are trusted only in `main.log`. In the other logs, a sender is attributed only from `I am:N` or `from replica N`; status/quorum/decision records are intentionally left unattributed.
- `spliced_client_lines.csv` preserves raw client-output lines with multiple records, client/protocol mixing, or reply values concatenated with following text. Numeric reply prefixes can be counted, but malformed line content and ordering should not be over-interpreted.
- `regency % N` is reported as the requested leader candidate rule, not treated as proof; observed `PROPOSE received from:N` leaders are shown separately in the CSV.

## Deliverables

| File | Contents |
|---|---|
| `analyze_logs.py` | Reproducible parser and report/CSV/plot generator. |
| `q1_progress.csv` / `q1_progress.png` | Per-log progress counts/line references and comparison plot. |
| `q2_sender_order.csv` / `q2_sender_order.png` | Per-CID first/last WRITE and ACCEPT sender, count, evidence lines. |
| `q3_views_votes.csv` / `q3_views_votes.png` | Per-CID inferred regency, observed leader, epoch(s), send/receive order. |
| `q4_consensus_chain.csv` / `q4_consensus_chain.png` | Per-CID/epoch phase counts, quorum counts and evidence lines. |
| `q5_timeout_recovery.csv` / `q5_timeout_recovery.png` | One run-summary row per log for untagged timeout/leader-change markers, plus per-CID/epoch retry and quorum rows. |
| `q6_regencies.csv` / `q6_regencies.png` | Attempted/installed regencies, STOP participation, status pairs and leadership evidence. |
| `unusual_messages.csv` | Warning/error and selected unusual recovery/protocol lines. |
| `spliced_client_lines.csv` | Source line numbers and raw text for detected spliced client output. |

## What could still be wrong

Merged line order cannot establish wall-clock timing or causality between replicas. The inferred local-regency window follows untagged `Last regency / next regency` status lines, which may come from different replicas. A missing installation marker means no installation was observed in the available log, not necessarily that the process never installed it. Workload counter value-to-CID mapping and timeout-to-CID mapping are inferences. The log snapshots may be truncated or contain output interleaving that the parser cannot unambiguously separate.
