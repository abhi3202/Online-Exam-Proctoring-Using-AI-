import cv2
import numpy as np
from deepface import DeepFace
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import warnings

warnings.filterwarnings('ignore')

class FaceDetector:
    def __init__(self, model_name='retinaface'):
        """
        Continuous RetinaFace + LSTM person detector (NO YOLO/object style).
        """
        self.model_name = model_name
        self.no_face_count = 0
        self.no_face_threshold = 5
        self.face_history = []
        self.history_size = 10
        self.lstm_model = self._build_lstm_model()
        
    def _build_lstm_model(self):
        model = Sequential([
            LSTM(32, input_shape=(self.history_size, 1), return_sequences=True),
            Dropout(0.2),
            LSTM(16),
            Dropout(0.2),
            Dense(8, activation='relu'),
            Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        return model
    
    def detect_faces(self, frame):
        """
        Pure RetinaFace face detection (faces = persons).
        """
        try:
            faces = DeepFace.extract_faces(img_path=frame, detector_backend=self.model_name)
            face_count = len(faces)
            
            # LSTM history update
            self.face_history.append(face_count > 0)
            if len(self.face_history) > self.history_size:
                self.face_history.pop(0)
            
            annotated = frame.copy()
            for face in faces:
                x, y, w, h = int(face['facial_area']['x']), int(face['facial_area']['y']), \
                             int(face['facial_area']['w']), int(face['facial_area']['h'])
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            return face_count, faces, annotated
            
        except Exception as e:
            self.face_history.append(False)
            if len(self.face_history) > self.history_size:
                self.face_history.pop(0)
            return 0, [], frame
    
    def _lstm_prediction(self):
        if len(self.face_history) < self.history_size:
            return 0.5
        sequence = np.array(self.face_history).reshape(1, self.history_size, 1)
        return float(self.lstm_model.predict(sequence, verbose=0)[0][0])
    
    def analyze_frame(self, frame, student_id=None):
        """
        CONTINUOUS RETINAFACE DETECTION + LSTM:
        NO PERSON/SINGLE/MULTIPLE faces continuously.
        """
        violations = []
        face_count, faces, annotated = self.detect_faces(frame)
        lstm_pred = self._lstm_prediction()
        
        # Continuous NO_FACE
        if face_count == 0:
            self.no_face_count += 1
            dynamic_thresh = max(2, self.no_face_threshold - int((1 - lstm_pred) * 3))
            if self.no_face_count >= dynamic_thresh:
                violations.append("NO_FACE_DETECTED")
        else:
            self.no_face_count = 0
        
        if face_count > 1:
            violations.append("MULTIPLE_FACES")
        
        classification = (
            "NO_PERSON" if face_count == 0 
            else "SINGLE_PERSON" if face_count == 1 
            else "MULTIPLE_PERSONS"
        )
        
        return {
            'person_count': face_count,
            'classification': classification,
            'faces': faces,
            'annotated_frame': annotated,
            'violations': violations,
            'no_face_streak': self.no_face_count,
            'lstm_face_prob': round(lstm_pred, 3)
        }

if __name__ == "__main__":
    print("=" * 60)
    print("RETINAFACE + LSTM CONTINUOUS PERSON DETECTOR")
    print("=" * 60)
    
    detector = FaceDetector('retinaface')
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Camera error")
        exit(1)
    
    print("ESC=Quit | R=Reset streak")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        result = detector.analyze_frame(frame)
        
        # Overlay
        y = 30
        cv2.putText(result['annotated_frame'], f"Count: {result['person_count']} ({result['classification']})", 
                   (10, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        y += 35
        cv2.putText(result['annotated_frame'], f"Streak: {result['no_face_streak']} | LSTM: {result['lstm_face_prob']}", 
                   (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        if result['violations']:
            cv2.putText(result['annotated_frame'], f"VIOLATIONS: {', '.join(result['violations'])}", 
                       (10, y+30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        cv2.imshow("RetinaFace + LSTM Continuous", result['annotated_frame'])
        
        k = cv2.waitKey(1) & 0xFF
        if k == 27 or k == ord('q'):
            break
        if k == ord('r'):
            detector.no_face_count = 0
            print("Streak reset")
    
    cap.release()
    cv2.destroyAllWindows()
    print("Continuous RetinaFace + LSTM ready!")
