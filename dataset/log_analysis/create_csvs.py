#!/usr/bin/env python3
import re, pathlib, collections, json

patterns = {
    'block_too_old': r'block too old',
    'failed_verify_sync_info': r'Failed to verify sync info',
    'OnLocalTimeout': r'OnLocalTimeout',
    'OnRemoteTimeout': r'OnRemoteTimeout',
    'not_enough_timeouts': r'not enough timeouts',
    'VoteRule_liveness_failed': r'VoteRule: liveness condition failed',
    'HighQC_updated': r'Successfully updated HighQC',
    'HighQC_not_updated': r'HighQC not updated',
    'advanceView': r'advanceView',
    'CommitRule': r'CommitRule',
    'DECIDE': r'DECIDE',
    'TryCommit': r'TryCommit',
    'OnNewView': r'OnNewView',
}

files = {
    'run-001': 'dataset/run-001-normal/main.log',
    'run-002': 'dataset/run-002-normal/main_2.log',
}

view_re = re.compile(r'Advanced to view (\d+)|view: (\d+)')
out_dir = pathlib.Path('dataset/log_analysis')
out_dir.mkdir(parents=True, exist_ok=True)

# Parse files into lines
logs = {k: pathlib.Path(p).read_text(errors='replace').splitlines() for k,p in files.items()}

# counts[pattern][run][view] = int
counts = {p: {r: collections.Counter() for r in files} for p in patterns}
unknown_counts = {p: {r:0 for r in files} for p in patterns}

for pname, ppat in patterns.items():
    prog = re.compile(ppat)
    for run, lines in logs.items():
        for i, line in enumerate(lines):
            if prog.search(line):
                found = None
                for j in range(max(0, i-3), min(len(lines), i+4)):
                    m = view_re.search(lines[j])
                    if m:
                        v = m.group(1) or m.group(2)
                        found = int(v)
                        break
                if found is None:
                    counts[pname][run][-1] += 1
                else:
                    counts[pname][run][found] += 1

# Helper to write CSV per pattern
import csv
summary = {}
for pname in patterns:
    # union of views (excluding -1 for numeric sequence)
    views = set()
    for run in files:
        views.update([v for v in counts[pname][run].keys() if v >= 0])
    views = sorted(views)
    # prepare rows for numeric views
    rows = []
    cum = {r:0 for r in files}
    divergence_view = None
    for v in views:
        row = {'view': v}
        for run in files:
            c = counts[pname][run].get(v, 0)
            row[f'count_{run}'] = c
            cum[run] += c
            row[f'cum_{run}'] = cum[run]
        row['cum_diff'] = cum['run-001'] - cum['run-002']
        rows.append(row)
        # divergence condition: run-001 >= 1.2 * run-002 and absolute diff >= 50
        if divergence_view is None and (cum['run-002']>0):
            if cum['run-001'] >= 1.2 * cum['run-002'] and (cum['run-001'] - cum['run-002']) >= 50:
                divergence_view = v
    # append unknown row
    unknown_r = {run: counts[pname][run].get(-1, 0) for run in files}
    # write CSV
    csv_path = out_dir / f'{pname}.csv'
    with csv_path.open('w', newline='') as fh:
        w = csv.writer(fh)
        hdr = ['view'] + [f'count_{r}' for r in files] + [f'cum_{r}' for r in files] + ['cum_diff']
        w.writerow(hdr)
        for r in rows:
            w.writerow([r['view']] + [r[f'count_{run}'] for run in files] + [r[f'cum_{run}'] for run in files] + [r['cum_diff']])
        # write unknown summary as last line
        w.writerow(['unknown'] + [unknown_r[run] for run in files] + ['']*(len(files)+1))
    summary[pname] = {
        'csv': str(csv_path),
        'total_run-001': sum(counts[pname]['run-001'].values()),
        'total_run-002': sum(counts[pname]['run-002'].values()),
        'unknown_run-001': counts[pname]['run-001'].get(-1,0),
        'unknown_run-002': counts[pname]['run-002'].get(-1,0),
        'divergence_view': divergence_view,
    }

# write summary json
with (out_dir / 'divergence_summary.json').open('w') as fh:
    json.dump(summary, fh, indent=2)

print('Wrote', len(summary), 'CSV files to', out_dir)
print('Summary example:', json.dumps({k:summary[k] for k in list(summary)[:3]}, indent=2))
print('Files:')
for k in summary:
    print(' -', summary[k]['csv'])

# Also write a combined CSV per view (numeric views union across patterns)
all_views = set()
for pname in patterns:
    for run in files:
        all_views.update([v for v in counts[pname][run].keys() if v >= 0])
all_views = sorted(all_views)
combined_csv = out_dir / 'combined_per_view.csv'
with combined_csv.open('w', newline='') as fh:
    w = csv.writer(fh)
    hdr = ['view']
    for pname in patterns:
        hdr += [f'{pname}_count_run-001', f'{pname}_count_run-002']
    w.writerow(hdr)
    for v in all_views:
        row = [v]
        for pname in patterns:
            row.append(counts[pname]['run-001'].get(v,0))
            row.append(counts[pname]['run-002'].get(v,0))
        w.writerow(row)
print('Wrote combined per-view file:', combined_csv)

# write top divergence picks
with (out_dir / 'readme_summary.txt').open('w') as fh:
    fh.write('Divergence summary per pattern:\n')
    for k,v in summary.items():
        fh.write(f"{k}: csv={v['csv']}, total1={v['total_run-001']}, total2={v['total_run-002']}, unknown1={v['unknown_run-001']}, unknown2={v['unknown_run-002']}, divergence_view={v['divergence_view']}\n")

print('Done')
