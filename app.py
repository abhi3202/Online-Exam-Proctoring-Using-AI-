# app.py  (at project root: Proctoring_system/app.py)

from flask import Flask, render_template, Response,request, redirect, url_for, session, jsonify
import cv2, os, json

from models.proctoring_systems import ProctoringSystem  # adjust name if you kept proctoring_systems.py
from database.database import create_user, get_user_by_email
from database.database import get_connection

app = Flask(__name__)
# Keep a global reference to the current proctoring session
proctoring = None
camera = None

app.secret_key = "change-me"


@app.route("/start_exam/<student_id>/<exam_id>")
def start_exam(student_id, exam_id):
    global proctoring, camera
    
    # Initialize a new ProctoringSystem for this student and exam
    config = {"frame_skip" : 4}
    proctoring = ProctoringSystem(student_id=student_id,
                                   exam_id=exam_id, 
                                   config=config)
    # Open camera here and reuse in video_feed
    if camera is None:
        camera = cv2.VideoCapture(0)

    # Render your student exam page
    # Make sure you have templates/student/exam.html created
    return render_template("student/exam.html", student_id=student_id, exam_id=exam_id)


def generate_frames():
    """
    Video generator for /video_feed.
    Uses the global camera and proctoring instance.
    """
    global camera, proctoring
    if camera is None or proctoring is None:
        return

    # frame_idx = 0

    while True:
        ret, frame = camera.read()
        if not ret:
            camera.release()
            camera = cv2.VideoCapture(0)
            continue

            # break

        # frame_idx += 1

        # Run all models on this frame
        results = proctoring.process_frame(frame)

        # If audio is enabled, process one audio chunk and attach to results
        if proctoring.audio_analyzer:
            audio_res = proctoring.process_audio()
            results["audio"] = audio_res
            proctoring._handle_audio_violations(audio_res)

        # Draw on frame
        display = proctoring.draw_combined_results(frame.copy(), results)

        # Encode and yield as MJPEG
        ret, buffer = cv2.imencode(".jpg", display)
        if not ret:
            continue
        jpg_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpg_bytes + b"\r\n"
        )


@app.route("/video_feed")
def video_feed():
    """
    MJPEG video stream for the exam page.
    """
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


def load_session_log(session_dir):
    log_path = os.path.join(session_dir, "session_log.json")
    if not os.path.exists(log_path):
        return None
    with open(log_path, "r") as f:
        return json.load(f)


@app.route("/admin")
def admin_dashboard():
    logs_root = os.path.join("logs")
    total_sessions = 0
    students = set()
    exams = set()

    if os.path.isdir(logs_root):
        for name in os.listdir(logs_root):
            if not name.startswith("session_"):
                continue
            total_sessions += 1
            parts = name[len("session_") :].split("_", 1)
            if len(parts) == 2:
                exam_id, student_id = parts
                students.add(student_id)
                exams.add(exam_id)

    stats = {
        "total_sessions": total_sessions,
        "unique_students": len(students),
        "unique_exams": len(exams),
    }
    return render_template("admin/dashboard.html", stats=stats)


@app.route("/admin/sessions")
def admin_sessions():
    logs_root = os.path.join("logs")
    sessions = []

    if os.path.isdir(logs_root):
        for name in os.listdir(logs_root):
            if not name.startswith("session_"):
                continue

            session_dir = os.path.join(logs_root, name)
            data = load_session_log(session_dir)
            if not data:
                continue

            sessions.append({
                "student_id": data["student_id"],
                "exam_id": data["exam_id"],
                "session_start": data["session_start"],
                "session_end": data["session_end"],
                "summary": data["violation_summary"],
            })

    # sort newest first
    sessions.sort(key=lambda s: s["session_start"], reverse=True)

    return render_template("admin/sessions.html", sessions=sessions)


@app.route("/admin/reports")
@app.route("/admin/reports/<exam_id>/<student_id>")
def admin_reports(exam_id=None, student_id=None):
    # If no specific session requested, just show an empty page or redirect
    if not exam_id or not student_id:
        return render_template(
            "admin/reports.html",
            exam_id="N/A",
            student_id="N/A",
            data={"violation_summary": {"total_violations": 0,
                                        "by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
                                        "violation_rate": 0.0},
                  "violation_history": [],
                  "session_start": "",
                  "session_end": ""}
        )

    session_dir = os.path.join("logs", f"session_{exam_id}_{student_id}")
    data = load_session_log(session_dir)
    if not data:
        # simple fallback if log not found
        data = {"violation_summary": {"total_violations": 0,
                                      "by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
                                      "violation_rate": 0.0},
                "violation_history": [],
                "session_start": "",
                "session_end": ""}

    return render_template(
        "admin/reports.html",
        exam_id=exam_id,
        student_id=student_id,
        data=data
    )

@app.route("/submit_exam/<student_id>/<exam_id>", methods=["POST"])
def submit_exam(student_id, exam_id):
    global proctoring, camera

    data = request.get_json() or {}
    answers = data.get("answers", [])

    # TODO: save answers in database if you want
    # Example: store as JSON in an exam_submissions table
    # Finalize proctoring session and write logs
    if proctoring is not None:
        try:
            proctoring.finalize_session()
        except Exception as e:
            print("Error Fnalizing session:",e)

    if camera is not None:
        camera.release()
        camera = None

    # For now just send a simple JSON response
    return jsonify({"status": "ok"})


@app.route("/admin/students")
def admin_students():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, role FROM users ORDER BY id")
    users = cur.fetchall()
    conn.close()
    return render_template("admin/students.html", users=users)

@app.route("/login", methods=["GET", "POST"])
def auth_login():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = get_user_by_email(email)
        if user and user["password"] == password:
            session["user"] = {
                "id": user["id"],
                "email": user["email"],
                "role": user["role"],
                "name": user["name"],
        }
        # TODO: replace with real DB check
        if email == "admin@example.com" and password == "admin":
            session["user"] = {"email": email, "role": "admin"}
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("start_exam", student_id = user["id"], exam_id = "DEMO"))
    else:
            error = "Invalid credentials"
    return render_template("auth/login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def auth_register():
    error = None
    if request.method == "POST":
        # Here you would save to database; for now we just redirect to login
        name = request.form["name"]
        email = request.form["email"]
        role = request.form["role"]
        password = request.form["password"]

        try:
            create_user(name, email, password, role)

        except Exception as e:
            # Most likely duplicate email
            error = "Registration failed : email already exists"
            return render_template("auth/register.html",error=error)
        return redirect(url_for("auth_login"))
    return render_template("auth/register.html", error=error)



@app.route("/student/profile")
def student_profile():
    user = session.get("user")
    if not user or user.get("role") != "student":
        return redirect(url_for("auth_login"))
    # user is a dict; pass it to template
    return render_template("student/profile.html", user=user)

@app.route("/exam_completed/<student_id>/<exam_id>")
def exam_completed(student_id, exam_id):
    return render_template(
        "student/completed.html",
        student_id=student_id,
        exam_id=exam_id,
    )



if __name__ == "__main__":
    # Development server; in production use gunicorn/uwsgi, etc.
    app.run(host="0.0.0.0", port=5000, debug=True)


