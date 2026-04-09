#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from database.database import get_all_labels, init_db
from utils.metrics import compute_metrics, print_metrics, save_metrics_report

def generate_metrics_report():
    init_db()  # Ensure DB initialized
    
    labels = get_all_labels()
    if not labels:
        print("No labels found. Label some detections first via /admin/label_sessions")
        print("Metrics require human-verified labels (human_true = 0/1).")
        print("\\nTo test: python app.py → admin login → label sessions → rerun")
        return
    
    print(f"Loaded {len(labels)} labels from database.")
    
    metrics = compute_metrics(labels)  # Pass raw rows now
    print_metrics(metrics)
    save_metrics_report(metrics, 'metrics_report.json')
    print("\\nSaved to metrics_report.json")

if __name__ == "__main__":
    generate_metrics_report()
