import sqlite3
from datetime import datetime

DB_NAME = "study_history.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # -------------------------
    # USERS
    # 誰が学習したか
    # -------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # -------------------------
    # QUESTIONS
    # 何を学習するか
    # -------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            lesson TEXT,
            source TEXT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'typing',
            created_at TEXT NOT NULL
        )
    """)

    # -------------------------
    # STUDY_HISTORY
    # いつ・どう答えたか
    # -------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            studied_at TEXT NOT NULL,
            result TEXT NOT NULL,
            user_answer TEXT,
            review_date TEXT,
            mode TEXT NOT NULL DEFAULT 'typing',
            study_round INTEGER NOT NULL DEFAULT 1,

            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    """)

    conn.commit()
    conn.close()


def save_question(
    subject,
    lesson,
    source,
    question,
    answer,
    mode="typing"
):
    conn = get_connection()
    cursor = conn.cursor()

    # 同じ問題がすでに登録されているか確認
    cursor.execute("""
        SELECT id
        FROM questions
        WHERE subject = ?
          AND lesson = ?
          AND question = ?
          AND answer = ?
    """, (subject, lesson, question, answer))

    existing = cursor.fetchone()

    if existing:
        question_id = existing[0]

    else:
        cursor.execute("""
            INSERT INTO questions (
                subject,
                lesson,
                source,
                question,
                answer,
                mode,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            subject,
            lesson,
            source,
            question,
            answer,
            mode,
            datetime.now().isoformat()
        ))

        question_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return question_id

def get_or_create_user(display_name="user01"):
    conn = get_connection()
    cursor = conn.cursor()

    # 同じ名前のユーザーがいるか確認
    cursor.execute("""
        SELECT id
        FROM users
        WHERE display_name = ?
    """, (display_name,))

    existing = cursor.fetchone()

    if existing:
        user_id = existing[0]
    else:
        cursor.execute("""
            INSERT INTO users (
                display_name,
                created_at
            )
            VALUES (?, ?)
        """, (
            display_name,
            datetime.now().isoformat()
        ))

        user_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return user_id


def save_study_history(
    user_id,
    question_id,
    result,
    user_answer,
    mode="typing",
    study_round=1,
    review_date=None
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO study_history (
            user_id,
            question_id,
            studied_at,
            result,
            user_answer,
            review_date,
            mode,
            study_round
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        question_id,
        datetime.now().isoformat(),
        result,
        user_answer,
        review_date,
        mode,
        study_round
    ))

    conn.commit()
    conn.close()
