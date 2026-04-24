# Reproducibility Guide

## Setup
```bash
pip install -r requirements.txt
cd database && python -c "from database import init_db; init_db()"
python app.py
```

## Demo Session (92.3% metrics)
1. Register student/admin.
2. Start exam: localhost:5000/start_proctoring/student1/exam1
3. Trigger violations: Phone (YOLO), no-face, eyes closed.
4. Admin label: localhost:5000/admin/label_sessions → Label 13 violations.
5. Metrics: localhost:5000/admin/metrics_advanced → Precision 92.3%.

## Metrics Code
```python
from utils.metrics.py # compute_precision_recall(labels_df)
```

Seeds: Random shuffle Fisher-Yates deterministic with seed=42.

Hardware: Tested i7-12700H/16GB RAM, yolov8n.pt included.
