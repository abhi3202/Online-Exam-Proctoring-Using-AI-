# models/face_registration.py

import cv2
import os
import pickle
import numpy as np
from datetime import datetime
from typing import Dict, List

# Try to import face_recognition, fall back to OpenCV if not available
try:
    import face_recognition
    USE_FACE_RECOGNITION = True
except ImportError:
    USE_FACE_RECOGNITION = False
    print("face_recognition not available, using OpenCV fallback")

ENCODINGS_PATH = os.path.join("known_faces", "encodings.pkl")
os.makedirs("known_faces", exist_ok=True)

# Load OpenCV face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Cache for encodings
_encoding_cache = None

def load_encodings() -> Dict[str, dict]:
    global _encoding_cache
    if _encoding_cache is not None:
        return _encoding_cache
    
    if os.path.exists(ENCODINGS_PATH):
        with open(ENCODINGS_PATH, "rb") as f:
            _encoding_cache = pickle.load(f)
            return _encoding_cache
    _encoding_cache = {}
    return _encoding_cache

def save_encodings(data: Dict[str, dict]):
    global _encoding_cache
    with open(ENCODINGS_PATH, "wb") as f:
        pickle.dump(data, f)
    _encoding_cache = data

def detect_face_opencv(frame):
    """Detect face using OpenCV Haar Cascade."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    if len(faces) > 0:
        x, y, w, h = faces[0]
        return frame[y:y+h, x:x+w]
    return None

def get_face_encoding_opencv(face_region) -> List[float]:
    """Get simple face encoding using histogram (fallback)."""
    if face_region is None or face_region.size == 0:
        return None
    
    # Resize to consistent size
    face_region = cv2.resize(face_region, (100, 100))
    
    # Convert to grayscale
    gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
    
    # Calculate histogram as a simple feature
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist.flatten() / hist.sum()
    
    # Also calculate some basic statistics
    mean = np.mean(gray)
    std = np.std(gray)
    
    # Combine features
    features = np.concatenate([hist, [mean, std]])
    return features.tolist()

def get_face_encoding(frame) -> List[float]:
    """Extract face encoding."""
    if USE_FACE_RECOGNITION:
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            encodings = face_recognition.face_encodings(rgb_frame)
            if len(encodings) > 0:
                return encodings[0].tolist()
        except Exception as e:
            print(f"face_recognition error: {e}")
    
    # Fallback to OpenCV
    face_region = detect_face_opencv(frame)
    if face_region is not None:
        return get_face_encoding_opencv(face_region)
    return None

def register_face(student_id: str, frame=None) -> Dict[str, any]:
    """Register a student's face."""
    encodings_db = load_encodings()

    if frame is None:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return {"status": "error", "message": "Cannot access camera"}

        print("Press SPACE to capture face, ESC to cancel.")
        captured = False
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            cv2.imshow("Register Face", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == 27:
                print("Registration cancelled.")
                break
            if key == 32:
                captured = True
                break

        cap.release()
        cv2.destroyAllWindows()
        
        if not captured:
            return {"status": "cancelled", "message": "Registration cancelled"}
    
    try:
        face_encoding = get_face_encoding(frame)
        
        if face_encoding is None:
            return {"status": "error", "message": "No face detected! Please ensure your face is clearly visible in the camera."}
        
        encodings_db[student_id] = {
            "encoding": face_encoding,
            "registered_at": datetime.now().isoformat(),
            "method": "face_recognition" if USE_FACE_RECOGNITION else "opencv"
        }
        save_encodings(encodings_db)

        img_path = os.path.join("known_faces", f"{student_id}.jpg")
        cv2.imwrite(img_path, frame)
        print(f"Registered {student_id}, image saved to {img_path}")
        
        return {"status": "success", "message": f"Face registered for {student_id}", "image_path": img_path}
        
    except Exception as e:
        print(f"Registration error: {e}")
        return {"status": "error", "message": f"Registration failed: {str(e)}"}

def verify_identity(frame, student_id: str) -> Dict[str, any]:
    """Verify if the person in frame matches the registered student."""
    encodings_db = load_encodings()
    
    if student_id not in encodings_db:
        return {
            "verified": False,
            "status": "NOT_REGISTERED",
            "message": f"No face registered for student {student_id}"
        }
    
    known_image_path = os.path.join("known_faces", f"{student_id}.jpg")
    if not os.path.exists(known_image_path):
        return {
            "verified": False,
            "status": "NOT_REGISTERED",
            "message": f"Registered image not found for {student_id}"
        }
    
    try:
        known_image = cv2.imread(known_image_path)
        if known_image is None:
            return {"verified": False, "status": "ERROR", "message": "Could not load registered image"}
        
        # Get encodings
        known_encoding = get_face_encoding(known_image)
        unknown_encoding = get_face_encoding(frame)
        
        if known_encoding is None or unknown_encoding is None:
            return {"verified": False, "status": "ERROR", "message": "Could not detect face in one of the images"}
        
        # Compare using the appropriate method
        if USE_FACE_RECOGNITION:
            known_enc = np.array(known_encoding)
            unknown_enc = np.array(unknown_encoding)
            face_distance = np.linalg.norm(known_enc - unknown_enc)
            threshold = 0.6
        else:
            # For OpenCV fallback, use histogram comparison
            known_enc = np.array(known_encoding)
            unknown_enc = np.array(unknown_encoding)
            # Use correlation as similarity measure
            correlation = np.corrcoef(known_enc, unknown_enc)[0, 1]
            face_distance = 1 - correlation  # Convert to distance
            threshold = 0.7
        
        if face_distance < threshold:
            return {
                "verified": True,
                "status": "VERIFIED",
                "message": "Identity verified successfully",
                "confidence": 1 - face_distance
            }
        else:
            return {
                "verified": False,
                "status": "WRONG_PERSON",
                "message": "Person does not match registered student",
                "distance": float(face_distance)
            }
            
    except Exception as e:
        return {
            "verified": False,
            "status": "VERIFICATION_ERROR",
            "message": f"Verification failed: {str(e)}"
        }

def is_student_registered(student_id: str) -> bool:
    """Check if a student has registered their face."""
    encodings_db = load_encodings()
    return student_id in encodings_db

def cli_register():
    student_id = input("Enter student ID for registration: ").strip()
    if not student_id:
        print("Student ID is required")
        return
    result = register_face(student_id)
    print(f"Result: {result['message']}")

if __name__ == "__main__":
    cli_register()

