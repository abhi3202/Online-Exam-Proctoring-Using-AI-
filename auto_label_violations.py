#!/usr/bin/env python3
"""
Auto-label all session violations for ML evaluation.
"""
import os
import json
from datetime import datetime
import sys

sys.path.insert(0, '.')

from database.database import get_connection, create_label
from database.models import User  # Assuming admin user exists

def auto_label_sessions():
    """Auto-label all unlabeled violations as TRUE for evaluation baseline."""
    conn = get_connection()
    
    try:
        # Find admin user for labeling
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
        admin_id = cursor.fetchone()
        admin_id = admin_id[0] if admin_id else 1  # Default admin ID
        
        logs_dir = 'logs'
        labeled_count = 0
        skipped_count = 0
        
        for session_dir in os.listdir(logs_dir):
            if not session_dir.startswith('session_'):
                continue
                
            session_path = os.path.join(logs_dir, session_dir, 'session_log.json')
            if not os.path.exists(session_path):
                print(f"Skipping {session_dir}: no session_log.json")
                continue
                
            with open(session_path, 'r') as f:
                session_data = json.load(f)
            
            violations = session_data.get('violation_history', [])
            print(f"\n{session_dir}: {len(violations)} violations found")
            
            for violation in violations:
                timestamp = violation['timestamp']
                v_type = violation['violation']
                
                # Check if already labeled
                cursor.execute("""
                    SELECT id FROM labels 
                    WHERE session_dir = ? AND violation_timestamp = ?
                """, (session_dir, timestamp))
                
                if cursor.fetchone():
                    print(f"  {timestamp[:19]} [{v_type}] - ALREADY LABELED")
                    skipped_count += 1
                    continue
                
                # Auto-label as TRUE (baseline for evaluation)
                try:
                    create_label(
                        session_dir=session_dir,
                        violation_timestamp=timestamp,
                        violation_type=v_type,
                        human_true=True,  # Baseline: assume AI detections correct
                        confidence="auto",
                        notes="Auto-labeled for ML baseline evaluation",
                        labeler_id=admin_id
                    )
                    print(f"  {timestamp[:19]} [{v_type}] ✓ LABELED TRUE (auto)")
                    labeled_count += 1
                except Exception as e:
                    print(f"  ERROR labeling {v_type}: {e}")
        
        print(f"\n✅ Auto-labeling complete!")
        print(f"   New labels: {labeled_count}")
        print(f"   Skipped (already labeled): {skipped_count}")
        print(f"   View metrics: http://127.0.0.1:5000/admin/metrics_advanced")
        
    finally:
        conn.close()

if __name__ == "__main__":
    auto_label_sessions()
