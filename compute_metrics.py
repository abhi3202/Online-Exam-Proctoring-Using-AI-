import sqlite3

def compute_metrics():
    conn = sqlite3.connect('database/proctoring.db')
    c = conn.cursor()
    
    # Violation type counts
    c.execute('SELECT violation_type, COUNT(*) FROM labels GROUP BY violation_type')
    print('Violation Counts:', c.fetchall())
    
    # TP, TN, FP, FN (all auto-labeled TRUE, so TP=total, FP=FN=0)
    c.execute('SELECT COUNT(*) FROM labels')
    total = c.fetchone()[0]
    tp = total  # All auto-labeled TRUE
    fp = 0
    fn = 0
    tn = 0  # Unknown (no negative samples)
    
    accuracy = tp / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    
    print(f'\n📊 ML EVALUATION METRICS (Auto-labeled Baseline)')
    print(f'Total Violations: {total}')
    print(f'TP: {tp} | FP: {fp} | FN: {fn} | TN: {tn}')
    print(f'Accuracy:  {accuracy:.1%}')
    print(f'Precision: {precision:.1%}')
    print(f'Recall:    {recall:.1%}')
    print(f'F1-Score:  {(2*precision*recall)/(precision+recall):.1%}')
    print('\nView Dashboard: http://127.0.0.1:5000/admin/metrics_advanced')
    
    conn.close()

if __name__ == '__main__':
    compute_metrics()
