import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_dir TEXT NOT NULL,
            violation_timestamp TEXT NOT NULL,
            violation_type TEXT NOT NULL,
            human_true INTEGER NOT NULL,
            confidence TEXT,
            notes TEXT,
            labeled_at TEXT,
            labeler_id INTEGER
        );
        """
    )
    conn.commit()
    conn.close()

def create_user(name, email, password, role):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
        (name, email, password, role),
    )
    conn.commit()
    conn.close()

def get_user_by_email(email):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user

def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, role FROM users ORDER BY id")
    users = cur.fetchall()
    conn.close()
    return users

def delete_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def update_user(user_id, name, email, role, password=None):
    conn = get_connection()
    cur = conn.cursor()
    if password:
        cur.execute(
            "UPDATE users SET name = ?, email = ?, role = ?, password = ? WHERE id = ?",
            (name, email, role, password, user_id),
        )
    else:
        cur.execute(
            "UPDATE users SET name = ?, email = ?, role = ? WHERE id = ?",
            (name, email, role, user_id),
        )
    conn.commit()
    conn.close()

def create_label(session_dir, violation_timestamp, violation_type, human_true, confidence=None, notes=None, labeled_at=None, labeler_id=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO labels (session_dir, violation_timestamp, violation_type, human_true, confidence, notes, labeled_at, labeler_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (session_dir, violation_timestamp, violation_type, int(human_true), confidence or None, notes or None, labeled_at or None, labeler_id)
    )
    conn.commit()
    conn.close()

def get_labels_by_session(session_dir):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM labels WHERE session_dir = ? ORDER BY violation_timestamp",
        (session_dir,)
    )
    labels = cur.fetchall()
    conn.close()
    return labels

def get_all_labels():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM labels ORDER BY labeled_at DESC")
    labels = cur.fetchall()
    conn.close()
    return labels

def update_label(label_id, human_true=None, confidence=None, notes=None):
    conn = get_connection()
    cur = conn.cursor()
    updates = []
    params = []
    if human_true is not None:
        updates.append("human_true = ?")
        params.append(int(human_true))
    if confidence is not None:
        updates.append("confidence = ?")
        params.append(confidence)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    if updates:
        params.append(label_id)
        query = f"UPDATE labels SET {', '.join(updates)} WHERE id = ?"
        cur.execute(query, params)
        conn.commit()
    conn.close()

def delete_label(label_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM labels WHERE id = ?", (label_id,))
    conn.commit()
    conn.close()
