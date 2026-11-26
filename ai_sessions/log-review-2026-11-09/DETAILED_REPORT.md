# BFT-SMaRt log analysis

## Summary

Four distinct logs were analyzed: [main.log](/home/ahmad/.vscode-server/data/agentSessionData/4fa2f888-d400-43aa-9594-40456401d100/attachments/4d5f30cf-68a7-4b02-816b-f6db968a10d5/main.log), [main_2.log](/home/ahmad/.vscode-server/data/agentSessionData/4fa2f888-d400-43aa-9594-40456401d100/attachments/8152cff6-a247-4080-912c-ca6d727dfc8c/main_2.log), [main_3.log](/home/ahmad/.vscode-server/data/agentSessionData/4fa2f888-d400-43aa-9594-40456401d100/attachments/b8557c40-36b7-4f26-8bf0-379c2b268ebb/main_3.log), and [main_4.log](/home/ahmad/.vscode-server/data/agentSessionData/4fa2f888-d400-43aa-9594-40456401d100/attachments/b00050bd-8532-487a-89e3-65f8e2fae6ef/main_4.log). The extra attachment [file_main_4.log](/home/ahmad/.vscode-server/data/agentSessionData/4fa2f888-d400-43aa-9594-40456401d100/attachments/38ca8a14-3993-48ae-a4ab-fa6c56e84735/file_main_4.log) is byte-for-byte identical to `main_4.log` and is not counted twice.

Each distinct run covers CIDs 0–999. All 1,000 CIDs have proposal, quorum, and local-decision evidence in each run. The two logs with a leader change recover CID 0 at epoch timestamp 1; this is the same CID, not a new consensus. `main_4.log` also has a regency-2 attempt that never shows installation, while decisions continue for CIDs 1–999. `main.log` and `main_3.log` have no leader-change/regency events. The identity-tagged WRITE send order tracks the leader change: replica 0 is most often first in the two regency-0 runs, and replica 1 is most often first after regency 1 is installed. ACCEPT send order is much more evenly distributed.

No wall-clock time is present or inferred. All sequences below are source line order. `N=4`, `F=1`, and the quorum threshold is 3; the STOP join threshold `F+1` is 2. The view tuples below are `regency:observed PROPOSE leader:protocol epoch timestamp`. Client counter/reply values do not contain a protocol CID; mapping a sequential value to `CID+1` is an explicit workload inference.

## Per-log results

### [main.log](/home/ahmad/.vscode-server/data/agentSessionData/4d5f30cf-68a7-4b02-816b-f6db968a10d5/main.log)

| Measure | Result |
|---|---|
| Progress and chain | 1,000 distinct proposal CIDs; 1,000 WRITE-quorum, ACCEPT-quorum, and decision CIDs. 1,000 counter values and 857 reply values map to CIDs by the `CID+1` inference; 188 CIDs have the complete chain in merged line order. |
| First / last WRITE sender (1,000 CIDs) | First: r0=711, r1=92, r2=111, r3=86. Last: r0=61, r1=314, r2=316, r3=309. |
| First / last ACCEPT sender (1,000 CIDs) | First: r0=218, r1=295, r2=247, r3=240. Last: r0=237, r1=237, r2=261, r3=265. |
| WRITE receipt order | First observed sender: r0=607, r1=115, r2=141, r3=137. Last: r0=72, r1=318, r2=304, r3=306. |
| View / leadership | `0:0:0` for all 1,000 CIDs. Regency 0 is the baseline; no regency change. |
| Timeout, recovery, anomalies | No timeout or regency events; no explicit WARN/ERROR/exception. 857 client-output lines are flagged as spliced or otherwise ambiguous. |

### [main_2.log](/home/ahmad/.vscode-server/data/agentSessionData/8152cff6-a247-4080-912c-ca6d727dfc8c/main_2.log)

| Measure | Result |
|---|---|
| Progress and chain | 1,000 distinct proposal CIDs; 1,000 WRITE-quorum, ACCEPT-quorum, and decision CIDs. 1,000 counter values and 1,000 reply values map to CIDs by the `CID+1` inference; 1,000 complete chains appear in merged line order. |
| First / last WRITE sender (1,000 CIDs) | First: r0=132, r1=624, r2=126, r3=118. Last: r0=313, r1=50, r2=335, r3=302. |
| First / last ACCEPT sender (1,000 CIDs) | First: r0=243, r1=204, r2=259, r3=294. Last: r0=269, r1=216, r2=261, r3=254. |
| WRITE receipt order | First observed sender: r0=158, r1=513, r2=153, r3=176. Last: r0=303, r1=88, r2=326, r3=283. |
| View / leadership | `0:0:0` for CID 0 and `1:1:0` for CIDs 1–999. Regency 1 is installed; candidate/observed new leader is r1. The previous leader r0 has no later observed PROPOSEs. |
| Timeout, recovery, anomalies | Six timeout records, four request-forwarding records, and two “Attempting to start leader change” records precede one installed regency. Four distinct STOP senders meet `F+1`; no uninstalled regency observed. No explicit WARN/ERROR/exception. 1,150 client-output lines are flagged as spliced or otherwise ambiguous. |

### [main_3.log](/home/ahmad/.vscode-server/data/agentSessionData/4fa2f888-d400-43aa-9594-40456401d100/attachments/b8557c40-36b7-4f26-8bf0-379c2b268ebb/main_3.log)

| Measure | Result |
|---|---|
| Progress and chain | 1,000 distinct proposal CIDs; 1,000 WRITE-quorum, ACCEPT-quorum, and decision CIDs. 1,000 counter values and 1,000 reply values map to CIDs by the `CID+1` inference; 1,000 complete chains appear in merged line order. |
| First / last WRITE sender (1,000 CIDs) | First: r0=618, r1=114, r2=128, r3=140. Last: r0=73, r1=304, r2=312, r3=311. |
| First / last ACCEPT sender (1,000 CIDs) | First: r0=203, r1=279, r2=263, r3=255. Last: r0=247, r1=228, r2=263, r3=262. |
| WRITE receipt order | First observed sender: r0=515, r1=144, r2=164, r3=177. Last: r0=108, r1=314, r2=325, r3=253. |
| View / leadership | `0:0:0` for all 1,000 CIDs. Regency 0 is the baseline; no regency change. |
| Timeout, recovery, anomalies | No timeout or regency events; no explicit WARN/ERROR/exception. 1,145 client-output lines are flagged as spliced or otherwise ambiguous. |

### [main_4.log](/home/ahmad/.vscode-server/data/agentSessionData/4fa2f888-d400-43aa-9594-40456401d100/attachments/b00050bd-8532-487a-89e3-65f8e2fae6ef/main_4.log)

| Measure | Result |
|---|---|
| Progress and chain | 1,000 distinct proposal CIDs; 1,000 WRITE-quorum, ACCEPT-quorum, and decision CIDs. 1,000 counter values and 1,000 reply values map to CIDs by the `CID+1` inference; 1,000 complete chains appear in merged line order. |
| First / last WRITE sender (1,000 CIDs) | First: r0=115, r1=624, r2=132, r3=129. Last: r0=315, r1=59, r2=322, r3=304. |
| First / last ACCEPT sender (1,000 CIDs) | First: r0=270, r1=219, r2=263, r3=248. Last: r0=260, r1=250, r2=240, r3=250. |
| WRITE receipt order | First observed sender: r0=160, r1=544, r2=153, r3=143. Last: r0=290, r1=78, r2=309, r3=323. |
| View / leadership | `0:0:0` for CID 0 and `1:1:0` for CIDs 1–999. Regency 1 is installed with r1 as observed leader; r0 has no later observed PROPOSEs. Regency 2 (candidate r2) is attempted but no installation is observed. |
| Timeout, recovery, anomalies | Seven timeout records, four request-forwarding records, and three “Attempting to start leader change” records precede/overlap the regency-1 recovery; four distinct STOP senders meet `F+1`. Regency 2 has only one distinct STOP sender, below threshold. No explicit WARN/ERROR/exception. 1,153 client-output lines are flagged as spliced or otherwise ambiguous. |

## Evidence and interpretation

### Core path and retries

- In `main.log`, CID 0 receives PROPOSE from leader 0 at line 84; a WRITE quorum of 3 is recorded at line 113, followed by ACCEPT at line 114; an ACCEPT quorum of 3 and local decision appear at lines 167–168.
- In `main_3.log`, CID 0 follows the same path: PROPOSE lines 84, 88, 90, and 93; WRITE quorum/ACCEPT evidence at lines 114, 115, 129, 130, 131, 132, 143, and 144; ACCEPT quorum/decision at lines 179 and 180.
- In `main_2.log`, the request timeout entries are at lines 163, 165, 167, 169, 171, and 174; four forwarding records to the leader occur at lines 164, 166, 168, and 170; leader-change attempts are logged at lines 172 and 175. Those timeout records do not name a CID. Their association with CID 0 is inferred from the adjacent recovery, which explicitly sends WRITE for CID 0 at timestamp 1, beginning at line 221. The retry reaches WRITE quorum at lines 245, 251, 264, and 279; ACCEPT is sent at lines 246, 253, 265, and 280; ACCEPT quorum and decision markers follow at lines 300, 301, 302, 305, and 306.
- In `main_4.log`, timeout records occur at lines 163, 165, 167, 169, 171, 174, and 195; four forwarding records to the leader occur at lines 164, 166, 168, and 170; leader-change attempts are logged at lines 172, 175, and 196. Regency-1 recovery sends STOPDATA at line 197 and SYNC at line 222, then resumes CID 0 at timestamp 1 at line 230. The retry reaches WRITE quorum at lines 252, 256, 262, and 277; ACCEPT is sent at lines 253, 257, 263, and 278; ACCEPT quorum and decision markers follow at lines 306, 308, 311, 312, and 318. Thus the retry is a higher-timestamp attempt of the same CID, not a replacement CID.
- The analyzer checks application counter/reply values by the sequential `CID+1` workload mapping. These values are not protocol CID fields. The lower complete-chain count in `main.log` reflects merged line order and spliced client output; it is not evidence that the protocol decided only 188 CIDs. All 1,000 CIDs have decision evidence.

### View and message ordering

- The recurring view patterns are `0:0:0` in `main.log` and `main_3.log`, and `1:1:0` for CIDs 1–999 in `main_2.log` and `main_4.log`. The single CID 0 in those latter logs begins under `0:0:0` and is retried at epoch timestamp 1. Membership view `ID:0` is distinct from these regencies and remains the same in all four logs.
- WRITE first-sender counts strongly favor the current leader: r0 is first for 711/1,000 CIDs in `main.log` and 618/1,000 in `main_3.log`; after regency 1, r1 is first for 624/1,000 CIDs in each of `main_2.log` and `main_4.log`. The same shift appears in WRITE receipt order: r0 is the first observed vote sender most often in the no-change runs, while r1 is first for 513/1,000 and 544/1,000 CIDs in `main_2.log` and `main_4.log`.
- WRITE last-sender counts favor replicas other than the leader: r0 is last for only 61 and 73 CIDs in the two regency-0 logs; r1 is last for only 50 and 59 CIDs after regency 1, while r2 is last for 335 and 322 CIDs. This supports an ordering difference associated with the leader, not a claim about elapsed latency.
- ACCEPT send first/last counts are comparatively even. ACCEPT receive-order sender identities are not logged, so an ACCEPT vote-receipt ordering cannot be established.
- These first/last and vote-order results use the first/last identity-bearing line per CID in merged line order. The recovery WRITE lines lack `I am:N` and are counted separately. ACCEPT send lines have no epoch timestamp; for CID 0, first/last ACCEPT ordering therefore spans the retry rather than separating epochs.

### Regency inventory, join order, and stalls

| Log | Regency inventory | STOP senders and join threshold | Leadership / progress |
|---|---|---|---|
| `main.log` | No regency-change attempt or installation; regency 0 is baseline. | No STOP events. | Leader candidate r0; all CIDs decide. |
| `main_2.log` | Regency 1 attempted and installed; no other nonzero regency. | Four distinct senders, r0/r1/r2/r3; `F+1=2` reached. First received sender is r0, then r3, r1, r2 in merged line order. Starter attribution to r0 is inferred. | Regency-1 PROPOSE leader is r1; previous leader r0 has no later PROPOSEs. CID 0 resumes at timestamp 1 and decides. |
| `main_3.log` | No regency-change attempt or installation; regency 0 is baseline. | No STOP events. | Leader candidate r0; all CIDs decide. |
| `main_4.log` | Regency 1 attempted and installed; regency 2 attempted but no installation observed. | Regency 1: four distinct senders r0/r1/r2/r3; threshold reached. First-seen order is r0, r3, r1, r2; starter attribution to r0 is inferred. Regency 2: only r1 is observed as a distinct STOP sender; threshold not reached. | Regency 1 uses r1, replacing r0. Regency 2's candidate is r2, but no r2-led proposal or `2 -> 2` installation status is observed. Later CIDs continue deciding under observed leader r1. |

Line evidence for the regency findings:

- In `main_2.log`, untagged local STOP sends for regency 1 occur at lines 173, 176, 185, and 190. The first received STOP is from r0 at line 177; first-seen distinct senders are r0 at line 177, r3 at line 183, r1 at line 188, and r2 at line 195. Thus r2 is last among the distinct senders observed in merged line order, an inferred late arrival. Status reaches `Last regency: 1, next regency: 1` at line 196. Because STOP-send lines contain no replica ID, r0 as starter is an inference from the first received sender, not a directly tagged local action.
- In `main_4.log`, regency-1 STOP-send lines are 173, 176, 187, and 188. First-seen received senders are r0 at line 177, r3 at line 183, r1 at line 191, and r2 at line 202. Status `0 -> 1` occurs at line 182 and `1 -> 1` at line 200, supporting installation of regency 1.
- The regency-2 attempt in `main_4.log` sends an untagged STOP at line 201. The only observed sender is r1, first at line 210 and repeated 567 times; the first `1 -> 2` status is at line 203. Four `1 -> 2` status records are present, but no `2 -> 2` status occurs. The tail continues to show `1 -> 1` at lines 129664, 129666, and 129668, while STOPs from r1 continue at lines 129663, 129665, and 129667.

  **Hypothesis:** regency 2 did not install because the `F+1=2` join threshold was not reached, leaving regency 1 current. The log does not establish why r0, r2, and r3 did not join this attempt.
- After the first regency-2 STOP, all later CIDs 1–999 still have decision markers (3,996 markers) and the observed leader remains r1. Thus the uninstalled attempt does not prevent later decisions in this log. This is a line-order observation, not proof that the attempt had no performance effect.
- In both logs with regency 1, 3,996 observed PROPOSEs are from r1 for the later CIDs, and none are attributed to the previous leader r0. The expected leader IDs (`regency mod N`) match the observed PROPOSE leaders for installed regencies. For uninstalled regency 2, the expected candidate r2 is not evidence that r2 actually became leader.
- A scan found no explicit WARN, ERROR, FATAL, exception, or traceback entries. In `main_2.log` and `main_4.log`, the logs explicitly forward the timed-out request to the leader before the STOP/leader-change sequence. Timeout/recovery messages are the main unusual protocol events. The raw client lines flagged as spliced are listed separately to prevent treating concatenated output as a clean one-event-per-line sequence.

## Saved analysis files

| Question | CSV | Plot | Contents |
|---|---|---|---|
| Q1 progress | [q1_progress.csv](./q1_progress.csv) | [q1_progress.png](./q1_progress.png) | Per-log counts, phase coverage, line references, execution/reply mapping, and comparison. |
| Q2 first/last senders | [q2_sender_order.csv](./q2_sender_order.csv) | [q2_sender_order.png](./q2_sender_order.png) | One row per log/CID/message type, first/last identity-tagged sender, source lines, and recovery-write caveat. |
| Q3 views and votes | [q3_views_votes.csv](./q3_views_votes.csv) | [q3_views_votes.png](./q3_views_votes.png) | Per-CID inferred regency/leader/epoch, PROPOSE leader, WRITE send/receive order, and ACCEPT send order. |
| Q4 consensus chain | [q4_consensus_chain.csv](./q4_consensus_chain.csv) | [q4_consensus_chain.png](./q4_consensus_chain.png) | Per-CID/epoch proposal, quorum, decision, inferred application/reply counts, and evidence lines. |
| Q5 timeout/recovery | [q5_timeout_recovery.csv](./q5_timeout_recovery.csv) | [q5_timeout_recovery.png](./q5_timeout_recovery.png) | Timeout and recovery markers, STOP/STOPDATA/SYNC events, retry WRITE evidence, and run-level counts. |
| Q6 regencies | [q6_regencies.csv](./q6_regencies.csv) | [q6_regencies.png](./q6_regencies.png) | Attempted/installed regencies, observed STOP senders/order, threshold, status pairs, and leadership evidence. |

Additional files: [analyze_logs.py](./analyze_logs.py) reproduces the six CSV/plot pairs; [unusual_messages.csv](./unusual_messages.csv) contains warning/error and selected protocol/recovery lines; [spliced_client_lines.csv](./spliced_client_lines.csv) preserves raw client lines that combine or concatenate records. The saved CSVs and plots were regenerated from the exact four source snapshots and compared byte-for-byte with these outputs.

## Token count

An exact per-task model-token meter was not available during this analysis, so I cannot provide a reliable token count.
