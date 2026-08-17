import json
from pathlib import Path
from collections import defaultdict, Counter

INPUT_FILE = Path("dataset/run-001-normal/baseline/regex_parsed_events.jsonl")

BASELINE_DIR = Path("dataset/run-001-normal/baseline")
OUTPUT_FILE = BASELINE_DIR / "rule_based_view_classification.jsonl"
SUMMARY_FILE = BASELINE_DIR / "rule_based_view_classification_summary.txt"


def classify_view(event_types):
    """
    Classify one HotStuff view using deterministic rules.
    This is a baseline method, not AI.
    """

    has_timeout = any(event in event_types for event in [
        "local_timeout",
        "remote_timeout",
        "not_enough_timeouts"
    ])

    has_failed = any(event in event_types for event in [
        "failed",
        "panic",
        "error"
    ])

    has_suspicious_noise = "block_too_old" in event_types

    has_commit = "commit" in event_types
    has_decide = "decide" in event_types
    has_exec = "exec" in event_types
    has_qc = "highqc_updated" in event_types

    if has_failed:
        return "suspicious_failed"

    if has_timeout and has_decide and has_exec:
        return "normal_with_timeout_noise"

    if has_timeout and not (has_decide and has_exec):
        return "suspicious_or_incomplete"

    if has_decide and has_exec:
        return "normal_successful"

    if has_qc and has_commit:
        return "partially_successful"

    if has_suspicious_noise:
        return "suspicious_or_noise"

    return "unknown"


def main():
    if not INPUT_FILE.exists():
        print(f"Input file not found: {INPUT_FILE}")
        print("Run baseline_regex_parser.py first.")
        return

    if OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()

    if SUMMARY_FILE.exists():
        SUMMARY_FILE.unlink()

    views = defaultdict(list)

    with INPUT_FILE.open("r", encoding="utf-8") as infile:
        for line in infile:
            event = json.loads(line)

            view = event.get("view")
            if view is None:
                continue

            views[view].append(event)

    classification_counts = Counter()
    total_views = 0

    with OUTPUT_FILE.open("w", encoding="utf-8") as outfile:
        for view, events in sorted(views.items()):
            event_types = [event["event_type"] for event in events]
            event_type_counts = Counter(event_types)

            replicas = sorted(set(event["replica"] for event in events))

            classification = classify_view(set(event_types))
            classification_counts[classification] += 1
            total_views += 1

            result = {
                "view": view,
                "classification": classification,
                "num_events": len(events),
                "replicas": replicas,
                "event_type_counts": dict(event_type_counts)
            }

            outfile.write(json.dumps(result) + "\n")

    with SUMMARY_FILE.open("w", encoding="utf-8") as summary:
        summary.write("Rule-based View Classification Baseline\n")
        summary.write("=======================================\n\n")
        summary.write(f"Input file: {INPUT_FILE}\n")
        summary.write(f"Total views classified: {total_views}\n")
        summary.write(f"Output file: {OUTPUT_FILE}\n\n")

        summary.write("Classification counts:\n")
        for classification, count in classification_counts.most_common():
            summary.write(f"{classification}: {count}\n")

    print("Done.")
    print(f"Total views classified: {total_views}")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Summary file: {SUMMARY_FILE}")


if __name__ == "__main__":
    main()