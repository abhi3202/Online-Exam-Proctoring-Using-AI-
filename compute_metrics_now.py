import sys
sys.path.insert(0, '.')
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, accuracy_score
from database.database import init_db, get_all_labels

def compute_metrics(rows):
    if not rows:
        return {"error": "No labels"}
    
    df = pd.DataFrame(rows)
    df['human_true'] = df['human_true'].astype(int)
    
    # Overall
    y_true = df['human_true'].values
    y_pred = np.ones(len(y_true))
    cm = confusion_matrix(y_true, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='binary', zero_division=0)
    acc = accuracy_score(y_true, y_pred)
    
    print("OVERALL METRICS:")
    print(f"Accuracy: {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall: {rec:.4f}")
    print(f"F1: {f1:.4f}")
    print("Confusion Matrix:")
    print(cm)
    
    # Per type
    print("\\nPER VIOLATION TYPE:")
    for vt in df['violation_type'].unique():
        type_df = df[df['violation_type'] == vt]
        if len(type_df) > 0:
            y_true_t = type_df['human_true'].values
            y_pred_t = np.ones(len(y_true_t))
            cm_t = confusion_matrix(y_true_t, y_pred_t)
            prec_t, rec_t, f1_t, _ = precision_recall_fscore_support(y_true_t, y_pred_t, average='binary', zero_division=0)
            acc_t = accuracy_score(y_true_t, y_pred_t)
            print(f"{vt}: Acc={acc_t:.4f}, Prec={prec_t:.4f}, Rec={rec_t:.4f}, F1={f1_t:.4f}, CM={cm_t}")

init_db()
labels = get_all_labels()
print(f"Loaded {len(labels)} labels")
compute_metrics(labels)
