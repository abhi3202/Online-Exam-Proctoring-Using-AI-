# models/object_detector.py

import cv2
import numpy as np
from typing import Dict, Any, List
from ultralytics import YOLO

# Focus on electronic gadgets only
PROHIBITED_LABELS = {
    "cell phone": "MOBILE_PHONE",
    "phone": "MOBILE_PHONE",
    "laptop": "LAPTOP",
    "keyboard": "KEYBOARD",
    "mouse": "MOUSE",
    "remote": "REMOTE_CONTROL",
    "tv": "SCREEN",
    "monitor": "SCREEN",
    "tablet": "TABLET"
}

class ObjectDetector:
    def __init__(self,
                 model_path: str = "yolov8n.pt",
                 confidence_threshold: float = 0.4):
        """
        model_path: path to YOLOv8 model (nano recommended).
        confidence_threshold: minimum confidence to keep a detection.
        """
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.warmup_done = False
        
        # Pre-warm the model with a dummy inference
        self._warmup()

    def _warmup(self):
        """Warm up the model with a small blank frame for faster first detection."""
        try:
            # Create a small dummy frame for warmup
            dummy_frame = np.zeros((320, 320, 3), dtype=np.uint8)
            # Run inference to initialize model
            _ = self.model(dummy_frame, conf=self.confidence_threshold, verbose=False)
            self.warmup_done = True
            print("Object detector warmup complete")
        except Exception as e:
            print(f"Object detector warmup failed: {e}")

    def analyze_frame(self, frame) -> Dict[str, Any]:
        """
        Input:
            frame: BGR image from OpenCV.
        Output:
            {
              "violations": [...],
              "detections": [
                {
                  "bbox": [x1, y1, x2, y2],
                  "label": str,
                  "confidence": float
                }, ...
              ],
              "person_count": int
            }

        Violations:
          - MOBILE_PHONE
          - LAPTOP
          - KEYBOARD
          - MOUSE
          - REMOTE_CONTROL
          - SCREEN
          - TABLET
          - MULTIPLE_PERSONS
        """
        # Use half resolution for faster inference (optional, can be toggled)
        # Note: This is a speed optimization - detection may be slightly less accurate
        h, w = frame.shape[:2]
        
        # Run detection
        results = self.model(frame, conf=self.confidence_threshold, verbose=False, imgsz=640)[0]

        violations: List[str] = []
        detections: List[Dict[str, Any]] = []
        person_count = 0

        # Process detections
        if results.boxes is not None and len(results.boxes) > 0:
            for box, cls, conf in zip(results.boxes.xyxy,
                                      results.boxes.cls,
                                      results.boxes.conf):
                x1, y1, x2, y2 = map(int, box.tolist())
                label = results.names[int(cls)]
                conf_val = float(conf)

                if label == "person":
                    person_count += 1

                vcode = PROHIBITED_LABELS.get(label.lower())
                if vcode:
                    violations.append(vcode)

                detections.append({
                    "bbox": [x1, y1, x2, y2],
                    "label": label,
                    "confidence": conf_val
                })

        if person_count > 1:
            violations.append("MULTIPLE_PERSONS")

        return {
            "violations": list(set(violations)),
            "detections": detections,
            "person_count": person_count
        }


if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    detector = ObjectDetector(model_path="yolov8n.pt", confidence_threshold=0.4)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        res = detector.analyze_frame(frame)

        # Draw detections
        for det in res["detections"]:
            x1, y1, x2, y2 = det["bbox"]
            label = f"{det['label']} {det['confidence']:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (0, 255, 0), 1)

        # Show violations summary (electronics only)
        text = ", ".join(res["violations"]) if res["violations"] else "NO ELECTRONIC GADGETS"
        cv2.putText(frame, text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 0, 255), 2)

        cv2.imshow("Object Detector - Electronics Focus", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()
