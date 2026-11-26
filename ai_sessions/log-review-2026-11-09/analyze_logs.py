#!/usr/bin/env python3
"""Reproducibly analyze four BFT-SMaRt logs using source line order only."""

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


LOG_ROOT = Path(__file__).resolve().parents[2] / "build/install/library/logs"
INPUTS = {
    "main.log": LOG_ROOT / "run-001/main.log",
    "main_2.log": LOG_ROOT / "run-002/main_2.log",
    "main_3.log": LOG_ROOT / "run-003/main_3.log",
    "main_4.log": LOG_ROOT / "run-004/main_4.log",
}
N = 4
F = 1
QUORUM = 2 * F + 1

PATTERNS = {
    "view": re.compile(r"In current view: ID:(\d+); F:(\d+);"),
    "propose_received": re.compile(
        r"PROPOSE received from:(\d+), for consensus cId:(\d+), I am:(\d+)"
    ),
    "propose": re.compile(r"Executing propose for cId:(\d+), Epoch Timestamp:(\d+)"),
    "write_send": re.compile(r"Sending WRITE for cId:(\d+), I am:(\d+)"),
    "write_receive": re.compile(r"WRITE received from:(\d+), for consensus cId:(\d+)"),
    "write_quorum": re.compile(
        r"I have (\d+), WRITE's for cId:(\d+), Epoch timestamp:(\d+)"
    ),
    "retry_write": re.compile(r"Sending WRITE message for CID (\d+), timestamp (\d+)"),
    "accept_send": re.compile(r"Sending ACCEPT message, cId:(\d+), I am:(\d+)"),
    "accept_quorum": re.compile(r"I have (\d+) ACCEPTs for cId:(\d+), Timestamp:(\d+)"),
    "decision": re.compile(r"Deciding consensus (\d+)"),
    "application": re.compile(r"Counter was incremented\. Current value = (\d+)"),
    "reply": re.compile(r"returned value:\s*(-?\d+)"),
    "timeout": re.compile(r"The following requests timed out:"),
    "send_stop": re.compile(r"Sending STOP message to install regency (\d+)"),
    "receive_stop": re.compile(
        r"Received leader change message of type STOP for regency (\d+) from replica (\d+)"
    ),
    "send_stopdata": re.compile(r"Sending STOPDATA of regency (\d+)"),
    "receive_stopdata": re.compile(
        r"Received leader change message of type STOPDATA for regency (\d+) from replica (\d+)"
    ),
    "send_sync": re.compile(r"Sending SYNC message for regency (\d+)"),
    "receive_sync": re.compile(
        r"Received leader change message of type SYNC for regency (\d+) from replica (\d+)"
    ),
    "status": re.compile(r"Last regency: (\d+), next regency: (\d+)"),
}
WARNING_RE = re.compile(r"\b(?:WARN(?:ING)?|ERROR|FATAL|Exception|Traceback)\b", re.I)
UNUSUAL_RE = re.compile(
    r"No out of context SYNC|I did not install any proof|"
    r"not install any proof|timed out|STOPDATA|Sending SYNC",
    re.I,
)
CLIENT_RE = re.compile(r"Counter was incremented|returned value:")
PROTOCOL_RE = re.compile(
    r"PROPOSE|Sending WRITE|WRITE received|I have .*WRITE|"
    r"Sending ACCEPT|I have .*ACCEPT|Deciding consensus|leader change"
)


def parse_log(name, path):
    events = []
    anomalies = []
    spliced = []
    line_count = 0
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line_number, raw in enumerate(stream, 1):
            line_count = line_number
            text = raw.rstrip("\r\n")
            tag = re.match(r"^\[replica(\d+)\]", text)
            # Only main.log has trustworthy [replicaN] prefixes.
            tagged_replica = int(tag.group(1)) if name == "main.log" and tag else ""
            for kind, pattern in PATTERNS.items():
                matches = list(pattern.finditer(text)) if kind in {"application", "reply"} else [
                    pattern.search(text)
                ]
                for match in (match for match in matches if match):
                    values = match.groups()
                    event = {
                        "run": name,
                        "kind": kind,
                        "line": line_number,
                        "text": text,
                        "tagged_replica": tagged_replica,
                    }
                    if kind == "view":
                        event.update(view_id=int(values[0]), f=int(values[1]))
                    elif kind == "propose_received":
                        event.update(
                            leader=int(values[0]),
                            cid=int(values[1]),
                            local_replica=int(values[2]),
                        )
                    elif kind in {"propose", "retry_write"}:
                        event.update(cid=int(values[0]), timestamp=int(values[1]))
                    elif kind in {"write_send", "accept_send"}:
                        event.update(cid=int(values[0]), replica=int(values[1]))
                    elif kind == "write_receive":
                        event.update(sender=int(values[0]), cid=int(values[1]))
                    elif kind in {"write_quorum", "accept_quorum"}:
                        event.update(count=int(values[0]), cid=int(values[1]), timestamp=int(values[2]))
                    elif kind in {"decision"}:
                        event.update(cid=int(values[0]))
                    elif kind == "application":
                        event.update(value=int(values[0]))
                    elif kind == "reply":
                        event.update(value=values[0])
                    elif kind in {
                        "send_stop",
                        "send_stopdata",
                        "send_sync",
                    }:
                        event.update(regency=int(values[0]))
                    elif kind in {"receive_stop", "receive_stopdata", "receive_sync"}:
                        event.update(regency=int(values[0]), sender=int(values[1]))
                    elif kind == "status":
                        event.update(last_regency=int(values[0]), next_regency=int(values[1]))
                    events.append(event)

            if WARNING_RE.search(text):
                anomalies.append(
                    {"run": name, "line": line_number, "kind": "warning_error", "text": text}
                )
            elif UNUSUAL_RE.search(text):
                anomalies.append(
                    {"run": name, "line": line_number, "kind": "protocol_unusual", "text": text}
                )

            counter_matches = len(re.findall(r"Counter was incremented", text))
            reply_matches = len(re.findall(r"returned value:", text))
            client_output_count = counter_matches + reply_matches
            has_client = bool(CLIENT_RE.search(text))
            has_protocol = bool(PROTOCOL_RE.search(text))
            malformed_reply_suffix = bool(
                re.search(r"returned value:\s*-?\d+[^\s,;\]\)]", text)
            )
            if client_output_count > 1 or (has_client and has_protocol) or malformed_reply_suffix:
                reason = (
                    "multiple client output records on one line"
                    if client_output_count > 1
                    else "client output spliced with protocol output"
                    if has_client and has_protocol
                    else "reply value concatenated with following log text"
                )
                spliced.append(
                    {
                        "run": name,
                        "line": line_number,
                        "reason": reason,
                        "client_output_count": client_output_count,
                        "protocol_marker_present": has_protocol,
                        "raw_line": text,
                    }
                )
    by_kind = defaultdict(list)
    by_kind_cid = defaultdict(lambda: defaultdict(list))
    for event in events:
        by_kind[event["kind"]].append(event)
        if "cid" in event:
            by_kind_cid[event["kind"]][event["cid"]].append(event)
    return {
        "name": name,
        "path": path,
        "line_count": line_count,
        "events": events,
        "by_kind": by_kind,
        "by_kind_cid": by_kind_cid,
        "anomalies": anomalies,
        "spliced": spliced,
    }


def selected(data, kind):
    return data["by_kind"].get(kind, [])


def for_cid(data, kind, cid):
    return data["by_kind_cid"].get(kind, {}).get(cid, [])


def grouped(data, kind, key_fields):
    result = defaultdict(list)
    for event in selected(data, kind):
        result[tuple(event[field] for field in key_fields)].append(event)
    return result


def csv_write(path, rows, fields=None):
    if fields is None:
        fields = list(rows[0]) if rows else ["run"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def line_list(events):
    return ";".join(str(event["line"]) for event in events)


def event_summary(data, kind):
    matches = selected(data, kind)
    return len(matches), line_list(matches)


def write_q1(parsed, out):
    rows = []
    kinds = [
        "view", "propose_received", "propose", "write_send", "write_receive",
        "write_quorum", "retry_write", "accept_send", "accept_quorum", "decision",
        "application", "reply", "timeout", "send_stop", "receive_stop",
        "send_stopdata", "receive_stopdata", "send_sync", "receive_sync", "status",
    ]
    for name, data in parsed.items():
        row = {
            "run": name,
            "line_count": data["line_count"],
            "cid_count_propose": len({e["cid"] for e in selected(data, "propose")}),
            "cid_min": min((e["cid"] for e in selected(data, "propose")), default=""),
            "cid_max": max((e["cid"] for e in selected(data, "propose")), default=""),
            "spliced_or_unparsed_client_lines": len(data["spliced"]),
            "warning_error_lines": sum(a["kind"] == "warning_error" for a in data["anomalies"]),
            "unusual_protocol_lines": sum(a["kind"] == "protocol_unusual" for a in data["anomalies"]),
        }
        for kind in kinds:
            row[kind + "_count"], row[kind + "_lines"] = event_summary(data, kind)
        rows.append(row)
    csv_write(out / "q1_progress.csv", rows)
    fields = [
        "propose", "write_send", "write_quorum", "accept_send", "accept_quorum",
        "decision", "application", "reply",
    ]
    fig, ax = plt.subplots(figsize=(13, 6))
    x = np.arange(len(parsed))
    width = 0.095
    colors = ["#4477AA", "#66CCEE", "#228833", "#CCBB44", "#EE6677", "#AA3377", "#BBBBBB", "#000000"]
    for index, (field, color) in enumerate(zip(fields, colors)):
        values = [sum(e["kind"] == field for e in d["events"]) for d in parsed.values()]
        ax.bar(x + (index - 3.5) * width, values, width, label=field, color=color)
    ax.set_xticks(x, list(parsed))
    ax.set_ylabel("Observed log markers (line-order counts)")
    ax.set_title("Q1 — Observed consensus progress and output markers")
    ax.legend(ncol=4, frameon=False)
    ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(out / "q1_progress.png", dpi=170)
    plt.close(fig)


def write_q2(parsed, out):
    rows = []
    for name, data in parsed.items():
        cids = sorted({e["cid"] for kind in ("write_send", "accept_send")
                       for e in selected(data, kind)})
        for kind in ("write_send", "accept_send"):
            for cid in cids:
                sends = sorted(for_cid(data, kind, cid), key=lambda e: e["line"])
                retries = for_cid(data, "retry_write", cid)
                rows.append({
                    "run": name,
                    "cid": cid,
                    "event": "WRITE" if kind == "write_send" else "ACCEPT",
                    "identity_tagged_send_count": len(sends),
                    "first_sender_replica": sends[0]["replica"] if sends else "",
                    "first_sender_line": sends[0]["line"] if sends else "",
                    "last_sender_replica": sends[-1]["replica"] if sends else "",
                    "last_sender_line": sends[-1]["line"] if sends else "",
                    "distinct_senders": ";".join(map(str, sorted({e["replica"] for e in sends}))),
                    "unattributed_recovery_write_sends": len(retries) if kind == "write_send" else 0,
                    "recovery_write_lines": line_list(retries) if kind == "write_send" else "",
                    "attribution": "I am:N field; recovery WRITE sender absent from line",
                })
    csv_write(out / "q2_sender_order.csv", rows)
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    for ax, kind in zip(axes, ("WRITE", "ACCEPT")):
        x = np.arange(len(parsed))
        width = .34
        for position, offset, color in (("first", -width / 2, "#167D8D"),
                                         ("last", width / 2, "#D66B45")):
            counts = []
            for name, data in parsed.items():
                cids = sorted({e["cid"] for e in selected(data, "write_send" if kind == "WRITE" else "accept_send")})
                senders = []
                for cid in cids:
                    matches = [e for e in selected(data, "write_send" if kind == "WRITE" else "accept_send")
                               if e["cid"] == cid]
                    matches.sort(key=lambda e: e["line"])
                    if matches:
                        senders.append(matches[0 if position == "first" else -1]["replica"])
                counts.append(Counter(senders))
            for replica in range(N):
                values = [c[replica] for c in counts]
                ax.bar(x + (replica - 1.5) * width / 4 + offset * .25, values,
                       width / 4, label=f"{position} R{replica}" if ax is axes[0] else None,
                       color=plt.cm.Set2(replica))
        ax.set_title(kind + " identity-tagged sender positions per CID")
        ax.set_ylabel("CIDs")
        ax.grid(axis="y", alpha=.2)
    axes[-1].set_xticks(np.arange(len(parsed)), list(parsed))
    axes[0].legend(ncol=4, frameon=False)
    fig.suptitle("Q2 — First/last replica issuing each protocol message")
    fig.tight_layout()
    fig.savefig(out / "q2_sender_order.png", dpi=170)
    plt.close(fig)


def regency_at_line(data, line):
    installed = [0]
    for event in selected(data, "status"):
        if event["line"] <= line and event["last_regency"] == event["next_regency"]:
            installed.append(event["last_regency"])
    return max(installed)


def write_q3(parsed, out):
    rows = []
    for name, data in parsed.items():
        cids = sorted(
            {e["cid"] for kind in ("propose", "write_receive", "write_send", "accept_send")
             for e in selected(data, kind)}
        )
        for cid in cids:
            proposal_receives = sorted(
                for_cid(data, "propose_received", cid),
                key=lambda e: e["line"],
            )
            props = sorted(for_cid(data, "propose", cid), key=lambda e: e["line"])
            receives = sorted(for_cid(data, "write_receive", cid), key=lambda e: e["line"])
            write_sends = sorted(for_cid(data, "write_send", cid), key=lambda e: e["line"])
            accept_sends = sorted(for_cid(data, "accept_send", cid), key=lambda e: e["line"])
            leader = proposal_receives[0]["leader"] if proposal_receives else ""
            proposal_line = proposal_receives[0]["line"] if proposal_receives else (
                props[0]["line"] if props else 0
            )
            cid_write_quorums = for_cid(data, "write_quorum", cid)
            cid_accept_quorums = for_cid(data, "accept_quorum", cid)
            cid_retries = for_cid(data, "retry_write", cid)
            timestamps = sorted({e["timestamp"] for e in props} |
                                {e["timestamp"] for e in cid_write_quorums} |
                                {e["timestamp"] for e in cid_accept_quorums} |
                                {e["timestamp"] for e in cid_retries})
            read_order = []
            for e in receives:
                if e["sender"] not in read_order:
                    read_order.append(e["sender"])
            status_regency = regency_at_line(data, proposal_line)
            writes_per_view = defaultdict(list)
            for event in write_sends:
                r = regency_at_line(data, event["line"])
                if event["replica"] not in writes_per_view[r]:
                    writes_per_view[r].append(event["replica"])
            accepts_per_view = defaultdict(list)
            for event in accept_sends:
                r = regency_at_line(data, event["line"])
                if event["replica"] not in accepts_per_view[r]:
                    accepts_per_view[r].append(event["replica"])
            rows.append({
                "run": name,
                "cid": cid,
                "first_observed_regency_inferred": status_regency,
                "observed_propose_leader_from_field": leader,
                "candidate_leader_regency_mod_N": status_regency % N,
                "proposal_timestamp_values_epoch_not_clock": ";".join(map(str, timestamps)),
                "view_pattern_first_proposal_regency_leader_epoch": (
                    f"{status_regency}:{leader}:{props[0]['timestamp'] if props else ''}"
                ),
                "first_propose_line": proposal_line or "",
                "propose_received_lines": line_list(proposal_receives),
                "write_send_order": ">".join(str(e["replica"]) for e in write_sends),
                "write_send_lines": line_list(write_sends),
                "first_write_sender": write_sends[0]["replica"] if write_sends else "",
                "last_write_sender": write_sends[-1]["replica"] if write_sends else "",
                "write_receive_distinct_sender_order_line_order": ">".join(map(str, read_order)),
                "write_receive_sender_observation_count": len(receives),
                "write_receive_lines": line_list(receives),
                "accept_send_order": ">".join(str(e["replica"]) for e in accept_sends),
                "accept_send_lines": line_list(accept_sends),
                "accept_quorum_count_sequence": ">".join(str(e["count"]) for e in sorted(
                    (e for e in selected(data, "accept_quorum") if e["cid"] == cid),
                    key=lambda e: e["line"])),
                "vote_order_scope": "merged file line order; accept receipt sender is not logged",
                "inference_note": "regency inferred from latest line-order Last==next status; unprefixed local line not replica-attributed",
            })
    csv_write(out / "q3_views_votes.csv", rows)
    fig, axes = plt.subplots(4, 3, figsize=(13, 12), sharey=True)
    kinds = [
        ("write_send", "WRITE send"), ("write_receive", "WRITE receive"),
        ("accept_send", "ACCEPT send"),
    ]
    for r, (name, data) in enumerate(parsed.items()):
        for c, (kind, title) in enumerate(kinds):
            first = Counter()
            last = Counter()
            for cid in {e["cid"] for e in selected(data, kind)}:
                events = sorted((e for e in selected(data, kind) if e["cid"] == cid),
                                key=lambda e: e["line"])
                replica_field = "sender" if kind == "write_receive" else "replica"
                distinct = []
                for event in events:
                    if event[replica_field] not in distinct:
                        distinct.append(event[replica_field])
                if distinct:
                    first[distinct[0]] += 1
                    last[distinct[-1]] += 1
            x = np.arange(N)
            width = .36
            axes[r, c].bar(x - width / 2, [first[i] for i in range(N)], width,
                           label="first distinct", color="#4477AA")
            axes[r, c].bar(x + width / 2, [last[i] for i in range(N)], width,
                           label="last distinct", color="#EE6677")
            axes[r, c].set_title(name + " | " + title)
            axes[r, c].set_xticks(x, [f"R{i}" for i in range(N)])
            axes[r, c].grid(axis="y", alpha=.2)
            if c == 0:
                axes[r, c].set_ylabel("CIDs")
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle("Q3 — Vote sender order in merged line order (not wall-clock order)")
    fig.tight_layout()
    fig.savefig(out / "q3_views_votes.png", dpi=170)
    plt.close(fig)


def write_q4(parsed, out):
    rows = []
    for name, data in parsed.items():
        cids = sorted({
            e["cid"]
            for kind in (
                "propose", "write_quorum", "accept_quorum", "retry_write",
                "write_send", "accept_send", "decision",
            )
            for e in selected(data, kind)
        })
        for cid in cids:
            timestamps = sorted(
                {
                    e["timestamp"]
                    for kind in ("propose", "write_quorum", "accept_quorum", "retry_write")
                    for e in for_cid(data, kind, cid)
                }
            ) or [0]
            cid_decisions = sorted(for_cid(data, "decision", cid), key=lambda e: e["line"])
            app_events = []
            for e in selected(data, "application"):
                if e["value"] == cid + 1:
                    app_events.append(e)
            reply_events = []
            for e in selected(data, "reply"):
                if str(e["value"]).lstrip("-").isdigit() and int(e["value"]) == cid + 1:
                    reply_events.append(e)
            epoch_accept = sorted(for_cid(data, "accept_quorum", cid), key=lambda e: e["line"])
            cid_write_quorums = sorted(
                for_cid(data, "write_quorum", cid), key=lambda e: e["line"]
            )
            cid_accept_sends = sorted(
                for_cid(data, "accept_send", cid), key=lambda e: e["line"]
            )
            decision_timestamp = epoch_accept[-1]["timestamp"] if epoch_accept else (
                timestamps[-1] if timestamps else 0
            )
            for timestamp in timestamps:
                props = [e for e in for_cid(data, "propose", cid) if e["timestamp"] == timestamp]
                write_q = [e for e in for_cid(data, "write_quorum", cid) if e["timestamp"] == timestamp]
                accept_q = [e for e in for_cid(data, "accept_quorum", cid) if e["timestamp"] == timestamp]
                accept_sends = [
                    send for send in cid_accept_sends
                    if (prior_write := [
                        event for event in cid_write_quorums
                        if event["line"] <= send["line"]
                    ])
                    and prior_write[-1]["timestamp"] == timestamp
                ]
                retries = [e for e in for_cid(data, "retry_write", cid) if e["timestamp"] == timestamp]
                execution = app_events if timestamp == decision_timestamp else []
                replies = reply_events if timestamp == decision_timestamp else []
                phase_lines = []
                phase_lines.extend(e["line"] for e in props)
                phase_lines.extend(e["line"] for e in write_q)
                phase_lines.extend(e["line"] for e in accept_sends)
                phase_lines.extend(e["line"] for e in accept_q)
                phase_lines.extend(e["line"] for e in cid_decisions)
                phase_lines.extend(e["line"] for e in execution)
                phase_lines.extend(e["line"] for e in replies)
                rows.append({
                    "run": name,
                    "cid": cid,
                    "epoch_timestamp": timestamp,
                    "proposal_execution_count": len(props),
                    "proposal_lines": line_list(props),
                    "identity_tagged_write_send_count_cid_all_epochs": sum(
                        e["cid"] == cid for e in selected(data, "write_send")),
                    "write_quorum_max_observed": max((e["count"] for e in write_q), default=0),
                    "write_quorum_lines": line_list(write_q),
                    "unattributed_recovery_write_send_count_this_epoch": len(retries),
                    "recovery_write_lines": line_list(retries),
                    "identity_tagged_accept_send_count_cid_all_epochs": sum(
                        e["cid"] == cid for e in selected(data, "accept_send")),
                    "accept_send_count_assigned_by_preceding_write_quorum": len(accept_sends),
                    "accept_send_lines": line_list(accept_sends),
                    "accept_quorum_max_observed": max((e["count"] for e in accept_q), default=0),
                    "accept_quorum_lines": line_list(accept_q),
                    "local_decision_marker_count_assigned_to_latest_accept_epoch": (
                        len(cid_decisions) if timestamp == decision_timestamp else 0
                    ),
                    "decision_lines": line_list(cid_decisions) if timestamp == decision_timestamp else "",
                    "application_output_count_value_cid_plus_1_inferred": len(execution),
                    "application_lines": line_list(execution),
                    "client_reply_count_value_cid_plus_1_inferred": len(replies),
                    "client_reply_lines": line_list(replies),
                    "phase_evidence_min_line": min(phase_lines) if phase_lines else "",
                    "phase_evidence_max_line": max(phase_lines) if phase_lines else "",
                    "attribution_caveat": "application/reply mapped by sequential counter value=CID+1; not a protocol CID field; unprefixed records are not assigned to a replica",
                })
    csv_write(out / "q4_consensus_chain.csv", rows)
    stage_specs = [
        ("propose", lambda d: len({e["cid"] for e in selected(d, "propose")})),
        ("WRITE quorum >=3", lambda d: len({e["cid"] for e in selected(d, "write_quorum") if e["count"] >= QUORUM})),
        ("ACCEPT send", lambda d: len({e["cid"] for e in selected(d, "accept_send")})),
        ("ACCEPT quorum >=3", lambda d: len({e["cid"] for e in selected(d, "accept_quorum") if e["count"] >= QUORUM})),
        ("local decision", lambda d: len({e["cid"] for e in selected(d, "decision")})),
        ("application value mapped", lambda d: len({e["value"] - 1 for e in selected(d, "application") if e["value"] > 0})),
        ("client reply value mapped", lambda d: len({int(e["value"]) - 1 for e in selected(d, "reply") if str(e["value"]).isdigit() and int(e["value"]) > 0})),
    ]
    fig, ax = plt.subplots(figsize=(13, 6))
    x = np.arange(len(parsed))
    width = .11
    for i, (label, fn) in enumerate(stage_specs):
        ax.bar(x + (i - (len(stage_specs) - 1) / 2) * width, [fn(d) for d in parsed.values()],
               width, label=label)
    ax.set_xticks(x, list(parsed))
    ax.set_ylabel("Distinct CIDs (marker counts may be >1 per CID)")
    ax.set_title("Q4 — Stage coverage by CID; execution/reply association is inferred")
    ax.legend(ncol=3, frameon=False)
    ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(out / "q4_consensus_chain.png", dpi=170)
    plt.close(fig)


def write_q5(parsed, out):
    rows = []
    for name, data in parsed.items():
        recovery_events = [
            e for e in data["events"]
            if e["kind"] in {
                "timeout", "send_stop", "receive_stop", "send_stopdata",
                "receive_stopdata", "send_sync", "receive_sync", "retry_write",
            }
        ]
        recovery_by_kind = defaultdict(list)
        for event in recovery_events:
            recovery_by_kind[event["kind"]].append(event)
        rows.append({
            "run": name,
            "record_scope": "run_recovery_summary",
            "cid": "",
            "epoch_timestamp": "",
            "timeout_count": len(recovery_by_kind["timeout"]),
            "timeout_lines": line_list(recovery_by_kind["timeout"]),
            "STOP_send_count_sender_identity_unavailable": len(recovery_by_kind["send_stop"]),
            "STOP_send_lines": line_list(recovery_by_kind["send_stop"]),
            "STOP_received_count": len(recovery_by_kind["receive_stop"]),
            "STOP_received_senders": ";".join(
                map(str, sorted({e["sender"] for e in recovery_by_kind["receive_stop"]}))
            ),
            "STOP_received_lines": line_list(recovery_by_kind["receive_stop"]),
            "STOPDATA_send_receive_count": (
                len(recovery_by_kind["send_stopdata"]) + len(recovery_by_kind["receive_stopdata"])
            ),
            "STOPDATA_lines": line_list(
                recovery_by_kind["send_stopdata"] + recovery_by_kind["receive_stopdata"]
            ),
            "SYNC_send_receive_count": (
                len(recovery_by_kind["send_sync"]) + len(recovery_by_kind["receive_sync"])
            ),
            "SYNC_lines": line_list(
                recovery_by_kind["send_sync"] + recovery_by_kind["receive_sync"]
            ),
            "recovery_WRITE_send_count": len(recovery_by_kind["retry_write"]),
            "recovery_WRITE_lines": line_list(recovery_by_kind["retry_write"]),
            "WRITE_quorum_max": "",
            "WRITE_quorum_lines": "",
            "ACCEPT_quorum_max": "",
            "ACCEPT_quorum_lines": "",
            "decision_marker_count_for_cid": "",
            "decision_lines": "",
            "evidence_first_line": min((e["line"] for e in recovery_events), default=""),
            "evidence_last_line": max((e["line"] for e in recovery_events), default=""),
            "timeout_cid_attribution": (
                "timeout/leader-change markers are run-scoped; the nearby retry WRITE is "
                "CID 0 at epoch timestamp 1, so a CID 0 association is inferred, not logged"
            ),
        })
        cids = sorted({e["cid"] for kind in ("retry_write", "write_quorum", "accept_quorum", "decision")
                       for e in selected(data, kind)})
        for cid in cids:
            timestamps = sorted({e["timestamp"] for kind in ("retry_write", "write_quorum", "accept_quorum")
                                 for e in for_cid(data, kind, cid)}) or [0]
            for timestamp in timestamps:
                retries = [e for e in for_cid(data, "retry_write", cid) if e["timestamp"] == timestamp]
                write_q = [e for e in for_cid(data, "write_quorum", cid) if e["timestamp"] == timestamp]
                accept_q = [e for e in for_cid(data, "accept_quorum", cid) if e["timestamp"] == timestamp]
                decisions = for_cid(data, "decision", cid)
                rows.append({
                    "run": name,
                    "record_scope": "consensus_epoch",
                    "cid": cid,
                    "epoch_timestamp": timestamp,
                    "timeout_count": "",
                    "timeout_lines": "",
                    "STOP_send_count_sender_identity_unavailable": "",
                    "STOP_send_lines": "",
                    "STOP_received_count": "",
                    "STOP_received_senders": "",
                    "STOP_received_lines": "",
                    "STOPDATA_send_receive_count": "",
                    "STOPDATA_lines": "",
                    "SYNC_send_receive_count": "",
                    "SYNC_lines": "",
                    "recovery_WRITE_send_count": len(retries),
                    "recovery_WRITE_lines": line_list(retries),
                    "WRITE_quorum_max": max((e["count"] for e in write_q), default=0),
                    "WRITE_quorum_lines": line_list(write_q),
                    "ACCEPT_quorum_max": max((e["count"] for e in accept_q), default=0),
                    "ACCEPT_quorum_lines": line_list(accept_q),
                    "decision_marker_count_for_cid": len(decisions) if timestamp == timestamps[-1] else 0,
                    "decision_lines": line_list(decisions) if timestamp == timestamps[-1] else "",
                    "evidence_first_line": min(
                        (e["line"] for e in retries + write_q + accept_q + decisions),
                        default="",
                    ),
                    "evidence_last_line": max(
                        (e["line"] for e in retries + write_q + accept_q + decisions),
                        default="",
                    ),
                    "timeout_cid_attribution": "",
                })
    csv_write(out / "q5_timeout_recovery.csv", rows)
    kinds = ["timeout", "send_stop", "receive_stop", "send_stopdata",
             "receive_stopdata", "send_sync", "receive_sync", "retry_write"]
    fig, ax = plt.subplots(figsize=(14, 6))
    x = np.arange(len(parsed))
    width = .09
    for i, kind in enumerate(kinds):
        ax.bar(x + (i - (len(kinds) - 1) / 2) * width,
               [sum(e["kind"] == kind for e in d["events"]) for d in parsed.values()],
               width, label=kind)
    ax.set_xticks(x, list(parsed))
    ax.set_ylabel("Occurrences in source log")
    ax.set_title("Q5 — Timeout and leader-change recovery markers")
    ax.legend(ncol=4, frameon=False)
    ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(out / "q5_timeout_recovery.png", dpi=170)
    plt.close(fig)


def write_q6(parsed, out):
    rows = []
    for name, data in parsed.items():
        attempted = sorted({e["regency"] for kind in ("send_stop", "receive_stop")
                            for e in selected(data, kind)})
        installed_status = defaultdict(list)
        for e in selected(data, "status"):
            if e["last_regency"] == e["next_regency"]:
                installed_status[e["last_regency"]].append(e)
        regencies = sorted({0} | set(attempted) | {r for r in installed_status if r > 0})
        install_lines = {
            r: min(e["line"] for e in events)
            for r, events in installed_status.items() if r > 0
        }
        for regency in regencies:
            stops = sorted((e for e in selected(data, "receive_stop") if e["regency"] == regency),
                           key=lambda e: e["line"])
            sent = [e for e in selected(data, "send_stop") if e["regency"] == regency]
            installed = regency == 0 or bool(installed_status.get(regency))
            first_event_line = min((e["line"] for e in sent + stops), default="")
            start = install_lines.get(regency, first_event_line if first_event_line else 0)
            later_installs = [line for r, line in install_lines.items() if r > regency and line > start]
            end = min(later_installs, default=data["line_count"] + 1)
            proposals = [e for e in selected(data, "propose_received")
                         if start <= e["line"] < end]
            proposal_senders = Counter(e["leader"] for e in proposals)
            senders_ordered = []
            for e in stops:
                if e["sender"] not in senders_ordered:
                    senders_ordered.append(e["sender"])
            status = [e for e in selected(data, "status")
                      if e["next_regency"] == regency or e["last_regency"] == regency]
            threshold = F + 1
            rows.append({
                "run": name,
                "regency": regency,
                "attempted_in_log": regency in attempted,
                "installed_observed": installed,
                "classification": "baseline/no change" if regency == 0 and not attempted else (
                    "installed" if installed else "attempted but not installed by log end"),
                "candidate_leader_regency_mod_N": regency % N,
                "observed_propose_leader_counts_in_regency_window": ";".join(
                    f"{replica}:{count}" for replica, count in sorted(proposal_senders.items())),
                "first_observed_STOP_sender_inferred_starter": stops[0]["sender"] if stops else "",
                "first_received_STOP_line": stops[0]["line"] if stops else "",
                "STOP_senders_first_seen_order_inferred": ">".join(map(str, senders_ordered)),
                "distinct_STOP_senders": len(set(e["sender"] for e in stops)),
                "distinct_STOP_sender_ids": ";".join(map(str, sorted({e["sender"] for e in stops}))),
                "STOP_received_event_count": len(stops),
                "STOP_send_identity_untagged_count": len(sent),
                "STOP_send_lines": line_list(sent),
                "STOP_receive_lines": line_list(stops),
                "F_plus_1_join_threshold": threshold,
                "F_plus_1_reached_by_distinct_STOP_senders": len({e["sender"] for e in stops}) >= threshold,
                "status_pairs_counts": ";".join(
                    f"{last}->{next_}:{count}" for (last, next_), count in sorted(
                        Counter((e["last_regency"], e["next_regency"]) for e in status).items())),
                "status_evidence_lines": line_list(status),
                "installation_evidence_lines": line_list(installed_status.get(regency, [])),
                "previous_installed_leader_candidate": (regency - 1) % N if regency else "",
                "previous_leader_propose_count_after_current_regency_begins": (
                    proposal_senders.get((regency - 1) % N, 0) if regency else 0),
                "propose_evidence_first_last_lines": (
                    f"{proposals[0]['line']}..{proposals[-1]['line']}" if proposals else ""),
                "inference": "STOP sender inferred from explicit 'from replica N'; starter inferred from first received STOP in merged line order; leader candidate uses user-specified regency mod N rule",
            })
    csv_write(out / "q6_regencies.csv", rows)
    fig, ax = plt.subplots(figsize=(13, 6))
    labels = []
    attempted_values = []
    installed_values = []
    for name, data in parsed.items():
        regs = sorted({e["regency"] for kind in ("send_stop", "receive_stop")
                       for e in selected(data, kind)})
        installed = sorted({e["last_regency"] for e in selected(data, "status")
                            if e["last_regency"] == e["next_regency"] and e["last_regency"] > 0})
        labels.append(name)
        attempted_values.append(len(regs))
        installed_values.append(len(installed))
    x = np.arange(len(parsed))
    width = .35
    ax.bar(x - width / 2, attempted_values, width, label="distinct attempted regencies", color="#EE6677")
    ax.bar(x + width / 2, installed_values, width, label="distinct nonzero installed regencies observed", color="#228833")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Regencies")
    ax.set_title("Q6 — Attempted versus installed leader-change regencies")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(out / "q6_regencies.png", dpi=170)
    plt.close(fig)


def write_anomalies(parsed, out):
    rows = []
    for data in parsed.values():
        rows.extend(data["anomalies"])
    csv_write(out / "unusual_messages.csv", rows, ["run", "line", "kind", "text"])
    splice_rows = [row for data in parsed.values() for row in data["spliced"]]
    csv_write(out / "spliced_client_lines.csv", splice_rows,
              ["run", "line", "reason", "client_output_count", "protocol_marker_present", "raw_line"])


def make_report(parsed, out):
    lines = [
        "# BFT-SMaRt log comparison",
        "",
        "Line order is used throughout; the logs contain no wall-clock timestamps. Any numeric timestamp below is the protocol epoch timestamp. In `main.log`, `[replicaN]` is directly observed. In the other logs, attribution is limited to explicit `I am:N` or `from replica N` fields; untagged local events are not assigned to a replica.",
        "",
        "## Per-log overview",
        "",
        "| Log | Lines | Propose CIDs | WRITE sends (tagged) | ACCEPT sends (tagged) | Decisions | Timeouts | Regency events | Spliced client lines |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, data in parsed.items():
        cids = sorted({e["cid"] for e in selected(data, "propose")})
        reg_events = sum(e["kind"] in {"send_stop", "receive_stop", "send_stopdata",
                                       "receive_stopdata", "send_sync", "receive_sync", "status"}
                         for e in data["events"])
        lines.append(
            f"| {name} | {data['line_count']} | {len(cids)} ({min(cids) if cids else '-'}–{max(cids) if cids else '-'}) "
            f"| {len(selected(data, 'write_send'))} | {len(selected(data, 'accept_send'))} "
            f"| {len(selected(data, 'decision'))} | {len(selected(data, 'timeout'))} "
            f"| {reg_events} | {len(data['spliced'])} |"
        )
    lines.extend([
        "",
        "## Consensus-chain coverage",
        "",
        "A quorum marker with count >= 3 is treated as observed quorum evidence (N=4, F=1). Application/reply values are mapped to CID+1 as a workload inference. The order checks below use the first matching source line in each merged log, not a global causal clock.",
        "",
        "| Log | PROPOSE CIDs | WRITE quorum CIDs | ACCEPT send CIDs | ACCEPT quorum CIDs | decision CIDs | application values mapped | reply values mapped | ordered through decision | full line-order chain |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for name, data in parsed.items():
        stages = {
            "propose": {e["cid"] for e in selected(data, "propose")},
            "write": {e["cid"] for e in selected(data, "write_quorum") if e["count"] >= QUORUM},
            "accept_send": {e["cid"] for e in selected(data, "accept_send")},
            "accept": {e["cid"] for e in selected(data, "accept_quorum") if e["count"] >= QUORUM},
            "decision": {e["cid"] for e in selected(data, "decision")},
            "application": {e["value"] - 1 for e in selected(data, "application") if e["value"] > 0},
            "reply": {
                int(e["value"]) - 1
                for e in selected(data, "reply")
                if str(e["value"]).lstrip("-").isdigit() and int(e["value"]) > 0
            },
        }
        through_decision = 0
        full_chain = 0
        for cid in stages["propose"]:
            events_by_stage = [
                for_cid(data, "propose", cid),
                [e for e in for_cid(data, "write_quorum", cid) if e["count"] >= QUORUM],
                for_cid(data, "accept_send", cid),
                [e for e in for_cid(data, "accept_quorum", cid) if e["count"] >= QUORUM],
                for_cid(data, "decision", cid),
                [e for e in selected(data, "application") if e["value"] == cid + 1],
                [
                    e for e in selected(data, "reply")
                    if str(e["value"]).lstrip("-").isdigit() and int(e["value"]) == cid + 1
                ],
            ]
            first_lines = [
                min((e["line"] for e in events), default=None)
                for events in events_by_stage
            ]
            if all(line is not None for line in first_lines[:5]) and first_lines[:5] == sorted(first_lines[:5]):
                through_decision += 1
            if all(line is not None for line in first_lines) and first_lines == sorted(first_lines):
                full_chain += 1
        lines.append(
            f"| {name} | {len(stages['propose'])} | {len(stages['write'])} | {len(stages['accept_send'])} "
            f"| {len(stages['accept'])} "
            f"| {len(stages['decision'])} | {len(stages['application'])} | {len(stages['reply'])} "
            f"| {through_decision} | {full_chain} |"
        )

    lines.extend([
        "",
        "## View and WRITE-vote order",
        "",
        "The view tuple is inferred as regency:PROPOSE leader:protocol epoch timestamp. WRITE receive order below is the sequence of distinct `from replica N` senders per CID in merged line order. It is not a wall-clock or causal ordering; ACCEPT receive-sender records are not present.",
        "",
    ])
    for name, data in parsed.items():
        patterns = Counter()
        first_votes = Counter()
        last_votes = Counter()
        for cid in sorted({e["cid"] for e in selected(data, "propose")}):
            props = sorted(for_cid(data, "propose", cid), key=lambda e: e["line"])
            received_proposals = sorted(
                for_cid(data, "propose_received", cid), key=lambda e: e["line"]
            )
            if props:
                regency = regency_at_line(data, props[0]["line"])
                leader = received_proposals[0]["leader"] if received_proposals else "?"
                patterns[f"{regency}:{leader}:{props[0]['timestamp']}"] += 1
            votes = sorted(for_cid(data, "write_receive", cid), key=lambda e: e["line"])
            distinct = []
            for event in votes:
                if event["sender"] not in distinct:
                    distinct.append(event["sender"])
            if distinct:
                first_votes[distinct[0]] += 1
                last_votes[distinct[-1]] += 1
        lines.append(
            f"- **{name}:** view patterns {patterns.most_common(5)}; "
            f"first WRITE-receive sender counts {dict(sorted(first_votes.items()))}; "
            f"last sender counts {dict(sorted(last_votes.items()))}."
        )

    lines.extend(["", "## Regency results", ""])
    for name, data in parsed.items():
        attempted = sorted({e["regency"] for kind in ("send_stop", "receive_stop")
                            for e in selected(data, kind)})
        installed = sorted({e["last_regency"] for e in selected(data, "status")
                            if e["last_regency"] == e["next_regency"] and e["last_regency"] > 0})
        if not attempted:
            lines.append(f"- **{name}: no regency-change events.** Regency 0 is the baseline; its view ID 0 is the membership view. View lines: " +
                         ", ".join(str(e["line"]) for e in selected(data, "view")) + ".")
            continue
        lines.append(f"- **{name}:** attempted regencies {attempted}; installed nonzero regencies {installed}. ")
        for regency in attempted:
            stops = sorted((e for e in selected(data, "receive_stop") if e["regency"] == regency),
                           key=lambda e: e["line"])
            senders = sorted({e["sender"] for e in stops})
            stop_order = []
            for event in stops:
                if event["sender"] not in stop_order:
                    stop_order.append(event["sender"])
            status = [e for e in selected(data, "status")
                      if e["last_regency"] == regency or e["next_regency"] == regency]
            line_pair = Counter((e["last_regency"], e["next_regency"]) for e in status)
            pair_text = ", ".join(f"{a}->{b} x{count}" for (a, b), count in sorted(line_pair.items()))
            send_stop = sorted(
                (e for e in selected(data, "send_stop") if e["regency"] == regency),
                key=lambda e: e["line"],
            )
            receive_samples = [e["line"] for e in stops[:3]]
            if len(stops) > 3:
                receive_samples.extend(e["line"] for e in stops[-2:])
            status_samples = [e["line"] for e in status[:3]]
            if len(status) > 3:
                status_samples.extend(e["line"] for e in status[-2:])
            receive_samples = list(dict.fromkeys(receive_samples))
            status_samples = list(dict.fromkeys(status_samples))
            installed_here = [
                e for e in selected(data, "status")
                if e["last_regency"] == e["next_regency"] == regency
            ]
            installation_lines = line_list(installed_here[:4])
            lines.append(
                f"  - regency {regency}: candidate leader {regency % N} (rule-based inference); "
                f"distinct STOP senders {senders} ({len(senders)}; F+1={F+1} "
                f"{'reached' if len(senders) >= F+1 else 'not reached'}); "
                f"first received sender {stops[0]['sender'] if stops else 'none'} "
                f"(starter inferred); order of first observed senders "
                f"{'>'.join(map(str, stop_order)) or 'none'}; "
                f"status pairs {pair_text or 'none'}; "
                f"untagged local STOP-send lines {line_list(send_stop) or 'none'}; "
                f"STOP-receive samples {receive_samples or 'none'}; "
                f"status samples {status_samples or 'none'}; "
                f"installation-status lines (if observed) {installation_lines or 'none'}."
            )
        if 2 in attempted and 2 not in installed:
            same = [e for e in selected(data, "status") if e["last_regency"] == 1 and e["next_regency"] == 2]
            stop2 = sorted(
                (e for e in selected(data, "receive_stop") if e["regency"] == 2),
                key=lambda e: e["line"],
            )
            later_decisions = [
                e for e in selected(data, "decision")
                if e["cid"] > 0 and stop2 and e["line"] > stop2[0]["line"]
            ]
            later_decision_cids = sorted({e["cid"] for e in later_decisions})
            lines.append(
                f"  - **Stall evidence:** regency 2 has {len(stop2)} received STOP records from "
                f"{sorted({e['sender'] for e in stop2})}; first/last STOP lines "
                f"{(stop2[0]['line'], stop2[-1]['line']) if stop2 else 'none'}; "
                f"{len(same)} status records say `Last regency: 1, next regency: 2` "
                f"(sample lines {line_list(same[:4])}); no `Last regency: 2, next regency: 2` "
                f"installation record occurs. Distinct later CIDs >0 with decision markers after "
                f"the first regency-2 STOP: {len(later_decision_cids)} "
                f"({min(later_decision_cids) if later_decision_cids else '-'}–"
                f"{max(later_decision_cids) if later_decision_cids else '-'}), "
                f"{len(later_decisions)} decision markers. "
                "**Hypothesis:** the regency-2 attempt stalled without installing a replacement; "
                "observed decisions for later CIDs continue under the previously installed view."
            )
    lines.extend([
        "",
        "## Interpretation and caveats",
        "",
        "- `WRITE` and `ACCEPT` send order means the order of identity-tagged send lines for a CID in the merged file. For a retried CID, it may combine attempts; recovery `Sending WRITE message for CID ...` has no sender identity and is kept separate.",
        "- `WRITE received from:N` gives vote sender identity. Its sequence is merged-file line order, not a proven global causal/clock order. No `ACCEPT received from:N` records were found; ACCEPT receive order is therefore unavailable. Quorum counts establish only observed count thresholds.",
        "- Recovery timeout lines do not carry a CID; the run-summary row leaves them unassigned, while nearby retry WRITEs explicitly identify CID 0 at epoch timestamp 1. Application counter/reply values are mapped to CID+1 only as a workload-based inference.",
        "- `[replicaN]` prefixes are trusted only in `main.log`. In the other logs, a sender is attributed only from `I am:N` or `from replica N`; status/quorum/decision records are intentionally left unattributed.",
        "- `spliced_client_lines.csv` preserves raw client-output lines with multiple records, client/protocol mixing, or reply values concatenated with following text. Numeric reply prefixes can be counted, but malformed line content and ordering should not be over-interpreted.",
        "- `regency % N` is reported as the requested leader candidate rule, not treated as proof; observed `PROPOSE received from:N` leaders are shown separately in the CSV.",
        "",
        "## Deliverables",
        "",
        "| File | Contents |",
        "|---|---|",
        "| `analyze_logs.py` | Reproducible parser and report/CSV/plot generator. |",
        "| `q1_progress.csv` / `q1_progress.png` | Per-log progress counts/line references and comparison plot. |",
        "| `q2_sender_order.csv` / `q2_sender_order.png` | Per-CID first/last WRITE and ACCEPT sender, count, evidence lines. |",
        "| `q3_views_votes.csv` / `q3_views_votes.png` | Per-CID inferred regency, observed leader, epoch(s), send/receive order. |",
        "| `q4_consensus_chain.csv` / `q4_consensus_chain.png` | Per-CID/epoch phase counts, quorum counts and evidence lines. |",
        "| `q5_timeout_recovery.csv` / `q5_timeout_recovery.png` | One run-summary row per log for untagged timeout/leader-change markers, plus per-CID/epoch retry and quorum rows. |",
        "| `q6_regencies.csv` / `q6_regencies.png` | Attempted/installed regencies, STOP participation, status pairs and leadership evidence. |",
        "| `unusual_messages.csv` | Warning/error and selected unusual recovery/protocol lines. |",
        "| `spliced_client_lines.csv` | Source line numbers and raw text for detected spliced client output. |",
        "",
        "## What could still be wrong",
        "",
        "Merged line order cannot establish wall-clock timing or causality between replicas. The inferred local-regency window follows untagged `Last regency / next regency` status lines, which may come from different replicas. A missing installation marker means no installation was observed in the available log, not necessarily that the process never installed it. Workload counter value-to-CID mapping and timeout-to-CID mapping are inferences. The log snapshots may be truncated or contain output interleaving that the parser cannot unambiguously separate.",
    ])
    (out / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--main", type=Path, default=INPUTS["main.log"])
    parser.add_argument("--main-2", type=Path, default=INPUTS["main_2.log"])
    parser.add_argument("--main-3", type=Path, default=INPUTS["main_3.log"])
    parser.add_argument("--main-4", type=Path, default=INPUTS["main_4.log"])
    args = parser.parse_args()
    paths = {
        "main.log": args.main,
        "main_2.log": args.main_2,
        "main_3.log": args.main_3,
        "main_4.log": args.main_4,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    parsed = {name: parse_log(name, path) for name, path in paths.items()}
    write_q1(parsed, args.output_dir)
    write_q2(parsed, args.output_dir)
    write_q3(parsed, args.output_dir)
    write_q4(parsed, args.output_dir)
    write_q5(parsed, args.output_dir)
    write_q6(parsed, args.output_dir)
    write_anomalies(parsed, args.output_dir)
    make_report(parsed, args.output_dir)
    print(f"Analyzed {len(parsed)} logs; wrote report, 6 question CSVs/plots, and anomaly CSVs to {args.output_dir}")
    for name, data in parsed.items():
        print(
            f"{name}: lines={data['line_count']}, propose_cids="
            f"{len({e['cid'] for e in selected(data, 'propose')})}, "
            f"tagged_write_sends={len(selected(data, 'write_send'))}, "
            f"tagged_accept_sends={len(selected(data, 'accept_send'))}, "
            f"decisions={len(selected(data, 'decision'))}, "
            f"timeouts={len(selected(data, 'timeout'))}, "
            f"spliced_lines={len(data['spliced'])}"
        )


if __name__ == "__main__":
    main()
