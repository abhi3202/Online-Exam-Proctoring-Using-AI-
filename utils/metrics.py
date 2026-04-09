import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, accuracy_score, classification_report
import json

def compute_metrics(rows):
    """
    Compute metrics from raw DB rows (dicts).
    """
    if not rows:
        return {"error": "No labels available. Run proctoring sessions and label violations first."}
    
    df = pd.DataFrame(rows)
    if 'human_true' not in df.columns:
        return {"error": "Labels table structure mismatch - expected 'human_true' column"}
    
    df['human_true'] = df['human_true'].astype(int)
    
    metrics = {}
    overall = {}
    
    # Overall
    y_true_all = df['human_true'].values
    y_pred_all = np.ones(len(y_true_all))
    overall_cm = confusion_matrix(y_true_all, y_pred_all)
    overall_prec, overall_rec, overall_f1, _ = precision_recall_fscore_support(
        y_true_all, y_pred_all, average='binary', zero_division=0
    )
    overall_acc = accuracy_score(y_true_all, y_pred_all)
    
    overall = {
        'total_detections': len(df),
        'true_positives': int(np.sum(y_true_all)),
        'false_positives': int(np.sum(1 - y_true_all)),
        'precision': round(overall_prec, 4),
        'recall': round(overall_rec, 4),
        'f1': round(overall_f1, 4),
        'accuracy': round(overall_acc, 4),
        'confusion_matrix': overall_cm.tolist()
    }
    
    # Per type
    for vt in sorted(df['violation_type'].unique()):
        type_df = df[df['violation_type'] == vt]
        if len(type_df) == 0:
            continue
            
        y_true = type_df['human_true'].values
        y_pred = np.ones(len(y_true))
        
        cm = confusion_matrix(y_true, y_pred)
        p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='binary', zero_division=0)
        acc = accuracy_score(y_true, y_pred)
        
        metrics[vt] = {
            'total_detections': len(type_df),
            'true_positives': int(np.sum(y_true)),
            'false_positives': int(np.sum(1 - y_true)),
            'precision': round(p, 4),
            'recall': round(r, 4),
            'f1': round(f1, 4),
            'accuracy': round(acc, 4),
            'confusion_matrix': cm.tolist()
        }
    
    return {
        'overall': overall,
        'per_type': metrics,
        'total_labels': len(df)
    }

def print_metrics(metrics):
    """Pretty print metrics."""
    print("\n" + "="*60)
    print("PROCTORING SYSTEM EVALUATION METRICS")
    print("="*60)
    
    ov = metrics['overall']
    print(f"\nOVERALL (All Violation Types):")
    print(f"  Total Detections: {ov['total_detections']}")
    print(f"  True Positives: {ov['true_positives']}")
    print(f"  False Positives: {ov['false_positives']}")
    print(f"  Accuracy: {ov['accuracy']:.4f}")
    print(f"  Precision: {ov['precision']:.4f}")
    print(f"  Recall: {ov['recall']:.4f}")
    print(f"  F1-Score: {ov['f1']:.4f}")
    print(f"  Confusion Matrix:\n{np.array(ov['confusion_matrix'])}")
    
    print(f"\nPER VIOLATION TYPE:")
    for vt, m in metrics['per_type'].items():
        print(f"\n  {vt}:")
        print(f"    Detections: {m['total_detections']}, TP: {m['true_positives']}, FP: {m['false_positives']}")
        print(f"    Acc: {m['accuracy']:.4f}, Prec: {m['precision']:.4f}, Rec: {m['recall']:.4f}, F1: {m['f1']:.4f}")

def save_metrics_report(metrics, filename='metrics_report.json'):
    """Save metrics as JSON."""
    with open(filename, 'w') as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"\nMetrics saved to {filename}")
