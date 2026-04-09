#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from database.database import init_db, get_all_labels
from utils.metrics import compute_metrics, print_metrics, save_metrics_report

init_db()
labels = get_all_labels()
print(f"Found {len(labels)} labels")

if labels:
    metrics = compute_metrics(labels)
    print_metrics(metrics)
    save_metrics_report(metrics)
else:
    print("No labels found - run proctoring and label violations first")

