#!/usr/bin/env python3
import csv
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

base = 'dataset/log_analysis'
plots_dir = os.path.join(base, 'plots')
os.makedirs(plots_dir, exist_ok=True)

metrics = {
    'advanceView': 'advanceView.csv',
    'HighQC_updated': 'HighQC_updated.csv',
    'DECIDE': 'DECIDE.csv',
    'CommitRule': 'CommitRule.csv',
    'OnRemoteTimeout': 'OnRemoteTimeout.csv',
    'block_too_old': 'block_too_old.csv',
    'failed_verify_sync_info': 'failed_verify_sync_info.csv'
}

results = {}
for name, fname in metrics.items():
    path = os.path.join(base, fname)
    if not os.path.exists(path):
        print('Missing', path)
        continue
    views = []
    count1 = []
    count2 = []
    cum1 = []
    cum2 = []
    with open(path, 'r') as fh:
        r = csv.reader(fh)
        header = next(r)
        for row in r:
            if not row: continue
            if row[0].strip().lower() == 'unknown':
                unknown1 = int(row[1]) if row[1] else 0
                unknown2 = int(row[2]) if row[2] else 0
                break
            try:
                v = int(row[0])
            except:
                continue
            views.append(v)
            # columns: view, count_run-001, count_run-002, cum_run-001, cum_run-002, cum_diff
            c1 = int(row[1]) if row[1] else 0
            c2 = int(row[2]) if row[2] else 0
            cu1 = int(row[3]) if len(row)>3 and row[3] else 0
            cu2 = int(row[4]) if len(row)>4 and row[4] else 0
            count1.append(c1)
            count2.append(c2)
            cum1.append(cu1)
            cum2.append(cu2)
    results[name] = dict(views=views, count1=count1, count2=count2, cum1=cum1, cum2=cum2, unknown1=locals().get('unknown1',0), unknown2=locals().get('unknown2',0))

# Plotting: per-metric two-panel: (top) counts per view, (bottom) cumulative
for name, data in results.items():
    if not data['views']:
        print('No numeric views for', name)
        continue
    fig, axs = plt.subplots(2,1, figsize=(10,7), sharex=True)
    axs[0].plot(data['views'], data['count1'], label='run-001', color='C0', alpha=0.7)
    axs[0].plot(data['views'], data['count2'], label='run-002', color='C1', alpha=0.7)
    axs[0].set_ylabel('counts per view')
    axs[0].legend()
    axs[0].grid(True, linestyle=':', alpha=0.5)

    axs[1].plot(data['views'], data['cum1'], label='cum run-001', color='C0')
    axs[1].plot(data['views'], data['cum2'], label='cum run-002', color='C1')
    axs[1].set_ylabel('cumulative counts')
    axs[1].set_xlabel('view')
    axs[1].legend()
    axs[1].grid(True, linestyle=':', alpha=0.5)

    fig.suptitle(name)
    out = os.path.join(plots_dir, f'{name}.png')
    fig.tight_layout(rect=[0,0,1,0.96])
    fig.savefig(out)
    plt.close(fig)
    print('Wrote', out)

# Identify which metric has largest final cumulative difference
best = None
best_diff = 0
for name, data in results.items():
    if not data['cum1'] or not data['cum2']:
        continue
    diff = data['cum1'][-1] - data['cum2'][-1]
    if abs(diff) > abs(best_diff):
        best_diff = diff
        best = name

if best:
    print('Metric with largest absolute cumulative difference:', best, best_diff)
    with open(os.path.join(plots_dir, 'best_metric.txt'), 'w') as fh:
        fh.write(f"{best},{best_diff}\n")
else:
    print('No best metric found')
