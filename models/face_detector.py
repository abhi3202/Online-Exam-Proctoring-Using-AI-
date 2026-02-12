# models/face_detector.py

import cv2
import os
import pickle
import numpy as np
from typing import Dict, Any, List
from deepface import DeepFace

ENCODINGS_PATH = "known_faces/encodings.pkl"

class FaceDetector:
    def __init__(self, known_faces_path: str = "known_faces",
                 model_name: str = "Facenet",
                 distance_metric: str = "cosine",
                 threshold: float = 0.7):
        self.known_faces_path = known_faces_path
        self.encodings_file = os.path.join(known_faces_path, "encodings.pkl")
        os.makedirs(known_faces_path, exist_ok=True)

        self.model_name = model_name
        self.distance_metric = distance_metric
        self.threshold = threshold

        # NO self.model here
        self.known_encodings, self.known_meta = self._load_encodings()

    def _load_encodings(self):
        if os.path.exists(self.encodings_file):
            with open(self.encodings_file, "rb") as f:
                data = pickle.load(f)
            return data["encodings"], data["meta"]
        return [], []

    def _save_encodings(self):
        with open(self.encodings_file, "wb") as f:
            pickle.dump({"encodings": self.known_encodings,
                         "meta": self.known_meta}, f)

    def _embed_face(self, img_bgr: np.ndarray) -> np.ndarray:
        # Pass numpy array directly; no model= argument
        reps = DeepFace.represent(
            img_path=img_bgr,
            model_name=self.model_name,
            enforce_detection=True,
            detector_backend="retinaface"
        )
        return np.array(reps[0]["embedding"], dtype="float32")

    def register_face(self, image_path: str, student_id: str, student_name: str):
        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise ValueError(f"Cannot read image: {image_path}")

        emb = self._embed_face(img_bgr)

        self.known_encodings.append(emb)
        self.known_meta.append({"student_id": student_id,
                                "student_name": student_name})
        self._save_encodings()

    def _compute_distance(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        if self.distance_metric == "cosine":
            num = np.dot(emb1, emb2)
            den = (np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8)
            return 1.0 - num / den
        elif self.distance_metric == "euclidean":
            return float(np.linalg.norm(emb1 - emb2))
        else:
            raise ValueError("Unsupported distance_metric")

    def analyze_frame(self, frame, expected_student_id: str) -> Dict[str, Any]:
        # Use frame array directly; no model= argument
        try:
            small = cv2.resize(frame, (0,0), fx = 0.5, fy = 0.5)
            reps = DeepFace.represent(
                img_path=frame,
                model_name=self.model_name,
                enforce_detection=False,
                detector_backend="retinaface"
            )
        except Exception:
            reps = []

        if not reps:
            return {"violations": ["NO_FACE"], "faces": []}

        faces_info: List[Dict[str, Any]] = []
        violations: List[str] = []

        for rep in reps:
            emb = np.array(rep["embedding"], dtype="float32")
            region = rep.get("facial_area") or {}
            x = region.get("x", 0)
            y = region.get("y", 0)
            w = region.get("w", 0)
            h = region.get("h", 0)
            box = (y, x + w, y + h, x)

            best_id = None
            best_dist = 1e9

            for known_emb, meta in zip(self.known_encodings, self.known_meta):
                dist = self._compute_distance(emb, known_emb)
                if dist < best_dist:
                    best_dist = dist
                    best_id = meta["student_id"]

            if best_dist > self.threshold or best_id is None:
                violations.append("UNKNOWN_PERSON")
                matched_student = None
            else:
                matched_student = best_id
                if matched_student != expected_student_id:
                    violations.append("WRONG_PERSON")

            faces_info.append({
                "box": box,
                "matched_student_id": matched_student,
                "distance": float(best_dist)
            })

        if len(reps) > 1:
            violations.append("MULTIPLE_FACES")

        return {
            "violations": list(set(violations)),
            "faces": faces_info
        }


