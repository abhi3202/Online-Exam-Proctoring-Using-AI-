# tests/test_detectors.py
"""
Comprehensive test script to verify all detectors in the proctoring system.
Tests: FaceDetector, GazeTracker, ObjectDetector, AudioAnalyzer

Controls:
    1 - Test FaceDetector
    2 - Test GazeTracker
    3 - Test ObjectDetector
    4 - Test AudioAnalyzer
    5 - Test All Detectors Together
    q - Quit

Requirements:
    pip install opencv-python pyaudio mediapipe ultralytics deepface tensorflow numpy
"""

import cv2
import numpy as np
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.face_detector import FaceDetector
from models.gaze_tracker import GazeTracker
from models.object_detector import ObjectDetector
from models.audio_analyzer import AudioAnalyzer


class DetectorTester:
    def __init__(self):
        print("=" * 60)
        print("PROCTORING SYSTEM - DETECTOR TEST SUITE")
        print("=" * 60)
        
        # Initialize detectors
        print("\n[1/4] Initializing FaceDetector...")
        self.face_detector = FaceDetector(model_name='retinaface')
        print("      ✓ FaceDetector initialized")
        
        print("\n[2/4] Initializing GazeTracker...")
        self.gaze_tracker = GazeTracker()
        print("      ✓ GazeTracker initialized")
        
        print("\n[3/4] Initializing ObjectDetector...")
        self.object_detector = ObjectDetector(model_path="yolov8n.pt", confidence_threshold=0.5)
        print("      ✓ ObjectDetector initialized")
        
        print("\n[4/4] Initializing AudioAnalyzer...")
        self.audio_analyzer = AudioAnalyzer(sample_rate=16000, chunk_duration=1.0)
        self.audio_analyzer.start_recording()
        print("      ✓ AudioAnalyzer initialized")
        
        # Video capture
        print("\n[SETUP] Opening webcam...")
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("ERROR: Could not open webcam!")
            sys.exit(1)
        
        # Test student ID for face verification
        self.test_student_id = "abhi"
        
        # Check if registered face exists
        known_image_path = os.path.join("known_faces", f"{self.test_student_id}.jpg")
        if os.path.exists(known_image_path):
            print(f"      ✓ Found registered face for student: {self.test_student_id}")
        else:
            print(f"      ⚠ No registered face found for {self.test_student_id}")
        
        print("\n" + "=" * 60)
        print("CONTROLS:")
        print("  1 - FaceDetector Test")
        print("  2 - GazeTracker Test")
        print("  3 - ObjectDetector Test")
        print("  4 - AudioAnalyzer Test")
        print("  5 - All Detectors Together")
        print("  q - Quit")
        print("=" * 60)
        
        self.current_test = None
        self.frame_count = 0
        
    def test_face_detector(self, frame):
        """Test FaceDetector and draw results"""
        result = self.face_detector.analyze_frame(frame, self.test_student_id)
        
        # Draw face bounding boxes
        display = result['annotated_frame'].copy()
        
        # Add info text
        info_lines = [
            f"Faces Detected: {result['face_count']}",
            f"Identity Status: {result['identity_status']}",
            f"Classification: {result['classification']}"
        ]
        
        y_offset = 30
        for line in info_lines:
            color = (0, 255, 0) if result['identity_status'] == "VERIFIED" else (0, 0, 255)
            cv2.putText(display, line, (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            y_offset += 25
        
        # Show violations
        if result['violations']:
            violations_text = "VIOLATIONS: " + ", ".join(result['violations'])
            cv2.putText(display, violations_text, (10, y_offset + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Status
        cv2.putText(display, "TESTING: FaceDetector", (10, display.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        return display, result
    
    def test_gaze_tracker(self, frame):
        """Test GazeTracker and draw results"""
        result = self.gaze_tracker.analyze_frame(frame)
        
        display = frame.copy()
        
        # Get metrics
        metrics = result.get('metrics', {})
        ear = metrics.get('ear', 0)
        nose_offset = metrics.get('nose_offset', (0, 0))
        
        info_lines = [
            f"EAR (Eye Aspect Ratio): {ear:.3f}",
            f"Nose Offset: ({nose_offset[0]:.3f}, {nose_offset[1]:.3f})",
            f"Status: {'OK' if not result['violations'] else 'VIOLATION'}"
        ]
        
        y_offset = 30
        for line in info_lines:
            cv2.putText(display, line, (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_offset += 25
        
        # Show violations
        if result['violations']:
            violations_text = "VIOLATIONS: " + ", ".join(result['violations'])
            cv2.putText(display, violations_text, (10, y_offset + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Status
        cv2.putText(display, "TESTING: GazeTracker", (10, display.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        return display, result
    
    def test_object_detector(self, frame):
        """Test ObjectDetector and draw results"""
        result = self.object_detector.analyze_frame(frame)
        
        display = frame.copy()
        
        # Draw bounding boxes for detected objects
        for det in result['detections']:
            x1, y1, x2, y2 = det['bbox']
            label = f"{det['label']} {det['confidence']:.2f}"
            
            # Color based on prohibited items
            prohibited = ['cell phone', 'laptop', 'keyboard', 'mouse', 'remote', 'tv', 'monitor', 'tablet']
            color = (0, 0, 255) if det['label'].lower() in prohibited else (0, 255, 0)
            
            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
            cv2.putText(display, label, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        info_lines = [
            f"Person Count: {result['person_count']}",
            f"Total Detections: {len(result['detections'])}"
        ]
        
        y_offset = 30
        for line in info_lines:
            cv2.putText(display, line, (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_offset += 25
        
        # Show violations
        if result['violations']:
            violations_text = "VIOLATIONS: " + ", ".join(result['violations'])
            cv2.putText(display, violations_text, (10, y_offset + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Status
        cv2.putText(display, "TESTING: ObjectDetector", (10, display.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        return display, result
    
    def test_audio_analyzer(self):
        """Test AudioAnalyzer"""
        try:
            chunk = self.audio_analyzer.get_next_chunk()
            result = self.audio_analyzer.analyze_audio_chunk(chunk)
            return result
        except Exception as e:
            return {"violations": [], "metrics": {}, "error": str(e)}
    
    def test_all_detectors(self, frame):
        """Test all detectors together"""
        # Face Detection
        face_result = self.face_detector.analyze_frame(frame, self.test_student_id)
        
        # Gaze Tracking
        gaze_result = self.gaze_tracker.analyze_frame(frame)
        
        # Object Detection
        obj_result = self.object_detector.analyze_frame(frame)
        
        # Audio Analysis
        audio_result = self.test_audio_analyzer()
        
        # Combine all violations
        all_violations = (
            face_result.get('violations', []) +
            gaze_result.get('violations', []) +
            obj_result.get('violations', []) +
            audio_result.get('violations', [])
        )
        
        # Create combined display
        display = frame.copy()
        
        # Draw face bounding boxes
        for face in face_result.get('faces', []):
            x, y, w, h = int(face['x']), int(face['y']), int(face['w']), int(face['h'])
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Draw object bounding boxes
        for det in obj_result['detections']:
            x1, y1, x2, y2 = det['bbox']
            prohibited = ['cell phone', 'laptop', 'keyboard', 'mouse', 'remote', 'tv', 'monitor', 'tablet']
            color = (0, 0, 255) if det['label'].lower() in prohibited else (0, 255, 0)
            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
        
        # Info panel
        info_lines = [
            f"Faces: {face_result['face_count']} | Persons: {obj_result['person_count']}",
            f"Identity: {face_result['identity_status']}",
            f"Audio: dB={audio_result['metrics'].get('db', 0):.1f} | Label={audio_result.get('label', 'N/A')}"
        ]
        
        y_offset = 30
        for line in info_lines:
            cv2.putText(display, line, (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 18
        
        # Show all violations
        if all_violations:
            violations_text = "VIOLATIONS: " + ", ".join(set(all_violations))
            cv2.putText(display, violations_text, (10, y_offset + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Status
        cv2.putText(display, "TESTING: All Detectors", (10, display.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        return display, {
            'face': face_result,
            'gaze': gaze_result,
            'object': obj_result,
            'audio': audio_result
        }
    
    def print_summary(self, results):
        """Print summary of detector results"""
        print("\n" + "-" * 40)
        print("DETECTOR RESULTS SUMMARY")
        print("-" * 40)
        
        if 'face' in results:
            print(f"Face: {results['face'].get('face_count', 0)} detected, "
                  f"Status: {results['face'].get('identity_status', 'UNKNOWN')}")
            print(f"  Violations: {results['face'].get('violations', [])}")
        
        if 'gaze' in results:
            print(f"Gaze: EAR={results['gaze'].get('metrics', {}).get('ear', 0):.3f}")
            print(f"  Violations: {results['gaze'].get('violations', [])}")
        
        if 'object' in results:
            print(f"Object: {results['object'].get('person_count', 0)} persons, "
                  f"{len(results['object'].get('detections', []))} detections")
            print(f"  Violations: {results['object'].get('violations', [])}")
        
        if 'audio' in results:
            print(f"Audio: {results['audio'].get('label', 'N/A')}, "
                  f"dB={results['audio'].get('metrics', {}).get('db', 0):.1f}")
            print(f"  Violations: {results['audio'].get('violations', [])}")
        
        print("-" * 40)
    
    def run(self):
        """Main test loop"""
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("ERROR: Could not read frame!")
                    break
                
                self.frame_count += 1
                
                # Resize for consistent display
                frame = cv2.resize(frame, (800, 600))
                
                if self.current_test == '1':
                    display, result = self.test_face_detector(frame)
                elif self.current_test == '2':
                    display, result = self.test_gaze_tracker(frame)
                elif self.current_test == '3':
                    display, result = self.test_object_detector(frame)
                elif self.current_test == '4':
                    display = frame.copy()
                    result = self.test_audio_analyzer()
                    # Show audio info
                    info_lines = [
                        f"Audio Label: {result.get('label', 'N/A')}",
                        f"Volume (dB): {result['metrics'].get('db', 0):.1f}",
                        f"Spectral Flatness: {result['metrics'].get('spectral_flatness', 0):.3f}"
                    ]
                    y_offset = 30
                    for line in info_lines:
                        cv2.putText(display, line, (10, y_offset),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        y_offset += 25
                    
                    if result.get('violations'):
                        cv2.putText(display, "VIOLATIONS: " + ", ".join(result['violations']),
                                    (10, y_offset + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    
                    cv2.putText(display, "TESTING: AudioAnalyzer", (10, display.shape[0] - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                elif self.current_test == '5':
                    display, result = self.test_all_detectors(frame)
                    # Print summary every 30 frames
                    if self.frame_count % 30 == 0:
                        self.print_summary(result)
                else:
                    # No test selected - show instructions
                    display = frame.copy()
                    cv2.putText(display, "Press key to select test:", (200, 250),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    cv2.putText(display, "1-Face | 2-Gaze | 3-Object | 4-Audio | 5-All | q-Quit",
                                (150, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                cv2.imshow("Proctoring Detector Test Suite", display)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key in [ord('1'), ord('2'), ord('3'), ord('4'), ord('5')]:
                    self.current_test = chr(key)
                    self.frame_count = 0
                    test_names = {
                        '1': 'FaceDetector',
                        '2': 'GazeTracker',
                        '3': 'ObjectDetector',
                        '4': 'AudioAnalyzer',
                        '5': 'All Detectors'
                    }
                    print(f"\n>>> Running {test_names[self.current_test]} test...")
                
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        print("\nCleaning up...")
        self.cap.release()
        cv2.destroyAllWindows()
        if self.audio_analyzer:
            self.audio_analyzer.stop_recording()
        print("Done!")


if __name__ == "__main__":
    tester = DetectorTester()
    tester.run()

