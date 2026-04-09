# models/proctoring_system.py

import os
import json
import uuid
import cv2
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.face_detector import FaceDetector
from models.gaze_tracker import GazeTracker
from models.object_detector import ObjectDetector
from models.audio_analyzer import AudioAnalyzer

# Frequency of identity verification (every N frames)
IDENTITY_VERIFY_INTERVAL = 60

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
    "TAB_SWITCH": "HIGH",
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
            "save_interval": 20,
            "alert_threshold": {
                "CRITICAL": 1,
                "HIGH": 3,
                "MEDIUM": 5,
                "LOW": 10
            },
            "frame_skip": 2,
            "object_detect_interval": 3,
        }
        self.config = {**default_config, **(config or {})}

        # Initialize modules
        self.face_detector = FaceDetector() if self.config["enable_face_detection"] else None
        self.gaze_tracker = GazeTracker() if self.config["enable_gaze_tracking"] else None
        self.object_detector = (
            ObjectDetector(model_path="yolov8n.pt", confidence_threshold=0.4)
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
        self.frame_latencies: List[float] = []
        self.current_warnings: List[str] = []  # Current warnings for popup display

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
            sev = entry.get("severity")
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

    def _verify_identity_continuous(self, frame) -> Dict[str, Any]:
        """
        Perform identity verification every IDENTITY_VERIFY_INTERVAL frames.
        """
        if self.total_frames % IDENTITY_VERIFY_INTERVAL != 0:
            return {"verified": False, "status": "SKIPPED", "message": "Not time for verification"}
        
        from models.face_registration import verify_identity
        return verify_identity(frame, self.student_id)

    def process_frame(self, frame) -> Dict[str, Any]:
        """
        Run face, gaze, and object detectors on a frame.
        """
        start_time = time.time()
        self.total_frames += 1
        all_violations: List[str] = []
        all_warnings: List[str] = []  # Warnings that are shown as popups but not recorded as violations
        results: Dict[str, Any] = {}

        # Face
        if self.face_detector:
            face_res = self.face_detector.analyze_frame(frame, self.student_id)
            results["face"] = face_res
            all_violations.extend(face_res.get("violations", []))

        # Gaze - treat as warnings, not violations
        if self.gaze_tracker:
            gaze_res = self.gaze_tracker.analyze_frame(frame)
            results["gaze"] = gaze_res
            
            # These gaze violations should be warnings only (not counted in evaluation)
            gaze_warnings = gaze_res.get("violations", [])
            warning_types = ["EYES_CLOSED", "LOOKING_AWAY", "HEAD_TURNED_AWAY"]
            
            for gw in gaze_warnings:
                if gw in warning_types:
                    all_warnings.append(gw)
                else:
                    all_violations.append(gw)

        # Objects
        if self.object_detector:
            obj_res = self.object_detector.analyze_frame(frame)
            results["object"] = obj_res
            all_violations.extend(obj_res.get("violations", []))

        uniq_violations = list(set(all_violations))
        uniq_warnings = list(set(all_warnings))
        
        results["violations"] = uniq_violations
        results["warnings"] = uniq_warnings  # Warnings shown as popups but not in evaluation

        # Log each visual violation and save frames for high/critical
        for v in uniq_violations:
            sev = self._classify_severity(v)
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "violation_id": str(uuid.uuid4()),
                "violation": v,
                "severity": sev
            }
            self.violation_history.append(entry)
            if sev in ("CRITICAL", "HIGH"):
                self._save_violation_frame(frame, v)

        # Continuous identity verification every 60 frames
        identity_result = self._verify_identity_continuous(frame)
        if identity_result.get("verified") is False and identity_result.get("status") not in ("SKIPPED", None):
            status = identity_result.get("status", "UNKNOWN")
            if status == "WRONG_PERSON":
                all_violations.append("WRONG_PERSON")
                results["violations"] = list(set(results["violations"] + ["WRONG_PERSON"]))
                self.violation_history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "violation_id": str(uuid.uuid4()),
                    "violation": "WRONG_PERSON",
                    "severity": "CRITICAL",
                    "type": "IDENTITY_CHECK"
                })
                self._save_violation_frame(frame, "IDENTITY_MISMATCH")
        
        results["identity_verification"] = identity_result
        
        # Track latency
        latency = (time.time() - start_time) * 1000
        self.frame_latencies.append(latency)
        
        # Keep only last 100 latencies
        if len(self.frame_latencies) > 100:
            self.frame_latencies = self.frame_latencies[-100:]

        return results

    def process_audio(self) -> Dict[str, Any]:
        """Get next audio chunk and analyze."""
        if not self.audio_analyzer:
            return {"violations": [], "metrics": {}, "label": "DISABLED"}

        chunk = self.audio_analyzer.get_next_chunk()
        res = self.audio_analyzer.analyze_audio_chunk(chunk)
        return res

    def _handle_audio_violations(self, audio_res: Dict[str, Any]):
        """Log audio violations."""
        now = datetime.utcnow()
        for v in audio_res.get("violations", []):
            sev = self._classify_severity(v)
            self.violation_history.append({
                "timestamp": now.isoformat(),
                "violation_id": str(uuid.uuid4()),
                "violation": v,
                "severity": sev,
                "type": "audio",
                "audio_label": audio_res.get("label"),
                "audio_metrics": audio_res.get("metrics", {})
            })

            if v == "MULTIPLE_VOICES":
                self.multiple_voices_events.append(now)
                one_minute_ago = now - timedelta(seconds=60)
                while self.multiple_voices_events and self.multiple_voices_events[0] < one_minute_ago:
                    self.multiple_voices_events.popleft()

                if len(self.multiple_voices_events) > 10:
                    self.violation_history.append({
                        "timestamp": now.isoformat(),
                        "violation": "MULTIPLE_VOICES_RATE_HIGH",
                        "severity": "CRITICAL"
                    })

    def draw_combined_results(self, frame, results: Dict[str, Any]) -> Any:
        """Overlay text on the frame."""
        violations_text = ", ".join(results.get("violations", [])) or "OK"
        cv2.putText(frame, violations_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 0, 255), 2)

        gaze_res = results.get("gaze")
        if gaze_res and gaze_res.get("warning"):
            cv2.putText(frame, gaze_res["warning"], (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (0, 0, 255), 2)

        audio_res = results.get("audio")
        if audio_res and audio_res.get("label") not in (None, "DISABLED"):
            audio_text = f"Audio: {audio_res['label']}"
            cv2.putText(frame, audio_text, (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (255, 0, 0), 2)

        return frame

    def start_monitoring(self, video_source=0):
        """Main loop for monitoring."""
        cap = cv2.VideoCapture(video_source)
        frame_idx = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Camera stream ended")
                    break

                frame_idx += 1

                if frame_idx % self.config["frame_skip"] != 0:
                    cv2.imshow("Proctoring", frame)
                    if cv2.waitKey(1) & 0xFF == 27:
                        break
                    continue

                results = self.process_frame(frame)

                if self.audio_analyzer:
                    audio_res = self.process_audio()
                    results["audio"] = audio_res
                    self._handle_audio_violations(audio_res)

                display = self.draw_combined_results(frame.copy(), results)
                cv2.imshow("Proctoring", display)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

                if frame_idx % (self.config["save_interval"] * 5) == 0:
                    self._save_session_log()
        finally:
            cap.release()
            cv2.destroyAllWindows()
            if self.audio_analyzer:
                self.audio_analyzer.stop_recording()
            self._save_session_log()

    def finalize_session(self):
        """Stop audio and write final session log."""
        if self.audio_analyzer:
            self.audio_analyzer.stop_recording()
        self._save_session_log()

    def log_violation(self, violation_type: str, severity: str, frame=None, details: dict = None):
        """Log a violation from external sources."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "violation_id": str(uuid.uuid4()),
            "violation": violation_type,
            "severity": severity,
            "source": "external"
        }
        if details:
            entry["details"] = details
        
        self.violation_history.append(entry)
        
        if frame is not None and severity in ("CRITICAL", "HIGH"):
            self._save_violation_frame(frame, violation_type)

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics for all detectors."""
        # Calculate detector-specific violations
        face_violations = [v for v in self.violation_history if 
                          v.get("violation") in ["WRONG_PERSON", "UNKNOWN_PERSON", "MULTIPLE_FACES", "NO_FACE_DETECTED"]]
        gaze_violations = [v for v in self.violation_history if 
                         v.get("violation") in ["HEAD_TURNED_AWAY", "LOOKING_AWAY", "EYES_CLOSED"]]
        object_violations = [v for v in self.violation_history if 
                           v.get("violation") in ["MOBILE_PHONE", "LAPTOP", "KEYBOARD", "MOUSE", "REMOTE_CONTROL", "SCREEN", "TABLET", "MULTIPLE_PERSONS"]]
        audio_violations = [v for v in self.violation_history if v.get("type") == "audio"]
        tab_switch_violations = [v for v in self.violation_history if v.get("violation") == "TAB_SWITCH"]

        # Calculate average latency
        avg_latency = sum(self.frame_latencies) / len(self.frame_latencies) if self.frame_latencies else 0
        
        # Calculate session duration
        duration = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            "session_info": {
                "student_id": self.student_id,
                "exam_id": self.exam_id,
                "start_time": self.start_time.isoformat(),
                "duration_seconds": round(duration, 2),
                "total_frames": self.total_frames,
            },
            "detectors": {
                "face_detector": {
                    "enabled": self.face_detector is not None,
                    "violations_count": len(face_violations),
                    "violations": list(set([v["violation"] for v in face_violations])),
                    "accuracy_estimate": max(0, 100 - (len(face_violations) / max(self.total_frames, 1) * 1000)),
                    "estimated_latency_ms": 200,
                },
                "gaze_tracker": {
                    "enabled": self.gaze_tracker is not None,
                    "violations_count": len(gaze_violations),
                    "violations": list(set([v["violation"] for v in gaze_violations])),
                    "accuracy_estimate": max(0, 100 - (len(gaze_violations) / max(self.total_frames, 1) * 500)),
                    "estimated_latency_ms": 10,
                },
                "object_detector": {
                    "enabled": self.object_detector is not None,
                    "violations_count": len(object_violations),
                    "violations": list(set([v["violation"] for v in object_violations])),
                    "accuracy_estimate": max(0, 100 - (len(object_violations) / max(self.total_frames, 1) * 300)),
                    "estimated_latency_ms": 20,
                },
                "audio_analyzer": {
                    "enabled": self.audio_analyzer is not None,
                    "violations_count": len(audio_violations),
                    "violations": list(set([v["violation"] for v in audio_violations])),
                    "accuracy_estimate": max(0, 100 - (len(audio_violations) / max(self.total_frames, 1) * 800)),
                    "estimated_latency_ms": 1500,
                }
            },
            "violations": {
                "total": len(self.violation_history),
                "by_severity": self._summarize_violations()["by_severity"],
                "by_type": {
                    "face": len(face_violations),
                    "gaze": len(gaze_violations),
                    "object": len(object_violations),
                    "audio": len(audio_violations),
                    "tab_switch": len(tab_switch_violations)
                }
            },
            "performance": {
                "avg_frame_latency_ms": round(avg_latency, 2),
                "frames_per_second": round(self.total_frames / max(duration, 1), 2),
                "violation_rate": round(len(self.violation_history) / max(self.total_frames, 1), 4),
            },
            "config": self.config
        }

