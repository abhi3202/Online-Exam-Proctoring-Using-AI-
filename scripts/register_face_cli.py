import sys
import os

# make project root importable
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.face_registration import register_face

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/register_face_cli.py <student_id>")
        sys.exit(1)

    student_id = sys.argv[1]
    register_face(student_id)
