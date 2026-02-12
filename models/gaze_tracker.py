# models/gaze_tracker.py

import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, Any

mp_face_mesh = mp.solutions.face_mesh

class GazeTracker:
    def __init__(self):
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Indices from MediaPipe Face Mesh spec
        self.left_eye_idx = [33, 160, 158, 133, 153, 144]
        self.right_eye_idx = [263, 387, 385, 362, 380, 373]

        # EAR threshold and gaze thresholds (tune for your setup)
        self.ear_closed_thresh = 0.20
        self.gaze_x_thresh = 0.12     # head turned
        self.gaze_x_strong = 0.18     # strong looking away
        self.gaze_y_strong = 0.18

    def _eye_aspect_ratio(self, landmarks, eye_indices):
        pts = np.array([[landmarks[i].x, landmarks[i].y] for i in eye_indices])
        # EAR: (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
        vert = np.linalg.norm(pts[1] - pts[5]) + np.linalg.norm(pts[2] - pts[4])
        horiz = np.linalg.norm(pts[0] - pts[3])
        return vert / (2.0 * horiz + 1e-6)

    def analyze_frame(self, frame) -> Dict[str, Any]:
        """
        Returns:
            {
              "violations": [...],
              "metrics": {
                  "ear": float,
                  "nose_offset": (dx, dy)
              }
            }

        Violations (as per README):
          - NO_FACE_DETECTED
          - HEAD_TURNED_AWAY
          - EYES_CLOSED
          - LOOKING_AWAY
        """
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self.face_mesh.process(rgb)

        if not res.multi_face_landmarks:
            return {
                "violations": ["NO_FACE_DETECTED"],
                "metrics": {}
            }

        face_landmarks = res.multi_face_landmarks[0].landmark
        violations = []

        # --- Eye aspect ratio (EYES_CLOSED) ---
        left_ear = self._eye_aspect_ratio(face_landmarks, self.left_eye_idx)
        right_ear = self._eye_aspect_ratio(face_landmarks, self.right_eye_idx)
        ear = (left_ear + right_ear) / 2.0

        if ear < self.ear_closed_thresh:
            violations.append("EYES_CLOSED")

        # --- Simple head / gaze heuristic using nose position ---
        nose = face_landmarks[1]  # nose tip
        cx, cy = 0.5, 0.5
        dx = nose.x - cx
        dy = nose.y - cy

        # Head turned left/right
        if abs(dx) > self.gaze_x_thresh:
            violations.append("HEAD_TURNED_AWAY")

        # Strong deviation from screen center -> looking away
        if abs(dx) > self.gaze_x_strong or abs(dy) > self.gaze_y_strong:
            violations.append("LOOKING_AWAY")

        return {
            "violations": list(set(violations)),
            "metrics": {
                "ear": float(ear),
                "nose_offset": (float(dx), float(dy))
            }
        }

if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    tracker = GazeTracker()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        res = tracker.analyze_frame(frame)

        text = ", ".join(res["violations"]) if res["violations"] else "OK"
        cv2.putText(frame, text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 0, 255), 2)

        cv2.imshow("Gaze Tracker", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()
