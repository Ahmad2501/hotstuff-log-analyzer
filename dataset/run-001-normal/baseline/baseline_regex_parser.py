import re
import json
from pathlib import Path
from collections import Counter

INPUT_FILE = Path("dataset/run-001-normal/main.log")

BASELINE_DIR = Path("dataset/run-001-normal/baseline")
BASELINE_DIR.mkdir(parents=True, exist_ok=True)

EVENTS_FILE = BASELINE_DIR / "regex_parsed_events.jsonl"
SUMMARY_FILE = BASELINE_DIR / "regex_parser_summary.txt"

LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\S+)\s+"
    r"(?P<level>\S+)\s+"
    r"(?P<replica>hs\d+)\s+"
    r"(?P<component>\S+)\s+"
    r"(?P<message>.*)$"
)

BLOCK_PATTERN = re.compile(
    r"Block\{ hash: (?P<hash>\S+) "
    r"parent: (?P<parent>\S+), "
    r"proposer: (?P<proposer>\d+), "
    r"view: (?P<view>\d+)"
)

QC_VIEW_PATTERN = re.compile(
    r"QC\{ hash: \S+, view: (?P<qc_view>\d+)"
)

ADVANCED_VIEW_PATTERN = re.compile(
    r"Advanced to view (?P<view>\d+)"
)

CURRENT_NEW_VIEW_PATTERN = re.compile(
    r"current view: (?P<current_view>\d+), new view: (?P<new_view>\d+)"
)

TIMEOUT_VIEW_PATTERN = re.compile(
    r"(OnLocalTimeout|View): (?P<view>\d+)"
)


def detect_event_type(message):
    if "Received proposal" in message:
        return "received_proposal"
    if "CollectVote" in message:
        return "collect_vote"
    if "TryCommit" in message:
        return "try_commit"
    if "Successfully updated HighQC" in message:
        return "highqc_updated"
    if "HighQC not updated" in message:
        return "highqc_not_updated"
    if "CommitRule - PRE_COMMIT" in message:
        return "pre_commit"
    if "CommitRule - COMMIT" in message:
        return "commit"
    if "CommitRule - DECIDE" in message:
        return "decide"
    if "EXEC:" in message:
        return "exec"
    if "OnLocalTimeout" in message:
        return "local_timeout"
    if "OnRemoteTimeout" in message:
        return "remote_timeout"
    if "not enough timeouts" in message:
        return "not_enough_timeouts"
    if "block too old" in message:
        return "block_too_old"
    if "failed" in message.lower():
        return "failed"
    if "panic" in message.lower():
        return "panic"
    if "error" in message.lower():
        return "error"

    return None


def extract_view(message):
    block_match = BLOCK_PATTERN.search(message)
    if block_match:
        return int(block_match.group("view"))

    advanced_match = ADVANCED_VIEW_PATTERN.search(message)
    if advanced_match:
        return int(advanced_match.group("view"))

    current_new_match = CURRENT_NEW_VIEW_PATTERN.search(message)
    if current_new_match:
        return int(current_new_match.group("current_view"))

    timeout_match = TIMEOUT_VIEW_PATTERN.search(message)
    if timeout_match:
        return int(timeout_match.group("view"))

    return None


def parse_line(line_number, line):
    log_match = LOG_PATTERN.match(line)
    if not log_match:
        return None

    timestamp = log_match.group("timestamp")
    level = log_match.group("level")
    replica = log_match.group("replica")
    component = log_match.group("component")
    message = log_match.group("message")

    event_type = detect_event_type(message)
    if event_type is None:
        return None

    event = {
        "line_number": line_number,
        "timestamp": timestamp,
        "level": level,
        "replica": replica,
        "component": component,
        "event_type": event_type,
        "view": extract_view(message),
        "block_hash": None,
        "parent_hash": None,
        "proposer": None,
        "qc_view": None,
        "message": message.strip()
    }

    block_match = BLOCK_PATTERN.search(message)
    if block_match:
        event["block_hash"] = block_match.group("hash")
        event["parent_hash"] = block_match.group("parent")
        event["proposer"] = int(block_match.group("proposer"))
        event["view"] = int(block_match.group("view"))

    qc_match = QC_VIEW_PATTERN.search(message)
    if qc_match:
        event["qc_view"] = int(qc_match.group("qc_view"))

    return event


def main():
    if not INPUT_FILE.exists():
        print(f"Input file not found: {INPUT_FILE}")
        return

    if EVENTS_FILE.exists():
        EVENTS_FILE.unlink()

    if SUMMARY_FILE.exists():
        SUMMARY_FILE.unlink()

    total_lines = 0
    parsed_events = 0
    event_counts = Counter()
    replica_counts = Counter()
    view_counts = Counter()

    with INPUT_FILE.open("r", encoding="utf-8", errors="ignore") as infile, \
         EVENTS_FILE.open("w", encoding="utf-8") as outfile:

        for line_number, line in enumerate(infile, start=1):
            total_lines += 1
            event = parse_line(line_number, line)

            if event is not None:
                parsed_events += 1
                event_counts[event["event_type"]] += 1
                replica_counts[event["replica"]] += 1

                if event["view"] is not None:
                    view_counts[event["view"]] += 1

                outfile.write(json.dumps(event) + "\n")

    with SUMMARY_FILE.open("w", encoding="utf-8") as summary:
        summary.write("Regex Parser Baseline\n")
        summary.write("=====================\n\n")
        summary.write(f"Input file: {INPUT_FILE}\n")
        summary.write(f"Total log lines: {total_lines}\n")
        summary.write(f"Parsed events: {parsed_events}\n")
        summary.write(f"Output file: {EVENTS_FILE}\n\n")

        summary.write("Event counts:\n")
        for event_type, count in event_counts.most_common():
            summary.write(f"{event_type}: {count}\n")

        summary.write("\nReplica counts:\n")
        for replica, count in replica_counts.most_common():
            summary.write(f"{replica}: {count}\n")

        summary.write("\nTop 20 views by number of parsed events:\n")
        for view, count in view_counts.most_common(20):
            summary.write(f"view {view}: {count}\n")

    print("Done.")
    print(f"Total lines: {total_lines}")
    print(f"Parsed events: {parsed_events}")
    print(f"Events file: {EVENTS_FILE}")
    print(f"Summary file: {SUMMARY_FILE}")


if __name__ == "__main__":
    main()