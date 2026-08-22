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

    
def get_study_history():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            study_history.id,
            users.display_name,
            questions.lesson,
            questions.question,
            questions.answer,
            study_history.result,
            study_history.user_answer,
            study_history.studied_at,
            study_history.review_date,
            study_history.study_round
        FROM study_history
        JOIN users
            ON study_history.user_id = users.id
        JOIN questions
            ON study_history.question_id = questions.id
        ORDER BY study_history.id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


def get_due_reviews(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().date().isoformat()

    cursor.execute("""
        SELECT
            questions.id,
            questions.lesson,
            questions.question,
            questions.answer,
            study_history.review_date
        FROM study_history
        JOIN questions
            ON study_history.question_id = questions.id
        WHERE study_history.user_id = ?
          AND study_history.id = (
              SELECT MAX(sh2.id)
              FROM study_history AS sh2
              WHERE sh2.user_id = study_history.user_id
                AND sh2.question_id = study_history.question_id
          )
          AND study_history.result = 'wrong'
          AND study_history.review_date IS NOT NULL
          AND study_history.review_date <= ?
        ORDER BY study_history.review_date ASC
    """, (
        user_id,
        today
    ))

    rows = cursor.fetchall()

    conn.close()

    return rows

def get_lesson_progress(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            q.lesson,
            COUNT(q.id) AS total_questions,

            SUM(
                CASE
                    WHEN latest.result = 'correct' THEN 1
                    ELSE 0
                END
            ) AS mastered,

            SUM(
                CASE
                    WHEN latest.result = 'wrong' THEN 1
                    ELSE 0
                END
            ) AS needs_review,

            SUM(
                CASE
                    WHEN latest.result IS NULL THEN 1
                    ELSE 0
                END
            ) AS not_studied

        FROM questions AS q

        LEFT JOIN (
            SELECT sh1.question_id, sh1.result
            FROM study_history AS sh1
            WHERE sh1.user_id = ?
              AND sh1.id = (
                  SELECT MAX(sh2.id)
                  FROM study_history AS sh2
                  WHERE sh2.user_id = sh1.user_id
                    AND sh2.question_id = sh1.question_id
              )
        ) AS latest
            ON q.id = latest.question_id

        GROUP BY q.lesson
        ORDER BY q.lesson
    """, (user_id,))

    rows = cursor.fetchall()

    conn.close()

    # 達成率を計算
    progress = []

    for row in rows:
        lesson = row[0]
        total = row[1]
        mastered = row[2] or 0
        needs_review = row[3] or 0
        not_studied = row[4] or 0

        if total > 0:
            progress_percent = int((mastered / total) * 100)
        else:
            progress_percent = 0

        progress.append({
            "lesson": lesson,
            "total": total,
            "mastered": mastered,
            "needs_review": needs_review,
            "not_studied": not_studied,
            "progress_percent": progress_percent
        })

    return progress
