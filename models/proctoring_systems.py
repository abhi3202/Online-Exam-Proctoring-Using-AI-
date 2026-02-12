# models/proctoring_system.py

import os
import json
import cv2
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from models.face_detector import FaceDetector
from models.gaze_tracker import GazeTracker
from models.object_detector import ObjectDetector
from models.audio_analyzer import AudioAnalyzer

# Severity mapping (tune as needed)
SEVERITY_MAP = {
    "WRONG_PERSON": "CRITICAL",
    "UNKNOWN_PERSON": "HIGH",
    "MULTIPLE_FACES": "CRITICAL",
    "MULTIPLE_PERSONS": "CRITICAL",
    "NO_FACE": "HIGH",
    "NO_FACE_DETECTED": "HIGH",
    "MOBILE_PHONE": "CRITICAL",
    "LAPTOP": "CRITICAL",
    "KEYBOARD": "MEDIUM",
    "MOUSE": "MEDIUM",
    "REMOTE_CONTROL": "MEDIUM",
    "SCREEN": "MEDIUM",
    "TABLET": "CRITICAL",
    "HEAD_TURNED_AWAY": "MEDIUM",
    "LOOKING_AWAY": "MEDIUM",
    "EYES_CLOSED": "LOW",
    "MULTIPLE_VOICES": "MEDIUM",
    "LOUD_AUDIO": "MEDIUM",
    "MULTIPLE_VOICES_RATE_HIGH": "CRITICAL",
}


class ProctoringSystem:
    def __init__(self,
                 student_id: str,
                 exam_id: str,
                 config: Optional[Dict[str, Any]] = None):
        self.student_id = student_id
        self.exam_id = exam_id

        # Default configuration (can be overridden by caller)
        default_config = {
            "enable_face_detection": True,
            "enable_gaze_tracking": True,
            "enable_object_detection": True,
            "enable_audio_analysis": True,
            "save_violation_frames": True,
            # Approximate seconds, but used via frame counts
            "save_interval": 20,
            "alert_threshold": {
                "CRITICAL": 1,
                "HIGH": 3,
                "MEDIUM": 5,
                "LOW": 10
            },
            "frame_skip": 2  # process every 2nd frame
        }
        self.config = {**default_config, **(config or {})}

        # Initialize modules
        self.face_detector = FaceDetector() if self.config["enable_face_detection"] else None
        self.gaze_tracker = GazeTracker() if self.config["enable_gaze_tracking"] else None
        self.object_detector = (
            ObjectDetector(model_path="yolov8n.pt", confidence_threshold=0.5)
            if self.config["enable_object_detection"] else None
        )

        if self.config["enable_audio_analysis"]:
            self.audio_analyzer = AudioAnalyzer()
            self.audio_analyzer.start_recording()
        else:
            self.audio_analyzer = None

        # Session-level tracking
        self.start_time = datetime.utcnow()
        self.total_frames = 0
        self.violation_history: List[Dict[str, Any]] = []

        # Track MULTIPLE_VOICES events (timestamps within last 60s)
        self.multiple_voices_events = deque()

        # Logging directories
        session_dir_name = f"session_{self.exam_id}_{self.student_id}"
        self.session_dir = os.path.join("logs", session_dir_name)
        self.violations_dir = os.path.join(self.session_dir, "violations")
        os.makedirs(self.violations_dir, exist_ok=True)

        self.session_log_path = os.path.join(self.session_dir, "session_log.json")

    def _classify_severity(self, violation: str) -> str:
        return SEVERITY_MAP.get(violation, "LOW")

    def _summarize_violations(self) -> Dict[str, Any]:
        by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for entry in self.violation_history:
            sev = entry["severity"]
            if sev in by_severity:
                by_severity[sev] += 1

        total_violations = len(self.violation_history)
        violation_rate = total_violations / max(self.total_frames, 1)

        return {
            "total_violations": total_violations,
            "by_severity": by_severity,
            "violation_rate": violation_rate
        }

    def _save_session_log(self):
        end_time = datetime.utcnow()
        summary = self._summarize_violations()

        log_data = {
            "student_id": self.student_id,
            "exam_id": self.exam_id,
            "session_start": self.start_time.isoformat(),
            "session_end": end_time.isoformat(),
            "total_frames": self.total_frames,
            "violation_summary": summary,
            "violation_history": self.violation_history
        }

        os.makedirs(self.session_dir, exist_ok=True)
        with open(self.session_log_path, "w") as f:
            json.dump(log_data, f, indent=2)

    def _save_violation_frame(self, frame, violation_code: str):
        if not self.config["save_violation_frames"]:
            return
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{violation_code}_{ts}.jpg"
        path = os.path.join(self.violations_dir, filename)
        cv2.imwrite(path, frame)

    def process_frame(self, frame) -> Dict[str, Any]:
        """
        Run face, gaze, and object detectors on a frame.
        """
        self.total_frames += 1
        all_violations: List[str] = []
        results: Dict[str, Any] = {}

        # Face
        if self.face_detector:
            face_res = self.face_detector.analyze_frame(frame, self.student_id)
            results["face"] = face_res
            all_violations.extend(face_res.get("violations", []))

        # Gaze
        if self.gaze_tracker:
            gaze_res = self.gaze_tracker.analyze_frame(frame)
            results["gaze"] = gaze_res
            all_violations.extend(gaze_res.get("violations", []))

        # Objects
        if self.object_detector:
            obj_res = self.object_detector.analyze_frame(frame)
            results["object"] = obj_res
            all_violations.extend(obj_res.get("violations", []))

        uniq_violations = list(set(all_violations))
        results["violations"] = uniq_violations

        # Log each visual violation and save frames for high/critical
        for v in uniq_violations:
            sev = self._classify_severity(v)
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "violation": v,
                "severity": sev
            }
            self.violation_history.append(entry)
            if sev in ("CRITICAL", "HIGH"):
                self._save_violation_frame(frame, v)

        return results

    def process_audio(self) -> Dict[str, Any]:
        """
        Get next audio chunk, analyze, and return:
          {
            "violations": [...],
            "metrics": {"db": float, "spectral_flatness": float},
            "label": "SILENT" | "NORMAL" | "LOUD" | "MULTIPLE_VOICES"
          }
        """
        if not self.audio_analyzer:
            return {"violations": [], "metrics": {}, "label": "DISABLED"}

        chunk = self.audio_analyzer.get_next_chunk()
        res = self.audio_analyzer.analyze_audio_chunk(chunk)
        return res

    def _handle_audio_violations(self, audio_res: Dict[str, Any]):
        """
        Log audio violations and enforce MULTIPLE_VOICES > 10 times per minute rule.
        """
        now = datetime.utcnow()
        for v in audio_res.get("violations", []):
            sev = self._classify_severity(v)
            self.violation_history.append({
                "timestamp": now.isoformat(),
                "violation": v,
                "severity": sev,
                "audio_label": audio_res.get("label"),
                "audio_metrics": audio_res.get("metrics", {})
            })

            if v == "MULTIPLE_VOICES":
                # Add current event
                self.multiple_voices_events.append(now)

                # Remove events older than 60 seconds
                one_minute_ago = now - timedelta(seconds=60)
                while self.multiple_voices_events and self.multiple_voices_events[0] < one_minute_ago:
                    self.multiple_voices_events.popleft()

                # If more than 10 MULTIPLE_VOICES in last 60s, log a rate-based critical event
                if len(self.multiple_voices_events) > 10:
                    self.violation_history.append({
                        "timestamp": now.isoformat(),
                        "violation": "MULTIPLE_VOICES_RATE_HIGH",
                        "severity": "CRITICAL"
                    })

    def draw_combined_results(self, frame, results: Dict[str, Any]) -> Any:
        """
        Overlay high-level text on the frame (you can extend this with boxes).
        """
        # Combined visual violations
        violations_text = ", ".join(results.get("violations", [])) or "OK"
        cv2.putText(frame, violations_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 0, 255), 2)

        # Gaze warning line
        gaze_res = results.get("gaze")
        if gaze_res and gaze_res.get("warning"):
            cv2.putText(frame, gaze_res["warning"], (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (0, 0, 255), 2)

        # Optional: show last audio label
        audio_res = results.get("audio")
        if audio_res and audio_res.get("label") not in (None, "DISABLED"):
            audio_text = f"Audio: {audio_res['label']}"
            cv2.putText(frame, audio_text, (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (255, 0, 0), 2)

        return frame

    def start_monitoring(self, video_source=0):
        """
        Main loop: capture video, run all modules, display, and save logs.
        """
        cap = cv2.VideoCapture(video_source)
        frame_idx = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Camera stream ended")
                    break

                frame_idx += 1

                # Frame skipping for performance
                if frame_idx % self.config["frame_skip"] != 0:
                    cv2.imshow("Proctoring", frame)
                    if cv2.waitKey(1) & 0xFF == 27:
                        break
                    continue

                # Visual modules
                results = self.process_frame(frame)

                # Audio module
                if self.audio_analyzer:
                    audio_res = self.process_audio()
                    results["audio"] = audio_res
                    self._handle_audio_violations(audio_res)

                # Draw combined overlays
                display = self.draw_combined_results(frame.copy(), results)
                cv2.imshow("Proctoring", display)
                if cv2.waitKey(1) & 0xFF == 27:  # ESC
                    break

                # Periodic session log save (approximate, frame-based)
                if frame_idx % (self.config["save_interval"] * 5) == 0:
                    self._save_session_log()
        finally:
            cap.release()
            cv2.destroyAllWindows()
            if self.audio_analyzer:
                self.audio_analyzer.stop_recording()
            self._save_session_log()

    def finalize_session(self):
        """
        Call this when the exam ends (web version).
        Stops audio and writes final session_log.json.
        """
        if self.audio_analyzer:
            self.audio_analyzer.stop_recording()
        self._save_session_log()
