from pathlib import Path
from collections import Counter

# Input log file
INPUT_FILE = Path("dataset/run-001-normal/main.log")

# Output directory
BASELINE_DIR = Path("dataset/run-001-normal/baseline")
BASELINE_DIR.mkdir(parents=True, exist_ok=True)

# Output files
FILTERED_FILE = BASELINE_DIR / "keyword_filtered.log"
SUMMARY_FILE = BASELINE_DIR / "keyword_summary.txt"

# Event patterns for keyword-based baseline
EVENT_PATTERNS = {
    "received_proposal": "Received proposal",
    "collect_vote": "CollectVote",
    "try_commit": "TryCommit",
    "highqc_updated": "Successfully updated HighQC",
    "highqc_not_updated": "HighQC not updated",
    "pre_commit": "CommitRule - PRE_COMMIT",
    "commit": "CommitRule - COMMIT",
    "decide": "CommitRule - DECIDE",
    "exec": "EXEC:",
    "local_timeout": "OnLocalTimeout",
    "remote_timeout": "OnRemoteTimeout",
    "not_enough_timeouts": "not enough timeouts",
    "block_too_old": "block too old",
    "failed": "failed",
    "panic": "panic",
    "error": "error",
}

EVENT_CATEGORIES = {
    "received_proposal": "protocol_progress",
    "collect_vote": "protocol_progress",
    "try_commit": "protocol_progress",
    "highqc_updated": "protocol_progress",
    "highqc_not_updated": "protocol_progress",

    "pre_commit": "commit_pipeline",
    "commit": "commit_pipeline",
    "decide": "commit_pipeline",
    "exec": "commit_pipeline",

    "local_timeout": "timeout_related",
    "remote_timeout": "timeout_related",
    "not_enough_timeouts": "timeout_related",

    "block_too_old": "suspicious_or_noise",
    "failed": "suspicious",
    "panic": "suspicious",
    "error": "suspicious",
}


def get_events(line):
    events = []
    lower_line = line.lower()

    for event_name, pattern in EVENT_PATTERNS.items():
        if pattern.lower() in lower_line:
            events.append(event_name)

    return events


def main():
    if not INPUT_FILE.exists():
        print(f"Input file not found: {INPUT_FILE}")
        return

    # These files are overwritten every time the script runs
    if FILTERED_FILE.exists():
        FILTERED_FILE.unlink()

    if SUMMARY_FILE.exists():
        SUMMARY_FILE.unlink()

    total_lines = 0
    matched_lines = 0
    event_counts = Counter()
    category_counts = Counter()

    with INPUT_FILE.open("r", encoding="utf-8", errors="ignore") as infile, \
         FILTERED_FILE.open("w", encoding="utf-8") as outfile:

        for line_number, line in enumerate(infile, start=1):
            total_lines += 1
            events = get_events(line)

            if events:
                matched_lines += 1

                categories = []
                for event in events:
                    event_counts[event] += 1
                    category = EVENT_CATEGORIES.get(event, "unknown")
                    category_counts[category] += 1
                    categories.append(category)

                outfile.write(
                    f"[line={line_number}] "
                    f"[events={','.join(events)}] "
                    f"[categories={','.join(sorted(set(categories)))}] "
                    f"{line}"
                )

    with SUMMARY_FILE.open("w", encoding="utf-8") as summary:
        summary.write("Keyword Filtering Baseline\n")
        summary.write("==========================\n\n")
        summary.write(f"Input file: {INPUT_FILE}\n")
        summary.write(f"Total log lines: {total_lines}\n")
        summary.write(f"Matched lines: {matched_lines}\n")
        summary.write(f"Filtered output: {FILTERED_FILE}\n\n")

        summary.write("Event counts:\n")
        for event, count in event_counts.most_common():
            summary.write(f"{event}: {count}\n")

        summary.write("\nCategory counts:\n")
        for category, count in category_counts.most_common():
            summary.write(f"{category}: {count}\n")

    print("Done.")
    print(f"Total lines: {total_lines}")
    print(f"Matched lines: {matched_lines}")
    print(f"Filtered file: {FILTERED_FILE}")
    print(f"Summary file: {SUMMARY_FILE}")


if __name__ == "__main__":
    main()